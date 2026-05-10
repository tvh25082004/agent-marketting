import logging
import asyncio
from typing import Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from ..config import settings

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
        self._running = False

    def start(self):
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def stop(self):
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")

    def add_job(self, job_id: str, func: Callable, interval_minutes: int = 2,
                args: tuple = None, kwargs: dict = None):
        if job_id in self.jobs:
            self.remove_job(job_id)

        job = self.scheduler.add_job(
            func,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            args=args or (),
            kwargs=kwargs or {},
            replace_existing=True,
            max_instances=1,
        )
        self.jobs[job_id] = job
        logger.info(f"Scheduled job '{job_id}' every {interval_minutes} minutes")
        return job

    def remove_job(self, job_id: str):
        if job_id in self.jobs:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass
            del self.jobs[job_id]
            logger.info(f"Removed job '{job_id}'")

    def list_jobs(self) -> list:
        jobs = []
        for job_id, job in self.jobs.items():
            jobs.append({
                "id": job_id,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "interval_minutes": job.trigger.interval_length / 60 if hasattr(job.trigger, 'interval_length') else None,
            })
        return jobs

    def is_running(self, job_id: str) -> bool:
        return job_id in self.jobs


scheduler_service = TaskScheduler()
