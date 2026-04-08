from dataclasses import asdict
from typing import Any

from filters.pipeline import FilterResult


def build_records(results: list[FilterResult]) -> list[dict[str, Any]]:
    records = []
    for r in results:
        if not r.passed:
            continue
        records.append({
            "instruction": r.pair.instruction,
            "input": r.pair.input,
            "output": r.pair.output,
        })
    return records
