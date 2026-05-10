import logging
import os
from typing import Any, Dict, Optional

from ..config import settings
from .base import BaseAgent

logger = logging.getLogger(__name__)

LIPSYNC_SYSTEM_PROMPT = """Bạn là Lipsync Agent — chuyên gia đồng bộ môi với audio.
Nhiệm vụ:
1. Nhận ảnh người, video tham chiếu và audio mục tiêu
2. Face-swap: thay khuôn mặt từ ảnh vào từng frame video tham chiếu
3. Lip-sync: vẽ miệng chuyển động theo audio mục tiêu
4. Trả về video MP4 hoàn chỉnh"""


class LipsyncAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="lipsync", system_prompt=LIPSYNC_SYSTEM_PROMPT, model_name=model_name)
        self.tool = None

    def _lazy_init(self):
        if self.tool is None:
            from ..tools.video_motion_tools import VideoMotionTool
            self.tool = VideoMotionTool()

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._lazy_init()

        source_image = input_data.get("image_path") or os.path.join(
            os.path.dirname(os.path.dirname(settings.temp_dir)), "input", "input.jpeg"
        )
        reference_video = input_data.get("reference_video") or os.path.join(
            os.path.dirname(os.path.dirname(settings.temp_dir)), "input", "videoinput.mp4"
        )
        audio_path = input_data.get("voice_path") or input_data.get("audio_path")

        logger.info(f"[LipsyncAgent] img={source_image}, ref={reference_video}, audio={audio_path}")

        if not audio_path or not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        if not os.path.exists(reference_video):
            raise FileNotFoundError(f"Reference video not found: {reference_video}")

        result_path = self.tool.generate(
            source_image=source_image,
            reference_video=reference_video,
            audio_path=audio_path,
        )

        if result_path and os.path.exists(result_path):
            return {
                "lipsync_video_path": result_path,
                "status": "completed",
            }

        err = self.tool.readiness_error() if not self.tool.ready() else "Generation returned no output"
        raise RuntimeError(err)
