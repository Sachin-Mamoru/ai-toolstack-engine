"""Tests for src/sitemap.py."""

from pathlib import Path
from unittest.mock import patch

SAMPLE_PAGES = [
    {
        "page_type": "best",
        "slug": "best-ai-code-review-tools",
        "title": "Best AI Code Review Tools",
        "primary_keyword": "best ai code review tools",
        "intent": "Find review tools",
    },
    {
        "page_type": "vs",
        "slug": "github-copilot-vs-cursor",
        "title": "GitHub Copilot vs Cursor",
        "primary_keyword": "github copilot vs cursor",
        "intent": "Choose between them",
    },
    {
        "page_type": "best",
        "slug": "best-ai-tools-for-kubernetes",
        "title": "Best AI Tools for Kubernetes",
        "primary_keyword": "best ai tools for kubernetes",
        "intent": "K8s AI tools",
    },
]
PUBLISHED_SLUGS = {"best-ai-code-review-tools", "github-copilot-vs-cursor"}

SITE_CFG = {
    "site_name": "Test Site",
    "site_url": "https://example.com",
    "site_description": "Test desc",
    "adsense_publisher_id": "",
    "pages_per_day": 3,
}


def _patch_site_dir(tmp_path: Path):
    """Context manager that redirects SITE_DIR to a temp directory."""
    return patch("src.sitemap.SITE_DIR", tmp_path)


def _patch_cfg():
    return patch("src.sitemap.get_site_config", return_value=SITE_CFG)


class TestGenerateSitemap:
    def test_sitemap_created(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_sitemap

            generate_sitemap(SAMPLE_PAGES, PUBLISHED_SLUGS)

        sitemap_path = tmp_path / "sitemap.xml"
        assert sitemap_path.exists()

    def test_sitemap_contains_published_urls(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_sitemap

            generate_sitemap(SAMPLE_PAGES, PUBLISHED_SLUGS)

        content = (tmp_path / "sitemap.xml").read_text()
        assert "best-ai-code-review-tools" in content
        assert "github-copilot-vs-cursor" in content

    def test_sitemap_excludes_unpublished(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_sitemap

            generate_sitemap(SAMPLE_PAGES, PUBLISHED_SLUGS)

        content = (tmp_path / "sitemap.xml").read_text()
        assert "best-ai-tools-for-kubernetes" not in content

    def test_sitemap_valid_xml(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_sitemap

            generate_sitemap(SAMPLE_PAGES, PUBLISHED_SLUGS)

        content = (tmp_path / "sitemap.xml").read_text()
        assert content.startswith('<?xml version="1.0"')
        assert "<urlset" in content
        assert "</urlset>" in content

    def test_sitemap_includes_index_pages(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_sitemap

            generate_sitemap(SAMPLE_PAGES, PUBLISHED_SLUGS)

        content = (tmp_path / "sitemap.xml").read_text()
        assert "https://example.com/" in content
        assert "https://example.com/best/" in content
        assert "https://example.com/vs/" in content


class TestGenerateRobotsTxt:
    def test_robots_created(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_robots_txt

            generate_robots_txt()

        assert (tmp_path / "robots.txt").exists()

    def test_robots_allows_all(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_robots_txt

            generate_robots_txt()

        content = (tmp_path / "robots.txt").read_text()
        assert "User-agent: *" in content
        assert "Allow: /" in content

    def test_robots_has_sitemap(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_robots_txt

            generate_robots_txt()

        content = (tmp_path / "robots.txt").read_text()
        assert "Sitemap:" in content
        assert "sitemap.xml" in content


class TestGenerateRssFeed:
    def test_rss_created(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_rss_feed

            generate_rss_feed(SAMPLE_PAGES, PUBLISHED_SLUGS)

        assert (tmp_path / "rss.xml").exists()

    def test_rss_valid_structure(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_rss_feed

            generate_rss_feed(SAMPLE_PAGES, PUBLISHED_SLUGS)

        content = (tmp_path / "rss.xml").read_text()
        assert '<?xml version="1.0"' in content
        assert "<rss" in content
        assert "<channel>" in content
        assert "</channel>" in content
        assert "</rss>" in content

    def test_rss_contains_published_items(self, tmp_path):
        with _patch_site_dir(tmp_path), _patch_cfg():
            from src.sitemap import generate_rss_feed

            generate_rss_feed(SAMPLE_PAGES, PUBLISHED_SLUGS)

        content = (tmp_path / "rss.xml").read_text()
        assert "best-ai-code-review-tools" in content
        assert "github-copilot-vs-cursor" in content
