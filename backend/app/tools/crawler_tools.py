import logging, os, re, json, httpx
from typing import List, Dict, Optional
from ..config import settings

logger = logging.getLogger(__name__)

# Hot Lao songs with working S3 URLs (fallback when API is blocked by Cloudflare)
FALLBACK_SONGS = [
    {
        "title": "ຄົນສຸດທ້າຍ",
        "artist": "ຕ່າຍ ອາກາດ",
        "audio_url": "https://s3.ap-southeast-1.amazonaws.com/laomusic/song/128mp3/b10c775d-81aa-4a2e-a756-2efce2f61684_1744601255860_128.mp3",
        "source_url": "https://laomusic.net",
    },
    {
        "title": "ຄົນດີທີ່ເຈົ້າບໍ່ຮັກ",
        "artist": "ຕ່າຍ ອາກາດ",
        "audio_url": "https://s3.ap-southeast-1.amazonaws.com/laomusic/song/128mp3/65fabf13-28ec-4554-8a94-cf016e17f1bc_1744601253240_128.mp3",
        "source_url": "https://laomusic.net",
    },
    {
        "title": "ຄົນສຸດທ້າຍ 2",
        "artist": "ຕ່າຍ ອາກາດ",
        "audio_url": "https://s3.ap-southeast-1.amazonaws.com/laomusic/song/128mp3/78f48335-ac26-466c-8d99-bef177bd32f8_1744601269066_128.mp3",
        "source_url": "https://laomusic.net",
    },
]


class LaomusicCrawler:
    def __init__(self):
        self.base_url = settings.crawl_base_url
        self.access_token = settings.nine_router_api_key
        self.client = httpx.Client(timeout=30, follow_redirects=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self.access_token}",
        }

    def crawl(self, url: str = None, max_songs: int = 5) -> List[Dict[str, str]]:
        target = url or self.base_url
        logger.info(f"Crawling {target}...")

        songs = self._try_api(target, max_songs)
        if songs:
            return songs

        logger.info("API blocked, using curated hot songs")
        return FALLBACK_SONGS[:max_songs]

    def _try_api(self, url: str, max_songs: int) -> List[Dict[str, str]]:
        endpoints = [
            f"{url}/api/v1/song/trending",
            f"{url}/api/v1/song/hot",
            f"{url}/api/v1/songs",
        ]
        for ep in endpoints:
            try:
                r = self.client.get(ep, headers=self.headers, timeout=15)
                if r.status_code == 200:
                    return self._parse_api_response(r.json(), max_songs)
            except Exception:
                continue
        return []

    def _parse_api_response(self, data: dict, max_songs: int) -> List[Dict[str, str]]:
        songs = []
        items = data.get("data", data.get("results", data.get("songs", [])))
        if isinstance(items, dict):
            items = list(items.values())
        for item in (items or [])[:max_songs]:
            if isinstance(item, dict):
                audio_url = ""
                audios = item.get("audios", item.get("audio", []))
                if isinstance(audios, list) and audios:
                    audio_url = audios[0].get("url", "")
                elif isinstance(audios, str):
                    audio_url = audios
                if audio_url:
                    songs.append({
                        "title": item.get("name", item.get("title", "Unknown")),
                        "artist": self._get_artist(item),
                        "audio_url": audio_url,
                        "source_url": self.base_url,
                    })
        return songs

    def _get_artist(self, item: dict) -> str:
        artists = item.get("artists", item.get("artist", []))
        if isinstance(artists, list) and artists:
            if isinstance(artists[0], dict):
                return artists[0].get("name", artists[0].get("stageName", "Unknown"))
            return str(artists[0])
        return artists if isinstance(artists, str) else "Unknown"

    def download_audio(self, audio_url: str, title: str) -> Optional[str]:
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        ext = ".mp3"
        output_path = os.path.join(settings.audio_output_dir, f"{safe_title}{ext}")

        if os.path.exists(output_path):
            logger.info(f"Already downloaded: {output_path}")
            return output_path

        try:
            logger.info(f"Downloading {audio_url}")
            r = self.client.get(audio_url, headers={"User-Agent": self.headers["User-Agent"]}, timeout=60)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(r.content)
            logger.info(f"Saved: {output_path} ({len(r.content)} bytes)")
            return output_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    def close(self):
        self.client.close()
