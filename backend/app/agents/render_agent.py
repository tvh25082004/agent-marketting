import logging, os
from typing import Optional, Dict, Any
from .base import BaseAgent
from ..config import settings
import subprocess

logger = logging.getLogger(__name__)


class RenderAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="render", system_prompt="", model_name=model_name)

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        source = input_data.get("karaoke_video_path") or input_data.get("lipsync_video_path") or input_data.get("background_video_path")
        if not source or not os.path.exists(source):
            return {"error": "No video source", "status": "failed"}

        output = os.path.join(settings.video_output_dir, f"final_{os.path.basename(source)}")

        dur = self._get_dur(source) or 60
        dur = max(30, min(dur, 262))

        cmd = [
            "ffmpeg", "-y", "-i", source,
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", output,
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)

        return {
            "final_video_path": output if os.path.exists(output) else source,
            "duration_seconds": dur,
            "status": "completed",
        }

    def _get_dur(self, path):
        try:
            import json
            r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                               capture_output=True, text=True, timeout=10)
            return float(json.loads(r.stdout)["format"]["duration"])
        except: return None
