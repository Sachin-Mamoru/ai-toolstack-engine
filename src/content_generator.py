"""Content generator: uses Gemini API to produce SEO articles for each page spec."""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
import time
from typing import Any

from google import genai
from google.genai import types as genai_types

from .config_loader import load_tools
from .utils import truncate, utc_today, word_count

logger = logging.getLogger(__name__)

# Ranked preference list – _resolve_model() picks the first one the key can reach.
GEMINI_MODEL_PREFERENCE = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.5-flash",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro",
    "gemini-2.5-pro-preview-03-25",
    "gemini-1.5-pro-002",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash",
    "gemini-1.0-pro",
]

_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds

# Module-level cache so model resolution only happens once per run
_cached_client: genai.Client | None = None
_cached_model: str | None = None


def _is_permanent(exc: BaseException) -> bool:
    """Return True for errors that will never succeed on retry (4xx non-429)."""
    msg = str(exc)
    return any(code in msg for code in ("404", "400", "403", "NOT_FOUND", "INVALID_ARGUMENT"))


def _resolve_model(client: genai.Client) -> str:
    """Return the best available generateContent model for this API key.

    1. Call client.models.list() to get the live set of models.
    2. Keep only those that support generateContent.
    3. Rank against GEMINI_MODEL_PREFERENCE; pick the highest-ranked.
    4. If list() fails, probe each preference entry directly.
    """
    # Allow hard override via env var
    env_model = os.getenv("GEMINI_MODEL")
    if env_model:
        logger.info("Model overridden via GEMINI_MODEL env var: %s", env_model)
        return env_model

    available: set[str] = set()
    try:
        for m in client.models.list():
            name: str = getattr(m, "name", "") or ""
            short = name.removeprefix("models/")
            # Include all text-generation models; the SDK doesn't reliably
            # expose supported_generation_methods in every version.
            if short and ("gemini" in short or "flash" in short or "pro" in short):
                available.add(short)
        logger.info("Live model list fetched (%d models)", len(available))
    except Exception as exc:  # noqa: BLE001
        logger.warning("ListModels failed, will probe directly: %s", str(exc)[:120])

    if available:
        for preferred in GEMINI_MODEL_PREFERENCE:
            if preferred in available:
                logger.info("Model resolved via ListModels: %s", preferred)
                return preferred
        # Heuristic fallback: any flash/pro model
        for name in sorted(available, reverse=True):
            if "flash" in name or "pro" in name:
                logger.info("Model resolved (heuristic): %s", name)
                return name
        fallback = sorted(available)[0]
        logger.info("Model resolved (first available): %s", fallback)
        return fallback

    # ListModels unavailable – probe each preference entry
    logger.warning("Probing model preference list directly")
    probe = "Reply with one word: OK"
    for model in GEMINI_MODEL_PREFERENCE:
        try:
            client.models.generate_content(model=model, contents=probe)
            logger.info("Model resolved via probe: %s", model)
            return model
        except Exception as exc:  # noqa: BLE001
            logger.debug("Model probe failed %s: %s", model, str(exc)[:80])

    last = GEMINI_MODEL_PREFERENCE[0]
    logger.error("All resolution strategies failed, using: %s", last)
    return last


def _init_gemini() -> tuple[genai.Client, str]:
    """Return a (client, model_name) pair, resolving the model dynamically."""
    global _cached_client, _cached_model  # noqa: PLW0603
    if _cached_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise OSError("GEMINI_API_KEY environment variable is not set.")
        _cached_client = genai.Client(api_key=api_key)
        _cached_model = _resolve_model(_cached_client)
        logger.info("Gemini ready, model=%s", _cached_model)
    return _cached_client, _cached_model  # type: ignore[return-value]


def _build_tools_context(page: dict, tools: list[dict]) -> str:
    """Return a compact YAML-like block of relevant tool info for the prompt."""
    category_keywords = {
        "coding_assistant": [
            "copilot",
            "cursor",
            "codeium",
            "tabnine",
            "aider",
            "cody",
            "continue",
        ],
        "code_review": [
            "review",
            "coderabbit",
            "codeclimate",
            "sonar",
            "codacy",
            "deepsource",
            "qodo",
        ],
        "security_scanning": ["security", "snyk", "semgrep", "checkov", "scan"],
        "observability": [
            "observabil",
            "monitor",
            "datadog",
            "grafana",
            "new relic",
            "dynatrace",
            "elastic",
            "splunk",
            "sentry",
        ],
        "incident_management": ["incident", "pagerduty", "opsgenie"],
        "iac": ["terraform", "pulumi", "ansible", "infrastructure", "iac"],
        "kubernetes": ["kubernetes", "k8s", "k9s", "lens", "karpenter"],
        "cloud_cost": ["cost", "kubecost", "infracost"],
        "cicd": ["ci/cd", "cicd", "pipeline", "harness", "github actions"],
        "dev_productivity": ["productivity", "warp", "linear", "langchain", "mintlify"],
    }

    keyword = page.get("primary_keyword", "").lower()
    title = page.get("title", "").lower()
    combined = f"{keyword} {title}"

    # Pick relevant tools based on keyword matching
    relevant: list[dict] = []
    for tool in tools:
        tool_name = tool["name"].lower()
        cat = tool.get("category", "")
        match = any(kw in combined for kw in category_keywords.get(cat, []))
        name_match = tool_name.split()[0] in combined or any(
            w in combined for w in tool_name.split()
        )
        if match or name_match:
            relevant.append(tool)

    # Fall back to all tools if nothing matched (shouldn't happen often)
    if len(relevant) < 2:
        relevant = tools[:8]

    lines = []
    for t in relevant[:10]:  # cap at 10 tools to keep prompt tight
        lines.append(
            f"- name: {t['name']}\n"
            f"  category: {t.get('category', 'unknown')}\n"
            f"  pricing: {t.get('pricing_summary', 'see website')}\n"
            f"  features: {'; '.join(t.get('features', [])[:3])}"
        )
    return "\n".join(lines)


