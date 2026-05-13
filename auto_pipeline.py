#!/usr/bin/env python3
"""
Auto Pipeline - Face Swap + Lip Sync + Audio Replacement
Optimized for MacOS M3

Usage:
  # Single video
  python3 auto_pipeline.py --image input/input.jpeg --video input/videoinput.mp4 --audio input/song.mp3

  # Batch all audios
  python3 auto_pipeline.py --batch --image input/input.jpeg --video input/videoinput.mp4

  # Dry run (show plan)
  python3 auto_pipeline.py --batch --dry-run
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AutoPipeline")

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMP_DIR = PROJECT_ROOT / "temp"
BACKEND_DIR = PROJECT_ROOT / "backend"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


class AutoPipeline:
    def __init__(self, image: str, video: str, audio: str = None, output_dir: str = None, fast: bool = False):
        self.image_path = Path(image)
        self.video_path = Path(video)
        self.audio_path = Path(audio) if audio else None
        self.output_dir = Path(output_dir) if output_dir else (OUTPUT_DIR / "videos")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._tool = None
        self.fast = fast

    def _get_tool(self):
        if self._tool is None:
            sys.path.insert(0, str(BACKEND_DIR))
            from app.config import settings as backend_settings
            from app.tools.video_motion_tools import VideoMotionTool
            self._tool = VideoMotionTool(skip_swap=self.fast)
        return self._tool

    def run(self) -> str | None:
        logger.info("=" * 50)
        logger.info("Auto Pipeline Started")
        logger.info(f"  Image : {self.image_path}")
        logger.info(f"  Video : {self.video_path}")
        logger.info(f"  Audio : {self.audio_path}")
        logger.info(f"  Mode  : {'FAST' if self.fast else 'FULL (with face swap)'}")
        logger.info("=" * 50)

        self._validate_inputs()

        timestamp = int(time.time())
        stem = self.audio_path.stem if self.audio_path else f"video_{timestamp}"
        final_path = self.output_dir / f"{stem}.mp4"

        os.makedirs(TEMP_DIR, exist_ok=True)

        tool = self._get_tool()
        if tool.ready():
            if self.fast:
                logger.info("Fast mode - lip sync + audio only (no face swap)")
            else:
                logger.info("InsightFace ready - running face swap + lip sync")
        else:
            logger.info("Lip sync only mode (no face swap)")

        result = tool.generate(
            source_image=str(self.image_path),
            reference_video=str(self.video_path),
            audio_path=str(self.audio_path),
            output_path=str(final_path),
        )

        if result and os.path.exists(result):
            mb = os.path.getsize(result) / 1_048_576
            dur = self._get_media_duration(result)
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Done! {dur:.1f}s, {mb:.1f}MB")
            logger.info(f"Output: {result}")
            logger.info(f"{'=' * 50}")
            return result

        logger.error("Pipeline failed - no output produced")
        return None

    def _validate_inputs(self):
        for p, name in [(self.image_path, "Image"), (self.video_path, "Video")]:
            if not p.exists():
                logger.error(f"{name} not found: {p}")
                sys.exit(1)
        if self.audio_path and not self.audio_path.exists():
            logger.error(f"Audio not found: {self.audio_path}")
            sys.exit(1)

    @staticmethod
    def _get_media_duration(path: str) -> float:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                capture_output=True, text=True, timeout=15,
            )
            return float(json.loads(r.stdout)["format"]["duration"])
        except Exception:
            return 0.0


def find_audio_files(directory: str) -> list[Path]:
    return sorted(
        f for f in Path(directory).iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    )


def detect_default_assets():
    assets = {"images": [], "videos": [], "audios": []}
    groups = {
        "images": {".jpg", ".jpeg", ".png", ".webp"},
        "videos": {".mp4", ".mov", ".mkv", ".webm"},
        "audios": AUDIO_EXTENSIONS,
    }
    for f in sorted(INPUT_DIR.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        for group, exts in groups.items():
            if ext in exts:
                assets[group].append(str(f))
                break

    image = assets["images"][0] if assets["images"] else None
    video = assets["videos"][0] if assets["videos"] else None
    logger.info(f"Detected: {len(assets['images'])} images, {len(assets['videos'])} videos, {len(assets['audios'])} audios")
    return image, video, assets["audios"]


def main():
    parser = argparse.ArgumentParser(description="Auto Pipeline - Face Swap + Lip Sync + Audio")
    parser.add_argument("--image", help="Source face image path")
    parser.add_argument("--video", help="Reference video path")
    parser.add_argument("--audio", help="Target audio path (single mode)")
    parser.add_argument("--batch", action="store_true", help="Batch process all audios")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR / "videos"), help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without processing")
    parser.add_argument("--wav", action="store_true", help="Auto convert MP3 to WAV before processing")
    parser.add_argument("--fast", action="store_true", help="Fast mode: lip sync only (skip face swap)")
    args = parser.parse_args()

    logger.info("Auto Pipeline - Face Swap + Lip Sync + Audio Replacement")
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Input dir: {INPUT_DIR}")
    logger.info(f"Output dir: {args.output_dir}")

    os.makedirs(args.output_dir, exist_ok=True)

    image = args.image
    video = args.video
    if not image or not video:
        det_img, det_vid, _ = detect_default_assets()
        image = image or det_img
        video = video or det_vid

    if not image:
        logger.error("No source image - place a .jpg in input/ or use --image")
        sys.exit(1)
    if not video:
        logger.error("No reference video - place a .mp4 in input/ or use --video")
        sys.exit(1)

    if args.audio:
        audio_files = [Path(args.audio)]
    elif args.batch:
        audio_files = find_audio_files(str(INPUT_DIR))
        if not audio_files:
            logger.error("No audio files in input/")
            sys.exit(1)
        logger.info(f"Batch mode: {len(audio_files)} audio files")
    else:
        audio_files = find_audio_files(str(INPUT_DIR))
        if audio_files:
            audio_files = [audio_files[0]]
            logger.info(f"Auto-selected audio: {audio_files[0].name}")
        else:
            logger.error("No audio - use --audio or place .mp3 in input/")
            sys.exit(1)

    if args.dry_run:
        logger.info("\n=== DRY RUN PLAN ===")
        logger.info(f"  Source image: {image}")
        logger.info(f"  Reference video: {video}")
        logger.info(f"  Audios ({len(audio_files)}):")
        for af in audio_files:
            logger.info(f"    - {af.name}")
        logger.info("\n  Pipeline: VideoMotionTool (face swap + lip sync + audio)")
        logger.info(f"  Output dir: {args.output_dir}")
        logger.info("\n  Run without --dry-run to execute.")
        return

    pipeline = AutoPipeline(image=image, video=video, output_dir=args.output_dir, fast=args.fast)
    results = []

    for idx, af in enumerate(audio_files):
        logger.info(f"\n{'#' * 50}")
        logger.info(f"# Job {idx + 1}/{len(audio_files)}: {af.name}")
        logger.info(f"{'#' * 50}")
        pipeline.audio_path = af
        result = pipeline.run()
        results.append({"audio": af.name, "output": result, "status": "success" if result else "failed"})

    logger.info(f"\n{'=' * 50}")
    logger.info("SUMMARY")
    logger.info("=" * 50)
    success = sum(1 for r in results if r["status"] == "success")
    for r in results:
        status_tag = "OK" if r["status"] == "success" else "FAIL"
        logger.info(f"  [{status_tag}] {r['audio']} -> {r['output'] or 'FAILED'}")
    logger.info(f"\nTotal: {len(results)}, Success: {success}, Failed: {len(results) - success}")
    logger.info(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
