"""news_fetcher.py — Fetch recent AI tool headlines from Google News RSS.

Uses only stdlib (urllib + xml.etree) so no extra dependencies are needed.
"""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Queries tuned to surface new AI developer/DevOps tool launches and updates
_QUERIES = [
    "AI developer tools 2026",
    "AI coding assistant launch",
    "LLM code generation tools",
    "AI DevOps automation tools",
    "AI code review new release",
    "AI observability monitoring tools",
    "AI security scanning developer",
    "new AI programming tools",
]

_RSS_BASE = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q={q}"


def fetch_headlines(max_per_query: int = 6) -> list[str]:
    """Return a deduplicated list of recent AI-tool news headlines.

    Silently skips any query that fails (network error, timeout, etc.)
    so the daily pipeline is never blocked by a news fetch failure.
    """
    seen: set[str] = set()
    headlines: list[str] = []

    for query in _QUERIES:
        url = _RSS_BASE.format(q=urllib.parse.quote(query))
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ai-toolstack-bot/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item")[:max_per_query]:
                title = (item.findtext("title") or "").strip()
                # Strip the source suffix Google News appends, e.g. " - TechCrunch"
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0].strip()
                if title and title not in seen:
                    seen.add(title)
                    headlines.append(title)
        except Exception as exc:  # noqa: BLE001
            logger.warning("News fetch failed for query %r: %s", query, exc)

    logger.info("Fetched %d news headlines across %d queries", len(headlines), len(_QUERIES))
    return headlines
