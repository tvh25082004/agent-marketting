from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict
import datetime


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    schedule: Optional[bool] = False
    interval_minutes: Optional[int] = 2


class ChatResponse(BaseModel):
    task_id: str
    status: str
    message: str
    workflow_type: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    workflow_type: str
    current_step: Optional[str] = None
    progress: Optional[float] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    video_url: Optional[str] = None


class AgentStepResponse(BaseModel):
    step_name: str
    agent_name: str
    status: str
    tokens_used: int
    model_used: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None


class TaskDetail(BaseModel):
    task_id: str
    workflow_type: str
    status: str
    input_data: Optional[Dict] = None
    output_data: Optional[Dict] = None
    tokens_used: int
    total_cost: float
    model_used: Optional[str] = None
    steps: List[AgentStepResponse] = []
    created_at: Optional[datetime.datetime] = None


class ScheduleConfig(BaseModel):
    enabled: bool
    interval_minutes: int = 2
    max_songs: int = 5
    model: Optional[str] = None


class MemorySearch(BaseModel):
    agent_name: Optional[str] = None
    key: Optional[str] = None
    memory_type: Optional[str] = None
    query: Optional[str] = None
    limit: int = 20


class FeedbackSubmit(BaseModel):
    task_id: Optional[str] = None
    video_id: Optional[int] = None
    score: float = Field(ge=0, le=10)
    feedback_text: Optional[str] = None


class LipSyncResponse(BaseModel):
    task_id: str
    status: str
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    used_fallback: bool = False
    error: Optional[str] = None


class ModelConfig(BaseModel):
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class VideoResponse(BaseModel):
    id: int
    title: str
    video_path: str
    video_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str
    feedback_score: Optional[float] = None
    created_at: Optional[datetime.datetime] = None
