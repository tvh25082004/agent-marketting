from typing import TypedDict, Optional, Any, List, Dict, Annotated
import operator


class AgentStep(TypedDict):
    step_name: str
    agent_name: str
    status: str
    input: Optional[Dict[str, Any]]
    output: Optional[Dict[str, Any]]
    tokens_used: int
    model_used: Optional[str]
    error: Optional[str]


class WorkflowState(TypedDict):
    task_id: str
    status: str
    workflow_type: str
    model: Optional[str]
    human_message: Optional[str]

    crawled_song: Optional[Dict[str, Any]]
    audio_path: Optional[str]
    image_path: Optional[str]
    reference_video: Optional[str]
    lyrics: Optional[str]
    lyrics_path: Optional[str]

    voice_path: Optional[str]
    voice_model: Optional[str]

    background_video_path: Optional[str]
    lipsync_video_path: Optional[str]
    karaoke_video_path: Optional[str]
    final_video_path: Optional[str]
    final_video_url: Optional[str]
    thumbnail_path: Optional[str]

    duration_seconds: Optional[float]
    output_metadata: Optional[Dict[str, Any]]

    current_step: Optional[str]
    steps: Annotated[List[AgentStep], operator.add]
    tokens_used: int
    total_cost: float
    error_message: Optional[str]

    scheduled: bool
    schedule_interval: Optional[int]
