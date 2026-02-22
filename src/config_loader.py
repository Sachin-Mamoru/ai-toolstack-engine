"""Config loader: reads YAML config files and returns typed dicts."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


CONFIG_DIR = Path(__file__).parent.parent / "config"


def _load(filename: str) -> Any:
    path = CONFIG_DIR / filename
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pages() -> list[dict]:
    data = _load("pages.yaml")
    return data.get("pages", [])


def load_tools() -> list[dict]:
    data = _load("tools.yaml")
    return data.get("tools", [])


def load_affiliates() -> dict[str, str]:
    data = _load("affiliates.yaml")
    return data.get("affiliates", {})


def get_published_slugs(content_dir: Path) -> set[str]:
    """Return set of already-published slugs by scanning content directory."""
    slugs: set[str] = set()
    for md_file in content_dir.rglob("*.md"):
        slugs.add(md_file.stem)
    return slugs


def get_site_config() -> dict:
    """Return site-level configuration with sensible defaults."""
    return {
        "site_name": os.getenv("SITE_NAME", "AI ToolStack Engine"),
        "site_url": os.getenv("SITE_URL", "https://aidevtools.me"),
        "site_description": (
            "Independent comparisons of AI tools for developers and DevOps engineers. "
            "No hype — just practical breakdowns to help you choose the right tool."
        ),
        "adsense_publisher_id": os.getenv("ADSENSE_PUBLISHER_ID", ""),
        "pages_per_day": int(os.getenv("PAGES_PER_DAY", "3")),
    }
