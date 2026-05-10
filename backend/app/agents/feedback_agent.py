import logging
from typing import Optional, Dict, Any
from .base import BaseAgent

logger = logging.getLogger(__name__)

FEEDBACK_SYSTEM_PROMPT = """Bạn là Feedback Agent chuyên đánh giá chất lượng video.
Nhiệm vụ:
1. Phân tích video đã tạo
2. Đánh giá chất lượng tổng thể
3. Đề xuất cải thiện
4. Học từ feedback trước đó
5. Cập nhật system prompt cho các agent khác"""


class FeedbackAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(
            name="feedback",
            system_prompt=FEEDBACK_SYSTEM_PROMPT,
            model_name=model_name,
        )

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        video_info = input_data.get("video_info", {})
        user_feedback = input_data.get("user_feedback")
        task_history = input_data.get("task_history", [])

        prompt = f"""Đánh giá chất lượng video sản xuất.

Thông tin video: {video_info}

Feedback người dùng: {user_feedback or 'Chưa có'}
Lịch sử tác vụ: {len(task_history)} tác vụ trước đó

Hãy phân tích:
1. Chất lượng video (1-10)
2. Điểm cần cải thiện
3. Gợi ý cụ thể cho lần tới
4. Có nên thay đổi model không?
5. Có nên điều chỉnh system prompt không?

Trả về JSON:
{{
    "score": 7.5,
    "strengths": [...],
    "weaknesses": [...],
    "improvements": [...],
    "model_suggestion": "...",
    "prompt_adjustments": "..."
}}"""

        response = self.llm.invoke(prompt)
        analysis = self._parse_json(response.content)

        analysis["status"] = "completed"
        return analysis
