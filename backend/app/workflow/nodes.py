import os, logging, json
from typing import Dict, Any
from .state import WorkflowState, AgentStep
from ..agents.crawler_agent import CrawlerAgent
from ..agents.music_agent import MusicAgent
from ..agents.lyric_agent import LyricAgent
from ..agents.voice_agent import VoiceAgent
from ..agents.video_agent import VideoAgent
from ..agents.lipsync_agent import LipsyncAgent
from ..agents.karaoke_agent import KaraokeAgent
from ..agents.render_agent import RenderAgent
from ..agents.feedback_agent import FeedbackAgent
from ..agents.supervisor import SupervisorAgent
from ..memory.manager import memory_manager
from ..services.langfuse import langfuse_service
from ..config import settings

logger = logging.getLogger(__name__)

# Path to the singer image (project root / input / input.jpeg)
SINGER_IMAGE = os.path.join(os.path.dirname(os.path.dirname(settings.temp_dir)), "input", "input.jpeg")


def create_step(name, agent, status="running", inp=None, out=None, tokens=0, model=None, error=None):
    return AgentStep(step_name=name, agent_name=agent, status=status,
                     input=inp or {}, output=out or {},
                     tokens_used=tokens, model_used=model, error=error)


async def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info(f"[supervisor] Planning for task {state.get('task_id')}")
    agent = SupervisorAgent(state.get("model"))
    plan = agent.get_workflow_plan(state.get("human_message", ""))
    wf_type = plan.get("workflow_type", "full_music_video")

    step_map = {
        "lipsync_only": "lipsync",
        "full_music_video": "crawl",
    }
    current_step = step_map.get(wf_type, "crawl")

    return {
        "workflow_type": wf_type,
        "current_step": current_step,
        "status": "running",
        "steps": [create_step("supervisor_plan", "supervisor", "completed",
                              inp={"message": state.get("human_message")},
                              out={"plan": plan},
                              tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model)],
    }


