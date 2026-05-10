import logging
import uuid
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..schemas import ScheduleConfig
from ..services.scheduler import scheduler_service
from ..workflow.graph import run_workflow
from ..config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/schedule", tags=["schedule"])


async def scheduled_task():
    task_id = str(uuid.uuid4())
    logger.info(f"[scheduled] Running automated crawl task: {task_id}")
    await run_workflow(
        task_id=task_id,
        message="Tự động crawl laomusic.net và tạo video mới",
        scheduled=True,
    )


@router.post("", response_model=dict)
async def create_schedule(config: ScheduleConfig):
    try:
        if config.enabled:
            scheduler_service.add_job(
                job_id="auto_crawl",
                func=scheduled_task,
                interval_minutes=config.interval_minutes,
            )
            return {
                "status": "scheduled",
                "message": f"Lịch trình đã được tạo: cứ {config.interval_minutes} phút crawl tự động",
                "interval_minutes": config.interval_minutes,
            }
        else:
            scheduler_service.remove_job("auto_crawl")
            return {
                "status": "disabled",
                "message": "Đã tắt lịch trình tự động",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=dict)
async def get_schedule():
    jobs = scheduler_service.list_jobs()
    return {
        "enabled": scheduler_service.is_running("auto_crawl"),
        "jobs": jobs,
    }


@router.delete("")
async def delete_schedule():
    scheduler_service.remove_job("auto_crawl")
    return {"status": "deleted", "message": "Đã xóa lịch trình"}
