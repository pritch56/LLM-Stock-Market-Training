import json
import logging

from llm_generation.client import LLMClient
from llm_generation.prompt_builder import SYSTEM_PROMPT, build_analysis_prompt

logger = logging.getLogger(__name__)


async def analyze_article_with_llm(client: LLMClient, article_text: str) -> list[dict]:
    prompt = build_analysis_prompt(article_text)
    try:
        text, _, _ = await client.complete(prompt, system=SYSTEM_PROMPT)
        data = json.loads(text)
        companies = data.get("companies", [])
        logger.info("LLM identified %d companies", len(companies))
        return companies
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse LLM response: %s", exc)
        return []
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return []
