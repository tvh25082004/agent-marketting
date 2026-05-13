import json
import logging
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from ..config import settings

logger = logging.getLogger(__name__)


class VideoMotionTool:
    """Face-swap + synthetic lip-sync pipeline using InsightFace + OpenCV.
    
    On Mac M3, runs with CPUExecutionProvider for InsightFace.
    Lip sync uses amplitude-based synthetic mouth animation.
    """

    def __init__(self, skip_swap: bool = False):
        self.swapper = None
        self.app = None
        self.skip_swap = skip_swap
        if not skip_swap:
            self._init_insightface()

    def _init_insightface(self):
        try:
            import insightface
            from insightface.app import FaceAnalysis
            from insightface.model_zoo import get_model

            self.app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            self.app.prepare(ctx_id=0, det_size=(320, 320))

            self.swapper = get_model(
                "inswapper_128.onnx", download=True, providers=["CPUExecutionProvider"]
            )
            logger.info("InsightFace initialized (swapper + buffalo_l detector)")
        except Exception as e:
            logger.warning(f"InsightFace init failed: {e}")
            self.swapper = None

    def ready(self) -> bool:
        return self.swapper is not None

    def readiness_error(self) -> str:
        if not self.swapper:
            return "InsightFace failed to initialize"
        return ""

    @staticmethod
    def _get_duration(path: str) -> float:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                capture_output=True, text=True, timeout=15,
            )
            return float(json.loads(r.stdout)["format"]["duration"])
        except Exception:
            return 0.0

    @staticmethod
    def _extract_amplitude(audio_path: str, fps: int, smooth: int = 3) -> np.ndarray:
        cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", str(fps), "-f", "f32le", "-"]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        amp = np.abs(np.frombuffer(r.stdout, dtype=np.float32))
        amp = np.convolve(amp, np.ones(smooth) / smooth, mode="same")
        peak = float(np.percentile(amp, 97)) or 1.0
        amp = np.clip(amp / peak, 0, 1)
        threshold = 0.08
        amp[amp < threshold] = 0
        return amp

    def generate(
        self,
        source_image: str,
        reference_video: str,
        audio_path: str,
        output_path: Optional[str] = None,
        lyrics: Optional[str] = None,
        trim_audio: bool = True,
        audio_duration: float = 20.0,
    ) -> Optional[str]:
        if output_path is None:
            stem = f"motion_{int(time.time())}"
            output_path = os.path.join(settings.video_output_dir, f"{stem}.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        for p in [source_image, reference_video, audio_path]:
            if not os.path.exists(p):
                logger.error(f"File not found: {p}")
                return None

        # Trim audio if requested
        processed_audio = audio_path
        if trim_audio:
            from .audio_trim import AudioTrimmer
            trimmer = AudioTrimmer()
            temp_audio = os.path.join(settings.temp_dir, f"trimmed_{int(time.time())}.aac")
            try:
                processed_audio = trimmer.trim_audio(
                    audio_path, temp_audio, duration=audio_duration, auto_detect_intro=True
                )
                logger.info(f"Audio trimmed to {audio_duration}s")
            except Exception as e:
                logger.warning(f"Audio trimming failed: {e}, using original")
                processed_audio = audio_path

        # Generate lyrics subtitle if provided
        subtitle_path = None
        if lyrics:
            from .lyrics_overlay import LyricsOverlay
            overlay = LyricsOverlay()
            subtitle_path = os.path.join(settings.temp_dir, f"lyrics_{int(time.time())}.ass")
            try:
                audio_dur = self._get_duration(processed_audio)
                subtitle_path = overlay.create_ass_subtitle(lyrics, subtitle_path, audio_dur, style="karaoke")
                logger.info(f"Lyrics subtitle created: {subtitle_path}")
            except Exception as e:
                logger.warning(f"Lyrics generation failed: {e}")
                subtitle_path = None

        return self._run_pipeline(source_image, reference_video, processed_audio, output_path, subtitle_path)

    def _run_pipeline(
        self, source_image: str, reference_video: str,
        audio_path: str, output_path: str, subtitle_path: Optional[str] = None,
    ) -> Optional[str]:
        start = time.time()
        logger.info("[VideoMotion] Starting face-swap + lip-sync pipeline")

        src_img = cv2.imread(source_image)
        if src_img is None:
            logger.error(f"Cannot read source image: {source_image}")
            return None

        src_face = None
        if self.swapper:
            faces = self.app.get(src_img)
            if faces:
                src_face = faces[0]
                logger.info(f"Source face: {src_face.bbox}")
            else:
                logger.warning("No face detected in source image")

        cap = cv2.VideoCapture(reference_video)
        if not cap.isOpened():
            logger.error(f"Cannot open reference video: {reference_video}")
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        audio_dur = self._get_duration(audio_path)
        target = min(total, int(audio_dur * fps))

        logger.info(f"  {width}x{height} @ {fps:.2f}fps  {target}/{total} frames")

        amp = self._extract_amplitude(audio_path, int(fps), smooth=3)
        if len(amp) < target:
            amp = np.pad(amp, (0, target - len(amp)), "edge")
        amp = amp[:target]

        smooth_amp = np.convolve(amp, np.ones(3)/3, mode='same')
        smooth_amp = np.clip(smooth_amp, 0, 1)

        count = 0

        # Haar cascade for fast face detection (used for lip sync positioning)
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
        except Exception:
            face_cascade = None

        cached_bbox = None
        cached_det = None
        DETECT_INTERVAL = 30

        # Pipe frames directly to FFmpeg to avoid disk space issues
        # Use temp video if subtitles are needed, otherwise output directly
        if subtitle_path and os.path.exists(subtitle_path):
            temp_video = os.path.join(settings.temp_dir, f"temp_video_{int(time.time())}.mp4")
            final_output = temp_video
        else:
            temp_video = None
            final_output = output_path
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{width}x{height}", "-framerate", str(fps),
            "-i", "-",
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", final_output,
        ]
        
        ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        for i in range(target):
            ret, frame = cap.read()
            if not ret:
                break

            current_bbox = None

            # Face swap with InsightFace (when available and not skipped)
            if self.swapper and src_face and not self.skip_swap:
                if i % DETECT_INTERVAL == 0 or cached_bbox is None:
                    dets = self.app.get(frame)
                    if dets:
                        biggest = max(dets, key=lambda f:
                            (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                        cached_bbox = biggest.bbox
                        cached_det = biggest
                        for det in dets:
                            frame = self.swapper.get(frame, det, src_face, paste_back=True)
                        current_bbox = cached_bbox
                elif cached_det is not None:
                    frame = self.swapper.get(frame, cached_det, src_face, paste_back=True)
                    current_bbox = cached_bbox

            # Fast face detection for lip sync position (always runs)
            if current_bbox is None and face_cascade is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                haar_faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
                if len(haar_faces) > 0:
                    fx, fy, fw, fh = haar_faces[0]
                    current_bbox = np.array([fx, fy, fx + fw, fy + fh], dtype=np.float64)
                elif cached_bbox is not None:
                    current_bbox = cached_bbox

            openness = max(0.0, min(1.0, float(smooth_amp[i]) * 2.2))
            if current_bbox is not None:
                frame = self._draw_improved_mouth(frame, openness, current_bbox, None,
                    prev_openness=float(smooth_amp[max(0, i-1)]) * 2.2 if i > 0 else openness,
                )
            elif cached_bbox is not None:
                frame = self._draw_improved_mouth(frame, openness, cached_bbox, None,
                    prev_openness=float(smooth_amp[max(0, i-1)]) * 2.2 if i > 0 else openness,
                )

            ffmpeg_proc.stdin.write(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes())
            count += 1

            if count % 100 == 0:
                elapsed_so_far = time.time() - start
                fps_rate = count / elapsed_so_far if elapsed_so_far > 0 else 0
                eta = (target - count) / fps_rate if fps_rate > 0 else 0
                logger.info(f"  {count}/{target} frames  ({elapsed_so_far:.0f}s, {fps_rate:.1f}fps, ETA {eta:.0f}s)")

        cap.release()
        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait(timeout=300)

        # Second pass: add subtitles if needed
        if temp_video and os.path.exists(temp_video):
            logger.info("Adding subtitle overlay...")
            # Properly escape path for FFmpeg subtitles filter
            # Replace backslashes and escape special characters
            sub_path_escaped = subtitle_path.replace("\\", "\\\\").replace(":", "\\:")
            subtitle_cmd = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-vf", f"subtitles='{sub_path_escaped}'",
                "-c:a", "copy",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                output_path,
            ]
            result = subprocess.run(subtitle_cmd, capture_output=True, timeout=300, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Subtitle overlay failed, trying alternative method...")
                # Alternative: use ass filter directly
                subtitle_cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_video,
                    "-vf", f"ass={subtitle_path}",
                    "-c:a", "copy",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    output_path,
                ]
                result = subprocess.run(subtitle_cmd, capture_output=True, timeout=300, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Both subtitle methods failed, using video without subtitles")
                    # Fallback: use video without subtitles
                    import shutil
                    shutil.move(temp_video, output_path)
                else:
                    # Clean up temp video
                    try:
                        os.remove(temp_video)
                    except OSError:
                        pass
            else:
                # Clean up temp video
                try:
                    os.remove(temp_video)
                except OSError:
                    pass

        elapsed = time.time() - start
        mb = os.path.getsize(output_path) / 1_048_576 if os.path.exists(output_path) else 0
        logger.info(f"[VideoMotion] Done: {output_path} ({count} frames, {mb:.1f}MB, {elapsed:.0f}s)")
        return output_path if os.path.exists(output_path) else None

    @staticmethod
    def _draw_improved_mouth(
        frame: np.ndarray,
        openness: float,
        face_box: np.ndarray,
        landmarks: Optional[np.ndarray] = None,
        prev_openness: float = 0,
    ) -> np.ndarray:
        x1, y1, x2, y2 = face_box.astype(int)
        face_w = x2 - x1
        face_h = y2 - y1
        face_cx = (x1 + x2) // 2
        face_cy = int(y1 + face_h * 0.78)

        if landmarks is not None and len(landmarks) >= 5:
            mouth_top = landmarks[1] if len(landmarks) > 1 else None
            mouth_bottom = landmarks[3] if len(landmarks) > 3 else None
            if mouth_top is not None and mouth_bottom is not None:
                face_cy = int((mouth_top[1] + mouth_bottom[1]) / 2)
                face_cx = int((mouth_top[0] + mouth_bottom[0]) / 2)

        open_factor = min(1.0, openness * 1.8)
        mouth_w_ratio = 0.28 + open_factor * 0.08
        mouth_h_ratio = 0.03 + open_factor * 0.12

        mw = max(20, int(face_w * mouth_w_ratio))
        mh = max(2, int(face_h * mouth_h_ratio))

        lip_color = (50, 60, 160)
        inner_color = (8, 5, 25)
        tooth_color = (200, 210, 225)

        H, W = frame.shape[:2]
        x_start = max(0, face_cx - mw // 2)
        x_end = min(W, face_cx + mw // 2)
        y_start = max(0, face_cy - mh // 2)
        y_end = min(H, face_cy + mh // 2)

        for y in range(y_start, y_end):
            dy = (y - face_cy) / (mh / 2) if mh > 0 else 1
            if abs(dy) >= 1:
                continue
            half_w = int(mw / 2 * math.sqrt(1 - dy * dy))
            row_x_start = max(0, face_cx - half_w)
            row_x_end = min(W, face_cx + half_w)

            local_open = abs(dy)

            if open_factor > 0.15 and local_open < 0.5:
                tooth_blend = min(1.0, (open_factor - 0.15) * 3)
                color = tuple(
                    int(tooth_color[c] * tooth_blend + inner_color[c] * (1 - tooth_blend))
                    for c in range(3)
                )
            elif open_factor > 0.05:
                lip_blend = 1.0 - abs(open_factor - 0.1) * 5
                lip_blend = max(0.2, min(1.0, lip_blend))
                color = tuple(
                    int(lip_color[c] * lip_blend + inner_color[c] * (1 - lip_blend))
                    for c in range(3)
                )
            else:
                color = lip_color

            frame[y, row_x_start:row_x_end] = color

        return frame
