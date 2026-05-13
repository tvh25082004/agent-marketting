#!/usr/bin/env python3
"""
Pipeline v3 - Face Swap + Subtitle Removal + Lip Sync + Karaoke
- Face swap using InsightFace (only biggest face, no multi-face flicker)
- Remove old hardcoded subtitles (median blur, no inpainting artifacts)
- Lip sync: landmark-based mouth warping matching audio amplitude (per-frame detection for accuracy)
- Karaoke overlay (title, artist, progress, music visualizer) - numpy-fast
- High quality encoding (CRF 18)
"""

import cv2
import json
import logging
import numpy as np
import os
import subprocess
import sys
import time
from pathlib import Path
from PIL import ImageFont, ImageDraw, Image as PILImage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("PipelineV3")

PROJECT_ROOT = Path(__file__).resolve().parent
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT_L = ImageFont.truetype(FONT_PATH, 56) if os.path.exists(FONT_PATH) else None
FONT_M = ImageFont.truetype(FONT_PATH, 32) if os.path.exists(FONT_PATH) else None
FONT_S = ImageFont.truetype(FONT_PATH, 22) if os.path.exists(FONT_PATH) else None

SUB_Y1 = 1344
SUB_Y2 = 1600

UPPER_INNER_LIP = [61, 62, 63]
LOWER_INNER_LIP = [65, 66, 67]
MOUTH_ALL = list(range(48, 68))


def get_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                          capture_output=True, text=True, timeout=15)
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def extract_amplitude(audio_path, fps, smooth=3):
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", str(fps), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    amp = np.abs(np.frombuffer(r.stdout, dtype=np.float32))
    amp = np.convolve(amp, np.ones(smooth)/smooth, mode="same")
    peak = float(np.percentile(amp, 97)) or 1.0
    amp = np.clip(amp / peak, 0, 1)
    amp[amp < 0.05] = 0
    return amp


def remove_subtitles(frame):
    sub = frame[SUB_Y1:SUB_Y2, :, :]
    frame[SUB_Y1:SUB_Y2, :, :] = cv2.medianBlur(sub, 9)
    return frame


def compute_mouth_openness(lm68):
    upper = np.mean([lm68[i][1] for i in UPPER_INNER_LIP])
    lower = np.mean([lm68[i][1] for i in LOWER_INNER_LIP])
    return max(0, lower - upper)


def compute_mouth_bbox(lm68, margin=1.8):
    pts = np.array([lm68[i][:2] for i in MOUTH_ALL])
    x_min, x_max = pts[:, 0].min(), pts[:, 0].max()
    y_min, y_max = pts[:, 1].min(), pts[:, 1].max()
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
    w = (x_max - x_min) * margin
    h = (y_max - y_min) * margin
    return int(cx - w/2), int(cy - h/2), int(cx + w/2), int(cy + h/2)


