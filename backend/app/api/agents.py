import logging
import os
import uuid
import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import UploadFile, File, Form

from ..schemas import (
    ChatRequest, ChatResponse, TaskStatus, TaskDetail,
    AgentStepResponse, VideoResponse, LipSyncResponse,
)
from ..database import get_session
from ..models import AgentTask, AgentStep as AgentStepModel, GeneratedVideo, AgentTaskStatus
from ..workflow.graph import run_workflow
from ..agents.lipsync_agent import LipsyncAgent
from ..tools.video_motion_tools import VideoMotionTool
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    task_id = str(uuid.uuid4())

    try:
        # TẠO RECORD VÀO DB TRƯỚC TIÊN ĐỂ FIX LỖI 404 KHI FRONTEND POLL
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
            message=f"Đã khởi tạo tác vụ: {task_id}. Hệ thống đang xử lý yêu cầu của bạn...",
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


@router.post("/lipsync")
async def direct_lipsync(
    image: UploadFile = File(...),
    audio: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    task_id = str(uuid.uuid4())
    upload_dir = os.path.join(settings.temp_dir, "uploads", task_id)
    os.makedirs(upload_dir, exist_ok=True)

    img_ext = os.path.splitext(image.filename or "image.jpg")[1] or ".jpg"
    aud_ext = os.path.splitext(audio.filename or "audio.mp3")[1] or ".mp3"
    image_path = os.path.join(upload_dir, f"input{img_ext}")
    audio_path = os.path.join(upload_dir, f"audio{aud_ext}")

    img_data = await image.read()
    with open(image_path, "wb") as f:
        f.write(img_data)
    aud_data = await audio.read()
    with open(audio_path, "wb") as f:
        f.write(aud_data)

    try:
        tool = VideoMotionTool()
        video_path = tool.generate(
            source_image=image_path,
            reference_video=os.path.join(
                os.path.dirname(os.path.dirname(settings.temp_dir)), "input", "videoinput.mp4"
            ),
            audio_path=audio_path,
        )
        video_url = f"/api/videos/{os.path.basename(video_path)}" if video_path else None

        return LipSyncResponse(
            task_id=task_id,
            status="completed" if video_path else "failed",
            video_url=video_url,
            video_path=video_path,
            duration_seconds=None,
            used_fallback=not tool.ready(),
            error=None if video_path else "Pipeline produced no output",
        )
    except Exception as e:
        logger.error(f"Lipsync failed: {e}")
        return LipSyncResponse(
            task_id=task_id,
            status="failed",
            error=str(e),
        )
