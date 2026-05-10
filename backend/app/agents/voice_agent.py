import logging, os
from typing import Optional, Dict, Any
from .base import BaseAgent
from ..config import settings

logger = logging.getLogger(__name__)

VOICE_SYSTEM_PROMPT = """Bạn là Voice Agent. Với nhạc Lào từ laomusic.net,
chúng ta GIỮ NGUYÊN audio gốc (không tạo giọng mới).
Audio gốc đã có giọng ca sĩ thật."""


class VoiceAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="voice", system_prompt=VOICE_SYSTEM_PROMPT, model_name=model_name)

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Keep original audio - the song already has vocals
        audio_path = input_data.get("audio_path")
        normalized_path = input_data.get("normalized_path") or audio_path

        return {
            "voice_path": normalized_path,
            "voice_config": {"source": "original", "language": "lo"},
            "language": "lo",
            "status": "completed",
        }
