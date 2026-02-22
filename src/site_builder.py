"""Static site builder: converts markdown content to HTML pages under site/."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import markdown as md_lib

from .config_loader import get_site_config
from .utils import utc_today

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "content"
SITE_DIR = REPO_ROOT / "site"
TEMPLATES_DIR = REPO_ROOT / "templates"


# ---------------------------------------------------------------------------
# Low-level HTML helpers
# ---------------------------------------------------------------------------


def _read_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def _markdown_to_html(text: str) -> str:
    extensions = ["tables", "fenced_code", "codehilite", "toc", "nl2br"]
    return md_lib.markdown(text, extensions=extensions)


def _render_template(template_name: str, **context: Any) -> str:
    template = _read_template(template_name)
    for key, value in context.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template


# ---------------------------------------------------------------------------
# Per-page rendering
# ---------------------------------------------------------------------------


def _build_faq_schema(faq: list[dict], page_url: str) -> str:
    """Generate JSON-LD FAQPage schema string."""
    entities = [
        {
            "@type": "Question",
            "name": item["question"],
            "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
        }
        for item in faq
    ]
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


def _build_article_schema(title: str, description: str, page_url: str, date_published: str) -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": date_published,
        "dateModified": utc_today(),
        "author": {"@type": "Organization", "name": "AI ToolStack Engine"},
        "url": page_url,
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


def render_content_page(
    page_spec: dict,
    generated: dict,
    output_dir: Path,
) -> Path:
    """Render a single content page to HTML.

    Parameters
    ----------
    page_spec:  Original page spec from pages.yaml
    generated:  Dict returned by content_generator (title, markdown, faq, …)
    output_dir: The directory under site/ where the HTML file should be saved

    Returns
    -------
    Path to the written HTML file
    """
    cfg = get_site_config()
    site_url = cfg["site_url"].rstrip("/")
    page_type = page_spec.get("page_type", "best")
    slug = page_spec["slug"]
    page_url = f"{site_url}/{page_type}/{slug}/"

    article_html = _markdown_to_html(generated.get("article_markdown", ""))
    faq = generated.get("faq", [])
    faq_schema = _build_faq_schema(faq, page_url) if faq else ""
    article_schema = _build_article_schema(
        generated.get("title", page_spec["title"]),
        generated.get("meta_description", ""),
        page_url,
        utc_today(),
    )

    faq_schema_script = ""
    if faq_schema:
        faq_schema_script = '<script type="application/ld+json">\n' + faq_schema + "\n</script>"

    adsense_block = ""
    if cfg.get("adsense_publisher_id"):
        adsense_block = (
            f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
            f'?client={cfg["adsense_publisher_id"]}" crossorigin="anonymous"></script>\n'
            f'<ins class="adsbygoogle" style="display:block" data-ad-client="{cfg["adsense_publisher_id"]}"'
            f' data-ad-slot="auto" data-ad-format="auto" data-full-width-responsive="true"></ins>\n'
            f"<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>"
        )

    html = _render_template(
        "page.html",
        SITE_NAME=cfg["site_name"],
        SITE_URL=site_url,
        PAGE_TITLE=generated.get("title", page_spec["title"]),
        META_DESCRIPTION=generated.get("meta_description", ""),
        PAGE_URL=page_url,
        ARTICLE_HTML=article_html,
        FAQ_SCHEMA_SCRIPT=faq_schema_script,
        ARTICLE_SCHEMA=article_schema,
        ADSENSE_BLOCK=adsense_block,
        LAST_UPDATED=utc_today(),
        PAGE_TYPE=page_type,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("Rendered page: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Index pages
# ---------------------------------------------------------------------------


def _page_card_html(p: dict, site_url: str) -> str:
    page_type = p.get("page_type", "best")
    slug = p.get("slug", "")
    title = p.get("title", slug)
    desc = p.get("intent", "")
    url = f"{site_url}/{page_type}/{slug}/"
    return (
        f'<article class="card">'
        f'<h2><a href="{url}">{title}</a></h2>'
        f"<p>{desc}</p>"
        f'<a class="btn" href="{url}">Read →</a>'
        f"</article>"
    )


def build_index_pages(all_pages: list[dict], published_slugs: set[str]) -> None:
    """Build /best/, /vs/, /categories/ index pages."""
    cfg = get_site_config()
    site_url = cfg["site_url"].rstrip("/")

    published = [p for p in all_pages if p["slug"] in published_slugs]
    best_pages = [p for p in published if p.get("page_type") == "best"]
    vs_pages = [p for p in published if p.get("page_type") == "vs"]

    # /best/
    best_cards = "\n".join(_page_card_html(p, site_url) for p in best_pages)
    best_html = _render_template(
        "index.html",
        SITE_NAME=cfg["site_name"],
        SITE_URL=site_url,
        PAGE_TITLE="Best AI Tools — Comparisons & Reviews",
        META_DESCRIPTION="Curated lists of the best AI tools for developers and DevOps engineers.",
        PAGE_URL=f"{site_url}/best/",
        SECTION_TITLE="Best AI Tools",
        SECTION_INTRO="Practical, engineer-written lists of the best AI tools by category.",
        CARDS_HTML=best_cards,
        ADSENSE_BLOCK="",
    )
    (SITE_DIR / "best").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "best" / "index.html").write_text(best_html, encoding="utf-8")

    # /vs/
    vs_cards = "\n".join(_page_card_html(p, site_url) for p in vs_pages)
    vs_html = _render_template(
        "index.html",
        SITE_NAME=cfg["site_name"],
        SITE_URL=site_url,
        PAGE_TITLE="AI Tool Comparisons — Side-by-Side Reviews",
        META_DESCRIPTION="Detailed AI tool comparisons to help developers choose the right tool.",
        PAGE_URL=f"{site_url}/vs/",
        SECTION_TITLE="Tool Comparisons",
        SECTION_INTRO="Head-to-head comparisons for the most common AI tool decisions developers face.",
        CARDS_HTML=vs_cards,
        ADSENSE_BLOCK="",
    )
    (SITE_DIR / "vs").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "vs" / "index.html").write_text(vs_html, encoding="utf-8")

    # /categories/
    categories: dict[str, list[dict]] = {}
    for p in published:
        kw = p.get("primary_keyword", "")
        # Simple category extraction from keyword
        if any(w in kw for w in ["kubernetes", "k8s"]):
            categories.setdefault("Kubernetes", []).append(p)
        elif any(w in kw for w in ["security", "scanning", "snyk", "semgrep"]):
            categories.setdefault("Security", []).append(p)
        elif any(w in kw for w in ["observab", "monitor", "log"]):
            categories.setdefault("Observability", []).append(p)
        elif any(w in kw for w in ["coding assistant", "code completion", "copilot", "cursor"]):
            categories.setdefault("Coding Assistants", []).append(p)
        elif any(w in kw for w in ["code review", "pull request"]):
            categories.setdefault("Code Review", []).append(p)
        elif any(w in kw for w in ["terraform", "pulumi", "infrastructure", "iac"]):
            categories.setdefault("Infrastructure as Code", []).append(p)
        elif any(w in kw for w in ["ci", "cd", "pipeline", "devops"]):
            categories.setdefault("CI/CD & DevOps", []).append(p)
        else:
            categories.setdefault("Developer Productivity", []).append(p)

    cat_cards = ""
    for cat_name, cat_pages in sorted(categories.items()):
        cat_slug = cat_name.lower().replace(" ", "-").replace("/", "-")
        cat_cards += f'<h2 id="{cat_slug}">{cat_name}</h2>\n'
        cat_cards += "\n".join(_page_card_html(p, site_url) for p in cat_pages)
        cat_cards += "\n"

    cat_html = _render_template(
        "index.html",
        SITE_NAME=cfg["site_name"],
        SITE_URL=site_url,
        PAGE_TITLE="AI Tool Categories for Developers",
        META_DESCRIPTION="Browse AI developer tools by category: coding assistants, observability, security, IaC, and more.",
        PAGE_URL=f"{site_url}/categories/",
        SECTION_TITLE="Browse by Category",
        SECTION_INTRO="Find AI tools by the problem you're trying to solve.",
        CARDS_HTML=cat_cards,
        ADSENSE_BLOCK="",
    )
    (SITE_DIR / "categories").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "categories" / "index.html").write_text(cat_html, encoding="utf-8")

    logger.info("Built index pages: /best/, /vs/, /categories/")


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------


def build_homepage(all_pages: list[dict], published_slugs: set[str]) -> None:
    """Build the root index.html."""
    cfg = get_site_config()
    site_url = cfg["site_url"].rstrip("/")
    published = [p for p in all_pages if p["slug"] in published_slugs]
    recent = published[-6:]  # last 6 published

    cards = "\n".join(_page_card_html(p, site_url) for p in reversed(recent))
    html = _render_template(
        "home.html",
        SITE_NAME=cfg["site_name"],
        SITE_URL=site_url,
        PAGE_TITLE=f"{cfg['site_name']} — AI Tools for Developers",
        META_DESCRIPTION=cfg["site_description"],
        PAGE_URL=site_url,
        RECENT_CARDS=cards,
        TOTAL_PAGES=len(published),
        ADSENSE_BLOCK="",
    )
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")
    logger.info("Built homepage")


# ---------------------------------------------------------------------------
# Copy static assets
# ---------------------------------------------------------------------------


def copy_static_assets() -> None:
    """Copy CSS/JS/images from templates/static to site/static."""
    src = TEMPLATES_DIR / "static"
    dst = SITE_DIR / "static"
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        logger.info("Copied static assets")


# ---------------------------------------------------------------------------
# AdSense-readiness static pages
# ---------------------------------------------------------------------------

_PRIVACY_MD = """# Privacy Policy

