import re
import unicodedata

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_REPEATED_PUNCT_RE = re.compile(r"([!?.]){3,}")
_URL_RE = re.compile(r"https?://\S+")
_WIKI_REF_RE = re.compile(r"\[\d+\]")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _WIKI_REF_RE.sub("", text)
    text = _REPEATED_PUNCT_RE.sub(r"\1\1\1", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)
