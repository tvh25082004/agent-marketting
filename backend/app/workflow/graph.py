import logging
import uuid
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from .state import WorkflowState
from . import nodes

logger = logging.getLogger(__name__)


def should_continue(state: WorkflowState) -> Literal["crawl", "process_audio", "get_lyrics",
                                                       "generate_voice", "create_video",
                                                       "lipsync",
                                                       "add_karaoke", "render",
                                                       "feedback", END]:
    status = state.get("status", "running")
    if status == "failed":
        return END

    current = state.get("current_step", "")
    step_map = {
        "crawl": "crawl",
        "process_audio": "process_audio",
        "get_lyrics": "get_lyrics",
        "generate_voice": "generate_voice",
        "create_video": "create_video",
        "lipsync": "lipsync",
        "add_karaoke": "add_karaoke",
        "render": "render",
        "completed": "feedback",
    }

    return step_map.get(current, END)


def create_workflow() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    workflow.add_node("supervisor", nodes.supervisor_node)
    workflow.add_node("crawl", nodes.crawl_node)
    workflow.add_node("process_audio", nodes.process_audio_node)
    workflow.add_node("get_lyrics", nodes.get_lyrics_node)
    workflow.add_node("generate_voice", nodes.generate_voice_node)
    workflow.add_node("create_video", nodes.create_video_node)
    workflow.add_node("lipsync", nodes.lipsync_node)
    workflow.add_node("add_karaoke", nodes.add_karaoke_node)
    workflow.add_node("render", nodes.render_node)
    workflow.add_node("feedback", nodes.feedback_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "crawl": "crawl",
            "lipsync": "lipsync",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "crawl",
        should_continue,
        {
            "process_audio": "process_audio",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "process_audio",
        should_continue,
        {
            "get_lyrics": "get_lyrics",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "get_lyrics",
        should_continue,
        {
            "generate_voice": "generate_voice",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "generate_voice",
        should_continue,
        {
            "create_video": "create_video",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "create_video",
        should_continue,
        {
            "lipsync": "lipsync",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "lipsync",
        should_continue,
        {
            "add_karaoke": "add_karaoke",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "add_karaoke",
        should_continue,
        {
            "render": "render",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "render",
        should_continue,
        {
            "feedback": "feedback",
            END: END,
        }
    )

    workflow.add_conditional_edges(
        "feedback",
        lambda s: END,
        {END: END}
    )

    return workflow


compiled_workflow = create_workflow().compile()


import asyncio
from ..database import async_session
from ..models import AgentTask, AgentStep, AgentTaskStatus, GeneratedVideo
from sqlalchemy import select, update
import datetime
import os

async def run_workflow(task_id: str, message: str,
                       model: str = None, scheduled: bool = False) -> Dict[str, Any]:
    initial_state: WorkflowState = {
        "task_id": task_id,
        "status": "running",
        "workflow_type": "music_video",
        "model": model,
        "human_message": message,
        "crawled_song": {},
        "audio_path": None,
        "image_path": None,
        "lyrics": None,
        "lyrics_path": None,
        "voice_path": None,
        "voice_model": None,
        "background_video_path": None,
        "lipsync_video_path": None,
        "karaoke_video_path": None,
        "final_video_path": None,
        "final_video_url": None,
        "thumbnail_path": None,
        "duration_seconds": None,
        "output_metadata": {},
        "current_step": "supervisor",
        "steps": [],
        "tokens_used": 0,
        "total_cost": 0.0,
        "error_message": None,
        "scheduled": scheduled,
        "schedule_interval": 2,
    }

    try:
        async with async_session() as session:
            await session.execute(
                update(AgentTask)
                .where(AgentTask.task_id == task_id)
                .values(status=AgentTaskStatus.RUNNING)
            )
            await session.commit()

        result = await compiled_workflow.ainvoke(initial_state)

        async with async_session() as session:
            db_status = AgentTaskStatus.COMPLETED if result.get("status") != "failed" else AgentTaskStatus.FAILED

            for step in result.get("steps", []):
                db_step = AgentStep(
                    task_id=(await session.execute(select(AgentTask.id).where(AgentTask.task_id == task_id))).scalar_one(),
                    step_name=step.get("agent_name", "unknown"),
                    agent_name=step.get("agent_name", "unknown"),
                    status=AgentTaskStatus.COMPLETED if "error" not in str(step) else AgentTaskStatus.FAILED,
                    output_data=step,
                    completed_at=datetime.datetime.utcnow()
                )
                session.add(db_step)

            await session.execute(
                update(AgentTask)
                .where(AgentTask.task_id == task_id)
                .values(
                    status=db_status,
                    output_data={"video_url": result.get("final_video_url"), "video_path": result.get("final_video_path")},
                    error_message=result.get("error_message"),
                    completed_at=datetime.datetime.utcnow()
                )
            )

            final_path = result.get("final_video_path")
            final_url = result.get("final_video_url")
            if db_status == AgentTaskStatus.COMPLETED and final_path and os.path.exists(final_path):
                existing = await session.execute(
                    select(GeneratedVideo).where(GeneratedVideo.task_id == task_id)
                )
                if not existing.scalar_one_or_none():
                    workflow_type = result.get("workflow_type") or "music_video"
                    title = "AI Dancing Lao MV" if workflow_type == "ai_dancing" else "Lao Music Video"
                    session.add(GeneratedVideo(
                        task_id=task_id,
                        title=title,
                        video_path=final_path,
                        video_url=final_url or f"/api/videos/{os.path.basename(final_path)}",
                        duration_seconds=result.get("duration_seconds"),
                        status="completed",
                    ))
            await session.commit()

        return result
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        async with async_session() as session:
            await session.execute(
                update(AgentTask)
                .where(AgentTask.task_id == task_id)
                .values(status=AgentTaskStatus.FAILED, error_message=str(e), completed_at=datetime.datetime.utcnow())
            )
            await session.commit()
        return {"status": "failed", "error_message": str(e)}


def get_workflow_graph() -> str:
    return compiled_workflow.get_graph().draw_mermaid()
