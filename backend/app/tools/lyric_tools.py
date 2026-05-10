import logging
import os
import re
import math
from typing import Optional, List, Dict
from ..config import settings

logger = logging.getLogger(__name__)


class LyricExtractor:
    def extract(self, title: str, artist: str) -> Optional[str]:
        logger.info(f"Extracting lyrics for: {title} - {artist}")
        return None

    def extract_from_audio(self, audio_path: str) -> Optional[str]:
        logger.info(f"Extracting lyrics from audio: {audio_path}")
        return None

    def create_srt(self, lyrics: str, audio_path: str, title: str) -> Optional[str]:
        if not lyrics:
            return None

        try:
            import json
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                audio_path,
            ]
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 60))
        except Exception:
            duration = 60.0

        lines = [l.strip() for l in lyrics.split("\n") if l.strip()]
        output_path = os.path.join(settings.temp_dir, f"{re.sub(r'[^\w]', '_', title)}.srt")

        with open(output_path, "w", encoding="utf-8") as f:
            line_duration = duration / max(len(lines), 1)
            for i, line in enumerate(lines):
                start = i * line_duration
                end = min((i + 1) * line_duration, duration)
                start_ts = self._seconds_to_srt(start)
                end_ts = self._seconds_to_srt(end)
                f.write(f"{i + 1}\n{start_ts} --> {end_ts}\n{line}\n\n")

        return output_path

    def create_ass(self, lyrics: str, audio_path: str, title: str) -> Optional[str]:
        if not lyrics:
            return None

        lines = [l.strip() for l in lyrics.split("\n") if l.strip()]
        output_path = os.path.join(settings.temp_dir, f"{re.sub(r'[^\w]', '_', title)}.ass")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\n")
            f.write("Title: Tinasoft Karaoke\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1080\n")
            f.write("PlayResY: 1920\n\n")
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, "
                    "SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
                    "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
                    "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, "
                    "MarginV, Encoding\n")
            f.write("Style: Karaoke,Arial,28,&H00FFFFFF,&H000000FF,"
                    "&H00000000,&H80000000,0,0,0,0,100,100,0,0,"
                    "1,2,1,2,30,30,80,0\n\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
                    "MarginV, Effect, Text\n")

            for i, line in enumerate(lines):
                start_sec = i * 3
                end_sec = (i + 1) * 3
                start_ts = self._seconds_to_ass(start_sec)
                end_ts = self._seconds_to_ass(end_sec)
                f.write(f"Dialogue: 0,{start_ts},{end_ts},Karaoke,,0,0,0,,"
                        f"{{\\k60}}{line}\n")

        return output_path

    def _seconds_to_srt(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _seconds_to_ass(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"
