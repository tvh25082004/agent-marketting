import logging
from typing import Optional, Any
from ..config import settings

logger = logging.getLogger(__name__)


class ModelWrapper:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def invoke(self, prompt: str) -> Any:
        raise NotImplementedError

    def get_model_info(self) -> dict:
        return {"name": self.model_name, "type": "base"}


class OpenAIModel(ModelWrapper):
    def __init__(self, model_name: str = None):
        super().__init__(model_name or settings.openai_model)
        self.api_key = settings.openai_api_key
        self.client = None

    def _ensure_client(self):
        if self.client is None:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai package not installed, using mock")

    def invoke(self, prompt: str) -> Any:
        self._ensure_client()
        if self.client is None:
            return type('Response', (), {'content': f'Mock response for: {prompt[:50]}...'})()

        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=settings.max_tokens_per_task,
        )
        return response.choices[0].message

    def get_model_info(self) -> dict:
        return {"name": self.model_name, "type": "openai", "provider": "OpenAI"}


class AnthropicModel(ModelWrapper):
    def __init__(self, model_name: str = None):
        super().__init__(model_name or settings.anthropic_model)
        self.api_key = settings.anthropic_api_key

    def invoke(self, prompt: str) -> Any:
        if not self.api_key:
            return type('Response', (), {'content': f'Mock Anthropic: {prompt[:50]}...'})()

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model_name,
                max_tokens=settings.max_tokens_per_task,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text if message.content else type('Response', (), {'content': ''})()
        except ImportError:
            return type('Response', (), {'content': f'Mock Anthropic: {prompt[:50]}...'})()

    def get_model_info(self) -> dict:
        return {"name": self.model_name, "type": "anthropic", "provider": "Anthropic"}


class OllamaModel(ModelWrapper):
    def __init__(self, model_name: str = None):
        super().__init__(model_name or settings.ollama_model)
        self.base_url = settings.ollama_base_url

    def invoke(self, prompt: str) -> Any:
        try:
            import httpx
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            data = response.json()
            return type('Response', (), {'content': data.get("response", "")})()
        except Exception as e:
            logger.warning(f"Ollama invoke failed: {e}")
            return type('Response', (), {'content': f'Mock Ollama: {prompt[:50]}...'})()

    def get_model_info(self) -> dict:
        return {"name": self.model_name, "type": "ollama", "provider": "Ollama"}


class NineRouterModel(ModelWrapper):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.base_url = settings.nine_router_base_url
        self.api_key = settings.nine_router_api_key
        self.client = None

    def _ensure_client(self):
        if self.client is None:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                logger.warning("openai package not installed, using mock")

    def invoke(self, prompt: str) -> Any:
        self._ensure_client()
        if self.client is None:
            return type('Response', (), {'content': f'[9Router:{self.model_name}] Mock: {prompt[:50]}...'})()

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.max_tokens_per_task,
            )
            return response.choices[0].message
        except Exception as e:
            logger.error(f"9Router invoke failed for {self.model_name}: {e}")
            return type('Response', (), {'content': f'[9Router Error] {e}'})()

    def get_model_info(self) -> dict:
        return {"name": self.model_name, "type": "9router", "provider": "9Router"}


class ModelManager:
    def __init__(self):
        self._models = {}
        self._default_model = settings.default_model

    def get_model(self, model_name: Optional[str] = None) -> ModelWrapper:
        name = model_name or self._default_model
        if name not in self._models:
            self._models[name] = self._create_model(name)
        return self._models[name]

    def _create_model(self, name: str) -> ModelWrapper:
        if "/" in name or name in ("gemini",):
            return NineRouterModel(name)
        elif name.startswith("gpt"):
            return OpenAIModel(name)
        elif name.startswith("claude"):
            return AnthropicModel(name)
        elif name in ("llama3", "mistral", "qwen2"):
            return OllamaModel(name)
        elif name.startswith("o3") or name.startswith("o1"):
            return OpenAIModel(name)
        else:
            logger.warning(f"Unknown model {name}, falling back to 9Router")
            return NineRouterModel(name)

    def calculate_cost(self, model_name: str, tokens: int) -> float:
        rates = {
            "gpt-4o": (2.5 / 1_000_000, 10.0 / 1_000_000),
            "gpt-4o-mini": (0.15 / 1_000_000, 0.6 / 1_000_000),
            "claude-sonnet-4-20250514": (3.0 / 1_000_000, 15.0 / 1_000_000),
            "claude-haiku-3-5": (0.8 / 1_000_000, 4.0 / 1_000_000),
        }
        if "/" in model_name:
            return tokens * 0.0000001
        if model_name in rates:
            input_rate, output_rate = rates[model_name]
            return tokens * input_rate
        return tokens * 0.000001

    def get_available_models(self) -> list:
        return settings.supported_models

    def set_default_model(self, model_name: str):
        if model_name in settings.supported_models:
            self._default_model = model_name


model_manager = ModelManager()
