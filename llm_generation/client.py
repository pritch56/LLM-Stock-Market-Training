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


class MockClient(LLMClient):
    """Generates template pairs locally without any API call. Useful for testing the pipeline."""

    async def complete(self, prompt: str, system: Optional[str] = None) -> tuple[str, int, int]:
        import json, re
        # Extract the passage from the prompt
        match = re.search(r'"""\n(.*?)\n"""', prompt, re.DOTALL)
        passage = match.group(1).strip()[:300] if match else "the provided text"
        pairs = [
            {
                "instruction": f"Summarise the following passage in your own words.",
                "input": passage[:200],
                "output": f"The passage discusses: {passage[:150]}. It provides an overview of the key concepts and their significance in context.",
            },
            {
                "instruction": "What is the main topic covered in this text?",
                "input": "",
                "output": f"The main topic is: {passage[:100]}. This subject is important because it covers fundamental ideas that have broad applications.",
            },
            {
                "instruction": "List three key points from the passage.",
                "input": passage[:200],
                "output": f"1. {passage[:60]}.\n2. The text elaborates on related concepts and their interactions.\n3. The material provides context for understanding the broader subject area.",
            },
        ]
        return json.dumps(pairs), 0, 0


def build_client(mock: bool = False) -> LLMClient:
    if mock:
        return MockClient()
    if settings.llm_provider == "anthropic":
        return AnthropicClient()
    if settings.llm_provider == "openai":
        return OpenAIClient()
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
