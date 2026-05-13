import logging
import os
import uuid
import datetime
import subprocess
import json
import time
import shutil
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import UploadFile, File, Form

from ..schemas import (
    ChatRequest, ChatResponse, TaskStatus, TaskDetail,
    AgentStepResponse, VideoResponse, LipSyncResponse,
    UploadResponse, ProcessRequest, ProcessResponse,
    BatchProcessResponse, BatchJobResult,
)
from ..database import get_session
from ..models import AgentTask, AgentStep as AgentStepModel, GeneratedVideo, AgentTaskStatus
from ..workflow.graph import run_workflow
from ..agents.lipsync_agent import LipsyncAgent
from ..tools.video_motion_tools import VideoMotionTool
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])

PROJECT_ROOT = Path(settings.temp_dir).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output" / "videos"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
ALLOWED_VIDEO = {".mp4", ".mov", ".mkv", ".webm"}


def _get_ext(filename: str, defaults: dict) -> str:
    ext = os.path.splitext(filename or "file")[1].lower()
    return ext if ext else defaults.get("ext", ".bin")


def _save_upload(file: UploadFile, dest_dir: str, prefix: str = "") -> str:
    ext = _get_ext(file.filename or "file", {"ext": ".bin"})
    filename = f"{prefix}{ext}" if prefix else f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(dest_dir, filename)
    with open(dest_path, "wb") as f:
        f.write(file.file.read())
    return dest_path


