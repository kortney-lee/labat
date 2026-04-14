# Trinity Pipeline Reference — Alex → LABAT → Shania

> **Do not bypass this pipeline.** All ad creation must go through the trinity orchestration endpoints.

---

## Overview

The "trinity" is three cooperating agents that handle ad creation end-to-end:

| Agent | Role | Service |
|-------|------|---------|
| **Alex** | Orchestrator — wires the full pipeline, calls LABAT + Shania, creates campaign/adset/creative/ad on Meta | `wihy-alex-{brand}` |
| **LABAT** | Intelligence — generates AI ad copy (Gemini), manages Meta Ads API (campaigns, adsets, creatives, ads), lead forms, performance analysis | `wihy-labat-{brand}` |
| **Shania** | Graphics — generates branded images via Imagen/templates, captions, hashtags | `wihy-shania-graphics` |

### Service URLs (as of April 2026)
```
Alex (per-brand):
  https://wihy-alex-vowels-12913076533.us-central1.run.app
  https://wihy-alex-wihy-12913076533.us-central1.run.app
  https://wihy-alex-cg-12913076533.us-central1.run.app
  https://wihy-alex-cn-12913076533.us-central1.run.app
  https://wihy-alex-pwc-12913076533.us-central1.run.app

LABAT (shared + per-brand):
  https://wihy-labat-12913076533.us-central1.run.app          (shared — Meta Ads API)
  https://wihy-labat-vowels-12913076533.us-central1.run.app   (vowels AI copy)
  https://wihy-labat-cg-12913076533.us-central1.run.app       (CG AI copy)

Shania:
  https://wihy-shania-graphics-12913076533.us-central1.run.app
```

### Authentication
All trinity endpoints require the admin token header:
```
X-Admin-Token: wihy-admin-token-2026
```

---

## Two Orchestration Pipelines

### 1. `POST /api/astra/orchestrate-photo-ad` (Traffic / Engagement ads)

**Flow:** Alex → Shania (generate image + caption) → LABAT (create Meta creative + ad)

Best for: brand awareness, traffic, engagement campaigns.

```json
{
  "topic": "5 sneaky ingredients to avoid in kids cereal",
  "brand": "vowels",
  "funnel_stage": "awareness",
  "cta_type": "LEARN_MORE",
  "daily_budget": 500
}
```

Pipeline steps:
1. Shania generates branded photo + caption from `topic`
2. Alex auto-creates campaign (objective based on funnel_stage) if `campaign_id` not provided
3. Alex auto-creates adset with targeting presets if `adset_id` not provided
4. LABAT creates ad creative with image + copy
5. LABAT creates ad (PAUSED by default)

### 2. `POST /api/astra/orchestrate-lead-ad` (Lead Generation ads)

**Flow:** Alex → LABAT (create lead form + campaign + adset + creative + ad)

Best for: lead capture (book downloads, email signups, free offers).

```json
{
  "brand": "vowels",
  "image_url": "https://storage.googleapis.com/wihy-web-assets/images/book-green.jpg",
  "ad_copy": "Your primary text here",
  "headline": "Your Headline Here",
  "cta_type": "DOWNLOAD",
  "lead_form_id": "981115591041114",
  "campaign_id": "120243298860640504",
  "daily_budget": 500,
  "privacy_policy_url": "https://whatishealthy.org/privacy",
  "thank_you_url": "https://whatishealthy.org/thank-you.html"
}
```

Pipeline steps:
1. Create lead form on Facebook Page (if `lead_form_id` not provided)
2. Create OUTCOME_LEADS campaign (if `campaign_id` not provided)
3. Create LEAD_GENERATION adset with `destination_type: ON_AD` (if `adset_id` not provided)
4. Create ad creative (image via `link_data` or video via `video_data`)
5. Create ad — PAUSED

---

## The Correct Process for Creating Ads

### Step 1: Generate AI Copy via LABAT

```bash
POST {LABAT_URL}/api/labat/ai/generate/ad-copy
```

```json
{
  "product_description": "What Is Healthy? - A free digital book...",
  "target_audience": "Health-conscious parents aged 25-55",
  "campaign_goal": "Lead generation - free book download",
  "num_variants": 5,
  "tone": "authoritative but approachable",
  "product": "whatishealthy",
  "funnel_stage": "conversion"
}
```

Returns `variants[]` each with: `headline`, `primary_text`, `description`, `cta`, `hook`, `target_emotion`.

### Step 2: Trigger Orchestration for EACH Variant

For lead ads:
```bash
POST {ALEX_URL}/api/astra/orchestrate-lead-ad
```

