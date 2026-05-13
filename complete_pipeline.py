#!/usr/bin/env python3
"""
Complete Video Pipeline - Face Swap + Audio Trim + Lip Sync + Lyrics Overlay

Features:
- Face swap using InsightFace
- Auto-detect and trim audio intro (20s segment)
- Lip sync with amplitude-based mouth animation
- Karaoke-style lyrics overlay

Usage:
  python3 complete_pipeline.py --image input/face.jpg --video input/video.mp4 --audio input/song.mp3 --lyrics "Line 1\nLine 2\nLine 3"
  
  # With lyrics file
  python3 complete_pipeline.py --image input/face.jpg --video input/video.mp4 --audio input/song.mp3 --lyrics-file input/lyrics.txt
  
  # Batch mode
  python3 complete_pipeline.py --batch --image input/face.jpg --video input/video.mp4
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("CompletePipeline")

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
BACKEND_DIR = PROJECT_ROOT / "backend"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


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


def process_video(
    image: str,
    video: str,
    audio: str,
    lyrics: str = None,
    output_dir: str = None,
    audio_duration: float = 20.0,
) -> str:
    """Process single video with all features."""
    sys.path.insert(0, str(BACKEND_DIR))
    from app.tools.video_motion_tools import VideoMotionTool
    
    tool = VideoMotionTool(skip_swap=False)
    
    if not tool.ready():
        logger.warning("InsightFace not ready - face swap will be skipped")
    
    output_dir = Path(output_dir) if output_dir else (OUTPUT_DIR / "videos")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = int(time.time())
    audio_stem = Path(audio).stem
    final_path = output_dir / f"{audio_stem}_{timestamp}.mp4"
    
    logger.info("=" * 60)
    logger.info("Complete Pipeline Started")
    logger.info(f"  Image    : {image}")
    logger.info(f"  Video    : {video}")
    logger.info(f"  Audio    : {audio}")
    logger.info(f"  Lyrics   : {'Yes' if lyrics else 'No'}")
    logger.info(f"  Duration : {audio_duration}s")
    logger.info("=" * 60)
    
    result = tool.generate(
        source_image=image,
        reference_video=video,
        audio_path=audio,
        output_path=str(final_path),
        lyrics=lyrics,
        trim_audio=True,
        audio_duration=audio_duration,
    )
    
    if result and os.path.exists(result):
        mb = os.path.getsize(result) / 1_048_576
        logger.info(f"\n{'=' * 60}")
        logger.info(f"✓ Success! {mb:.1f}MB")
        logger.info(f"  Output: {result}")
        logger.info(f"{'=' * 60}")
        return result
    else:
        logger.error("Pipeline failed")
        return None


def main():
    parser = argparse.ArgumentParser(description="Complete Video Pipeline")
    parser.add_argument("--image", help="Source face image")
    parser.add_argument("--video", help="Reference video")
    parser.add_argument("--audio", help="Audio file (single mode)")
    parser.add_argument("--lyrics", help="Lyrics text (newline separated)")
    parser.add_argument("--lyrics-file", help="Lyrics file path")
    parser.add_argument("--duration", type=float, default=20.0, help="Audio duration (default: 20s)")
    parser.add_argument("--batch", action="store_true", help="Batch process all audios")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR / "videos"), help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without processing")
    args = parser.parse_args()

    logger.info("Complete Video Pipeline - Face Swap + Audio Trim + Lip Sync + Lyrics")
    logger.info(f"Project root: {PROJECT_ROOT}")

    # Detect assets
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

    # Load lyrics
    lyrics = args.lyrics
    if args.lyrics_file and os.path.exists(args.lyrics_file):
        with open(args.lyrics_file, "r", encoding="utf-8") as f:
            lyrics = f.read()
        logger.info(f"Loaded lyrics from: {args.lyrics_file}")

    # Get audio files
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
        logger.info(f"  Audio duration: {args.duration}s")
        logger.info(f"  Lyrics: {'Yes' if lyrics else 'No'}")
        logger.info(f"  Audios ({len(audio_files)}):")
        for af in audio_files:
            logger.info(f"    - {af.name}")
        logger.info("\n  Pipeline:")
        logger.info("    1. Face swap (InsightFace)")
        logger.info("    2. Audio trim (auto-detect intro)")
        logger.info("    3. Lip sync (amplitude-based)")
        logger.info("    4. Lyrics overlay (ASS karaoke)")
        logger.info(f"\n  Output dir: {args.output_dir}")
        logger.info("\n  Run without --dry-run to execute.")
        return

    # Process videos
    results = []
    for idx, af in enumerate(audio_files):
        logger.info(f"\n{'#' * 60}")
        logger.info(f"# Job {idx + 1}/{len(audio_files)}: {af.name}")
        logger.info(f"{'#' * 60}")
        
        result = process_video(
            image=image,
            video=video,
            audio=str(af),
            lyrics=lyrics,
            output_dir=args.output_dir,
            audio_duration=args.duration,
        )
        
        results.append({
            "audio": af.name,
            "output": result,
            "status": "success" if result else "failed"
        })

    # Summary
    logger.info(f"\n{'=' * 60}")
    logger.info("SUMMARY")
    logger.info("=" * 60)
    success = sum(1 for r in results if r["status"] == "success")
    for r in results:
        status_tag = "✓" if r["status"] == "success" else "✗"
        logger.info(f"  [{status_tag}] {r['audio']}")
        if r["output"]:
            logger.info(f"      → {r['output']}")
    logger.info(f"\nTotal: {len(results)}, Success: {success}, Failed: {len(results) - success}")
    logger.info(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