def _build_internal_links(page: dict, all_pages: list[dict]) -> str:
    """Return 3-5 internal link suggestions as markdown."""
    current_slug = page.get("slug", "")
    current_kw = page.get("primary_keyword", "").lower()
    related: list[tuple[int, dict]] = []

    for p in all_pages:
        if p.get("slug") == current_slug:
            continue
        # Simple relevance: shared words between keywords
        other_kw = p.get("primary_keyword", "").lower()
        shared = len(set(current_kw.split()) & set(other_kw.split()))
        if shared >= 2:
            related.append((shared, p))

    related.sort(key=lambda x: x[0], reverse=True)
    top = [p for _, p in related[:5]]

    if not top:
        # Fallback: pick random pages of same type
        same_type = [
            p
            for p in all_pages
            if p.get("page_type") == page.get("page_type") and p.get("slug") != current_slug
        ]
        top = same_type[:5]

    links = []
    for p in top:
        page_type = p.get("page_type", "best")
        slug = p.get("slug", "")
        title = p.get("title", slug)
        links.append(f"[{title}](/{page_type}/{slug}/)")

    return "\n".join(f"- {lnk}" for lnk in links)


BEST_PAGE_PROMPT = textwrap.dedent(
    """
You are a senior DevOps engineer writing a practical, SEO-optimised article for developers.
Do NOT use marketing hype. Be direct, technical, and honest.

## Page details
- Title: {title}
- Primary keyword: {primary_keyword}
- Intent: {intent}
- Target audience: {target_audience}
- Today's date: {today}

## Relevant tools to cover
{tools_context}

## Suggested internal links to weave in naturally
{internal_links}

## Requirements
Write an article of 1400–2000 words covering:
1. A concise intro (3–4 sentences) stating who this guide is for and what they'll learn.
2. A markdown comparison table with columns: Tool | Best For | Pricing | Free Tier
3. A "Best for" section with bullet points per tool.
4. Pros & Cons for each tool (2–3 per side max).
5. Pricing section: use "free tier / paid plans" language; never state hard dollar amounts unless they are universally known and stable.
6. A "Decision flow" section: "If you need X → choose Y" bullets.
7. An FAQs section with 4–6 questions and answers (for FAQ schema).
8. Natural affiliate CTA placement markers: insert exactly these markers in the text:
   - `<!-- AFFILIATE_CTA_TOP -->` after the intro paragraph
   - `<!-- AFFILIATE_CTA_MID -->` after the comparison table
   - `<!-- AFFILIATE_CTA_BOTTOM -->` before the FAQs
9. A "Last Updated: {today}" line at the very top.

## Output format
Return ONLY a valid JSON object with these exact fields — no markdown fences, no extra text:
{{
  "title": "<page title>",
  "meta_description": "<150–160 char SEO meta description>",
  "article_markdown": "<full article in markdown, 1400–2000 words>",
  "faq": [
    {{"question": "...", "answer": "..."}},
    ...
  ],
  "affiliate_slots": ["TOP", "MID", "BOTTOM"]
}}
"""
).strip()


