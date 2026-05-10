import logging, os
from typing import Optional, Dict, Any
from .base import BaseAgent
from ..config import settings

logger = logging.getLogger(__name__)

KARAOKE_SYSTEM_PROMPT = """Bạn là Karaoke Agent. 
Karaoke lyrics đã được tích hợp trong VideoGenerator,
agent này chỉ pass-through kết quả."""


class KaraokeAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="karaoke", system_prompt=KARAOKE_SYSTEM_PROMPT, model_name=model_name)

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        video_path = input_data.get("lipsync_video_path") or input_data.get("background_video_path")
        return {
            "karaoke_video_path": video_path,
            "status": "completed" if video_path else "failed",
        }
