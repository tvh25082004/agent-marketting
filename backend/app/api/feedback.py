import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..schemas import FeedbackSubmit
from ..database import get_session
from ..models import FeedbackEntry, GeneratedVideo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=dict)
async def submit_feedback(feedback: FeedbackSubmit, session: AsyncSession = Depends(get_session)):
    try:
        entry = FeedbackEntry(
            task_id=feedback.task_id,
            video_id=feedback.video_id,
            score=feedback.score,
            feedback_text=feedback.feedback_text,
            feedback_type="explicit",
        )
        session.add(entry)

        if feedback.video_id:
            video_result = await session.execute(
                select(GeneratedVideo).where(GeneratedVideo.id == feedback.video_id)
            )
            video = video_result.scalar_one_or_none()
            if video:
                video.feedback_score = feedback.score
                video.feedback_notes = feedback.feedback_text

        await session.commit()
        return {"status": "recorded", "score": feedback.score}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[dict])
async def get_feedback(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(
            select(FeedbackEntry).order_by(FeedbackEntry.created_at.desc()).limit(100)
        )
        entries = result.scalars().all()
        return [
            {
                "id": e.id,
                "task_id": e.task_id,
                "video_id": e.video_id,
                "score": e.score,
                "feedback_text": e.feedback_text,
                "feedback_type": e.feedback_type,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
