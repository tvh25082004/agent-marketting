import logging
import os
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class LyricsOverlay:
    """Generate ASS subtitle file for karaoke-style lyrics overlay."""
    
    @staticmethod
    def parse_lyrics(lyrics_text: str) -> List[str]:
        """Parse lyrics into lines."""
        lines = [l.strip() for l in lyrics_text.split("\n") if l.strip()]
        # Remove timestamps if present
        lines = [re.sub(r'^\[\d+:\d+\.\d+\]', '', l).strip() for l in lines]
        return [l for l in lines if l]
    
    def create_ass_subtitle(
        self,
        lyrics: str,
        output_path: str,
        duration: float,
        style: str = "karaoke",
    ) -> str:
        """
        Create ASS subtitle file with lyrics.
        
        Args:
            lyrics: Lyrics text (one line per subtitle)
            output_path: Output .ass file path
            duration: Total duration in seconds
            style: Style preset (karaoke, bottom, center)
        
        Returns:
            Path to generated ASS file
        """
        lines = self.parse_lyrics(lyrics)
        if not lines:
            raise ValueError("No lyrics provided")
        
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        # Calculate timing
        line_duration = duration / len(lines)
        
        # Style configurations
        styles = {
            "karaoke": {
                "fontsize": 32,
                "color": "&H00FFFFFF",  # White
                "outline_color": "&H00000000",  # Black outline
                "alignment": 2,  # Bottom center
                "margin_v": 60,
            },
            "bottom": {
                "fontsize": 28,
                "color": "&H00FFFF00",  # Yellow
                "outline_color": "&H00000000",
                "alignment": 2,
                "margin_v": 40,
            },
            "center": {
                "fontsize": 36,
                "color": "&H00FFFFFF",
                "outline_color": "&H00000000",
                "alignment": 5,  # Center
                "margin_v": 0,
            },
        }
        
        style_config = styles.get(style, styles["karaoke"])
        
        with open(output_path, "w", encoding="utf-8") as f:
            # Header
            f.write("[Script Info]\n")
            f.write("Title: Tinasoft Karaoke\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1080\n")
            f.write("PlayResY: 1920\n")
            f.write("WrapStyle: 0\n\n")
            
            # Styles
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                   "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                   "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                   "Alignment, MarginL, MarginR, MarginV, Encoding\n")
            
            f.write(f"Style: Default,Arial,{style_config['fontsize']},"
                   f"{style_config['color']},&H000000FF,"
                   f"{style_config['outline_color']},&H80000000,"
                   f"-1,0,0,0,100,100,0,0,1,3,2,"
                   f"{style_config['alignment']},30,30,{style_config['margin_v']},1\n\n")
            
            # Events
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            for i, line in enumerate(lines):
                start_sec = i * line_duration
                end_sec = min((i + 1) * line_duration, duration)
                start_ts = self._seconds_to_ass(start_sec)
                end_ts = self._seconds_to_ass(end_sec)
                
                # Karaoke effect: highlight text progressively
                if style == "karaoke":
                    # Split line into words for karaoke effect
                    words = line.split()
                    word_duration = (end_sec - start_sec) / max(len(words), 1)
                    karaoke_text = ""
                    for j, word in enumerate(words):
                        k_time = int(word_duration * 100)  # centiseconds
                        karaoke_text += f"{{\\k{k_time}}}{word} "
                    text = karaoke_text.strip()
                else:
                    text = line
                
                f.write(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}\n")
        
        logger.info(f"Created ASS subtitle: {output_path} ({len(lines)} lines)")
        return output_path
    
    @staticmethod
    def _seconds_to_ass(seconds: float) -> str:
        """Convert seconds to ASS timestamp format (H:MM:SS.CS)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"
