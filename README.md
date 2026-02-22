# AI ToolStack Engine

> **100% automated** AI tool comparison site for developers and DevOps engineers.
> Publishes high-intent "best-of" lists and head-to-head comparisons.
> Earns revenue via **affiliate links** and **Google AdSense** — with zero manual publishing steps.

---

## What This Site Is

**AI ToolStack Engine** generates and publishes SEO-optimised comparison pages for AI developer tools:

- **Best-of lists** — "Best AI code review tools", "Best AI tools for Kubernetes", etc.
- **VS pages** — "GitHub Copilot vs Cursor", "Datadog vs New Relic AI features", etc.

Every article is:

- Written in a practical engineering tone (no marketing hype)
- 1,400–2,000 words with comparison tables, pros/cons, pricing notes, and FAQs
- Structured for Google rich results (Article + FAQPage JSON-LD schema)
- Automatically published daily via GitHub Actions

---

## How It Earns Money

### 1. Affiliate links
Each article contains three affiliate CTA blocks (top, mid, bottom).  
Affiliate URLs are mapped in `config/affiliates.yaml`.  
When a reader clicks through and converts, you earn a commission.

**Affiliate programmes to join:**
| Tool | Programme |
|------|-----------|
| GitHub Copilot | GitHub Partner Programme |
| Datadog | Datadog Affiliate Programme |
| New Relic | Impact.com / direct |
| Snyk | Snyk Partner Programme |
| PagerDuty | PagerDuty Affiliate via CJ Affiliate |
| Tabnine | Tabnine Referral Programme |
| Cursor | Direct partnership |

Update `config/affiliates.yaml` with your real affiliate URLs and they will appear in every relevant article automatically on the next build.

### 2. Google AdSense
AdSense `<ins>` blocks are included in the layout templates.  
Set the `ADSENSE_PUBLISHER_ID` secret in GitHub → Settings → Secrets.  
Once set, AdSense ads render on every page automatically.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Content generation | Google Gemini API (`gemini-1.5-flash`) |
| Static site builder | Pure Python (no Jekyll/Hugo) |
| Hosting | GitHub Pages (free) |
| Automation | GitHub Actions (free tier) |
| Linting/formatting | ruff + black |
| Tests | pytest |

---

## Exact Setup Steps

### Prerequisites
- Python 3.11+
- A GitHub account
- A Google Cloud account with Gemini API access

### Step 1 — Fork/clone and install

```bash
git clone https://github.com/sachin/ai-toolstack-engine.git
cd ai-toolstack-engine
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Step 2 — Add your Gemini API key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create an API key.
2. In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GEMINI_API_KEY`
   - Value: your key

### Step 3 — Configure your site URL

In GitHub: **Settings → Secrets and variables → Actions → Variables → New repository variable**

| Name | Value |
|------|-------|
| `SITE_URL` | `https://aidevtools.me` |
| `SITE_NAME` | `AI ToolStack Engine` (or your brand name) |

### Step 4 — Configure your custom domain

A `CNAME` file containing `aidevtools.me` is already in the repo and gets copied to `site/` on every build.

Point your DNS at GitHub Pages (add these records at your registrar):

| Type | Host | Value |
|------|------|-------|
| `A` | `@` | `185.199.108.153` |
| `A` | `@` | `185.199.109.153` |
| `A` | `@` | `185.199.110.153` |
| `A` | `@` | `185.199.111.153` |
| `CNAME` | `www` | `sachin.github.io` |

Then in GitHub: **Settings → Pages → Custom domain** → enter `aidevtools.me` → Save → check "Enforce HTTPS" once the cert is issued (~10 min).

### Step 5 — Enable GitHub Pages

1. **Settings → Pages**
2. Source: **GitHub Actions**
3. That's it — the workflow handles deployment automatically.

### Step 6 — Test locally

```bash
# Generate 1 page (uses GEMINI_API_KEY from your environment)
export GEMINI_API_KEY=your-key-here
python scripts/daily_run.py --pages 1

# Build the site locally
python scripts/build_site.py

# Open site/index.html in your browser
open site/index.html
```

### Step 7 — Trigger the first run

Either wait for the daily 06:00 UTC cron, or:

1. Go to **Actions → Daily Generate & Deploy → Run workflow**
2. Set "Number of pages to generate" to `5` for a faster start
3. Click **Run workflow**

---

## How to Add Affiliate Links

1. Open `config/affiliates.yaml`
2. Replace the placeholder homepage URL with your affiliate URL for any tool:

```yaml
affiliates:
  GitHub Copilot: https://github.com/features/copilot?ref=your-affiliate-id
  Datadog: https://www.datadoghq.com/?ref=your-affiliate-id
```

3. Re-run the site build to update all pages (or wait for the next daily run):

```bash
python scripts/build_site.py
```

Affiliate links are injected automatically into every article that mentions the tool.

---