def warp_mouth(frame, lm68, target_open, current_open, strength=1.0):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = compute_mouth_bbox(lm68, 1.8)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1 or current_open < 1:
        return frame

    scale = (target_open / current_open)
    scale = max(0.3, min(2.5, scale))
    scale = scale * strength + 1.0 * (1 - strength)
    if abs(scale - 1.0) < 0.05:
        return frame

    roi = frame[y1:y2, x1:x2].copy()
    roi_h, roi_w = roi.shape[:2]
    cy = int(lm68[62][1] - y1)

    ys, xs = np.mgrid[0:roi_h, 0:roi_w]
    ys_norm = (ys - cy) / max(roi_h, 1)
    ys_new = np.clip(cy + ys_norm * (roi_h * scale), 0, roi_h - 1)

    warped = cv2.remap(roi, xs.astype(np.float32), ys_new.astype(np.float32),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    mask = np.zeros((roi_h, roi_w), dtype=np.float32)
    mpts = np.array([lm68[i][:2] for i in MOUTH_ALL], dtype=np.int32)
    mpts[:, 0] -= x1
    mpts[:, 1] -= y1
    cv2.fillConvexPoly(mask, mpts, 1.0)
    ks = max(5, min(roi_h, roi_w)//12 * 2 + 1)
    mask = cv2.GaussianBlur(mask, (ks, ks), 0)
    mask = np.clip(mask, 0, 1)

    m3 = np.dstack([mask]*3)
    frame[y1:y2, x1:x2] = (roi * (1 - m3) + warped * m3).astype(np.uint8)
    return frame


def sharpen_face(frame, bbox, strength=0.5):
    """Sharpen face region to compensate for inswapper's low-res blur."""
    x1, y1, x2, y2 = bbox.astype(int)
    x1, y1 = max(0, x1), max(0, y1)
    x2 = min(frame.shape[1], x2)
    y2 = min(frame.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return frame
    face = frame[y1:y2, x1:x2]
    blurred = cv2.GaussianBlur(face, (0, 0), 3)
    sharpened = cv2.addWeighted(face, 1.0 + strength, blurred, -strength, 0)
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
    frame[y1:y2, x1:x2] = sharpened
    return frame


def create_text_overlay(W, H):
    overlay = PILImage.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if FONT_L:
        title = "ຄົນດີທີ່ເຈົ້າບໍ່ຮັກ"
        bbox = draw.textbbox((0, 0), title, font=FONT_L)
        tw = bbox[2] - bbox[0]
        draw.text((W//2 - tw//2 + 2, 52), title, fill=(0, 0, 0, 180), font=FONT_L)
        draw.text((W//2 - tw//2, 50), title, fill=(255, 255, 255, 240), font=FONT_L)
    if FONT_M:
        artist = "Voradeth Ditthavong"
        bbox = draw.textbbox((0, 0), artist, font=FONT_M)
        tw = bbox[2] - bbox[0]
        draw.text((W//2 - tw//2 + 1, 112), artist, fill=(0, 0, 0, 120), font=FONT_M)
        draw.text((W//2 - tw//2, 110), artist, fill=(220, 220, 220, 200), font=FONT_M)
    return overlay


def apply_overlay(frame, text_pil, amp_val, pct):
    H, W = frame.shape[:2]
    overlay = frame.copy()
    overlay[:150, :] = (30, 30, 30)
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

    if text_pil is not None:
        text_np = np.array(text_pil)
        alpha = text_np[:, :, 3:4].astype(np.float32) / 255.0
        rgb = text_np[:, :, :3].astype(np.float32)
        frame[:] = (frame.astype(np.float32) * (1 - alpha) + rgb * alpha).astype(np.uint8)

    bar_w = min(700, W - 60)
    bar_x = (W - bar_w) // 2
    bar_y = H - 60
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 8), (80, 80, 80), -1)
    fill_w = int(bar_w * pct / 100)
    if fill_w > 0:
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + 8), (50, 200, 255), -1)

    vibe_y = H - 90
    amp_w = max(2, int(bar_w * amp_val * 0.7))
    r = min(255, 100 + int(amp_val * 155))
    g = min(255, 50 + int(amp_val * 100))
    cv2.rectangle(frame, (bar_x, vibe_y), (bar_x + amp_w, vibe_y + 16), (r, g, 30), -1)
    return frame


def main():
    image_path = str(PROJECT_ROOT / "input/input.jpeg")
    video_path = str(PROJECT_ROOT / "input/videoinput.mp4")
    audio_path = str(PROJECT_ROOT / "output/audio/climax_20s.mp3")
    output_path = str(PROJECT_ROOT / "output/videos/final_video_v3.mp4")

    logger.info("=" * 50)
    logger.info("PIPELINE V3 - Face Swap + Sub Removal + Lip Sync + Karaoke")
    logger.info("=" * 50)

    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model

    logger.info("Initializing InsightFace...")
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(320, 320))
    swapper = get_model("inswapper_128.onnx", download=True,
                        providers=["CoreMLExecutionProvider", "CPUExecutionProvider"])

    src_img = cv2.imread(image_path)
    src_faces = app.get(src_img)
    if not src_faces:
        logger.error("No face in source image!")
        sys.exit(1)
    src_face = src_faces[0]
    logger.info(f"Source face: {src_face.bbox}")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    audio_dur = get_duration(audio_path)
    target = min(total, int(audio_dur * fps))
    logger.info(f"Video: {width}x{height} @ {fps:.2f}fps, {target}/{total} frames, audio={audio_dur:.1f}s")

    amp = extract_amplitude(audio_path, int(fps), smooth=3)
    if len(amp) < target:
        amp = np.pad(amp, (0, target - len(amp)), "edge")
    amp = amp[:target]
    smooth_amp = np.clip(np.convolve(amp, np.ones(5)/5, mode='same'), 0, 1)

    text_overlay = create_text_overlay(width, height)

    raw_path = str(TEMP_DIR / "final_v3.raw")
    raw_fd = open(raw_path, "wb")

    start = time.time()
    biggest_det = None
    frame_count = 0
    min_open = 2.0
    max_open = 35.0

    for i in range(target):
        ret, frame = cap.read()
        if not ret:
            break

        frame = remove_subtitles(frame)

        # Face swap - only swap the BIGGEST face (no multi-face flicker)
        dets = app.get(frame)
        if dets:
            biggest_det = max(dets, key=lambda f:
                (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            frame = swapper.get(frame, biggest_det, src_face, paste_back=True)
            frame = sharpen_face(frame, biggest_det.bbox, strength=0.4)

        # Lip sync using fresh landmarks from current frame
        if biggest_det is not None and hasattr(biggest_det, 'landmark_3d_68'):
            lm68 = biggest_det.landmark_3d_68
            curr_open = compute_mouth_openness(lm68)
            target_amp = float(smooth_amp[i])
            target_open = min_open + target_amp * (max_open - min_open)
            frame = warp_mouth(frame, lm68, target_open, curr_open, strength=0.7)

        # Apply karaoke overlay
        pct = (i / target) * 100
        amp_val = float(amp[i])
        frame = apply_overlay(frame, text_overlay, amp_val, pct)

        raw_fd.write(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes())
        frame_count += 1

        if frame_count % 50 == 0:
            elapsed = time.time() - start
            rate = frame_count / elapsed if elapsed > 0 else 0
            eta = (target - frame_count) / rate if rate > 0 else 0
            logger.info(f"  {frame_count}/{target} frames ({elapsed:.0f}s, {rate:.1f}fps, ETA {eta:.0f}s)")

    cap.release()
    raw_fd.close()

    logger.info("Encoding with ffmpeg (CRF 18, high quality)...")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{width}x{height}", "-framerate", str(fps),
        "-i", raw_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        output_path,
    ], check=True, timeout=600, capture_output=True)

    try:
        os.remove(raw_path)
    except Exception:
        pass

    total_time = time.time() - start
    mb = os.path.getsize(output_path) / 1_048_576 if os.path.exists(output_path) else 0
    dur = get_duration(output_path)
    logger.info(f"\n{'='*50}")
    logger.info(f"DONE! {dur:.1f}s, {mb:.1f}MB, {total_time:.0f}s total")
    logger.info(f"Output: {output_path}")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
