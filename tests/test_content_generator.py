"""Tests for content_generator helper functions."""
from __future__ import annotations

import pytest

from src.content_generator import _parse_delimited_response

SAMPLE_RAW = """\
<<<TITLE>>>
Best AI Coding Tools 2024
<<<META>>>
A developer's guide to the best AI coding assistants available today.
<<<ARTICLE>>>
## Introduction

Last Updated: 2024-01-01

Here is an article with **markdown**, a code block, and special chars:

```python
config = {"key": "value", "nested": {"a": 1}}
```

It has 'single quotes', "double quotes", and {braces}.

<!-- AFFILIATE_CTA_TOP -->

## Comparison Table

| Tool | Best For |
|------|----------|
| Copilot | General coding |
| Cursor | AI-native editing |
<<<FAQ>>>
Q: What is the best tool?
A: GitHub Copilot is great for most developers.

Q: Is there a free option?
A: Yes, Codeium and Cursor both offer free tiers.

Q: Does it work offline?
A: No, these are cloud-based services.
<<<END>>>
"""


def test_parse_delimited_basic():
    result = _parse_delimited_response(SAMPLE_RAW)
    assert result["title"] == "Best AI Coding Tools 2024"
    assert "developer's guide" in result["meta_description"]
    assert "Comparison Table" in result["article_markdown"]
    assert result["affiliate_slots"] == ["TOP", "MID", "BOTTOM"]


def test_parse_delimited_faq():
    result = _parse_delimited_response(SAMPLE_RAW)
    faq = result["faq"]
    assert len(faq) == 3
    assert faq[0]["question"] == "What is the best tool?"
    assert "Copilot" in faq[0]["answer"]
    assert faq[2]["question"] == "Does it work offline?"


def test_parse_delimited_preserves_code_blocks():
    result = _parse_delimited_response(SAMPLE_RAW)
    assert '```python' in result["article_markdown"]
    assert '"key": "value"' in result["article_markdown"]


def test_parse_delimited_preserves_special_chars():
    result = _parse_delimited_response(SAMPLE_RAW)
    article = result["article_markdown"]
    assert "{braces}" in article
    assert "'single quotes'" in article
    assert '"double quotes"' in article


def test_parse_delimited_missing_article_raises():
    bad_raw = "<<<TITLE>>>\nSome Title\n<<<META>>>\nSome meta\n<<<END>>>"
    with pytest.raises(ValueError, match="<<<ARTICLE>>>"):
        _parse_delimited_response(bad_raw)


def test_parse_delimited_extra_text_before_title():
    """LLMs sometimes emit preamble before the first delimiter."""
    raw = "Sure, here is the article:\n\n" + SAMPLE_RAW
    result = _parse_delimited_response(raw)
    assert result["title"] == "Best AI Coding Tools 2024"


def test_parse_delimited_empty_faq():
    raw = SAMPLE_RAW.replace(
        "Q: What is the best tool?\nA: GitHub Copilot is great for most developers.\n\n"
        "Q: Is there a free option?\nA: Yes, Codeium and Cursor both offer free tiers.\n\n"
        "Q: Does it work offline?\nA: No, these are cloud-based services.",
        "",
    )
    result = _parse_delimited_response(raw)
    assert result["faq"] == []