**First call** — let the pipeline create campaign + adset:
```json
{
  "brand": "vowels",
  "image_url": "https://storage.googleapis.com/...",
  "ad_copy": "<primary_text from variant 1>",
  "headline": "<headline from variant 1>",
  "cta_type": "DOWNLOAD",
  "lead_form_id": "<existing form ID>",
  "daily_budget": 500
}
```

The response includes `campaign.id` and `adset.id`.

**Subsequent calls** — reuse the campaign + adset from the first call:
```json
{
  "brand": "vowels",
  "image_url": "https://storage.googleapis.com/...",
  "ad_copy": "<primary_text from variant 2>",
  "headline": "<headline from variant 2>",
  "cta_type": "DOWNLOAD",
  "lead_form_id": "<same form ID>",
  "campaign_id": "<from first call>",
  "adset_id": "<from first call>",
  "daily_budget": 500
}
```

### Step 3: Activate

Ads are created PAUSED. Activate via LABAT:

```bash
# Activate campaign
PUT {LABAT_URL}/api/labat/ads/campaigns/{campaign_id}
Body: {"status": "ACTIVE"}

# Activate adset
PUT {LABAT_URL}/api/labat/ads/adsets/{adset_id}
Body: {"status": "ACTIVE"}

# Activate each ad
PUT {LABAT_URL}/api/labat/ads/ads/{ad_id}
Body: {"status": "ACTIVE"}
```

> **Note:** The endpoints are `PUT`, not `POST /status`. There are no `/status` sub-routes.

---

## Critical Rules & Gotchas

### 1. Lead ads require `destination_type: ON_AD`

Meta requires all LEAD_GENERATION adsets to have `destination_type: ON_AD`. The orchestrate-lead-ad pipeline sets this automatically when it creates the adset.

**If you pass a manually-created `adset_id` that doesn't have `ON_AD`, the ad creation will fail:**
```
"Creative with lead form can only be used for Lead Generation objective
and ON_AD destination" | code=100 | subcode=1892040
```

**Fix:** Don't pass `adset_id` — let the pipeline create one with the correct settings. Or ensure your manually-created adset has `destination_type: ON_AD` and `optimization_goal: LEAD_GENERATION`.

### 2. Image field is `picture`, NOT `image_url`

For `link_data` creatives (image ads), Meta requires the field `picture`:
```python
link_data_spec["picture"] = body.image_url   # ✅ correct
link_data_spec["image_url"] = body.image_url  # ❌ WRONG — Meta ignores this
```

For `video_data` creatives, the thumbnail IS `image_url` (confusingly).

### 3. Instagram field is `instagram_user_id`, NOT `instagram_actor_id`

```python
creative_spec["instagram_user_id"] = ig_actor_id   # ✅ correct
creative_spec["instagram_actor_id"] = ig_actor_id   # ❌ WRONG
```

### 4. Brand domains are centralized in `src/labat/brands.py`

Never hardcode domain mappings. Import from the single source of truth:
```python
from src.labat.brands import BRAND_DOMAINS, BRAND_PAGE_IDS, normalize_brand
```

| Brand Key | Domain | Page ID |
|-----------|--------|---------|
| wihy | wihy.ai | 937763702752161 |
| vowels | vowels.org | 100193518975897 |
| communitygroceries | communitygroceries.com | 2051601018287997 |
| childrennutrition | whatishealthy.org | 269598952893508 |
| parentingwithchrist | parentingwithchrist.com | 329626030226536 |

### 5. Deprecated Meta fields
- `video_feeds` and `reels` — removed from `facebook_positions`
- `targeting_optimization` — removed from adset targeting
- `RIGHT_HAND_COLUMN` — no longer valid placement for lead ads

### 6. Can't set budget at both campaign and adset level
Pick one. The pipeline uses campaign-level `daily_budget`.

### 7. `cloudbuild.*.yaml` — keep LABAT_URL current
Each per-brand Alex cloudbuild references the LABAT URL. If the Cloud Run URL format changes, update all cloudbuilds:
```yaml
# Current format (April 2026):
- name: LABAT_URL
  value: https://wihy-labat-vowels-12913076533.us-central1.run.app
# OLD format (deprecated):
# value: https://wihy-labat-vowels-n4l2vldq3q-uc.a.run.app
```

---

## Existing Campaigns & IDs

### Vowels (Book)
| Resource | ID |
|----------|----|
| Campaign | `120243298860640504` — "What Is Healthy - Book Lead Gen - April 2026" |
| AdSet | `120243299719930504` — "Vowels - Lead Gen Adset - 20260406" (ON_AD) |
| Lead Form | `981115591041114` — "What Is Healthy - Free Book Download April 2026" |
| Book Image | `https://storage.googleapis.com/wihy-web-assets/images/book-green.jpg` |
| Landing | `https://whatishealthy.org/` |
| Privacy | `https://whatishealthy.org/privacy` |
| Thank You | `https://whatishealthy.org/thank-you.html` |

