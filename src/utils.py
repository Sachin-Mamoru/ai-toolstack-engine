"""Utility helpers: slugs, timestamps, deduplication, markdown processing."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone


def slugify(text: str) -> str:
    """Convert arbitrary text to a URL-safe slug.

    Examples
    --------
    >>> slugify("GitHub Copilot vs Cursor!")
    'github-copilot-vs-cursor'
    >>> slugify("Best AI Tools for K8s/Kubernetes")
    'best-ai-tools-for-k8s-kubernetes'
    """
    text = str(text)
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # Replace non-alphanumeric chars (except hyphens) with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


def utc_now_iso() -> str:
    """Return current UTC datetime as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_today() -> str:
    """Return today's date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def truncate(text: str, max_chars: int = 160) -> str:
    """Truncate text to max_chars, ending at a word boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated.rstrip(".,;:") + "…"


def extract_headings(markdown: str) -> list[str]:
    """Return list of heading texts (all levels) from markdown."""
    pattern = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(markdown)]


def word_count(text: str) -> int:
    """Approximate word count of a string."""
    return len(text.split()) if text.strip() else 0


def sanitize_filename(name: str) -> str:
    """Return a safe filename from arbitrary string."""
    return re.sub(r"[^\w\-.]", "_", name)
