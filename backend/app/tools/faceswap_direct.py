#!/usr/bin/env python3
"""
Direct Face Swap CLI Tool - sử dụng InsightFace để face swap video.
Chạy độc lập không cần FastAPI.

Usage:
  python faceswap_direct.py --source input/input.jpeg --target input/videoinput.mp4 --output output/swapped.mp4
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FaceSwapDirect")


def get_duration(path: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=15,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def faceswap_cli(source: str, target: str, output: str):
    start = time.time()

    for p, name in [(source, "Source"), (target, "Target")]:
        if not os.path.exists(p):
            logger.error(f"{name} file not found: {p}")
            return False

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.error("OpenCV required: pip install opencv-python")
        return False

    try:
        import insightface
        from insightface.app import FaceAnalysis
        from insightface.model_zoo import get_model
    except ImportError:
        logger.warning("InsightFace not installed, copying video as-is")
        subprocess.run(["ffmpeg", "-y", "-i", target, "-c", "copy", output], capture_output=True)
        return os.path.exists(output)

    logger.info("Initializing InsightFace...")

    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(320, 320))

    swapper = get_model("inswapper_128.onnx", download=True, providers=["CPUExecutionProvider"])

    src_img = cv2.imread(source)
    if src_img is None:
        logger.error(f"Cannot read source image: {source}")
        return False

    src_faces = app.get(src_img)
    if not src_faces:
        logger.warning("No face detected in source image, copying video as-is")
        subprocess.run(["ffmpeg", "-y", "-i", target, "-c", "copy", output], capture_output=True)
        return os.path.exists(output)

    src_face = src_faces[0]
    logger.info(f"Source face: {src_face.bbox}")

    cap = cv2.VideoCapture(target)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {target}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(f"Video: {width}x{height} @ {fps:.2f}fps, {total} frames")

    raw_path = output.replace(".mp4", f"_{int(time.time())}.raw")
    count = 0
    DETECT_INTERVAL = 10

    with open(raw_path, "wb") as fp:
        for i in range(total):
            ret, frame = cap.read()
            if not ret:
                break

            if i % DETECT_INTERVAL == 0:
                dets = app.get(frame)
                if dets:
                    current_dets = dets
            elif 'current_dets' in dir():
                pass

            dets = app.get(frame) if i % DETECT_INTERVAL == 0 else (
                current_dets if 'current_dets' in dir() else [])

            if dets:
                current_dets = dets
                for det in dets:
                    frame = swapper.get(frame, det, src_face, paste_back=True)

            fp.write(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes())
            count += 1

            if count % 100 == 0:
                logger.info(f"  {count}/{total} frames")

    cap.release()

    if count == 0:
        logger.error("No frames processed")
        return False

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{width}x{height}", "-framerate", str(fps),
        "-i", raw_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", output,
    ], capture_output=True, timeout=900)

    try:
        os.remove(raw_path)
    except OSError:
        pass

    elapsed = time.time() - start
    mb = os.path.getsize(output) / 1_048_576 if os.path.exists(output) else 0
    logger.info(f"Done: {output} ({count} frames, {mb:.1f}MB, {elapsed:.0f}s)")
    return os.path.exists(output)


def main():
    parser = argparse.ArgumentParser(description="Face Swap CLI Tool")
    parser.add_argument("--source", required=True, help="Source face image")
    parser.add_argument("--target", required=True, help="Target video")
    parser.add_argument("--output", required=True, help="Output video path")
    args = parser.parse_args()

    ok = faceswap_cli(args.source, args.target, args.output)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
