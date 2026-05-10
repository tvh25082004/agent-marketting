import json
import logging
import time
from typing import Optional, Any, Dict
from ..models.model_manager import model_manager
from ..services.langfuse import langfuse_service

logger = logging.getLogger(__name__)


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model_name: Optional[str] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.llm = model_manager.get_model(model_name)
        self.total_tokens = 0
        self.total_cost = 0.0

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    def update_model(self, model_name: str):
        self.model_name = model_name
        self.llm = model_manager.get_model(model_name)

    def log_llm_call(self, prompt: str, response: str, tokens: int, model: str):
        self.total_tokens += tokens
        cost = model_manager.calculate_cost(model, tokens)
        self.total_cost += cost
        langfuse_service.log_llm_call(
            agent=self.name,
            model=model,
            prompt=prompt,
            response=response,
            tokens=tokens,
            cost=cost,
        )

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        try:
            result = self._execute(input_data)
            elapsed = time.time() - start
            logger.info(f"[{self.name}] completed in {elapsed:.2f}s | tokens={self.total_tokens} | cost=${self.total_cost:.4f}")
            return {"status": "completed", "data": result, "tokens_used": self.total_tokens, "cost": self.total_cost}
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[{self.name}] failed after {elapsed:.2f}s: {e}")
            return {"status": "failed", "error": str(e), "tokens_used": self.total_tokens, "cost": self.total_cost}

    def should_retry(self, error: str, attempt: int) -> bool:
        return False

    def _execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
