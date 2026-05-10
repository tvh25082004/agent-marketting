import logging
from typing import Optional
from .base import BaseAgent

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """Bạn là Supervisor Agent của hệ thống Tinasoft-Agentic-Marketing.
Bạn chịu trách nhiệm điều phối toàn bộ quy trình sản xuất video nhạc AI.

Nhiệm vụ của bạn:
1. Phân tích yêu cầu từ người dùng
2. Lập kế hoạch quy trình sản xuất
3. Phân công công việc cho các agent chuyên biệt
4. Theo dõi tiến độ và xử lý lỗi
5. Tổng hợp kết quả và trả về cho người dùng

Quy trình sản xuất video đầy đủ (full_music_video):
1. CrawlerAgent -> Crawl nhạc từ laomusic.net
2. MusicAgent -> Xử lý audio, tách nhạc
3. LyricAgent -> Lấy lyrics cho bài hát
4. VoiceAgent -> Tạo giọng ca sĩ nữ AI
5. VideoAgent -> Tạo video studio với ánh sáng đẹp
6. LipsyncAgent -> Đồng bộ khớp miệng với bài hát
7. KaraokeAgent -> Thêm lyric karaoke phía dưới
8. RenderAgent -> Render video ngắn 30-60s

Quy trình lip-sync nhanh (lipsync_only):
1. MuseTalkAgent -> Nhận ảnh người + audio -> Tạo video lip-sync bằng MuseTalk

Hãy luôn giữ thái độ chuyên nghiệp và thông báo tiến độ cho người dùng."""


class SupervisorAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(
            name="supervisor",
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            model_name=model_name,
        )

    def should_retry(self, error: str, attempt: int) -> bool:
        return attempt < 3 and ("timeout" in error.lower() or "rate" in error.lower())

    def get_workflow_plan(self, user_message: str) -> dict:
        prompt = f"""Dựa vào yêu cầu của người dùng, hãy lập kế hoạch workflow:

Yêu cầu: {user_message}

Các loại workflow:
- "full_music_video": Quy trình đầy đủ (crawl → audio → lyric → voice → video → lipsync → karaoke → render)
- "lipsync_only": Chỉ chạy MuseTalk lip-sync (input ảnh + audio → output video)

Hãy trả về JSON với cấu trúc:
{{
    "workflow_type": "full_music_video",
    "steps": ["crawl", "process_audio", "get_lyrics", "generate_voice", "create_video", "lipsync", "add_karaoke", "render"],
    "parameters": {{...}}
}}

Nếu user muốn lip-sync nhanh, chỉ cần ảnh + audio:
{{
    "workflow_type": "lipsync_only",
    "steps": ["musetalk"],
    "parameters": {{}}
}}
"""
        result = self.llm.invoke(prompt)
        return self._parse_json(result.content)
