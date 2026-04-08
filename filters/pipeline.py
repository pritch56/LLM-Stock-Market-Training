import logging
from dataclasses import dataclass

from filters.duplicate_filter import PairDeduplicator
from filters.language_filter import passes_language
from filters.length_filter import passes_length
from filters.toxicity_filter import passes_toxicity
from llm_generation.generator import RawPair

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    pair: RawPair
    passed: bool
    reason: str


def run_filters(pairs: list[RawPair]) -> list[FilterResult]:
    dedup = PairDeduplicator()
    results = []

    for pair in pairs:
        for check in (passes_length, passes_language, passes_toxicity, dedup.passes_duplicate):
            ok, reason = check(pair)
            if not ok:
                results.append(FilterResult(pair=pair, passed=False, reason=reason))
                logger.debug("Filtered pair: %s", reason)
                break
        else:
            results.append(FilterResult(pair=pair, passed=True, reason=""))

    passed = sum(1 for r in results if r.passed)
    logger.info("Filtering: %d/%d pairs passed", passed, len(results))
    return results
