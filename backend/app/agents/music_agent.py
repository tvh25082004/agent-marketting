import logging, os
from typing import Optional, Dict, Any
from .base import BaseAgent
from ..tools.audio_tools import AudioProcessor

logger = logging.getLogger(__name__)

MUSIC_SYSTEM_PROMPT = """Bạn là Music Agent chuyên xử lý audio nhạc.
Nhiệm vụ:
1. Phân tích file audio đã tải về từ laomusic.net
2. Chuẩn hóa chất lượng âm thanh
3. Chuẩn bị audio cho quá trình tạo video"""


class MusicAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="music", system_prompt=MUSIC_SYSTEM_PROMPT, model_name=model_name)
        self.processor = AudioProcessor()

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        audio_path = input_data.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            return {"error": "Audio file not found", "status": "failed"}

        info = self.processor.analyze(audio_path)
        normalized_path = self.processor.normalize(audio_path)

        return {
            "original_path": audio_path,
            "normalized_path": normalized_path,
            "info": info,
            "status": "completed",
        }
