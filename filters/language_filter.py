import logging

from config.settings import settings
from llm_generation.generator import RawPair

logger = logging.getLogger(__name__)

try:
    from langdetect import detect, LangDetectException
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not installed; language filtering disabled")


def passes_language(pair: RawPair) -> tuple[bool, str]:
    if not _LANGDETECT_AVAILABLE:
        return True, ""
    try:
        lang = detect(pair.output)
        if lang not in settings.allowed_languages:
            return False, f"language_{lang}"
    except LangDetectException:
        pass
    return True, ""