*Last updated: {today}*

## Information We Collect

This website does not collect personally identifiable information from visitors.

We use **Google Analytics** (if configured) to understand aggregate traffic patterns.
The analytics data is anonymised and does not identify individuals.

## Cookies

We may use cookies for analytics and advertising purposes (Google AdSense).
You can disable cookies in your browser settings at any time.

## Affiliate Links

Some links on this site are affiliate links. This means we may earn a commission if you
click through and make a purchase, at no extra cost to you.
We only recommend tools we believe are genuinely useful. Affiliate relationships do not
influence our editorial judgement.

## Third-Party Advertising

We use Google AdSense to display advertisements. Google may use cookies to serve ads
based on your prior visits to this website and other sites.
You can opt out of personalised advertising by visiting
[Google Ads Settings](https://www.google.com/settings/ads).

## Contact

If you have any questions about this privacy policy, please use the
[contact page](/contact/).
"""

_ABOUT_MD = """# About AI ToolStack Engine

AI ToolStack Engine is an independent website that publishes practical comparisons of
AI tools for software engineers and DevOps professionals.

## Our Mission

The AI developer tool space is crowded and noisy. Every vendor claims to be the best.
Our goal is to cut through the hype and give engineers honest, structured comparisons
they can use to make informed decisions.

## What We Cover

- **AI coding assistants**: GitHub Copilot, Cursor, Codeium, Tabnine, and more
- **Code review tools**: CodeRabbit, SonarQube, CodeClimate, and others
- **Observability platforms**: Datadog, New Relic, Grafana, Dynatrace
- **Security scanners**: Snyk, Semgrep, Checkov, Terrascan
- **Infrastructure as code**: Terraform, Pulumi, Ansible AI tooling
- **Kubernetes tools**: k9s, Lens, Karpenter, Kubecost
- **DevOps productivity**: CI/CD, incident response, cloud cost tools

## How We Make Money

We earn revenue through:
1. **Affiliate links** — when you click through to a paid tool and convert, we may earn a commission
2. **Google AdSense** — display advertising

Neither revenue source influences our editorial recommendations.

## Our Process

Each article is generated using AI and reviewed for accuracy against publicly available
product documentation and pricing pages. We update articles regularly as products change.

Pricing information is kept intentionally high-level (e.g., "free tier / paid plans")
to avoid publishing stale figures.
"""

_CONTACT_MD = """# Contact

Have a question, correction, or business enquiry?

**Email:** contact@aidevtools.me

## Corrections

If you spot an error in any of our comparisons — incorrect pricing, outdated features,
or a missing tool — please let us know. We take accuracy seriously and will update the
relevant article promptly.

## Affiliate & Partnership Enquiries

If you represent an AI developer tool and would like to discuss affiliate arrangements
or sponsored placement, please email us with your product details.

Note: Paid placements are clearly disclosed. We do not write fake positive reviews.
"""


def build_static_pages() -> None:
    """Generate Privacy Policy, About, and Contact pages."""
    cfg = get_site_config()
    site_url = cfg["site_url"].rstrip("/")
    today = utc_today()

    pages = [
        (
            "privacy",
            "Privacy Policy",
            "Our privacy policy covering analytics, cookies, and affiliate links.",
            _PRIVACY_MD.format(today=today),
        ),
        (
            "about",
            "About AI ToolStack Engine",
            "Independent AI tool comparisons for developers and DevOps engineers.",
            _ABOUT_MD,
        ),
        (
            "contact",
            "Contact Us",
            "Get in touch with corrections, questions, or partnership enquiries.",
            _CONTACT_MD,
        ),
    ]

    for slug, title, description, md_content in pages:
        html_body = _markdown_to_html(md_content)
        html = _render_template(
            "static_page.html",
            SITE_NAME=cfg["site_name"],
            SITE_URL=site_url,
            PAGE_TITLE=title,
            META_DESCRIPTION=description,
            PAGE_URL=f"{site_url}/{slug}/",
            CONTENT_HTML=html_body,
        )
        out_dir = SITE_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        logger.info("Built static page: /%s/", slug)
