import re
from typing import Optional

from bs4 import BeautifulSoup

_NOISE_TAGS = {
    "script", "style", "nav", "footer", "header", "aside",
    "form", "button", "iframe", "noscript", "svg", "figure",
}

_WHITESPACE_RE = re.compile(r"\n{3,}")
_INLINE_SPACE_RE = re.compile(r"[ \t]{2,}")


def extract_text(html: str, selector: Optional[str] = None) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    root = soup.select_one(selector) if selector else soup.body or soup
    if root is None:
        root = soup

    text = root.get_text(separator="\n")
    text = _INLINE_SPACE_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub("\n\n", text)
    return text.strip()
