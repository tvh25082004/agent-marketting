import logging, os, re
from typing import Optional, Dict, Any
from .base import BaseAgent
from ..tools.lyric_tools import LyricExtractor

logger = logging.getLogger(__name__)

LYRIC_SYSTEM_PROMPT = """Bạn là Lyric Agent chuyên tạo lyrics cho bài hát Lào.
Nhiệm vụ:
1. Tạo lyrics tiếng Lào cho bài hát
2. Tạo file SRT/ASS cho karaoke
3. Hỗ trợ tiếng Lào"""


class LyricAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="lyric", system_prompt=LYRIC_SYSTEM_PROMPT, model_name=model_name)
        self.extractor = LyricExtractor()

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        title = input_data.get("title", "")
        audio_path = input_data.get("audio_path")

        lyrics = self._generate_lyrics(title)
        srt_path = None
        if lyrics and audio_path and os.path.exists(audio_path):
            srt_path = self.extractor.create_srt(lyrics, audio_path, title)

        return {
            "lyrics": lyrics,
            "srt_path": srt_path,
            "language": "lo",
            "status": "completed" if lyrics else "failed",
        }

    def _generate_lyrics(self, title: str) -> str:
        prompt = f"""Generate lyrics for a Lao song titled "{title or 'Unknown'}".
Write 20-30 lines in LAO script only.
Each line on a new line.
Example:
ຄົນສຸດທ້າຍ ທີ່ເຄີຍຮັກ
ບໍ່ມີວັນລືມ ເສັ້ນທາງທີ່ເຄີຍຍ່າງ
Return ONLY the lyrics, no explanations."""
        response = self.llm.invoke(prompt)
        return response.content.strip()
