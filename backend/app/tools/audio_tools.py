import logging
import os
import subprocess
from typing import Optional, Dict, Any, Tuple
from ..config import settings

logger = logging.getLogger(__name__)


class AudioProcessor:
    def analyze(self, audio_path: str) -> Optional[Dict[str, Any]]:
        if not audio_path or not os.path.exists(audio_path):
            return None
        try:
            import json
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            info = json.loads(result.stdout)
            format_info = info.get("format", {})
            stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})

            return {
                "filename": os.path.basename(audio_path),
                "duration_seconds": float(format_info.get("duration", 0)),
                "size_bytes": int(format_info.get("size", 0)),
                "bitrate": format_info.get("bit_rate", "0"),
                "sample_rate": stream.get("sample_rate", "0"),
                "channels": stream.get("channels", 0),
                "codec": stream.get("codec_name", "unknown"),
            }
        except Exception as e:
            logger.warning(f"Audio analysis failed: {e}")
            return None

    def normalize(self, audio_path: str) -> str:
        output_path = os.path.join(settings.temp_dir, f"normalized_{os.path.basename(audio_path)}")
        if os.path.exists(output_path):
            return output_path
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)
            return output_path if os.path.exists(output_path) else audio_path
        except Exception as e:
            logger.warning(f"Audio normalization failed: {e}")
            return audio_path

    def separate_vocals(self, audio_path: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            from spleeter.separator import Separator
            separator = Separator("spleeter:2stems")
            output_dir = os.path.join(settings.temp_dir, "spleeter_output")
            separator.separate_to_file(audio_path, output_dir)
            base = os.path.splitext(os.path.basename(audio_path))[0]
            vocal_path = os.path.join(output_dir, base, "vocals.wav")
            instrumental_path = os.path.join(output_dir, base, "accompaniment.wav")
            return (vocal_path if os.path.exists(vocal_path) else None,
                    instrumental_path if os.path.exists(instrumental_path) else None)
        except ImportError:
            logger.warning("Spleeter not installed, skipping vocal separation")
            return (audio_path, None)
        except Exception as e:
            logger.warning(f"Vocal separation failed: {e}")
            return (audio_path, None)

    def get_duration(self, audio_path: str) -> float:
        try:
            import json
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0))
        except Exception:
            return 0.0

    def trim(self, audio_path: str, start: float, end: float) -> str:
        output_path = os.path.join(settings.temp_dir, f"trimmed_{os.path.basename(audio_path)}")
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-ss", str(start),
                "-to", str(end),
                "-c:a", "aac",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)
            return output_path if os.path.exists(output_path) else audio_path
        except Exception:
            return audio_path