VS_PAGE_PROMPT = textwrap.dedent(
    """
You are a senior software engineer writing an honest, practical comparison article for other developers.
No hype. No sponsored tone. Treat readers as intelligent engineers who need real information.

## Page details
- Title: {title}
- Primary keyword: {primary_keyword}
- Intent: {intent}
- Target audience: {target_audience}
- Today's date: {today}

## Relevant tools to cover
{tools_context}

## Suggested internal links to weave in naturally
{internal_links}

## Requirements
Write a comparison article of 1400–2000 words covering:
1. A 3-sentence intro framing the comparison (who should read this and why it matters).
2. A quick "TL;DR" verdict box (1–2 sentences per tool).
3. A detailed feature-by-feature comparison table (markdown).
4. A dedicated section for each tool with:
   - What it does well
   - What it lacks
   - Pricing (free tier / paid plans language only)
   - Who it's best for
5. Head-to-head verdict for 3–4 specific use cases.
6. A "Which should you choose?" decision flow (bullet style).
7. FAQs: 4–6 questions comparing the two tools.
8. Natural affiliate CTA placement markers: insert exactly these markers:
   - `<!-- AFFILIATE_CTA_TOP -->` after the intro
   - `<!-- AFFILIATE_CTA_MID -->` after the comparison table
   - `<!-- AFFILIATE_CTA_BOTTOM -->` before the FAQs
9. A "Last Updated: {today}" line at the very top.

## Output format
Return ONLY a valid JSON object with these exact fields — no markdown fences, no extra text:
{{
  "title": "<page title>",
  "meta_description": "<150–160 char SEO meta description>",
  "article_markdown": "<full article in markdown, 1400–2000 words>",
  "faq": [
    {{"question": "...", "answer": "..."}},
    ...
  ],
  "affiliate_slots": ["TOP", "MID", "BOTTOM"]
}}
"""
).strip()


def _parse_json_response(raw: str) -> dict[str, Any]:
    """Extract and parse JSON from model response, stripping accidental fences."""
    text = raw.strip()
    # Strip ```json ... ``` fences if present
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    return json.loads(text)


def _call_gemini_with_retry(client: genai.Client, model: str, prompt: str) -> str:
    """Call Gemini API with exponential back-off retry.

    Permanent errors (404, 400, 403) are raised immediately without retrying.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=8192,
                ),
            )
            return response.text
        except Exception as exc:
            if _is_permanent(exc):
                logger.error("Permanent API error (not retrying): %s", exc)
                raise
            logger.warning("Gemini call attempt %d failed: %s", attempt, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY * attempt)
            else:
                raise


def generate_page_content(
    page: dict,
    all_pages: list[dict],
    tools: list[dict] | None = None,
) -> dict[str, Any]:
    """Generate full page content for a single page spec using Gemini.

    Parameters
    ----------
    page:       A single page spec dict from pages.yaml
    all_pages:  All page specs (for internal linking)
    tools:      Tool list from tools.yaml (loaded once externally for efficiency)

    Returns
    -------
    dict with keys: title, meta_description, article_markdown, faq, affiliate_slots
    """
    if tools is None:
        tools = load_tools()

    client, model = _init_gemini()
    tools_context = _build_tools_context(page, tools)
    internal_links = _build_internal_links(page, all_pages)
    today = utc_today()

    template = BEST_PAGE_PROMPT if page.get("page_type") == "best" else VS_PAGE_PROMPT
    prompt = template.format(
        title=page["title"],
        primary_keyword=page["primary_keyword"],
        intent=page.get("intent", ""),
        target_audience=page.get("target_audience", "developers"),
        today=today,
        tools_context=tools_context,
        internal_links=internal_links,
    )

    logger.info("Generating content for: %s", page["slug"])
    raw = _call_gemini_with_retry(client, model, prompt)

    try:
        result = _parse_json_response(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse JSON for %s: %s\nRaw:\n%s", page["slug"], exc, raw[:500])
        raise

    # Validate and normalise
    result.setdefault("title", page["title"])
    result.setdefault("meta_description", truncate(page.get("intent", page["title"]), 160))
    result.setdefault("article_markdown", "")
    result.setdefault("faq", [])
    result.setdefault("affiliate_slots", ["TOP", "MID", "BOTTOM"])

    wc = word_count(result["article_markdown"])
    if wc < 800:
        logger.warning("Article for %s is short: %d words", page["slug"], wc)

    logger.info("Generated %d words for %s", wc, page["slug"])
    return result


def inject_affiliate_links(
    markdown: str,
    page: dict,
    tools: list[dict],
    affiliates: dict[str, str],
) -> str:
    """Replace CTA marker comments with real affiliate link blocks."""
    # Find which tools are mentioned in the article
    mentioned_tools = [t for t in tools if t["name"].lower() in markdown.lower()][:3]  # top 3

    def make_cta(position: str) -> str:
        if not mentioned_tools:
            return ""
        tool = (
            mentioned_tools[0]
            if position == "TOP"
            else (
                mentioned_tools[1]
                if position == "MID" and len(mentioned_tools) > 1
                else mentioned_tools[-1]
            )
        )
        url = affiliates.get(tool["name"], tool.get("homepage_url", "#"))
        verb = "Try" if position in ("TOP", "MID") else "Get started with"
        return (
            f'\n\n> **{verb} {tool["name"]} →** [{tool["name"]}]({url}) '
            f'— {tool.get("pricing_summary", "see pricing")}\n\n'
        )

    for pos in ("TOP", "MID", "BOTTOM"):
        marker = f"<!-- AFFILIATE_CTA_{pos} -->"
        markdown = markdown.replace(marker, make_cta(pos))

    return markdown
