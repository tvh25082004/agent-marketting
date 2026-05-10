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
    """Face-swap + synthetic lip-sync pipeline using InsightFace + OpenCV."""

    def __init__(self):
        self.swapper = None
        self.app = None
        self._init_insightface()

    def _init_insightface(self):
        try:
            import insightface
            from insightface.app import FaceAnalysis
            from insightface.model_zoo import get_model

            self.app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            self.app.prepare(ctx_id=0, det_size=(640, 640))

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
            return "InsightFace failed to initialize (try: pip install insightface onnxruntime)"
        return ""

    # ── helpers ──────────────────────────────────────────────────────────

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
    def _extract_amplitude(audio_path: str, fps: int) -> np.ndarray:
        cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", str(fps), "-f", "f32le", "-"]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        amp = np.abs(np.frombuffer(r.stdout, dtype=np.float32))
        amp = np.convolve(amp, np.ones(5) / 5, mode="same")
        peak = float(np.percentile(amp, 95)) or 1.0
        return np.clip(amp / peak, 0, 1)

    @staticmethod
    def _draw_synthetic_mouth(frame: np.ndarray, openness: float, face_box: np.ndarray) -> np.ndarray:
        x1, y1, x2, y2 = face_box.astype(int)
        face_cx = (x1 + x2) // 2
        face_cy = int(y1 + (y2 - y1) * 0.78)

        mw = int(70 + 55 * openness)
        mh = int(3 + 38 * openness)
        lip_r, lip_g, lip_b = 175, 70, 85
        inner_r, inner_g, inner_b = 28, 5, 8
        H, W = frame.shape[:2]

        for dy in range(-mh // 2, mh // 2 + 1):
            ratio = 2 * dy / max(mh, 1)
            half_w = 0 if abs(ratio) >= 1 else int(mw / 2 * math.sqrt(1 - ratio ** 2))
            local_open = abs(dy) / (mh / 2) if mh > 0 else 1

            for dx in range(-half_w, half_w + 1):
                px, py = face_cx + dx, face_cy + dy
                if not (0 <= px < W and 0 <= py < H):
                    continue

                if local_open < 0.18:
                    r = min(255, int(lip_r * (1 - local_open * 3) + 238 * local_open * 3))
                    g = min(255, int(lip_g * (1 - local_open * 3) + 200 * local_open * 3))
                    b = min(255, int(lip_b * (1 - local_open * 3) + 170 * local_open * 3))
                    frame[py, px] = [b, g, r]
                elif local_open < 0.3 and openness > 0.3:
                    if abs(dx) < half_w * 0.6 and dy < 0:
                        tk = min(1.0, (0.6 + 0.3 * openness) * 1.5)
                        frame[py, px] = [min(255, int(225 * tk + inner_b * (1 - tk))),
                                          min(255, int(235 * tk + inner_g * (1 - tk))),
                                          min(255, int(240 * tk + inner_r * (1 - tk)))]
                    else:
                        frame[py, px] = [inner_b, inner_g, inner_r]
                else:
                    frame[py, px] = [inner_b, inner_g, inner_r]

        return frame

    # ── public API ───────────────────────────────────────────────────────

    def generate(
        self,
        source_image: str,
        reference_video: str,
        audio_path: str,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        if output_path is None:
            stem = f"motion_{int(time.time())}"
            output_path = os.path.join(settings.video_output_dir, f"{stem}.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        for p in [source_image, reference_video, audio_path]:
            if not os.path.exists(p):
                logger.error(f"File not found: {p}")
                return None

        return self._run_pipeline(source_image, reference_video, audio_path, output_path)

    def _run_pipeline(
        self, source_image: str, reference_video: str,
        audio_path: str, output_path: str,
    ) -> Optional[str]:
        start = time.time()
        logger.info("[VideoMotion] Starting face-swap + lip-sync pipeline")

        # 1. Load source face
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

        # 2. Open reference video
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

        # 3. Audio amplitude → per-frame openness
        amp = self._extract_amplitude(audio_path, int(fps))
        if len(amp) < target:
            amp = np.pad(amp, (0, target - len(amp)), "edge")
        amp = amp[:target]

        # 4. Process frames
        raw_path = os.path.join(settings.temp_dir, f"motion_{int(time.time())}.rgb")
        count = 0

        with open(raw_path, "wb") as fp:
            for i in range(target):
                ret, frame = cap.read()
                if not ret:
                    break

                # 4. Detect face once per frame, use for both swap and mouth
                dets = self.app.get(frame) if self.swapper else []

                # 4a. Face swap
                if self.swapper and src_face:
                    for det in dets:
                        frame = self.swapper.get(frame, det, src_face, paste_back=True)

                # 4b. Synthetic lip-sync on the largest face
                openness = max(0.05, min(1.0, float(amp[i]) * 2.5))
                if dets:
                    biggest = max(dets, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                    frame = self._draw_synthetic_mouth(frame, openness, biggest.bbox)

                fp.write(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes())
                count += 1

                if count % 100 == 0:
                    logger.info(f"  {count}/{target} frames")

        cap.release()

        if count == 0:
            logger.error("No frames processed")
            return None

        # 5. Encode
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "rawvideo", "-pixel_format", "rgb24",
            "-video_size", f"{width}x{height}", "-framerate", str(fps),
            "-i", raw_path,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", output_path,
        ], capture_output=True, timeout=900)

        try:
            os.remove(raw_path)
        except OSError:
            pass

        elapsed = time.time() - start
        mb = os.path.getsize(output_path) / 1_048_576 if os.path.exists(output_path) else 0
        logger.info(f"[VideoMotion] Done: {output_path} ({count} frames, {mb:.1f}MB, {elapsed:.0f}s)")
        return output_path if os.path.exists(output_path) else None
