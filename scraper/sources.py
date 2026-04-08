from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SourceConfig:
    name: str
    url: str
    type: str  # "static" | "dynamic"
    content_selector: Optional[str] = None
    follow_links: bool = False
    tags: list[str] = field(default_factory=list)


def load_sources(path: Path) -> list[SourceConfig]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return [SourceConfig(**s) for s in data["sources"]]
