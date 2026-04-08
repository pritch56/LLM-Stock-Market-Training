import hashlib


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Deduplicator:
    def __init__(self):
        self._seen: set[str] = set()

    def is_duplicate(self, text: str) -> bool:
        h = content_hash(text)
        if h in self._seen:
            return True
        self._seen.add(h)
        return False

    def reset(self) -> None:
        self._seen.clear()
