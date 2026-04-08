import logging
from abc import ABC, abstractmethod
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None) -> tuple[str, int, int]:
        """Return (text, prompt_tokens, output_tokens)."""


class AnthropicClient(LLMClient):
    def __init__(self):
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(self, prompt: str, system: Optional[str] = None) -> tuple[str, int, int]:
        kwargs = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)
        text = response.content[0].text
        return text, response.usage.input_tokens, response.usage.output_tokens


class OpenAIClient(LLMClient):
    def __init__(self):
        import openai
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def complete(self, prompt: str, system: Optional[str] = None) -> tuple[str, int, int]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            messages=messages,
        )
        text = response.choices[0].message.content
        usage = response.usage
        return text, usage.prompt_tokens, usage.completion_tokens


def build_client() -> LLMClient:
    if settings.llm_provider == "anthropic":
        return AnthropicClient()
    if settings.llm_provider == "openai":
        return OpenAIClient()
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
