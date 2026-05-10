from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List
import os

_BASE = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Tinasoft-Agentic-Marketing"
    app_version: str = "1.0.0"
    debug: bool = True

    database_url: str = "sqlite+aiosqlite:///./tinasoft.db"
    redis_url: str = "redis://localhost:6379/0"

    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    nine_router_base_url: str = "http://localhost:20128/v1"
    nine_router_api_key: str = "sk-259b9f08e24eebc4-5afkfh-ccf90543"

    supported_models: List[str] = [
        "gpt-4o", "gpt-4o-mini",
        "claude-sonnet-4-20250514", "claude-haiku-3-5",
        "llama3", "mistral", "qwen2",
        "gemini", "gc/gemini-3-flash-preview", "gc/gemini-3-pro-preview",
        "ag/gemini-3-flash", "ag/gemini-3.1-pro-low",
    ]

    default_model: str = "gemini"
    max_tokens_per_task: int = 32000
    max_concurrent_agents: int = 5
    agent_timeout_seconds: int = 300

    output_dir: str = str(_BASE / "output")
    video_output_dir: str = str(_BASE / "output" / "videos")
    audio_output_dir: str = str(_BASE / "output" / "audio")
    temp_dir: str = str(_BASE / "temp")
    upload_dir: str = str(_BASE / "temp" / "uploads")

    crawl_interval_minutes: int = 2
    crawl_base_url: str = "https://laomusic.net"
    max_songs_per_crawl: int = 5

    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30
    video_duration_min: int = 30
    video_duration_max: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
os.makedirs(settings.output_dir, exist_ok=True)
os.makedirs(settings.video_output_dir, exist_ok=True)
os.makedirs(settings.audio_output_dir, exist_ok=True)
os.makedirs(settings.temp_dir, exist_ok=True)
