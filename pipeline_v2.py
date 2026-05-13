#!/usr/bin/env python3
"""
Pipeline v2 - Face Swap + Lip Sync + Karaoke
Improved version with better face tracking, karaoke overlay, and lip sync.
"""

import argparse
import json
import logging
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PipelineV2")

PROJECT_ROOT = Path(__file__).resolve().parent
TEMP_DIR = PROJECT_ROOT / "temp"
OUTPUT_DIR = PROJECT_ROOT / "output" / "videos"
BACKEND_DIR = PROJECT_ROOT / "backend"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_duration(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=15,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def extract_amplitude(audio_path: str, fps: int, smooth: int = 3) -> np.ndarray:
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", str(fps), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    amp = np.abs(np.frombuffer(r.stdout, dtype=np.float32))
    amp = np.convolve(amp, np.ones(smooth) / smooth, mode="same")
    peak = float(np.percentile(amp, 97)) or 1.0
    amp = np.clip(amp / peak, 0, 1)
    amp[amp < 0.06] = 0
    return amp


from PIL import ImageFont, ImageDraw, Image as PILImage


FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
try:
    FONT_TITLE = ImageFont.truetype(FONT_PATH, 52)
    FONT_ARTIST = ImageFont.truetype(FONT_PATH, 32)
    FONT_PROGRESS = ImageFont.truetype(FONT_PATH, 24)
except Exception:
    FONT_TITLE = FONT_ARTIST = FONT_PROGRESS = None


class PipelineV2:
    def __init__(self, image: str, video: str, audio: str, output: str = None, fast: bool = False):
        self.image_path = Path(image)
        self.video_path = Path(video)
        self.audio_path = Path(audio)
        self.output_path = output or str(OUTPUT_DIR / f"{Path(audio).stem}.mp4")
        self.fast = fast
        self.swapper = None
        self.app = None

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        if not fast:
            self._init_insightface()

    def _init_insightface(self):
        try:
            import insightface
            from insightface.app import FaceAnalysis
            from insightface.model_zoo import get_model
            self.app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            self.app.prepare(ctx_id=0, det_size=(320, 320))
            self.swapper = get_model("inswapper_128.onnx", download=True, providers=["CPUExecutionProvider"])
            logger.info("InsightFace initialized")
        except Exception as e:
            logger.warning(f"InsightFace init failed: {e}")
            self.swapper = None

    def ready(self) -> bool:
        return self.swapper is not None

    def run(self):
        start_time = time.time()
        logger.info("=" * 50)
        logger.info(f"Pipeline V2 Started")
        logger.info(f"  Image : {self.image_path}")
        logger.info(f"  Video : {self.video_path}")
        logger.info(f"  Audio : {self.audio_path}")
        logger.info(f"  Output: {self.output_path}")
        logger.info(f"  Mode  : {'FAST' if self.fast else 'FULL'}")
        logger.info("=" * 50)

        for p in [self.image_path, self.video_path, self.audio_path]:
            if not p.exists():
                logger.error(f"File not found: {p}")
                return None

        src_img = cv2.imread(str(self.image_path))
        if src_img is None:
            logger.error(f"Cannot read image: {self.image_path}")
            return None

        src_face = None
        if self.swapper:
            faces = self.app.get(src_img)
            if faces:
                src_face = faces[0]
                logger.info(f"Source face: {src_face.bbox}")
            else:
                logger.warning("No face detected in source image")

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            logger.error(f"Cannot open video: {self.video_path}")
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        audio_dur = get_duration(str(self.audio_path))
        target = min(total_frames, int(audio_dur * fps))

        logger.info(f"  {width}x{height} @ {fps:.2f}fps  {target}/{total_frames} frames")

        amp = extract_amplitude(str(self.audio_path), int(fps), smooth=3)
        if len(amp) < target:
            amp = np.pad(amp, (0, target - len(amp)), "edge")
        amp = amp[:target]

        smooth_amp = np.convolve(amp, np.ones(3)/3, mode='same')
        smooth_amp = np.clip(smooth_amp, 0, 1)

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

        cached_bbox = None
        cached_det = None
        DETECT_INTERVAL = 10

        raw_path = str(TEMP_DIR / "frames.raw")
        raw_fd = open(raw_path, "wb")

        frame_count = 0
        face_swap_count = 0
        haar_count = 0

        for i in range(target):
            ret, frame = cap.read()
            if not ret:
                break

            current_bbox = None

            if self.swapper and src_face and not self.fast:
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
                        face_swap_count += 1
                elif cached_det is not None:
                    frame = self.swapper.get(frame, cached_det, src_face, paste_back=True)
                    face_swap_count += 1
                    current_bbox = cached_bbox

            if current_bbox is None and face_cascade is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                haar_faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
                if len(haar_faces) > 0:
                    fx, fy, fw, fh = haar_faces[0]
                    current_bbox = np.array([fx, fy, fx + fw, fy + fh], dtype=np.float64)
                    cached_bbox = current_bbox
                    haar_count += 1
                elif cached_bbox is not None:
                    current_bbox = cached_bbox

            openness = max(0.0, min(1.0, float(smooth_amp[i]) * 2.4))
            prev_openness = float(smooth_amp[max(0, i-1)]) * 2.4 if i > 0 else openness

            bbox_to_use = current_bbox if current_bbox is not None else cached_bbox
            if bbox_to_use is not None:
                frame = self._draw_mouth(frame, openness, bbox_to_use, prev_openness)

            pil_img = PILImage.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
            draw = ImageDraw.Draw(pil_img, "RGBA")

            if FONT_TITLE:
                overlay_top = PILImage.new("RGBA", pil_img.size, (0, 0, 0, 0))
                d_top = ImageDraw.Draw(overlay_top)

                d_top.text((pil_img.width // 2, 60), "ຄົນດີທີ່ເຈົ້າບໍ່ຮັກ",
                           fill=(255, 255, 255, 230), font=FONT_TITLE, anchor="mt")

                d_top.text((pil_img.width // 2, 120), "Voradeth Ditthavong",
                           fill=(200, 200, 200, 180), font=FONT_ARTIST, anchor="mt")

                pct = i / target * 100 if target > 0 else 0
                bar_w = 600
                bar_h = 6
                bar_x = (pil_img.width - bar_w) // 2
                bar_y = pil_img.height - 50
                fill_w = int(bar_w * pct / 100)
                d_top.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                                fill=(255, 255, 255, 60))
                d_top.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h],
                                fill=(255, 200, 0, 200))

                amp_bar = int(smooth_amp[i] * bar_w * 0.8)
                vibe_y = pil_img.height - 80
                d_top.rectangle([bar_x, vibe_y, bar_x + amp_bar, vibe_y + bar_h * 2],
                                fill=(255, 100, 50, 180))
                d_top.text((pil_img.width // 2, vibe_y - 8), f"♪ {'▓' * max(1, int(smooth_amp[i] * 15))}",
                           fill=(255, 255, 100, 200), font=FONT_PROGRESS, anchor="mb")

                d_top.text((pil_img.width // 2, bar_y + 15), f"{pct:.0f}%",
                           fill=(200, 200, 200, 150), font=FONT_PROGRESS, anchor="mt")

                pil_img = PILImage.alpha_composite(pil_img, overlay_top)

            frame = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
            raw_fd.write(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes())
            frame_count += 1

            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                rate = frame_count / elapsed if elapsed > 0 else 0
                eta = (target - frame_count) / rate if rate > 0 else 0
                logger.info(f"  {frame_count}/{target} frames  ({elapsed:.0f}s, {rate:.1f}fps, ETA {eta:.0f}s)")

        cap.release()
        raw_fd.close()

        logger.info(f"Encoding with ffmpeg...")
        enc_start = time.time()
        enc_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{width}x{height}", "-framerate", str(fps),
            "-i", raw_path,
            "-i", str(self.audio_path),
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest",
            self.output_path,
        ]
        result = subprocess.run(enc_cmd, check=False, timeout=600, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg stderr:\n{result.stderr[:2000]}")
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}")
        logger.info(f"Encoding done in {time.time() - enc_start:.0f}s")

        try:
            os.remove(raw_path)
        except OSError:
            pass

        total_time = time.time() - start_time
        mb = os.path.getsize(self.output_path) / 1_048_576 if os.path.exists(self.output_path) else 0
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Done! {total_time:.0f}s, {mb:.1f}MB")
        logger.info(f"  Frames: {frame_count}")
        logger.info(f"  Face swaps: {face_swap_count}")
        logger.info(f"  Haar detections: {haar_count}")
        logger.info(f"  Output: {self.output_path}")
        logger.info(f"{'=' * 50}")

        return self.output_path if os.path.exists(self.output_path) else None

    @staticmethod
    def _draw_mouth(frame: np.ndarray, openness: float, face_box: np.ndarray,
                    prev_openness: float = 0) -> np.ndarray:
        x1, y1, x2, y2 = face_box.astype(int)
        face_w = x2 - x1
        face_h = y2 - y1
        face_cx = (x1 + x2) // 2
        face_cy = int(y1 + face_h * 0.78)

        open_factor = min(1.0, openness * 1.6)

        if prev_openness > 0.3 and openness < 0.1:
            open_factor = max(open_factor, 0.15)

        mouth_w_ratio = 0.26 + open_factor * 0.10
        mouth_h_ratio = 0.02 + open_factor * 0.14

        mw = max(18, int(face_w * mouth_w_ratio))
        mh = max(2, int(face_h * mouth_h_ratio))

        lip_color = (40, 50, 150)
        inner_color = (6, 3, 20)
        tooth_color = (190, 200, 215)

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

            if open_factor > 0.12 and local_open < 0.45:
                tooth_blend = min(1.0, (open_factor - 0.12) * 4)
                color = tuple(
                    int(tooth_color[c] * tooth_blend + inner_color[c] * (1 - tooth_blend))
                    for c in range(3)
                )
            elif open_factor > 0.04:
                lip_blend = 1.0 - abs(open_factor - 0.08) * 6
                lip_blend = max(0.15, min(1.0, lip_blend))
                color = tuple(
                    int(lip_color[c] * lip_blend + inner_color[c] * (1 - lip_blend))
                    for c in range(3)
                )
            else:
                color = lip_color

            frame[y, row_x_start:row_x_end] = color

        return frame


def main():
    parser = argparse.ArgumentParser(description="Pipeline V2 - Face Swap + Lip Sync + Karaoke")
    parser.add_argument("--image", default="input/input.jpeg")
    parser.add_argument("--video", default="input/videoinput.mp4")
    parser.add_argument("--audio", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--fast", action="store_true", help="Skip face swap")
    parser.add_argument("--trim", type=float, default=0, help="Trim audio to N seconds")
    args = parser.parse_args()

    audio = args.audio
    if not audio:
        from pathlib import Path
        audios = sorted(Path("input").glob("*.mp3"))
        if audios:
            audio = str(audios[0])
            logger.info(f"Auto-selected audio: {audio}")

    if args.trim > 0:
        trimmed = str(TEMP_DIR / "trimmed_audio.mp3")
        subprocess.run(["ffmpeg", "-y", "-i", audio, "-t", str(args.trim), "-acodec", "copy", trimmed],
                       capture_output=True, timeout=60)
        audio = trimmed
        logger.info(f"Trimmed audio to {args.trim}s: {audio}")

    pipeline = PipelineV2(image=args.image, video=args.video, audio=audio,
                          output=args.output, fast=args.fast)
    result = pipeline.run()
    if result:
        logger.info(f"\nSuccess! Open your video at:\n  {result}")
    else:
        logger.error("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
