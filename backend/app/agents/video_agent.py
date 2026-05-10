import logging, os
from typing import Optional, Dict, Any
from .base import BaseAgent
from ..tools.video_tools import VideoGenerator
from ..config import settings

logger = logging.getLogger(__name__)

VIDEO_SYSTEM_PROMPT = """Bạn là Video Agent chuyên tạo video ca sĩ AI.
Nhiệm vụ:
1. Tạo video từ ảnh input.jpeg + audio nhạc Lào
2. Thêm hiệu ứng Ken Burns zoom (chuyển động ảnh)
3. Tạo mouth animation nhép theo nhạc
4. Thêm karaoke lyrics
5. Xuất video Full HD chất lượng cao"""


class VideoAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="video", system_prompt=VIDEO_SYSTEM_PROMPT, model_name=model_name)
        self.generator = VideoGenerator()

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        audio_path = input_data.get("voice_path") or input_data.get("audio_path")
        lyrics = input_data.get("lyrics")
        image_path = input_data.get("image_path") or os.path.join(settings.temp_dir, "..", "input", "input.jpeg")

        output_path = os.path.join(settings.video_output_dir, f"singer_video_{hash(str(input_data))}.mp4")

        result = self.generator.generate_singer_video(
            image_path=image_path,
            audio_path=audio_path,
            lyrics=lyrics,
            output_path=output_path,
        )

        return {
            "background_video_path": result,
            "duration_seconds": self._get_dur(result),
            "status": "completed" if result else "failed",
        }

    def _get_dur(self, path):
        if not path or not os.path.exists(path):
            return None
        try:
            import json, subprocess
            r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                               capture_output=True, text=True, timeout=10)
            return float(json.loads(r.stdout)["format"]["duration"])
        except: return None
