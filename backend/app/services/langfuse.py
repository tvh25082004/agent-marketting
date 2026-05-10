import logging
import json
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


class LangfuseService:
    def __init__(self):
        self.client = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse
                self.client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                self._initialized = True
                logger.info("Langfuse initialized successfully")
            except ImportError:
                logger.warning("langfuse package not installed")
            except Exception as e:
                logger.warning(f"Langfuse init failed: {e}")

    def log_llm_call(self, agent: str, model: str, prompt: str,
                     response: str, tokens: int, cost: float):
        self.initialize()
        if not self.client:
            return

        try:
            generation = self.client.generation(
                name=f"{agent}_llm_call",
                model=model,
                model_parameters={"max_tokens": settings.max_tokens_per_task},
                input=prompt,
                output=response,
                usage={"total_tokens": tokens},
                metadata={"agent": agent, "cost": cost},
            )
            generation.end()
        except Exception as e:
            logger.warning(f"Langfuse log failed: {e}")

    def create_trace(self, name: str, metadata: dict = None) -> Optional[any]:
        self.initialize()
        if not self.client:
            return None
        try:
            return self.client.trace(name=name, metadata=metadata or {})
        except Exception as e:
            logger.warning(f"Langfuse trace failed: {e}")
            return None

    def create_span(self, trace_id: str, name: str, metadata: dict = None) -> Optional[any]:
        self.initialize()
        if not self.client:
            return None
        try:
            return self.client.span(
                name=name,
                trace_id=trace_id,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.warning(f"Langfuse span failed: {e}")
            return None

    def score_observation(self, trace_id: str, name: str, value: float):
        self.initialize()
        if not self.client:
            return
        try:
            self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
            )
        except Exception as e:
            logger.warning(f"Langfuse score failed: {e}")


langfuse_service = LangfuseService()
