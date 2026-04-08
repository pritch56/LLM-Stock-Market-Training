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

    _MOCK_TICKERS = [
        {"name": "Apple Inc.", "ticker": "AAPL", "exchange": "NASDAQ",
         "relevance": "Major tech company frequently discussed in ML and finance contexts."},
        {"name": "Microsoft Corporation", "ticker": "MSFT", "exchange": "NASDAQ",
         "relevance": "Key player in cloud computing and AI infrastructure."},
    ]

    async def complete(self, prompt: str, system: Optional[str] = None) -> tuple[str, int, int]:
        import json, re

        # Entity extraction call
        if "extract all companies" in prompt.lower() or '"entities"' in prompt:
            return json.dumps({"entities": self._MOCK_TICKERS}), 0, 0

        # Pair generation call
        match = re.search(r'"""\n(.*?)\n"""', prompt, re.DOTALL)
        passage = match.group(1).strip()[:300] if match else "the provided text"
        pairs = [
            {
                "instruction": "What is the potential stock market impact of the developments described in this passage?",
                "input": passage[:200],
                "output": (
                    f"The passage highlights developments relevant to Apple Inc. (AAPL) and Microsoft Corporation (MSFT). "
                    f"Based on: {passage[:100]}. "
                    "These factors could influence investor sentiment and near-term price action for companies in this sector."
                ),
            },
            {
                "instruction": "Which companies and tickers are most exposed to the risks or opportunities described?",
                "input": "",
                "output": (
                    "Apple Inc. (AAPL) and Microsoft Corporation (MSFT) are directly exposed to these developments. "
                    f"The core theme — {passage[:80]} — suggests potential upside for firms with strong AI and cloud exposure. "
                    "Investors should monitor earnings guidance and sector rotation signals."
                ),
            },
            {
                "instruction": "Summarise the key investment signals from this passage.",
                "input": passage[:200],
                "output": (
                    f"Key signal: {passage[:80]}. "
                    "This is relevant to AAPL (Apple Inc.) on NASDAQ and MSFT (Microsoft Corporation) on NASDAQ. "
                    "The information suggests monitoring these tickers for momentum or mean-reversion setups depending on broader market conditions."
                ),
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