### WIHY
| Resource | ID |
|----------|----|
| Campaign | `120243278136210504` |
| AdSet | `120243278136840504` |
| Lead Form | `1931899670777549` |

### Community Groceries
| Resource | ID |
|----------|----|
| Campaign | `120243278517510504` |
| AdSet | `120243278518860504` |
| Lead Form | `2025843878283288` |

---

## Autonomous Ad Creation (AdPostingService)

The `AdPostingService` in `src/alex/services/ad_posting_service.py` runs a 24-hour cycle:

1. **Learn** — Fetches performance data from LABAT, identifies winners/losers by CTR
2. **Decide** — Picks brand + funnel stage based on performance (or default rotation)
3. **Create** — Calls `orchestrate-lead-ad` (if `LEAD_ONLY_MODE=true`) or `orchestrate-photo-ad`
4. **Score** — Updates angle performance for future cycles

Each brand has directional ad angles in `BRAND_AD_ANGLES` — these are NOT final copy, they're directions that get passed to the pipeline for AI expansion.

---

## Key Source Files

| File | Purpose |
|------|---------|
| `src/alex/routers/alex_routes.py` | Orchestration endpoints (orchestrate-photo-ad L300, orchestrate-lead-ad L902) |
| `src/alex/services/ad_posting_service.py` | Autonomous 24h ad creation loop |
| `src/labat/routers/ads_routes.py` | Meta Ads CRUD (campaigns, adsets, ads, creatives) |
| `src/labat/routers/ai_routes.py` | AI copy generation (`/generate/ad-copy`) |
| `src/labat/services/content_service.py` | Gemini-powered content generation |
| `src/labat/services/strategy_rules.py` | Brand positioning rules injected into AI prompts |
| `src/labat/brands.py` | Centralized brand → page/domain/IG mapping |
| `cloudbuild.alex-vowels.yaml` | Vowels Alex deployment (references LABAT_URL) |

---

## Quick Reference — PowerShell Commands

### Generate AI Copy
```powershell
$labat = "https://wihy-labat-12913076533.us-central1.run.app"
$h = @{"X-Admin-Token"="wihy-admin-token-2026";"Content-Type"="application/json"}
$body = '{"product_description":"...","target_audience":"...","campaign_goal":"...","num_variants":5,"product":"whatishealthy","funnel_stage":"conversion"}'
$r = Invoke-WebRequest -Uri "$labat/api/labat/ai/generate/ad-copy" -Headers $h -Method POST -Body $body -UseBasicParsing -TimeoutSec 90
$r.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

### Trigger Lead Ad Pipeline
```powershell
$alex = "https://wihy-alex-vowels-12913076533.us-central1.run.app"
$h = @{"X-Admin-Token"="wihy-admin-token-2026";"Content-Type"="application/json"}
$body = '{"brand":"vowels","image_url":"...","ad_copy":"...","headline":"...","cta_type":"DOWNLOAD","lead_form_id":"981115591041114","campaign_id":"120243298860640504","adset_id":"120243299719930504"}'
$r = Invoke-WebRequest -Uri "$alex/api/astra/orchestrate-lead-ad" -Headers $h -Method POST -Body $body -UseBasicParsing -TimeoutSec 120
$r.Content | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

### Activate Ads
```powershell
$labat = "https://wihy-labat-12913076533.us-central1.run.app"
$h = @{"X-Admin-Token"="wihy-admin-token-2026";"Content-Type"="application/json"}

# Campaign
Invoke-WebRequest -Uri "$labat/api/labat/ads/campaigns/{id}" -Headers $h -Method PUT -Body '{"status":"ACTIVE"}' -UseBasicParsing

# AdSet
Invoke-WebRequest -Uri "$labat/api/labat/ads/adsets/{id}" -Headers $h -Method PUT -Body '{"status":"ACTIVE"}' -UseBasicParsing

# Ad
Invoke-WebRequest -Uri "$labat/api/labat/ads/ads/{id}" -Headers $h -Method PUT -Body '{"status":"ACTIVE"}' -UseBasicParsing
```

### List Ads Under an AdSet
```powershell
$r = Invoke-WebRequest -Uri "$labat/api/labat/ads/ads?adset_id={id}" -Headers $h -Method GET -UseBasicParsing
$r.Content | ConvertFrom-Json | ConvertTo-Json -Depth 3
```