## How to Scale to 500+ Pages

The system is designed to scale linearly. Here's the path:

### 1. Add more pages to `config/pages.yaml`

The file already has 60 page specs. Add as many as you want:

```yaml
- page_type: best
  primary_keyword: best ai tools for rust developers
  title: "Best AI Tools for Rust Developers in 2026"
  slug: best-ai-tools-for-rust-developers
  intent: Find AI coding assistants that work well with Rust
  target_audience: Rust developers, systems programmers
```

### 2. Increase `PAGES_PER_DAY`

Set the `PAGES_PER_DAY` environment variable (or GitHub Variable):

```
PAGES_PER_DAY=10
```

At 10 pages/day, 500 pages takes ~50 days.  
At 5 pages/day, ~100 days.

### 3. Add more tools to `config/tools.yaml`

More tools = richer articles. Add any AI dev tool following the existing schema.

### 4. Run multiple workflow triggers per day

Edit `.github/workflows/deploy.yml` to add more cron entries:

```yaml
schedule:
  - cron: "0 6 * * *"   # 06:00 UTC
  - cron: "0 14 * * *"  # 14:00 UTC
  - cron: "0 20 * * *"  # 20:00 UTC
```

This triples throughput while still respecting GitHub Actions free-tier limits.

---

## AdSense Readiness Checklist

Before applying for Google AdSense, make sure you have these pages published:

- [ ] **Privacy Policy** — required by AdSense; discloses data collection and affiliate links
- [ ] **About page** — explains who runs the site and the editorial process
- [ ] **Contact page** — provides a way to reach you (email or contact form)
- [ ] At least **20–30 published articles** with original content
- [ ] No broken links on the homepage and index pages
- [ ] Mobile-responsive design ✅ (included in `templates/static/style.css`)
- [ ] Valid HTML with correct meta tags ✅ (built into templates)
- [ ] Sitemap submitted to Google Search Console ✅ (`/sitemap.xml` auto-generated)
- [ ] `robots.txt` in place ✅ (auto-generated)

Static versions of Privacy Policy, About, and Contact pages are auto-generated at build time (see `scripts/build_site.py`).

---

## Project Structure

```
ai-toolstack-engine/
├── .github/
│   └── workflows/
│       └── deploy.yml          ← Daily generate + deploy workflow
├── config/
│   ├── pages.yaml              ← 60+ page specs (best + vs)
│   ├── tools.yaml              ← 50+ AI/dev tool definitions
│   └── affiliates.yaml         ← tool → affiliate URL mapping
├── content/                    ← Generated markdown (committed by bot)
│   ├── best/
│   └── vs/
├── scripts/
│   ├── daily_run.py            ← Generates N new pages per day
│   └── build_site.py           ← Rebuilds entire static site
├── site/                       ← Built HTML (deployed to GitHub Pages)
│   ├── best/
│   ├── vs/
│   ├── categories/
│   ├── static/
│   ├── index.html
│   ├── sitemap.xml
│   ├── robots.txt
│   └── rss.xml
├── src/
│   ├── __init__.py
│   ├── config_loader.py        ← YAML config reading
│   ├── content_generator.py    ← Gemini API integration
│   ├── site_builder.py         ← Markdown → HTML + index pages
│   ├── sitemap.py              ← sitemap.xml, robots.txt, rss.xml
│   └── utils.py                ← slugify, timestamps, word count
├── templates/
│   ├── page.html               ← Content page template
│   ├── index.html              ← Section listing template
│   ├── home.html               ← Homepage template
│   └── static/
│       └── style.css           ← Dark-theme CSS
├── tests/
│   ├── test_utils.py
│   ├── test_sitemap.py
│   └── test_site_builder.py
├── .gitignore
├── pyproject.toml
└── README.md
```

---

## Local Development

```bash
# Lint
ruff check src/ scripts/ tests/

# Format
black src/ scripts/ tests/

# Tests
pytest tests/ -v

# Dry run (no Gemini calls)
python scripts/daily_run.py --dry-run

# Full local generate + build
export GEMINI_API_KEY=your-key
python scripts/daily_run.py --pages 3
python scripts/build_site.py
```

---

## Environment Variables Reference

| Variable | Where to set | Description |
|----------|-------------|-------------|
| `GEMINI_API_KEY` | GitHub Secret | Required. Your Google Gemini API key. |
| `ADSENSE_PUBLISHER_ID` | GitHub Secret | Optional. Your `ca-pub-XXXXXXXX` AdSense ID. |
| `SITE_URL` | GitHub Variable | Your GitHub Pages URL. |
| `SITE_NAME` | GitHub Variable | Your site's display name. |
| `PAGES_PER_DAY` | GitHub Variable | How many pages to generate per run (default: 3). |
| `GEMINI_MODEL` | GitHub Variable | Gemini model to use (default: `gemini-1.5-flash`). |

---

## License

MIT