@router.get("/assets")
async def list_input_assets():
    assets = {"audio": [], "images": [], "videos": []}
    groups = {
        "audio": ALLOWED_AUDIO,
        "images": ALLOWED_IMAGE,
        "videos": ALLOWED_VIDEO,
    }
    for item in sorted(INPUT_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_file():
            continue
        ext = item.suffix.lower()
        for group, extensions in groups.items():
            if ext in extensions:
                assets[group].append({
                    "name": item.name,
                    "path": f"input/{item.name}",
                    "size": item.stat().st_size,
                })
                break
    return assets


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    task_id = str(uuid.uuid4())

    try:
        task = AgentTask(
            task_id=task_id,
            workflow_type="music_video",
            status=AgentTaskStatus.PENDING,
            input_data={"message": request.message, "model": request.model, "scheduled": request.schedule},
            model_used=request.model or "default",
            started_at=datetime.datetime.utcnow()
        )
        session.add(task)
        await session.commit()

        background_tasks.add_task(
            run_workflow,
            task_id=task_id,
            message=request.message,
            model=request.model,
            scheduled=request.schedule or False,
        )

        return ChatResponse(
            task_id=task_id,
            status="running",
            message=f"Da khoi tao tac vu: {task_id}. He thong dang xu ly...",
            workflow_type="music_video",
        )
    except Exception as e:
        logger.error(f"Failed to start chat task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=List[TaskStatus])
async def list_tasks(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(AgentTask).order_by(AgentTask.created_at.desc()).limit(50)
        )
        tasks = result.scalars().all()

        return [
            TaskStatus(
                task_id=t.task_id,
                status=t.status.value if hasattr(t.status, 'value') else str(t.status),
                workflow_type=t.workflow_type,
                error_message=t.error_message,
                started_at=t.started_at,
                completed_at=t.completed_at,
                video_url=t.output_data.get("video_url") if t.output_data else None,
            )
            for t in tasks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(AgentTask).where(AgentTask.task_id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    steps_result = await session.execute(
        select(AgentStepModel).where(AgentStepModel.task_id == task.id)
    )
    steps = steps_result.scalars().all()

    return TaskDetail(
        task_id=task.task_id,
        workflow_type=task.workflow_type,
        status=task.status.value if hasattr(task.status, 'value') else str(task.status),
        input_data=task.input_data,
        output_data=task.output_data,
        tokens_used=task.tokens_used or 0,
        total_cost=task.total_cost or 0.0,
        model_used=task.model_used,
        steps=[
            AgentStepResponse(
                step_name=s.step_name,
                agent_name=s.agent_name,
                status=s.status.value if hasattr(s.status, 'value') else str(s.status),
                tokens_used=s.tokens_used or 0,
                model_used=s.model_used,
                started_at=s.started_at,
                completed_at=s.completed_at,
            )
            for s in steps
        ],
        created_at=task.created_at,
    )


@router.get("/videos", response_model=List[VideoResponse])
async def list_videos(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(GeneratedVideo).order_by(GeneratedVideo.created_at.desc()).limit(50)
        )
        videos = result.scalars().all()

        return [
            VideoResponse(
                id=v.id,
                title=v.title,
                video_path=v.video_path,
                video_url=v.video_url,
                thumbnail_path=v.thumbnail_path,
                duration_seconds=v.duration_seconds,
                status=v.status,
                feedback_score=v.feedback_score,
                created_at=v.created_at,
            )
            for v in videos
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Upload API ──────────────────────────────────────────────────────

@router.post("/upload/image", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    ext = _get_ext(file.filename or "image.jpg", {"ext": ".jpg"})
    if ext not in ALLOWED_IMAGE:
        raise HTTPException(status_code=400, detail=f"Invalid image format: {ext}")
    dest = _save_upload(file, str(INPUT_DIR), prefix=f"img_{uuid.uuid4().hex[:8]}")
    return UploadResponse(
        filename=os.path.basename(dest),
        path=f"input/{os.path.basename(dest)}",
        url=f"/static/input/{os.path.basename(dest)}",
        size=os.path.getsize(dest),
        file_type="image",
    )


@router.post("/upload/audio", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    ext = _get_ext(file.filename or "audio.mp3", {"ext": ".mp3"})
    if ext not in ALLOWED_AUDIO:
        raise HTTPException(status_code=400, detail=f"Invalid audio format: {ext}")
    dest = _save_upload(file, str(INPUT_DIR), prefix=f"aud_{uuid.uuid4().hex[:8]}")
    return UploadResponse(
        filename=os.path.basename(dest),
        path=f"input/{os.path.basename(dest)}",
        url=f"/static/input/{os.path.basename(dest)}",
        size=os.path.getsize(dest),
        file_type="audio",
    )


@router.post("/upload/video", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    ext = _get_ext(file.filename or "video.mp4", {"ext": ".mp4"})
    if ext not in ALLOWED_VIDEO:
        raise HTTPException(status_code=400, detail=f"Invalid video format: {ext}")
    dest = _save_upload(file, str(INPUT_DIR), prefix=f"vid_{uuid.uuid4().hex[:8]}")
    return UploadResponse(
        filename=os.path.basename(dest),
        path=f"input/{os.path.basename(dest)}",
        url=f"/static/input/{os.path.basename(dest)}",
        size=os.path.getsize(dest),
        file_type="video",
    )


# ── Direct Process API ──────────────────────────────────────────────

def _resolve_path(p: str) -> str:
    if p.startswith("input/"):
        return str(INPUT_DIR / Path(p).name)
    if p.startswith("/static/input/"):
        return str(INPUT_DIR / Path(p).name)
    return p


def _process_single(image_path: str, video_path: str, audio_path: str, task_id: str = None) -> str | None:
    image_path = _resolve_path(image_path)
    video_path = _resolve_path(video_path)
    audio_path = _resolve_path(audio_path)

    for p, name in [(image_path, "Image"), (video_path, "Video"), (audio_path, "Audio")]:
        if not os.path.exists(p):
            logger.error(f"{name} not found: {p}")
            return None

    try:
        tool = VideoMotionTool()
        if not tool.ready():
            logger.warning("InsightFace not ready, using fallback synthetic mode")

        result = tool.generate(
            source_image=image_path,
            reference_video=video_path,
            audio_path=audio_path,
        )
        return result
    except Exception as e:
        logger.error(f"Process failed: {e}")
        return None


@router.post("/process", response_model=ProcessResponse)
async def direct_process(
    request: ProcessRequest,
    session: AsyncSession = Depends(get_session),
):
    task_id = str(uuid.uuid4())

    task = AgentTask(
        task_id=task_id,
        workflow_type="direct_process",
        status=AgentTaskStatus.PENDING,
        input_data={"image": request.image_path, "video": request.video_path, "audio": request.audio_path},
        model_used="direct",
        started_at=datetime.datetime.utcnow(),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    try:
        await session.execute(
            select(AgentTask).where(AgentTask.task_id == task_id)
        )
        await session.execute(
            select(AgentTask).where(AgentTask.task_id == task_id)
        )

        video_path = _process_single(request.image_path, request.video_path, request.audio_path, task_id)

        if video_path and os.path.exists(video_path):
            video_url = f"/api/videos/{os.path.basename(video_path)}"
            task.status = AgentTaskStatus.COMPLETED
            task.output_data = {"video_url": video_url, "video_path": video_path}
            task.completed_at = datetime.datetime.utcnow()
            await session.commit()

            existing = await session.execute(
                select(GeneratedVideo).where(GeneratedVideo.task_id == task_id)
            )
            if not existing.scalar_one_or_none():
                session.add(GeneratedVideo(
                    task_id=task_id,
                    title=f"Direct_{os.path.basename(video_path)}",
                    video_path=video_path,
                    video_url=video_url,
                    status="completed",
                ))
                await session.commit()

            return ProcessResponse(
                task_id=task_id,
                status="completed",
                video_url=video_url,
                video_path=video_path,
            )

        task.status = AgentTaskStatus.FAILED
        task.error_message = "Pipeline produced no output"
        task.completed_at = datetime.datetime.utcnow()
        await session.commit()

        return ProcessResponse(
            task_id=task_id,
            status="failed",
            message="Pipeline produced no output",
        )

    except Exception as e:
        logger.error(f"Direct process error: {e}")
        task.status = AgentTaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.datetime.utcnow()
        await session.commit()

        return ProcessResponse(
            task_id=task_id,
            status="failed",
            message=str(e),
        )


# ── Batch Process API ──────────────────────────────────────────────

@router.post("/batch", response_model=BatchProcessResponse)
async def batch_process(
    image_path: str = Form(...),
    video_path: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    task_id = str(uuid.uuid4())
    image_path = _resolve_path(image_path)
    video_path = _resolve_path(video_path)

    audio_files = sorted([
        f for f in INPUT_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in ALLOWED_AUDIO
    ])

    if not audio_files:
        raise HTTPException(status_code=400, detail="No audio files in input/")

    logger.info(f"Batch {task_id}: {len(audio_files)} audios with img={image_path}, vid={video_path}")

    task = AgentTask(
        task_id=task_id,
        workflow_type="batch_process",
        status=AgentTaskStatus.RUNNING,
        input_data={"image": image_path, "video": video_path, "audio_count": len(audio_files)},
        model_used="direct",
        started_at=datetime.datetime.utcnow(),
    )
    session.add(task)
    await session.commit()

    results = []
    success_count = 0

    for af in audio_files:
        job_id = str(uuid.uuid4())
        logger.info(f"  Processing {af.name}...")

        video_result = _process_single(
            image_path=image_path,
            video_path=video_path,
            audio_path=str(af),
            task_id=job_id,
        )

        if video_result and os.path.exists(video_result):
            video_url = f"/api/videos/{os.path.basename(video_result)}"
            results.append(BatchJobResult(
                audio_name=af.name,
                status="completed",
                video_url=video_url,
                video_path=video_result,
            ))

            session.add(GeneratedVideo(
                task_id=task_id,
                title=f"Batch_{af.stem}",
                video_path=video_result,
                video_url=video_url,
                status="completed",
            ))
            success_count += 1
        else:
            results.append(BatchJobResult(
                audio_name=af.name,
                status="failed",
            ))

        await session.commit()

    task.status = AgentTaskStatus.COMPLETED
    task.output_data = {
        "total": len(audio_files),
        "success": success_count,
        "failed": len(audio_files) - success_count,
    }
    task.completed_at = datetime.datetime.utcnow()
    await session.commit()

    return BatchProcessResponse(
        task_id=task_id,
        status="completed",
        total=len(audio_files),
        results=results,
    )


# ── Lipsync (Original, enhanced) ────────────────────────────────────

@router.post("/lipsync")
async def direct_lipsync(
    image: UploadFile = File(...),
    audio: UploadFile = File(...),
    video: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    task_id = str(uuid.uuid4())
    upload_dir = os.path.join(settings.temp_dir, "uploads", task_id)
    os.makedirs(upload_dir, exist_ok=True)

    img_ext = _get_ext(image.filename or "image.jpg", {"ext": ".jpg"})
    aud_ext = _get_ext(audio.filename or "audio.mp3", {"ext": ".mp3"})
    image_path = os.path.join(upload_dir, f"input{img_ext}")
    audio_path = os.path.join(upload_dir, f"audio{aud_ext}")

    img_data = await image.read()
    with open(image_path, "wb") as f:
        f.write(img_data)
    aud_data = await audio.read()
    with open(audio_path, "wb") as f:
        f.write(aud_data)

    # Use uploaded video or fallback to default
    if video:
        vid_ext = _get_ext(video.filename or "video.mp4", {"ext": ".mp4"})
        video_path = os.path.join(upload_dir, f"video{vid_ext}")
        vid_data = await video.read()
        with open(video_path, "wb") as f:
            f.write(vid_data)
    else:
        video_path = str(INPUT_DIR / "videoinput.mp4")
        if not os.path.exists(video_path):
            video_path = None

    if not video_path:
        return LipSyncResponse(
            task_id=task_id,
            status="failed",
            error="No video provided and no default video found",
        )

    try:
        tool = VideoMotionTool()
        video_result = tool.generate(
            source_image=image_path,
            reference_video=video_path,
            audio_path=audio_path,
        )
        video_url = f"/api/videos/{os.path.basename(video_result)}" if video_result else None

        return LipSyncResponse(
            task_id=task_id,
            status="completed" if video_result else "failed",
            video_url=video_url,
            video_path=video_result,
            duration_seconds=None,
            used_fallback=not tool.ready(),
            error=None if video_result else "Pipeline produced no output",
        )
    except Exception as e:
        logger.error(f"Lipsync failed: {e}")
        return LipSyncResponse(
            task_id=task_id,
            status="failed",
            error=str(e),
        )
