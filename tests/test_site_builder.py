"""Tests for src/site_builder.py — page rendering and index generation."""
import re
from pathlib import Path
from unittest.mock import patch

SITE_CFG = {
    "site_name": "Test Site",
    "site_url": "https://example.com",
    "site_description": "Test desc",
    "adsense_publisher_id": "",
    "pages_per_day": 3,
}

SAMPLE_PAGE_SPEC = {
    "page_type": "best",
    "slug": "best-ai-code-review-tools",
    "title": "Best AI Code Review Tools in 2026",
    "primary_keyword": "best ai code review tools",
    "intent": "Find the best AI-powered code review tools",
    "target_audience": "developers",
}

SAMPLE_GENERATED = {
    "title": "Best AI Code Review Tools in 2026",
    "meta_description": "Discover the best AI code review tools in 2026 for developers.",
    "article_markdown": (
        "## Introduction\n\nThis is a test article about AI code review tools.\n\n"
        "## Comparison Table\n\n| Tool | Best For | Pricing |\n|---|---|---|\n"
        "| CodeRabbit | PR reviews | Free/Paid |\n\n"
        "## Frequently Asked Questions\n\n"
        "### What is the best AI code review tool?\n\nCodeRabbit is widely regarded...\n"
    ),
    "faq": [
        {"question": "What is the best AI code review tool?", "answer": "CodeRabbit is widely regarded..."},
        {"question": "Are AI code review tools worth it?", "answer": "Yes, they save significant time..."},
    ],
    "affiliate_slots": ["TOP", "MID", "BOTTOM"],
}


def _patch_cfg():
    return patch("src.site_builder.get_site_config", return_value=SITE_CFG)


class TestRenderContentPage:
    def test_html_file_created(self, tmp_path):
        out = tmp_path / "best" / "best-ai-code-review-tools"

        with _patch_cfg():
            from src.site_builder import render_content_page
            result = render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, out)

        assert result.exists()
        assert result.name == "index.html"

    def test_html_contains_title(self, tmp_path):
        out = tmp_path / "best" / "best-ai-code-review-tools"
        with _patch_cfg():
            from src.site_builder import render_content_page
            render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, out)

        content = (out / "index.html").read_text()
        assert "Best AI Code Review Tools in 2026" in content

    def test_html_contains_meta_description(self, tmp_path):
        out = tmp_path / "best" / "best-ai-code-review-tools"
        with _patch_cfg():
            from src.site_builder import render_content_page
            render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, out)

        content = (out / "index.html").read_text()
        # content.lower() converts everything; use lowercase needle
        assert "best ai code review tools in 2026" in content.lower()

    def test_html_contains_article_content(self, tmp_path):
        out = tmp_path / "best" / "best-ai-code-review-tools"
        with _patch_cfg():
            from src.site_builder import render_content_page
            render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, out)

        content = (out / "index.html").read_text()
        # Markdown table should be converted to HTML table
        assert "<table>" in content.lower() or "<tr>" in content.lower()

    def test_html_has_faq_schema(self, tmp_path):
        out = tmp_path / "best" / "best-ai-code-review-tools"
        with _patch_cfg():
            from src.site_builder import render_content_page
            render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, out)

        content = (out / "index.html").read_text()
        assert "FAQPage" in content

    def test_html_has_article_schema(self, tmp_path):
        out = tmp_path / "best" / "best-ai-code-review-tools"
        with _patch_cfg():
            from src.site_builder import render_content_page
            render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, out)

        content = (out / "index.html").read_text()
        assert "Article" in content

    def test_html_has_canonical_link(self, tmp_path):
        out = tmp_path / "best" / "best-ai-code-review-tools"
        with _patch_cfg():
            from src.site_builder import render_content_page
            render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, out)

        content = (out / "index.html").read_text()
        assert 'rel="canonical"' in content
        assert "best-ai-code-review-tools" in content

    def test_output_directory_created_automatically(self, tmp_path):
        deeply_nested = tmp_path / "a" / "b" / "c" / "slug"
        assert not deeply_nested.exists()

        with _patch_cfg():
            from src.site_builder import render_content_page
            render_content_page(SAMPLE_PAGE_SPEC, SAMPLE_GENERATED, deeply_nested)

        assert (deeply_nested / "index.html").exists()


