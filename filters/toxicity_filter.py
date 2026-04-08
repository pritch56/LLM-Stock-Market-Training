import re

from llm_generation.generator import RawPair

_TOXIC_PATTERNS = re.compile(
    r"\b(fuck|shit|bitch|asshole|nigger|faggot|cunt|retard)\b",
    re.IGNORECASE,
)


def passes_toxicity(pair: RawPair) -> tuple[bool, str]:
    combined = f"{pair.instruction} {pair.input} {pair.output}"
    if _TOXIC_PATTERNS.search(combined):
        return False, "toxic_content"
    return True, ""
