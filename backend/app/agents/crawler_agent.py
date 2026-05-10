import logging, os
from typing import Optional, Dict, Any
from .base import BaseAgent
from ..tools.crawler_tools import LaomusicCrawler

logger = logging.getLogger(__name__)

CRAWLER_SYSTEM_PROMPT = """Bạn là Crawler Agent chuyên crawl dữ liệu nhạc từ laomusic.net.
Nhiệm vụ:
1. Crawl danh sách bài hát từ laomusic.net (dùng API hoặc danh sách có sẵn)
2. Tải file audio (MP3) từ S3 về máy
3. Trích xuất thông tin bài hát (title, artist)
4. Báo cáo kết quả"""


class CrawlerAgent(BaseAgent):
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(name="crawler", system_prompt=CRAWLER_SYSTEM_PROMPT, model_name=model_name)
        self.crawler = LaomusicCrawler()

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        url = input_data.get("url", "https://laomusic.net")
        max_songs = input_data.get("max_songs", 5)

        songs = self.crawler.crawl(url, max_songs)
        if not songs:
            return {"songs": [], "total": 0, "message": "Không tìm thấy bài hát nào"}

        results = []
        for song in songs:
            audio_path = self.crawler.download_audio(song["audio_url"], song["title"])
            song["audio_path"] = audio_path
            song["crawled"] = True
            results.append(song)

        return {"songs": results, "total": len(results), "message": f"Đã crawl {len(results)} bài hát"}
