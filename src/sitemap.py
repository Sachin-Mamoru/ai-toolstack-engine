"""Generates sitemap.xml, robots.txt, and RSS feed."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from .config_loader import get_site_config
from .utils import utc_today

logger = logging.getLogger(__name__)

SITE_DIR = Path(__file__).parent.parent / "site"


def generate_sitemap(all_pages: list[dict], published_slugs: set[str]) -> None:
    """Write site/sitemap.xml."""
    cfg = get_site_config()
    site_url = cfg["site_url"].rstrip("/")
    today = utc_today()

    urls: list[str] = [
        site_url + "/",
        site_url + "/best/",
        site_url + "/vs/",
        site_url + "/categories/",
    ]

    for page in all_pages:
        if page["slug"] in published_slugs:
            urls.append(f"{site_url}/{page['page_type']}/{page['slug']}/")

    url_entries = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n  </url>"
        for u in urls
    )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{url_entries}\n"
        "</urlset>"
    )
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    logger.info("Generated sitemap.xml with %d URLs", len(urls))


def generate_robots_txt() -> None:
    """Write site/robots.txt."""
    cfg = get_site_config()
    site_url = cfg["site_url"].rstrip("/")
    robots = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {site_url}/sitemap.xml\n"
    )
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "robots.txt").write_text(robots, encoding="utf-8")
    logger.info("Generated robots.txt")


def generate_rss_feed(all_pages: list[dict], published_slugs: set[str]) -> None:
    """Write site/rss.xml (RSS 2.0 feed of recently published pages)."""
    cfg = get_site_config()
    site_url = cfg["site_url"].rstrip("/")
    site_name = cfg["site_name"]
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    # Show latest 20 published pages
    published = [p for p in all_pages if p["slug"] in published_slugs]
    recent = published[-20:]

    items: list[str] = []
    for page in reversed(recent):
        page_url = f"{site_url}/{page['page_type']}/{page['slug']}/"
        title = page.get("title", page["slug"])
        desc = page.get("intent", "")
        items.append(
            f"  <item>\n"
            f"    <title><![CDATA[{title}]]></title>\n"
            f"    <link>{page_url}</link>\n"
            f"    <guid isPermaLink=\"true\">{page_url}</guid>\n"
            f"    <description><![CDATA[{desc}]]></description>\n"
            f"    <pubDate>{pub_date}</pubDate>\n"
            f"  </item>"
        )

    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{site_name}</title>\n"
        f"    <link>{site_url}/</link>\n"
        f"    <description>{cfg['site_description']}</description>\n"
        f"    <lastBuildDate>{pub_date}</lastBuildDate>\n"
        f'    <atom:link href="{site_url}/rss.xml" rel="self" type="application/rss+xml"/>\n'
        + "\n".join(items)
        + "\n  </channel>\n</rss>"
    )
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "rss.xml").write_text(rss, encoding="utf-8")
    logger.info("Generated rss.xml with %d items", len(recent))