async def crawl_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[crawler] Starting crawl")
    agent = CrawlerAgent(state.get("model"))
    context = await memory_manager.get_context("crawler")
    result = agent.run({"url": settings.crawl_base_url, "max_songs": settings.max_songs_per_crawl, "context": context})
    songs = result.get("data", {}).get("songs", [])
    song = songs[0] if songs else {}

    if song:
        await memory_manager.remember("crawler", f"song_{song.get('title')}", song)

    return {
        "crawled_song": song,
        "audio_path": song.get("audio_path"),
        "current_step": "process_audio" if result["status"] == "completed" else "failed",
        "status": "running" if result["status"] == "completed" else "failed",
        "steps": [create_step("crawl_music", "crawler", result["status"],
                              inp={"url": settings.crawl_base_url},
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }


async def process_audio_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[music] Processing audio")
    agent = MusicAgent(state.get("model"))
    result = agent.run({"audio_path": state.get("audio_path")})

    # Also pass image path in state for later use
    return {
        "current_step": "get_lyrics",
        "image_path": SINGER_IMAGE,
        "steps": [create_step("process_audio", "music", result["status"],
                              inp={"audio_path": state.get("audio_path")},
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }


async def get_lyrics_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[lyric] Getting lyrics")
    agent = LyricAgent(state.get("model"))
    song = state.get("crawled_song", {})
    result = agent.run({"title": song.get("title", ""), "audio_path": state.get("audio_path")})

    return {
        "lyrics": result.get("data", {}).get("lyrics"),
        "lyrics_path": result.get("data", {}).get("srt_path"),
        "current_step": "generate_voice",
        "steps": [create_step("get_lyrics", "lyric", result["status"],
                              inp={"title": song.get("title")},
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }


async def generate_voice_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[voice] Using original audio (no TTS needed)")
    agent = VoiceAgent(state.get("model"))
    result = agent.run({"audio_path": state.get("audio_path")})

    return {
        "voice_path": result.get("data", {}).get("voice_path"),
        "current_step": "create_video",
        "steps": [create_step("generate_voice", "voice", result["status"],
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }


async def create_video_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[video] Creating singer video")
    agent = VideoAgent(state.get("model"))
    song = state.get("crawled_song", {})
    result = agent.run({
        "audio_path": state.get("audio_path"),
        "voice_path": state.get("voice_path"),
        "lyrics": state.get("lyrics"),
        "title": song.get("title", ""),
        "image_path": state.get("image_path") or SINGER_IMAGE,
    })

    return {
        "background_video_path": result.get("data", {}).get("background_video_path"),
        "duration_seconds": result.get("data", {}).get("duration_seconds"),
        "current_step": "lipsync",
        "steps": [create_step("create_video", "video", result["status"],
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }


async def lipsync_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[lipsync] Running face-swap + lip-sync pipeline")
    agent = LipsyncAgent(state.get("model"))
    result = agent.run({
        "image_path": state.get("image_path") or SINGER_IMAGE,
        "voice_path": state.get("voice_path") or state.get("audio_path"),
    })

    ok = result["status"] == "completed"
    return {
        "lipsync_video_path": result.get("data", {}).get("lipsync_video_path"),
        "current_step": "add_karaoke" if ok else "failed",
        "status": "running" if ok else "failed",
        "error_message": None if ok else result.get("error"),
        "steps": [create_step("lipsync", "lipsync", result["status"],
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }



async def add_karaoke_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[karaoke] Pass-through (integrated in video)")
    agent = KaraokeAgent(state.get("model"))
    result = agent.run({"lipsync_video_path": state.get("lipsync_video_path"),
                        "background_video_path": state.get("background_video_path")})

    return {
        "karaoke_video_path": result.get("data", {}).get("karaoke_video_path"),
        "current_step": "render",
        "steps": [create_step("add_karaoke", "karaoke", result["status"],
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }


async def render_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[render] Rendering final video")
    agent = RenderAgent(state.get("model"))
    result = agent.run({
        "karaoke_video_path": state.get("karaoke_video_path"),
        "lipsync_video_path": state.get("lipsync_video_path"),
        "background_video_path": state.get("background_video_path"),
    })

    final_path = result.get("data", {}).get("final_video_path")
    duration = result.get("data", {}).get("duration_seconds")
    song = state.get("crawled_song", {})
    video_url = f"/api/videos/{os.path.basename(final_path)}" if final_path and os.path.exists(final_path) else None

    if final_path and os.path.exists(final_path):
        await memory_manager.remember("render", f"video_{song.get('title', 'unknown')}",
                                      {"path": final_path, "url": video_url, "duration": duration, "title": song.get("title")})

    return {
        "final_video_path": final_path,
        "final_video_url": video_url,
        "duration_seconds": duration,
        "current_step": "completed",
        "status": "completed",
        "output_metadata": {"song_title": song.get("title"), "song_artist": song.get("artist"), "duration": duration, "video_url": video_url},
        "steps": [create_step("render", "render", result["status"],
                              out=result, tokens=agent.total_tokens,
                              model=agent.model_name or settings.default_model,
                              error=result.get("error"))],
    }


async def feedback_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[feedback] Analyzing results")
    agent = FeedbackAgent(state.get("model"))
    result = agent.run({
        "video_info": {"title": state.get("crawled_song", {}).get("title"), "duration": state.get("duration_seconds"), "path": state.get("final_video_path")},
        "task_history": state.get("steps", []),
    })
    feedback_data = result.get("data", {})
    if feedback_data:
        await memory_manager.remember("feedback", f"feedback_{state['task_id']}", feedback_data, importance=0.8)

    return {"steps": [create_step("feedback_analysis", "feedback", result["status"],
                                  out=result, tokens=agent.total_tokens,
                                  model=agent.model_name or settings.default_model,
                                  error=result.get("error"))]}
