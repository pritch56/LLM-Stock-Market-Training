import hashlib

from llm_generation.generator import RawPair


class PairDeduplicator:
    def __init__(self):
        self._seen: set[str] = set()

    def passes_duplicate(self, pair: RawPair) -> tuple[bool, str]:
        key = hashlib.sha256(
            f"{pair.instruction.lower().strip()}{pair.output[:200].lower().strip()}".encode()
        ).hexdigest()
        if key in self._seen:
            return False, "duplicate_pair"
        self._seen.add(key)
        return True, ""
