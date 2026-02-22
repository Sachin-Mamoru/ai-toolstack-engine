"""build_site.py — Rebuilds the entire static site from content/.

Usage:
    python scripts/build_site.py

Reads all markdown files in content/, renders them to HTML under site/,
and regenerates all index pages, sitemap, robots.txt, and RSS feed.
"""

from __future__ import annotations

import logging
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import get_published_slugs, load_pages
from src.site_builder import (
    CONTENT_DIR,
    REPO_ROOT,
    SITE_DIR,
    build_homepage,
    build_index_pages,
    build_static_pages,
    copy_static_assets,
    render_content_page,
)
from src.sitemap import generate_robots_txt, generate_rss_feed, generate_sitemap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("build_site")

_FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)


def parse_front_matter(text: str) -> dict:
    """Parse YAML-like front matter from a markdown file."""
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    data: dict = {}
    for m in _FIELD_RE.finditer(block):
        key, value = m.group(1), m.group(2).strip()
        # Strip surrounding quotes from JSON-style strings
        if value.startswith('"') and value.endswith('"'):
            try:
                import json

                value = json.loads(value)
            except Exception:
                pass
        data[key] = value
    return data


def parse_article_body(text: str) -> str:
    """Return the markdown body after stripping front matter."""
    return _FRONT_MATTER_RE.sub("", text, count=1)


def load_generated_from_file(md_path: Path) -> dict:
    """Reconstruct the 'generated' dict from a saved markdown file."""
    raw = md_path.read_text(encoding="utf-8")
    fm = parse_front_matter(raw)
    body = parse_article_body(raw)

    # Extract FAQ items from the body (### heading pattern in the FAQ section)
    faq: list[dict] = []
    faq_section_match = re.search(
        r"## Frequently Asked Questions\n(.*?)(?=\n## |\Z)",
        body,
        re.DOTALL,
    )
    if faq_section_match:
        faq_text = faq_section_match.group(1)
        qa_pairs = re.findall(r"### (.+?)\n\n(.+?)(?=\n### |\Z)", faq_text, re.DOTALL)
        faq = [{"question": q.strip(), "answer": a.strip()} for q, a in qa_pairs]

    return {
        "title": fm.get("title", md_path.stem),
        "meta_description": fm.get("meta_description", ""),
        "article_markdown": body,
        "faq": faq,
        "affiliate_slots": ["TOP", "MID", "BOTTOM"],
    }


def build_all() -> None:
    all_pages = load_pages()
    published_slugs = get_published_slugs(CONTENT_DIR)
    page_lookup = {p["slug"]: p for p in all_pages}

    rendered = 0
    errors = 0

    for md_file in sorted(CONTENT_DIR.rglob("*.md")):
        slug = md_file.stem
        page_spec = page_lookup.get(slug)
        if not page_spec:
            logger.warning("No page spec found for slug: %s — skipping", slug)
            continue

        page_type = page_spec.get("page_type", "best")
        out_dir = SITE_DIR / page_type / slug

        try:
            generated = load_generated_from_file(md_file)
            render_content_page(page_spec, generated, out_dir)
            rendered += 1
        except Exception as exc:
            logger.error("Failed to render %s: %s", slug, exc)
            errors += 1

    logger.info("Rendered %d pages (%d errors)", rendered, errors)

    build_index_pages(all_pages, published_slugs)
    build_homepage(all_pages, published_slugs)
    generate_sitemap(all_pages, published_slugs)
    generate_robots_txt()
    generate_rss_feed(all_pages, published_slugs)
    build_static_pages()
    copy_static_assets()

    # Copy CNAME so GitHub Pages keeps the custom domain after every deploy
    cname_src = REPO_ROOT / "CNAME"
    if cname_src.exists():
        shutil.copy(cname_src, SITE_DIR / "CNAME")
        logger.info("Copied CNAME → site/CNAME")

    logger.info("Site build complete. Output: %s", SITE_DIR)


if __name__ == "__main__":
    build_all()
