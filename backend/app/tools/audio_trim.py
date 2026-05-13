import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioTrimmer:
    """Trim audio intro and extract segment."""
    
    @staticmethod
    def detect_silence_end(audio_path: str, silence_thresh: str = "-40dB", min_silence: float = 0.5) -> float:
        """Detect where intro silence/speech ends."""
        cmd = [
            "ffmpeg", "-i", audio_path,
            "-af", f"silencedetect=noise={silence_thresh}:d={min_silence}",
            "-f", "null", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Parse silence_end from stderr
        for line in result.stderr.split("\n"):
            if "silence_end:" in line:
                try:
                    end_time = float(line.split("silence_end:")[1].split("|")[0].strip())
                    return end_time
                except (ValueError, IndexError):
                    continue
        
        return 0.0
    
    @staticmethod
    def get_duration(audio_path: str) -> float:
        """Get audio duration."""
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            info = json.loads(result.stdout)
            return float(info["format"]["duration"])
        except Exception:
            return 0.0
    
    def trim_audio(
        self,
        input_path: str,
        output_path: str,
        duration: float = 20.0,
        auto_detect_intro: bool = True,
        start_offset: float = 0.0,
    ) -> str:
        """
        Trim audio to specified duration, optionally skipping intro.
        
        Args:
            input_path: Input audio file
            output_path: Output audio file
            duration: Target duration in seconds (default 20s)
            auto_detect_intro: Auto-detect and skip intro silence/speech
            start_offset: Manual start offset (used if auto_detect_intro=False)
        
        Returns:
            Path to trimmed audio file
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Audio not found: {input_path}")
        
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        total_duration = self.get_duration(input_path)
        logger.info(f"Audio duration: {total_duration:.1f}s")
        
        # Detect intro end
        if auto_detect_intro:
            intro_end = self.detect_silence_end(input_path)
            if intro_end > 0:
                logger.info(f"Detected intro end at {intro_end:.1f}s")
                start_time = intro_end
            else:
                logger.info("No intro detected, using manual offset")
                start_time = start_offset
        else:
            start_time = start_offset
        
        # Ensure we don't exceed audio length
        if start_time + duration > total_duration:
            duration = total_duration - start_time
            logger.warning(f"Adjusted duration to {duration:.1f}s to fit audio length")
        
        # Trim audio
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", input_path,
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, timeout=120)
        
        if os.path.exists(output_path):
            trimmed_dur = self.get_duration(output_path)
            logger.info(f"Trimmed audio: {output_path} ({trimmed_dur:.1f}s)")
            return output_path
        else:
            raise RuntimeError("Audio trimming failed")