class TestMarkdownToHtml:
    def test_headers_converted(self):
        from src.site_builder import _markdown_to_html

        html = _markdown_to_html("# Hello\n\n## World")
        assert "<h1" in html
        assert "<h2" in html

    def test_table_converted(self):
        from src.site_builder import _markdown_to_html

        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = _markdown_to_html(md)
        assert "<table>" in html.lower()
        assert "<th>" in html.lower() or "<thead>" in html.lower()

    def test_markdown_links_converted(self):
        from src.site_builder import _markdown_to_html

        html = _markdown_to_html("[Click here](https://example.com)")
        assert "<a href=" in html
        assert "https://example.com" in html

    def test_empty_string(self):
        from src.site_builder import _markdown_to_html

        assert _markdown_to_html("") == ""

    def test_code_block_converted(self):
        from src.site_builder import _markdown_to_html

        html = _markdown_to_html("```python\nprint('hello')\n```")
        assert "<code" in html


class TestBuildFaqSchema:
    def test_schema_type(self):
        import json

        from src.site_builder import _build_faq_schema

        faq = [{"question": "What is X?", "answer": "X is Y."}]
        schema_str = _build_faq_schema(faq, "https://example.com/page/")
        schema = json.loads(schema_str)
        assert schema["@type"] == "FAQPage"

    def test_schema_contains_questions(self):
        import json

        from src.site_builder import _build_faq_schema

        faq = [
            {"question": "Q1?", "answer": "A1."},
            {"question": "Q2?", "answer": "A2."},
        ]
        schema_str = _build_faq_schema(faq, "https://example.com/page/")
        schema = json.loads(schema_str)
        assert len(schema["mainEntity"]) == 2
        assert schema["mainEntity"][0]["name"] == "Q1?"

    def test_empty_faq(self):
        import json

        from src.site_builder import _build_faq_schema

        schema_str = _build_faq_schema([], "https://example.com/page/")
        schema = json.loads(schema_str)
        assert schema["mainEntity"] == []


class TestSlugConsistency:
    """Ensure page slugs are URL-safe and unique."""

    def test_all_slugs_are_url_safe(self):

        import yaml

        pages_path = Path(__file__).parent.parent / "config" / "pages.yaml"
        with open(pages_path, encoding="utf-8") as f:
            pages = yaml.safe_load(f)["pages"]

        slug_re = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
        for page in pages:
            slug = page["slug"]
            assert slug_re.match(slug), f"Slug '{slug}' is not URL-safe"

    def test_all_slugs_are_unique(self):

        import yaml

        pages_path = Path(__file__).parent.parent / "config" / "pages.yaml"
        with open(pages_path, encoding="utf-8") as f:
            pages = yaml.safe_load(f)["pages"]

        slugs = [p["slug"] for p in pages]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found in pages.yaml"

    def test_minimum_page_count(self):

        import yaml

        pages_path = Path(__file__).parent.parent / "config" / "pages.yaml"
        with open(pages_path, encoding="utf-8") as f:
            pages = yaml.safe_load(f)["pages"]

        assert len(pages) >= 60, f"Expected at least 60 pages, got {len(pages)}"

    def test_best_and_vs_pages_present(self):

        import yaml

        pages_path = Path(__file__).parent.parent / "config" / "pages.yaml"
        with open(pages_path, encoding="utf-8") as f:
            pages = yaml.safe_load(f)["pages"]

        types = {p["page_type"] for p in pages}
        assert "best" in types
        assert "vs" in types
