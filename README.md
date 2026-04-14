# LABAT — WIHY Growth Agents

Five AI-powered agents that automate paid ads, SEO discovery, social posting, and community engagement for the WIHY brand family.

## Agents

| Agent | Service | Role | Entry Point |
|-------|---------|------|-------------|
| **LABAT** | `wihy-labat` | Lead Automation, Business Ads & Targeting (Meta/Facebook) | `src.apps.labat_app:app` |
| **Alex** | `wihy-alex` | SEO discovery, keyword research, autonomous content | `src.apps.alex_app:app` |
| **Astra** | `wihy-astra` | Discovery agent (Alex alias) | `src.apps.astra_app:app` |
| **Shania** | `wihy-shania` | Facebook/LinkedIn publishing & posting | `src.apps.shania_app:app` |
| **Maya** | `wihy-maya` | Community engagement, replies, comments, threads | `src.apps.maya_app:app` |

## Brands

All agents serve 5 brands via `*_BRAND_SCOPE` env var:

| Brand | Scope Value | Domain |
|-------|-------------|--------|
| WIHY | `wihy` | wihy.ai |
| Community Groceries | `communitygroceries` | communitygroceries.com |
| Vowels | `vowels` | vowels.org |
| Children's Nutrition | `childrennutrition` | whatishealthy.org |
| Parenting with Christ | `parentingwithchrist` | parentingwithchrist.com |

## Repo Structure

```
labat/
├── src/
│   ├── apps/                    # FastAPI app entry points
│   │   ├── labat_app.py         # LABAT (paid ads)
│   │   ├── alex_app.py          # Alex (SEO discovery)
│   │   ├── astra_app.py         # Astra (Alex alias)
│   │   ├── shania_app.py        # Shania (posting)
│   │   └── maya_app.py          # Maya (engagement)
│   ├── labat/                   # LABAT core (ads, automation, leads, content, strategy)
│   │   ├── services/            # 27 service modules
│   │   ├── routers/             # 21 API routers
│   │   ├── brands.py            # Brand-to-page mapping
│   │   ├── config.py            # Meta/LinkedIn/Gemini config
│   │   ├── meta_client.py       # Meta Graph API client
│   │   └── schemas.py           # Pydantic models
│   ├── alex/                    # Alex/Astra (SEO, keyword discovery, ad posting)
│   │   ├── services/            # alex_service.py, ad_posting_service.py
│   │   ├── routers/             # alex_routes.py
│   │   └── config.py
│   ├── maya/                    # Maya (engagement, threads, social posting)
│   │   ├── services/            # engagement_poster_service, social_posting_service
│   │   └── routers/             # engagement_routes.py
│   └── shared/                  # Shared deps copied from wihy_ml
│       ├── auth/                # JWT verification (auth_client.py)
│       ├── config/              # Model config (models.py)
│       └── middleware/          # Request logger
├── shania/                      # Shania Graphics (TypeScript/Node.js)
├── cloudbuild.*.yaml            # 20 Cloud Build configs
├── Dockerfile                   # Single image, APP_MODULE selects agent
├── requirements.txt
└── .env.example
```

## Deployment

Single Docker image, multiple Cloud Run services. `APP_MODULE` env var selects which agent boots.

```bash
# Deploy LABAT (all brands)
gcloud builds submit --config cloudbuild.labat.yaml

# Deploy brand-scoped LABAT
gcloud builds submit --config cloudbuild.labat-wihy.yaml
gcloud builds submit --config cloudbuild.labat-cg.yaml

# Deploy Alex (SEO discovery)
gcloud builds submit --config cloudbuild.alex.yaml

# Deploy Shania (posting)
gcloud builds submit --config cloudbuild.shania.yaml

# Deploy Maya (engagement)
gcloud builds submit --config cloudbuild.maya.yaml

# Deploy Shania Graphics (TypeScript)
gcloud builds submit --config cloudbuild.shania-graphics.yaml
```

## Local Development

```bash
# Setup
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # fill in secrets

# Run LABAT locally
uvicorn src.apps.labat_app:app --host 0.0.0.0 --port 8080

# Run Alex
uvicorn src.apps.alex_app:app --host 0.0.0.0 --port 8081

# Run Maya
uvicorn src.apps.maya_app:app --host 0.0.0.0 --port 8082
```

## Firebase Routing

Traffic is routed from Firebase Hosting to Cloud Run services:

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
```

## Key Architecture

- **Strategy Rules** (`src/labat/services/strategy_rules.py`): Single source of truth for brand positioning, targeting presets, funnel rules, and lead form questions. Used by LABAT and Alex.
- **Automation** (`src/labat/services/automation_service.py`): Hourly cron cycle — auto-pause underperformers, auto-scale winners, A/B rotation.
- **Lead Sync** (`src/labat/services/lead_sync_service.py`): Pull Meta lead form submissions → Firestore → welcome email.
- **Brand Isolation**: Same ad account (`act_218581359635343`), isolated by `LABAT_BRAND_SCOPE` env var per deployment.

## Relationship to wihy_ml

This repo was extracted from [wihy_ml](https://github.com/kortney-lee/wihy_ml). The `src/shared/` directory contains minimal copies of modules that were originally in wihy_ml's core:

- `src/shared/auth/auth_client.py` — JWT verification via auth.wihy.ai
- `src/shared/config/models.py` — OpenAI model configuration
- `src/shared/middleware/request_logger.py` — Verbose HTTP logging

The wihy_ml repo retains copies of `conversions_service.py` and `page_store.py` for its own consumers (book_routes, launch_routes, blog_publisher).
