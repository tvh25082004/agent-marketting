import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from .database import Base
import enum


class AgentTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(128), unique=True, index=True, nullable=False)
    workflow_type = Column(String(64), nullable=False)
    status = Column(SAEnum(AgentTaskStatus), default=AgentTaskStatus.PENDING)
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    model_used = Column(String(64), nullable=True)
    tokens_used = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    scheduled = Column(Boolean, default=False)

    steps = relationship("AgentStep", back_populates="task", cascade="all, delete-orphan")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("agent_tasks.id"), nullable=False)
    step_name = Column(String(64), nullable=False)
    agent_name = Column(String(64), nullable=False)
    status = Column(SAEnum(AgentTaskStatus), default=AgentTaskStatus.PENDING)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(64), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    task = relationship("AgentTask", back_populates="steps")


class CrawledSong(Base):
    __tablename__ = "crawled_songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    artist = Column(String(256), default="Unknown")
    audio_url = Column(String(512), nullable=False)
    audio_path = Column(String(512), nullable=True)
    lyrics = Column(Text, nullable=True)
    lyrics_path = Column(String(512), nullable=True)
    source_url = Column(String(512), nullable=False)
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed = Column(Boolean, default=False)


class GeneratedVideo(Base):
    __tablename__ = "generated_videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(128), ForeignKey("agent_tasks.task_id"), nullable=True)
    song_id = Column(Integer, ForeignKey("crawled_songs.id"), nullable=True)
    title = Column(String(256), nullable=False)
    video_path = Column(String(512), nullable=False)
    thumbnail_path = Column(String(512), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    video_url = Column(String(512), nullable=True)
    status = Column(String(32), default="completed")
    feedback_score = Column(Float, nullable=True)
    feedback_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(64), nullable=False)
    key = Column(String(256), nullable=False)
    value = Column(JSON, nullable=False)
    memory_type = Column(String(32), default="episodic")
    importance = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class FeedbackEntry(Base):
    __tablename__ = "feedback_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(128), ForeignKey("agent_tasks.task_id"), nullable=True)
    video_id = Column(Integer, ForeignKey("generated_videos.id"), nullable=True)
    score = Column(Float, nullable=False)
    feedback_text = Column(Text, nullable=True)
    feedback_type = Column(String(32), default="explicit")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
