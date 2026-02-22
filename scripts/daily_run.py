"""daily_run.py — Orchestrates the daily page generation pipeline.

Usage:
    python scripts/daily_run.py [--pages N] [--dry-run]

Picks N unpublished pages from config/pages.yaml (in order), generates
content using Gemini, writes markdown to content/, then triggers a full
site rebuild.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Make sure src/ is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import (
    get_published_slugs,
    get_site_config,
    load_affiliates,
    load_pages,
    load_tools,
)
from src.content_generator import generate_page_content, inject_affiliate_links
from src.utils import utc_today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("daily_run")

REPO_ROOT = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "content"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate N new pages per day.")
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Number of pages to generate (overrides PAGES_PER_DAY env / config)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print which pages would be generated without calling Gemini",
    )
    return parser.parse_args()


def pick_next_pages(all_pages: list[dict], published_slugs: set[str], n: int) -> list[dict]:
    """Return the next N un-published pages in config order."""
    pending = [p for p in all_pages if p["slug"] not in published_slugs]
    return pending[:n]


def save_markdown(page_spec: dict, generated: dict) -> Path:
    """Persist generated content as a markdown file in content/."""
    page_type = page_spec.get("page_type", "best")
    slug = page_spec["slug"]
    out_dir = CONTENT_DIR / page_type
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.md"

    # Front-matter + article
    front_matter = "\n".join(
        [
            "---",
            f"title: {json.dumps(generated.get('title', page_spec['title']))}",
            f"slug: {slug}",
            f"page_type: {page_type}",
            f"primary_keyword: {page_spec.get('primary_keyword', '')}",
            f"meta_description: {json.dumps(generated.get('meta_description', ''))}",
            f"date_published: {utc_today()}",
            f"last_updated: {utc_today()}",
            "---",
            "",
        ]
    )

    faq_block = ""
    if generated.get("faq"):
        faq_lines = ["\n## Frequently Asked Questions\n"]
        for item in generated["faq"]:
            faq_lines.append(f"### {item['question']}\n\n{item['answer']}\n")
        faq_block = "\n".join(faq_lines)

    content = front_matter + generated.get("article_markdown", "") + "\n" + faq_block
    out_path.write_text(content, encoding="utf-8")
    logger.info("Saved: %s", out_path)
    return out_path


def main() -> None:
    args = parse_args()
    cfg = get_site_config()
    n_pages = args.pages if args.pages is not None else cfg["pages_per_day"]

    all_pages = load_pages()
    published_slugs = get_published_slugs(CONTENT_DIR)
    logger.info(
        "Total pages: %d | Published: %d | Pending: %d",
        len(all_pages),
        len(published_slugs),
        len(all_pages) - len(published_slugs),
    )

    to_generate = pick_next_pages(all_pages, published_slugs, n_pages)
    if not to_generate:
        logger.info("All pages are already published. Nothing to do.")
        return

    if args.dry_run:
        logger.info("DRY RUN — would generate:")
        for p in to_generate:
            logger.info("  [%s] %s → %s", p["page_type"], p["primary_keyword"], p["slug"])
        return

    tools = load_tools()
    affiliates = load_affiliates()
    generated_count = 0

    for page_spec in to_generate:
        try:
            generated = generate_page_content(page_spec, all_pages, tools=tools)
            # Inject affiliate links into the article markdown
            generated["article_markdown"] = inject_affiliate_links(
                generated["article_markdown"], page_spec, tools, affiliates
            )
            save_markdown(page_spec, generated)
            generated_count += 1
        except Exception as exc:
            logger.exception("Failed to generate %s: %s", page_spec["slug"], exc)
            continue

    logger.info(
        "Daily generation complete. Generated %d/%d pages.",
        generated_count,
        len(to_generate),
    )
    if generated_count == 0 and len(to_generate) > 0:
        logger.error("All page generations failed. Exiting with error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
