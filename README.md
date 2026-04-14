# LABAT — WIHY Growth & Marketing Automation Platform

Five AI-powered agents and a complete marketing stack: paid ads, organic SEO, social posting, community engagement, lead funnels, and content publishing — all deployed as independent Cloud Run microservices.

---

## Table of Contents

- [Agents](#agents)
- [Brands](#brands)
- [Architecture Overview](#architecture-overview)
- [Repository Structure](#repository-structure)
- [Cloud Run Services](#cloud-run-services)
- [Book Funnel](#book-funnel)
- [Content Pipeline](#content-pipeline)
- [SEO Tooling](#seo-tooling)
- [Ad Management](#ad-management)
- [Deployment](#deployment)
- [Firebase Routing](#firebase-routing)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Key Architecture Concepts](#key-architecture-concepts)
- [Scripts Reference](#scripts-reference)
- [Data Files](#data-files)
- [Documentation](#documentation)
- [Relationship to wihy_ml](#relationship-to-wihy_ml)

---

## Agents

| Agent | Cloud Run Service | Role | Entry Point |
|-------|-------------------|------|-------------|
| **LABAT** | `wihy-labat` | Lead Automation, Business Ads & Targeting (Meta/Facebook) | `src.apps.labat_app:app` |
| **Alex** | `wihy-alex` | SEO discovery, keyword research, autonomous blog content | `src.apps.alex_app:app` |
| **Astra** | `wihy-astra` | Discovery agent (Alex variant for different brand scopes) | `src.apps.astra_app:app` |
| **Shania** | `wihy-shania` | Facebook/LinkedIn/Instagram post creation & publishing | `src.apps.shania_app:app` |
| **Maya** | `wihy-maya` | Community engagement — replies, comments, threads | `src.apps.maya_app:app` |
| **Master** | `wihy-master-agent` | Orchestrator — coordinates cross-agent campaigns | `src.apps.master_agent_app:app` |

### What Each Agent Does

**LABAT** — The paid-ads engine. Creates Meta/Facebook ad campaigns, manages lead forms, runs A/B tests, auto-pauses underperformers, auto-scales winners, syncs leads to Firestore, and triggers welcome emails via SendGrid.

**Alex / Astra** — The SEO brain. Pulls Google Search Console data, discovers keyword opportunities, generates blog post topics, creates comparison pages, and publishes content to WordPress via REST API.

**Shania** — The creative arm. Generates branded social media graphics (TypeScript/Puppeteer) and publishes posts to Facebook Pages and LinkedIn. Supports 12+ template types (stat cards, research tips, hook images, quote cards, etc.) across all brands.

**Maya** — The engagement layer. Monitors social media threads, auto-replies to comments, posts to Twitter/Instagram/Facebook/Threads/TikTok, and manages community interactions.

**Master Agent** — The orchestrator. Coordinates multi-agent workflows: "create a campaign" → LABAT creates ads → Shania generates creatives → Alex writes landing page content → Maya handles engagement on the posts.

---

## Brands

All agents serve 5 brands. Each deployment is scoped via `*_BRAND_SCOPE` env vars:

| Brand | Scope Value | Domain | Focus |
|-------|-------------|--------|-------|
| **WIHY** | `wihy` | wihy.ai | AI-powered health platform |
| **Community Groceries** | `communitygroceries` | communitygroceries.com | Affordable healthy eating |
| **Vowels** | `vowels` | vowels.org | Clean eating & family nutrition |
| **Children's Nutrition** | `childrennutrition` | whatishealthy.org | Kids' health & nutrition |
| **Parenting with Christ** | `parentingwithchrist` | parentingwithchrist.com | Faith-based family wellness |

---

## Architecture Overview

```
                    ┌──────────────┐
                    │ Firebase     │
                    │ Hosting      │
                    └──────┬───────┘
                           │ URL-based routing
        ┌──────────┬───────┼───────┬───────────┐
        ▼          ▼       ▼       ▼           ▼
  ┌──────────┐ ┌────────┐ ┌─────┐ ┌────────┐ ┌──────┐
  │ LABAT    │ │ Alex/  │ │Maya │ │Shania  │ │Book  │
  │ (Ads)    │ │ Astra  │ │(Eng)│ │Graphics│ │Funnel│
  └────┬─────┘ └───┬────┘ └──┬──┘ └───┬────┘ └──┬───┘
       │            │         │        │          │
       ▼            ▼         ▼        ▼          ▼
  ┌─────────┐  ┌─────────┐  ┌──────┐  ┌───────┐  ┌─────────┐
  │Meta API │  │GSC API  │  │Social│  │Puppeteer│ │Stripe  │
  │Lead Sync│  │WordPress│  │APIs  │  │Node.js │  │Firestore│
  │Firestore│  │Firestore│  │      │  │        │  │SendGrid │
  └─────────┘  └─────────┘  └──────┘  └───────┘  └─────────┘
```

**Single Docker image** → multiple Cloud Run services. The `APP_MODULE` env var selects which FastAPI app boots:

```dockerfile
ENV APP_MODULE=src.apps.labat_app:app   # default
CMD uvicorn $APP_MODULE --host 0.0.0.0 --port $PORT --workers 1
```

---

## Repository Structure

```
labat/
├── src/
│   ├── apps/                        # FastAPI entry points (8 apps)
│   │   ├── labat_app.py             # LABAT paid ads service
│   │   ├── alex_app.py              # Alex SEO discovery
│   │   ├── astra_app.py             # Astra (Alex variant)
│   │   ├── shania_app.py            # Shania social posting
│   │   ├── maya_app.py              # Maya engagement
│   │   ├── master_agent_app.py      # Master orchestrator
│   │   ├── book_app.py              # Book funnel / WhatIsHealthy landing
│   │   └── moltbook_bot.py          # Automated research posting bot
│   │
│   ├── labat/                       # LABAT core (116 files)
│   │   ├── services/                # 27 service modules
│   │   │   ├── strategy_rules.py    # Brand positioning & targeting presets
│   │   │   ├── automation_service.py # Hourly cron: pause/scale/rotate
│   │   │   ├── lead_sync_service.py  # Meta → Firestore → SendGrid
│   │   │   ├── campaign_service.py   # Campaign CRUD
│   │   │   ├── creative_service.py   # Ad creative management
│   │   │   ├── compliance_service.py # Ad policy enforcement
│   │   │   └── ...
│   │   ├── routers/                 # 21 API routers
│   │   │   ├── ads_routes.py        # Ad campaign endpoints
│   │   │   ├── leads_routes.py      # Lead management
│   │   │   ├── automation_routes.py  # Cron triggers
│   │   │   ├── blog_routes.py       # Blog publishing endpoints
│   │   │   ├── content_routes.py    # Content generation
│   │   │   ├── master_agent_routes.py # Cross-agent orchestration
│   │   │   └── ...
│   │   ├── brands.py                # Brand → Facebook Page ID mapping
│   │   ├── config.py                # Meta/LinkedIn/Gemini configuration
│   │   ├── meta_client.py           # Meta Graph API client
│   │   ├── linkedin_client.py       # LinkedIn API client
│   │   └── schemas.py               # Pydantic request/response models
│   │
│   ├── alex/                        # Alex/Astra SEO agent (15 files)
│   │   ├── services/alex_service.py  # SEO analysis & content generation
│   │   ├── services/ad_posting_service.py # Ad-to-blog integration
│   │   ├── routers/alex_routes.py    # SEO API endpoints
│   │   └── config.py                # Alex-specific config
│   │
│   ├── maya/                        # Maya engagement agent (7 files)
│   │   ├── services/
│   │   │   ├── engagement_poster_service.py  # Thread monitoring & replies
│   │   │   ├── social_posting_service.py     # Multi-platform posting
│   │   │   └── social_template_registry.py   # Post templates
│   │   └── routers/engagement_routes.py
│   │
│   ├── content/                     # Content pipeline (13 files)
│   │   ├── blog_publisher.py        # WordPress REST API publisher
│   │   ├── page_renderer.py         # HTML page generation
│   │   ├── generate_health_posts.py  # AI-generated health blog posts
│   │   ├── generate_comparison_pages.py # Product comparison content
│   │   ├── generate_trending_meal_pages.py # Trending meal content
│   │   ├── generate_wihy_posts.py   # WIHY-branded posts
│   │   ├── meals_publisher.py       # Meal-focused content
│   │   ├── backfill_meal_hero_images.py # Hero image generation
│   │   ├── patch_commercial_pages.py # Update published pages
│   │   ├── patch_factor_pages.py    # Factor page updates
│   │   ├── post_publish_hooks.py    # Post-publication automation
│   │   └── commercial_page_policy.py # Content compliance rules
│   │
│   ├── services/                    # Book funnel services (6 files)
│   │   ├── book_leads_service.py    # eBook lead capture → Firestore
│   │   ├── book_stripe_service.py   # Stripe checkout for book orders
│   │   ├── nurture_service.py       # Email nurture sequences (SendGrid)
│   │   ├── launch_leads_service.py  # Launch/waitlist lead capture
│   │   ├── launch_nurture_service.py # Launch email sequences
│   │   └── page_store.py            # JSON file store for SEO page drafts
│   │
│   ├── routers/                     # Book funnel routes (2 files)
│   │   ├── book_routes.py           # Book lead capture, Stripe, Meta CAPI
│   │   └── launch_routes.py         # Launch/waitlist lead capture, Meta CAPI
│   │
│   └── shared/                      # Shared deps from wihy_ml (8 files)
│       ├── auth/auth_client.py      # JWT verification via auth.wihy.ai
│       ├── config/models.py         # OpenAI model configuration
│       ├── middleware/request_logger.py # HTTP request logging
│       └── monitoring/              # Health checks & metrics
│
├── shania/                          # Shania Graphics (TypeScript/Node.js)
│   ├── src/                         # TypeScript source (templates, renderers)
│   ├── preview/                     # Generated preview images & HTML
│   ├── package.json
│   └── tsconfig.json
│
├── static_whatishealthy/            # Book funnel landing page (22 files)
│   ├── index.html                   # Main landing page
│   ├── confirm-download.html        # Email confirmation
│   ├── thank-you.html               # Post-download thank you
│   ├── oto.html                     # One-time offer upsell
│   ├── unsubscribe.html             # Unsubscribe page
│   ├── WhatisHealthy_eBook.pdf      # The actual eBook
│   ├── book-*.jpg/png               # Book cover variants
│   └── *.png/svg                    # Logos & lifestyle images
│
├── data/                            # SEO data & ad assets (67 files)
│   ├── ad_images/                   # 34 ad creative images
│   ├── blog_heroes/                 # Blog hero images
│   ├── cg_*.json                    # Community Groceries SEO packs
│   ├── wihy_*.json                  # WIHY keyword & content data
│   ├── gsc_*.json                   # Google Search Console exports
│   ├── health_keywords_*.json       # Health keyword databases
│   └── cors_*.json                  # CORS configs for GCS buckets
│
├── cloudbuild.*.yaml                # 24 Cloud Build configs
├── firebase.json                    # Firebase Hosting routing
├── firebase.labat.json              # LABAT-specific Firebase config
├── firebase.whatishealthy.json       # WhatIsHealthy Firebase config
├── Dockerfile                       # Single image, APP_MODULE selects agent
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
└── *.md                             # Architecture docs & guides
```

---

## Cloud Run Services

| Service | Cloud Run Name | Build Config | APP_MODULE |
|---------|---------------|--------------|------------|
| **LABAT** (generic) | `wihy-labat` | `cloudbuild.labat.yaml` | `src.apps.labat_app:app` |
| **LABAT WIHY** | `wihy-labat-wihy` | `cloudbuild.labat-wihy.yaml` | `src.apps.labat_app:app` |
| **LABAT CG** | `wihy-labat-cg` | `cloudbuild.labat-cg.yaml` | `src.apps.labat_app:app` |
| **LABAT Vowels** | `wihy-labat-vowels` | `cloudbuild.labat-vowels.yaml` | `src.apps.labat_app:app` |
| **LABAT CN** | `wihy-labat-cn` | `cloudbuild.labat-cn.yaml` | `src.apps.labat_app:app` |
| **LABAT PWC** | `wihy-labat-pwc` | `cloudbuild.labat-pwc.yaml` | `src.apps.labat_app:app` |
| **Alex** (generic) | `wihy-alex` | `cloudbuild.alex.yaml` | `src.apps.alex_app:app` |
| **Alex WIHY** | `wihy-alex-wihy` | `cloudbuild.alex-wihy.yaml` | `src.apps.alex_app:app` |
| **Alex CG** | `wihy-alex-cg` | `cloudbuild.alex-cg.yaml` | `src.apps.alex_app:app` |
| **Alex Vowels** | `wihy-alex-vowels` | `cloudbuild.alex-vowels.yaml` | `src.apps.alex_app:app` |
| **Alex CN** | `wihy-alex-cn` | `cloudbuild.alex-cn.yaml` | `src.apps.alex_app:app` |
| **Alex PWC** | `wihy-alex-pwc` | `cloudbuild.alex-pwc.yaml` | `src.apps.alex_app:app` |
| **Astra** | `wihy-astra` | `cloudbuild.astra.yaml` | `src.apps.astra_app:app` |
| **Shania** (generic) | `wihy-shania` | `cloudbuild.shania.yaml` | `src.apps.shania_app:app` |
| **Shania Graphics** | `wihy-shania-graphics` | `cloudbuild.shania-graphics.yaml` | Node.js |
| **Shania WIHY** | `wihy-shania-wihy` | `cloudbuild.shania-wihy.yaml` | `src.apps.shania_app:app` |
| **Shania CG** | `wihy-shania-cg` | `cloudbuild.shania-cg.yaml` | `src.apps.shania_app:app` |
| **Shania Vowels** | `wihy-shania-vowels` | `cloudbuild.shania-vowels.yaml` | `src.apps.shania_app:app` |
| **Shania CN** | `wihy-shania-cn` | `cloudbuild.shania-cn.yaml` | `src.apps.shania_app:app` |
| **Shania PWC** | `wihy-shania-pwc` | `cloudbuild.shania-pwc.yaml` | `src.apps.shania_app:app` |
| **Maya** | `wihy-maya` | `cloudbuild.maya.yaml` | `src.apps.maya_app:app` |
| **Master Agent** | `wihy-master-agent` | `cloudbuild.master.yaml` | `src.apps.master_agent_app:app` |
| **Book Funnel** | `wihy-ml-book` | `cloudbuild.book.yaml` | `src.apps.book_app:app` |
| **Moltbook Bot** | `wihy-moltbook` | `cloudbuild.moltbook.yaml` | `src.apps.moltbook_bot:app` |

All services run on GCP Cloud Run in `us-central1`, scale to zero, and use `--allow-unauthenticated`.

---

## Book Funnel

The "What Is Healthy?" eBook funnel converts cold traffic into email subscribers:

```
Meta Ad → Landing Page → Email Capture → eBook Download → Nurture Sequence → Upsell
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Landing page | `static_whatishealthy/index.html` | Lead magnet offer page |
| Confirmation | `static_whatishealthy/confirm-download.html` | Email verification |
| Thank you | `static_whatishealthy/thank-you.html` | Download delivery |
| Upsell | `static_whatishealthy/oto.html` | One-time offer |
| App entry | `src/apps/book_app.py` | FastAPI app serving static + API |
| Lead capture | `src/services/book_leads_service.py` | Firestore lead storage |
| Payments | `src/services/book_stripe_service.py` | Stripe checkout |
| Nurture | `src/services/nurture_service.py` | SendGrid drip emails |
| Routes | `src/routers/book_routes.py` | API endpoints + Meta CAPI tracking |
| Launch leads | `src/services/launch_leads_service.py` | Waitlist lead capture |
| Launch nurture | `src/services/launch_nurture_service.py` | Launch email sequences |
| Launch routes | `src/routers/launch_routes.py` | Launch API + Meta CAPI |

### Meta Conversions API (CAPI)

Both `book_routes.py` and `launch_routes.py` send server-side conversion events to Meta via the Conversions API for accurate ad attribution (bypasses browser ad blockers).

---

## Content Pipeline

The `src/content/` module generates and publishes blog content to WordPress sites:

| File | Purpose |
|------|---------|
| `blog_publisher.py` | Core WordPress REST API publisher |
| `page_renderer.py` | HTML page generation from templates |
| `generate_health_posts.py` | AI-generated health/nutrition articles |
| `generate_comparison_pages.py` | Product comparison pages (SEO) |
| `generate_trending_meal_pages.py` | Trending meal content pages |
| `generate_wihy_posts.py` | WIHY-branded blog posts |
| `meals_publisher.py` | Meal-focused content publishing |
| `backfill_meal_hero_images.py` | Generate hero images for posts |
| `patch_commercial_pages.py` | Update published commercial pages |
| `patch_factor_pages.py` | Factor page updates (bulk) |
| `post_publish_hooks.py` | Post-publish automation (IndexNow, internal links) |
| `commercial_page_policy.py` | Content compliance & policy rules |

---

## SEO Tooling

Scripts in the root directory for SEO research and keyword management:

### Google Search Console

| Script | Purpose |
|--------|---------|
| `_gsc_all_queries.py` | Export all GSC search queries |
| `_gsc_analyze.py` | Analyze GSC performance data |
| `_gsc_broad_health.py` | Broad health keyword discovery |
| `_gsc_health_keywords.py` | Health-specific keyword extraction |
| `_gsc_query.py` | Query specific GSC data |
| `_gsc_trending_meals.py` | Trending meal search terms |
| `_gsc_user_queries.py` | User query pattern analysis |

### Keyword Building

| Script | Purpose |
|--------|---------|
| `_build_curated_keywords.py` | Build curated keyword lists |
| `_build_food_lifestyle_keywords.py` | Food & lifestyle keyword generation |
| `_build_google_search_keywords.py` | Google search keyword packs |
| `_build_holistic_keywords.py` | Holistic health keywords |
| `_build_vitamin_keywords.py` | Vitamin/supplement keywords |
| `_build_wihy_content_keywords_old.py` | Legacy WIHY keyword builder |
| `_build_trending_meal_inventory.py` | Trending meal keyword inventory |
| `_health_keywords.py` | Master health keyword processor |
| `_brand_search_terms.py` | Brand search term analysis |
| `_find_health_kw.py` | Health keyword finder |
| `_find_test_kw.py` | Test keyword discovery |
| `_list_all_keywords.py` | List all keywords across brands |
| `_extract_all_queries.py` | Extract all search queries |
| `_clean_keywords.py` | Deduplicate & clean keyword lists |
| `_check_diet_keywords.py` | Diet-specific keyword validation |
| `_check_dupes.py` / `_find_dupes.py` | Duplicate detection |
| `_check_seo.py` | SEO health check |
| `_regen_sitemap.py` | Regenerate XML sitemaps |

### Blog Management

| Script | Purpose |
|--------|---------|
| `_backfill_indexnow.py` | Submit pages to IndexNow for faster crawling |
| `_backfill_internal_links.py` | Add internal links to existing posts |
| `_fix_existing_posts.py` | Bulk fix published posts |
| `_fix_dupe_title.py` | Fix duplicate title tags |
| `_inspect_post.py` | Inspect individual post data |
| `_inspect_book_training.py` | Inspect book training data |
| `_check_post.py` | Validate post content |
| `_check_progress.py` | Check publishing progress |
| `_scan_body_json.py` | Scan post body JSON structure |

---

## Ad Management

Scripts for Meta/Facebook ad creation and management:

| Script | Purpose |
|--------|---------|
| `_create_formula_ads.py` | Create formula-based ad campaigns |
| `_fix_vowels_ads.py` | Fix Vowels brand ads (original) |
| `_fix_vowels_ads_v3.py` – `v7.py` | Iterative Vowels ad fixes |
| `_cleanup_old_vowels_ads.py` | Clean up deprecated ad sets |
| `_check_ads.py` | Check ad status |
| `_check_ad_perf.py` | Check ad performance metrics |
| `_check_asset_groups.py` | Audit ad asset groups |
| `_update_ad_links.py` | Update destination URLs in ads |
| `_backfill_56_images.py` | Backfill missing ad images |

Ad creative images are stored in `data/ad_images/` (34 files).

---

## Deployment

### Deploy Individual Services

```bash
# LABAT (all brands)
gcloud builds submit --config cloudbuild.labat.yaml

# Brand-scoped LABAT (one per brand)
gcloud builds submit --config cloudbuild.labat-wihy.yaml
gcloud builds submit --config cloudbuild.labat-cg.yaml
gcloud builds submit --config cloudbuild.labat-vowels.yaml
gcloud builds submit --config cloudbuild.labat-cn.yaml
gcloud builds submit --config cloudbuild.labat-pwc.yaml

# Alex SEO (all brands)
gcloud builds submit --config cloudbuild.alex.yaml

# Brand-scoped Alex
gcloud builds submit --config cloudbuild.alex-wihy.yaml
gcloud builds submit --config cloudbuild.alex-cg.yaml

# Shania posting
gcloud builds submit --config cloudbuild.shania.yaml

# Shania Graphics (TypeScript service)
gcloud builds submit --config cloudbuild.shania-graphics.yaml

# Maya engagement
gcloud builds submit --config cloudbuild.maya.yaml

# Master Agent orchestrator
gcloud builds submit --config cloudbuild.master.yaml

# Book funnel
gcloud builds submit --config cloudbuild.book.yaml

# Moltbook research bot
gcloud builds submit --config cloudbuild.moltbook.yaml
```

### Deploy Firebase Routing

```bash
firebase deploy --only hosting
```

---

## Firebase Routing

Firebase Hosting rewrites incoming traffic to Cloud Run services:

```
/api/labat-wihy/**     → wihy-labat-wihy
/api/labat-cg/**       → wihy-labat-cg
/api/labat-vowels/**   → wihy-labat-vowels
/api/labat-cn/**       → wihy-labat-cn
/api/labat-pwc/**      → wihy-labat-pwc
/api/labat/**          → wihy-labat (generic)
/api/astra/**          → wihy-astra
/api/graphics/**       → wihy-shania-graphics
/api/engagement/**     → wihy-maya
/api/book/**           → wihy-ml-book
/api/launch/**         → wihy-ml-book
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Shania Graphics only)
- `.env` file with required secrets

### Setup

```bash
# Python environment
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# Copy env template
cp .env.example .env
# Fill in secrets (Meta tokens, OpenAI key, etc.)
```

### Run Locally

```bash
# LABAT (paid ads)
uvicorn src.apps.labat_app:app --host 0.0.0.0 --port 8080

# Alex (SEO)
uvicorn src.apps.alex_app:app --host 0.0.0.0 --port 8081

# Maya (engagement)
uvicorn src.apps.maya_app:app --host 0.0.0.0 --port 8082

# Book funnel
uvicorn src.apps.book_app:app --host 0.0.0.0 --port 8083

# Master Agent
uvicorn src.apps.master_agent_app:app --host 0.0.0.0 --port 8084

# Shania Graphics (TypeScript)
cd shania && npm install && npm run dev
```

### Run Scripts

```bash
# SEO keyword analysis
python _gsc_all_queries.py

# Generate health blog posts
python -m src.content.generate_health_posts

# Check ad performance
python _check_ad_perf.py
```

---

## Environment Variables

See [.env.example](.env.example) for the full template.

### Required (Core)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API for AI content generation |
| `WIHY_ML_CLIENT_ID` | Auth for services.wihy.ai |
| `WIHY_ML_CLIENT_SECRET` | Auth for services.wihy.ai |

### Meta / Facebook

| Variable | Purpose |
|----------|---------|
| `META_ACCESS_TOKEN` | Meta Graph API access |
| `META_AD_ACCOUNT_ID` | Ad account (`act_218581359635343`) |
| `META_BUSINESS_ID` | Business Manager ID |

### Shania (Posting)

| Variable | Purpose |
|----------|---------|
| `SHANIA_PAGE_ACCESS_TOKEN` | Facebook Page posting |
| `SHANIA_LONG_LIVED_USER_TOKEN` | Long-lived token for Page API |

### Maya (Engagement)

| Variable | Purpose |
|----------|---------|
| `TWITTER_API_KEY` / `SECRET` | Twitter/X API |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram posting |
| `THREADS_ACCESS_TOKEN` | Threads posting |

### Brand Scoping

| Variable | Purpose |
|----------|---------|
| `LABAT_BRAND_SCOPE` | Scope LABAT to a brand (`wihy`, `communitygroceries`, etc.) |
| `ALEX_BRAND_SCOPE` | Scope Alex to a brand |
| `SHANIA_BRAND_SCOPE` | Scope Shania to a brand |

---

## Key Architecture Concepts

### Strategy Rules (Single Source of Truth)

`src/labat/services/strategy_rules.py` contains ALL brand positioning, targeting presets, funnel rules, and lead form questions. Both LABAT and Alex reference this to maintain consistent messaging.

### Automation Cycle

`src/labat/services/automation_service.py` runs an hourly loop:
1. Check ad performance metrics
2. Auto-pause underperforming ad sets (CPA > threshold)
3. Auto-scale winning ad sets (increase budget)
4. Rotate A/B creative variants
5. Sync new leads from Meta to Firestore

### Lead Sync Pipeline

```
Meta Lead Form → lead_sync_service.py → Firestore → SendGrid Welcome Email
                                        ↓
                                nurture_service.py → Drip email sequence
```

### Brand Isolation

All 5 brands share one Meta ad account (`act_218581359635343`) but are isolated via:
- `LABAT_BRAND_SCOPE` env var per Cloud Run deployment
- `brands.py` maps scope → Facebook Page IDs, pixel IDs, domains
- Campaign naming convention: `{brand}_{funnel_stage}_{variant}`

### Shania Graphics Pipeline

```
Content request → Shania API → TypeScript template engine → Puppeteer → PNG/HTML
                                        ↓
                              12+ templates × 5 brands × 2 sizes (feed/story)
```

---

## Scripts Reference

### Test Scripts

| Script | Purpose |
|--------|---------|
| `test_labat_api.py` | Test LABAT API endpoints |
| `test_labat_campaign_shania.py` | Test LABAT → Shania creative flow |
| `test_labat_full.py` | Full LABAT integration test |
| `test_labat_live.py` | Live LABAT test against prod |
| `test_live_campaign.py` | Live campaign creation test |
| `test_master_agent.py` | Master Agent orchestration test |
| `test_orchestrate_post.py` | Post orchestration test |
| `test_shania_labat_roundtrip.py` | Shania ↔ LABAT roundtrip |
| `tmp_test_shania.py` | Quick Shania test |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `check_groups.py` | Check Facebook ad groups |
| `list_pages.py` | List WordPress pages |
| `tmp_fix_cg_bad_slug.py` | Fix CG bad URL slugs |
| `tmp_generate_missing_images.py` | Generate missing hero images |
| `tmp_publish_cg_topic_posts.py` | Bulk publish CG topic posts |
| `tmp_verify_images.py` | Verify image URLs are valid |

---

## Data Files

### SEO Data (`data/`)

| File Pattern | Purpose |
|-------------|---------|
| `cg_*.json` | Community Groceries keyword packs, page maps, topic hubs |
| `wihy_*.json` | WIHY keyword data, content keywords, post progress |
| `gsc_*.json` | Google Search Console query exports |
| `health_keywords_*.json` | Health keyword databases (all, curated, Google search) |
| `communitygroceries_*.json` | CG comparison & trending meal page data |
| `cors_*.json` | CORS configs for GCS buckets |

### Ad Assets (`data/ad_images/`)

34 ad creative images used by Meta campaigns. Referenced by LABAT when creating ad sets.

### Blog Assets (`data/blog_heroes/`)

Hero images for blog posts, generated by `backfill_meal_hero_images.py`.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [AGENT_OWNERSHIP.md](AGENT_OWNERSHIP.md) | Which agent owns which responsibility |
| [BRAND_AGENT_STRATEGY.md](BRAND_AGENT_STRATEGY.md) | Multi-brand agent strategy |
| [TRINITY_PIPELINE_REFERENCE.md](TRINITY_PIPELINE_REFERENCE.md) | LABAT → Shania → Alex pipeline |
| [MASTER_AGENT_EXTERNAL_INTEGRATION.md](MASTER_AGENT_EXTERNAL_INTEGRATION.md) | Master Agent integration guide |
| [WHATISHEALTHY_SALES_PLAYBOOK.md](WHATISHEALTHY_SALES_PLAYBOOK.md) | Book funnel sales playbook |
| [LEAD_GEN_STANDARDS_IMPLEMENTATION_PLAN.md](LEAD_GEN_STANDARDS_IMPLEMENTATION_PLAN.md) | Lead gen implementation |
| [ENGAGEMENT_API_GUIDE.md](ENGAGEMENT_API_GUIDE.md) | Maya engagement API reference |
| [LINKEDIN_SETUP_GUIDE.md](LINKEDIN_SETUP_GUIDE.md) | LinkedIn API setup |
| [AUTH_NOTIFICATION_API.md](AUTH_NOTIFICATION_API.md) | Auth notification system |
| [SENDGRID_EMAIL_SYSTEM.md](SENDGRID_EMAIL_SYSTEM.md) | SendGrid email configuration |
| [AUTONOMOUS_CROSS_CHANNEL_PLAN_APR2026.md](AUTONOMOUS_CROSS_CHANNEL_PLAN_APR2026.md) | Cross-channel automation plan |
| [CLIENT_BLOG_FRONTEND_PLAN_MAR2026.md](CLIENT_BLOG_FRONTEND_PLAN_MAR2026.md) | Blog frontend architecture |

---

## Relationship to wihy_ml

This repo was extracted from [wihy_ml](https://github.com/kortney-lee/wihy_ml) (the WIHY ML backend). The split separates concerns:

| Repo | Purpose |
|------|---------|
| **labat** (this repo) | Growth agents, paid ads, SEO, content publishing, lead funnels |
| **wihy_ml** | Health AI core — RAG, meal planning, fitness, nutrition, chat |

### Shared Dependencies

The `src/shared/` directory contains minimal copies of modules originally in wihy_ml:

- `src/shared/auth/auth_client.py` — JWT verification via `auth.wihy.ai`
- `src/shared/config/models.py` — OpenAI model configuration
- `src/shared/middleware/request_logger.py` — Structured HTTP logging

### Cross-Repo Communication

Agents communicate with wihy_ml services via HTTP:

```
LABAT → services.wihy.ai (X-Client-ID / X-Client-Secret headers)
Alex  → services.wihy.ai/api/research (PubMed research)
Maya  → ml.wihy.ai/ask (AI-generated replies)
```
