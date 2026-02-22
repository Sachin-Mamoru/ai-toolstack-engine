"""Tests for src/utils.py utility functions."""

from src.utils import extract_headings, slugify, truncate, utc_today, word_count


class TestSlugify:
    def test_lowercase(self):
        assert slugify("GitHub Copilot") == "github-copilot"

    def test_special_chars_removed(self):
        assert slugify("Best AI Tools!") == "best-ai-tools"

    def test_spaces_become_hyphens(self):
        assert slugify("best ai code review tools") == "best-ai-code-review-tools"

    def test_multiple_spaces_collapse(self):
        assert slugify("too   many   spaces") == "too-many-spaces"

    def test_vs_page(self):
        assert slugify("GitHub Copilot vs Cursor") == "github-copilot-vs-cursor"

    def test_slash_in_text(self):
        result = slugify("K8s/Kubernetes tools")
        assert "k8s" in result
        assert "kubernetes" in result
        assert " " not in result

    def test_leading_trailing_hyphens_stripped(self):
        result = slugify("--leading-trailing--")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_numbers_preserved(self):
        assert "2026" in slugify("Best tools 2026")

    def test_unicode_normalized(self):
        result = slugify("café tools")
        assert "caf" in result
        assert " " not in result

    def test_empty_string(self):
        assert slugify("") == ""

    def test_already_slug(self):
        assert slugify("best-ai-tools") == "best-ai-tools"


class TestTruncate:
    def test_short_text_unchanged(self):
        text = "Short text."
        assert truncate(text, 160) == text

    def test_long_text_trimmed(self):
        text = "word " * 50  # 250 chars
        result = truncate(text, 160)
        assert len(result) <= 161  # 160 + ellipsis char

    def test_ends_with_ellipsis(self):
        text = "a " * 100
        result = truncate(text, 50)
        assert result.endswith("…")

    def test_word_boundary(self):
        text = "The quick brown fox jumps over the lazy dog"
        result = truncate(text, 20)
        # Should not cut in the middle of a word
        for word in result.replace("…", "").split():
            assert word in text.split()

    def test_exactly_max_chars_unchanged(self):
        text = "a" * 160
        assert truncate(text, 160) == text


class TestWordCount:
    def test_basic_count(self):
        assert word_count("one two three") == 3

    def test_single_word(self):
        assert word_count("hello") == 1

    def test_empty_string(self):
        assert word_count("") == 0  # "".split() returns [] in Python 3

    def test_markdown_text(self):
        text = "## Heading\n\nSome text here.\n\n- Item one\n- Item two"
        assert word_count(text) > 5


class TestExtractHeadings:
    def test_single_h1(self):
        md = "# My Heading\n\nSome text."
        assert extract_headings(md) == ["My Heading"]

    def test_multiple_levels(self):
        md = "# H1\n## H2\n### H3\n"
        headings = extract_headings(md)
        assert headings == ["H1", "H2", "H3"]

    def test_no_headings(self):
        assert extract_headings("Just some plain text.") == []

    def test_inline_heading_not_matched(self):
        # # must be at line start
        md = "text ## not a heading\n# Real heading"
        headings = extract_headings(md)
        assert "not a heading" not in headings
        assert "Real heading" in headings


class TestUtcToday:
    def test_format(self):
        today = utc_today()
        import re

        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", today), f"Unexpected format: {today}"
