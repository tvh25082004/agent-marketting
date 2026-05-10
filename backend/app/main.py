import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .api import agents, schedule, memory, feedback
from .services.scheduler import scheduler_service
from .services.langfuse import langfuse_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    await init_db()
    langfuse_service.initialize()
    scheduler_service.start()
    yield
    scheduler_service.stop()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(schedule.router)
app.include_router(memory.router)
app.include_router(feedback.router)

os.makedirs(settings.video_output_dir, exist_ok=True)
app.mount("/api/videos", StaticFiles(directory=settings.video_output_dir), name="videos")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "models_available": settings.supported_models,
    }


@app.get("/api/models")
async def get_models():
    from .models.model_manager import model_manager
    return {
        "models": model_manager.get_available_models(),
        "default": settings.default_model,
    }
