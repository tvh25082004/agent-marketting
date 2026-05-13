#!/usr/bin/env python3
"""
Pipeline Final - Face Swap + Audio + Karaoke
- Face swap using InsightFace
- Audio from climax segment
- Karaoke overlay (title, artist, progress, music visualizer)
- NO synthetic lip sync (avoids fake-looking mouth)
"""

import json, logging, os, subprocess, sys, time, math
from pathlib import Path
import cv2, numpy as np
from PIL import ImageFont, ImageDraw, Image as PILImage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("FinalPipeline")

PROJECT_ROOT = Path(__file__).resolve().parent
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT_L = ImageFont.truetype(FONT_PATH, 56) if os.path.exists(FONT_PATH) else None
FONT_M = ImageFont.truetype(FONT_PATH, 32) if os.path.exists(FONT_PATH) else None
FONT_S = ImageFont.truetype(FONT_PATH, 22) if os.path.exists(FONT_PATH) else None

def get_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                          capture_output=True, text=True, timeout=15)
        return float(json.loads(r.stdout)["format"]["duration"])
    except: return 0.0

def extract_amplitude(audio_path, fps, smooth=3):
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", str(fps), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    amp = np.abs(np.frombuffer(r.stdout, dtype=np.float32))
    amp = np.convolve(amp, np.ones(smooth)/smooth, mode="same")
    peak = float(np.percentile(amp, 97)) or 1.0
    amp = np.clip(amp / peak, 0, 1)
    amp[amp < 0.05] = 0
    return amp

def add_overlay(frame_pil, amp_val, pct, total_frames, frame_idx):
    """Add karaoke overlay to frame using Pillow. Fast - no alpha composite."""
    W, H = frame_pil.size
    draw = ImageDraw.Draw(frame_pil)

    # Semi-transparent top bar
    for y in range(0, 150):
        for x in range(0, W):
            px = frame_pil.getpixel((x, y))
            alpha = max(0, 150 - y)
            r = max(0, px[0] - alpha//3)
            g = max(0, px[1] - alpha//3)
            b = max(0, px[2] - alpha//3)
            frame_pil.putpixel((x, y), (r, g, b))

    # Song title
    if FONT_L:
        tx = W // 2
        ty = 50
        bbox = draw.textbbox((0, 0), "ຄົນດີທີ່ເຈົ້າບໍ່ຮັກ", font=FONT_L)
        tw = bbox[2] - bbox[0]
        # Shadow
        draw.text((tx - tw//2 + 2, ty + 2), "ຄົນດີທີ່ເຈົ້າບໍ່ຮັກ", fill=(0,0,0,180), font=FONT_L)
        draw.text((tx - tw//2, ty), "ຄົນດີທີ່ເຈົ້າບໍ່ຮັກ", fill=(255,255,255,240), font=FONT_L)

    # Artist
    if FONT_M:
        bbox = draw.textbbox((0, 0), "Voradeth Ditthavong", font=FONT_M)
        tw = bbox[2] - bbox[0]
        draw.text((W//2 - tw//2 + 1, 112), "Voradeth Ditthavong", fill=(0,0,0,120), font=FONT_M)
        draw.text((W//2 - tw//2, 110), "Voradeth Ditthavong", fill=(220,220,220,200), font=FONT_M)

    # Bottom bar - background
    bar_w = min(700, W - 60)
    bar_h = 8
    bar_x = (W - bar_w) // 2
    bar_y = H - 60
    fill_w = int(bar_w * pct / 100)

    # Progress bar background
    for y in range(bar_y, bar_y + bar_h):
        for x in range(bar_x, bar_x + bar_w):
            if y < H and x < W:
                px = frame_pil.getpixel((x, y))
                frame_pil.putpixel((x, y), (
                    min(255, px[0] + 30),
                    min(255, px[1] + 30),
                    min(255, px[2] + 30)
                ))

    # Progress bar fill
    for y in range(bar_y, bar_y + bar_h):
        for x in range(bar_x, bar_x + fill_w):
            if y < H and x < W:
                frame_pil.putpixel((x, y), (255, 200, 50))

    # Music visualizer bar
    vibe_y = H - 90
    amp_w = max(2, int(bar_w * amp_val * 0.7))
    for y in range(vibe_y, vibe_y + bar_h * 2):
        for x in range(bar_x, bar_x + amp_w):
            if y < H and x < W:
                r = min(255, 100 + int(amp_val * 155))
                g = min(255, 50 + int(amp_val * 100))
                b = min(255, 30)
                frame_pil.putpixel((x, y), (r, g, b))

    # Percentage text
    if FONT_S:
        bbox = draw.textbbox((0, 0), f"{pct:.0f}%", font=FONT_S)
        tw = bbox[2] - bbox[0]
        draw.text((W//2 - tw//2, bar_y + bar_h + 4), f"{pct:.0f}%", fill=(200,200,200,180), font=FONT_S)

    return frame_pil


def main():
    image_path = "input/input.jpeg"
    video_path = "input/videoinput.mp4"
    audio_path = "output/audio/climax_20s.mp3"
    output_path = "output/videos/final_video.mp4"

    logger.info("=" * 50)
    logger.info("FINAL PIPELINE - Face Swap + Audio + Karaoke")
    logger.info("=" * 50)

    # Init InsightFace
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model

    logger.info("Initializing InsightFace...")
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(320, 320))
    swapper = get_model("inswapper_128.onnx", download=True, providers=["CPUExecutionProvider"])

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

    raw_path = str(TEMP_DIR / "final_faceswap.raw")
    raw_fd = open(raw_path, "wb")

    start = time.time()
    cached_bbox = None
    cached_det = None
    frame_count = 0

    for i in range(target):
        ret, frame = cap.read()
        if not ret:
            break

        # Face swap
        if i % 15 == 0 or cached_bbox is None:
            dets = app.get(frame)
            if dets:
                cached_det = max(dets, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                cached_bbox = cached_det.bbox
                for det in dets:
                    frame = swapper.get(frame, det, src_face, paste_back=True)
        elif cached_det is not None:
            frame = swapper.get(frame, cached_det, src_face, paste_back=True)

        # Karaoke overlay
        pct = (i / target) * 100 if target > 0 else 0
        amp_val = float(amp[i]) if i < len(amp) else 0
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(frame_rgb)
        pil_img = add_overlay(pil_img, amp_val, pct, target, i)
        frame_out = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        raw_fd.write(cv2.cvtColor(frame_out, cv2.COLOR_BGR2RGB).tobytes())
        frame_count += 1

        if frame_count % 50 == 0:
            elapsed = time.time() - start
            rate = frame_count / elapsed if elapsed > 0 else 0
            eta = (target - frame_count) / rate if rate > 0 else 0
            logger.info(f"  {frame_count}/{target} frames ({elapsed:.0f}s, {rate:.1f}fps, ETA {eta:.0f}s)")

    cap.release()
    raw_fd.close()

    logger.info("Encoding with ffmpeg...")
    enc_start = time.time()
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{width}x{height}", "-framerate", str(fps),
        "-i", raw_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        output_path,
    ], check=True, timeout=600, capture_output=True)

    try: os.remove(raw_path)
    except: pass

    total = time.time() - start
    mb = os.path.getsize(output_path) / 1_048_576 if os.path.exists(output_path) else 0
    dur = get_duration(output_path)
    logger.info(f"\n{'='*50}")
    logger.info(f"DONE! {dur:.1f}s, {mb:.1f}MB, {total:.0f}s")
    logger.info(f"Output: {output_path}")
    logger.info(f"{'='*50}")

if __name__ == "__main__":
    main()
