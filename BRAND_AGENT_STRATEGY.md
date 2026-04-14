# WIHY Brand Agent Strategy — Find, Capture, Convert

> **Last Updated:** April 5, 2026
> **Goal:** Every brand runs its own set of autonomous agents that find leads, save money, and convert on autopilot.

---

## The Funnel: Find → Capture → Convert

| Stage | What Happens | Who Does It |
|-------|-------------|-------------|
| **Find** | Discover audiences on social, SEO, and paid — drive them to a form or page | Alex, Shania, LABAT |
| **Capture** | Collect email + first name + last name via Facebook Lead Forms or landing pages | LABAT (lead forms), Book (landing page) |
| **Convert** | Nurture via email drip, retarget with ads, drive to product signup | LABAT (retargeting), Lead Sync (email nurture) |

---

## Brand Lead Capture Strategy

### WIHY (`wihy.ai`)

| Channel | Strategy | Assets |
|---------|----------|--------|
| **Facebook + Instagram** | **Lead Form Ads** — video lead ad with form collecting **email, first name, last name** | `WIHYVIDEO_web.mp4`, `WIHYVIDEO_Mobile.mp4` (in `shania/assets/Wihy/`) |
| **Threads** | Organic posts (Shania) — drives to wihy.ai | — |
| **LinkedIn** | Organic posts (WIHY-only platform) — professional health positioning | — |
| **SEO** | Alex keyword discovery + content queue → organic traffic to wihy.ai | — |
| **Paid Ads** | LABAT creates OUTCOME_LEADS campaigns with lead form attached | Video creative + lead form |

**Lead Flow:**
```
Facebook/Instagram Ad (video mp4) → Lead Form (email, first, last) → Firestore (launch_leads) → Welcome Email → wihy.ai signup
```

### Community Groceries (`communitygroceries.com`)

| Channel | Strategy | Assets |
|---------|----------|--------|
| **Facebook + Instagram** | **Lead Form Ads** — video lead ad with form collecting **email, first name, last name** | `CGHeader_fb.mp4`, `CGHeader_mobile.mp4` (in `shania/assets/CommunityGroceries/`) |
| **Threads** | Organic posts (Shania) — drives to communitygroceries.com | — |
| **SEO** | Alex keyword discovery — affordable meals, budget grocery, family nutrition | — |
| **Paid Ads** | LABAT creates OUTCOME_LEADS campaigns with lead form attached | Video creative + lead form |

**Lead Flow:**
```
Facebook/Instagram Ad (video mp4) → Lead Form (email, first, last) → Firestore (launch_leads) → Welcome Email → communitygroceries.com signup
```

### Vowels (`vowels.org`)

| Channel | Strategy | Assets |
|---------|----------|--------|
| **Facebook + Instagram + Threads** | **Organic posts only** — Shania auto-posts data storytelling, book promotion content | `Vowels_logo.png` |
| **SEO** | Alex keyword discovery — data analytics, health research | — |
| **Paid Ads** | LABAT runs awareness/consideration ads (NOT lead forms) | Image creatives |

**No lead form ads.** Vowels social presence is about brand awareness and book promotion. Leads come through the Children's Nutrition / whatishealthy.org funnel instead.

### Parenting with Christ (`parentingwithchrist.com`)

| Channel | Strategy | Assets |
|---------|----------|--------|
| **Facebook + Instagram + Threads** | **Organic posts only** — Shania auto-posts faith-based parenting content (fasting, discipline, self-control) | Logo (TODO — needs creation) |
| **SEO** | Alex keyword discovery — Christian parenting, Biblical discipline, faith family | — |
| **Paid Ads** | LABAT runs awareness/consideration ads (NOT lead forms) | Image creatives |

**No lead form ads.** PWC social is about building community and trust through consistent faith-based content.

### Children's Nutrition Education (`whatishealthy.org`)

| Channel | Strategy | Assets |
|---------|----------|--------|
| **Facebook + Instagram + Threads** | **Organic posts only** — Shania auto-posts picky eater tips, kids nutrition, book promotion | Book covers (`BookGreen.jpg`, `BookOrange.jpg`, etc.), `5-STAR Hi Res 2025.png` |
| **Landing Page** | whatishealthy.org — free eBook download captures email | `WhatisHealthy_eBook.pdf`, `static_whatishealthy/` |
| **SEO** | Alex keyword discovery — children nutrition, picky eaters, kids healthy eating | — |
| **Paid Ads** | LABAT runs awareness ads promoting the free book download → whatishealthy.org | Image creatives with book covers |

**Lead capture is via the Book landing page (whatishealthy.org)** — not Facebook lead forms. User downloads free eBook and enters email. Nurture emails sent from `info@vowels.org`.

---

## All Agents — Complete Inventory

### 1. Alex (SEO Discovery Agent)
- **Cloud Run:** `wihy-alex-{brand}` (5 per-brand instances)
- **APP_MODULE:** `src.apps.alex_app:app`
- **Routes:** `/api/alex/*`
- **Brand Scope:** `ALEX_BRAND_SCOPE` env var
- **Role:** **FIND** — Autonomous SEO agent that discovers keywords, generates content briefs, scans for ranking opportunities, and ingests analytics
- **Background Loops (6):**
  - Keyword discovery (every 6h)
  - Content queue generation (every 4h)
  - Page refresh audit (every 24h)
  - Opportunity scan (every 24h)
  - Analytics ingestion (every 1h)
  - Daily performance report (every 24h)
- **Ad Integration:** When `AD_POSTING_ENABLED=true`, Alex also creates paid ads via LABAT (learning loop: pull insights → identify winners → create new ad)
- **Per-Brand Instances:**

| Instance | Cloud Run | LABAT URL |
|----------|-----------|-----------|
| wihy | `wihy-alex-wihy` | `https://wihy-labat-wihy-n4l2vldq3q-uc.a.run.app` |
| cg | `wihy-alex-cg` | `https://wihy-labat-cg-n4l2vldq3q-uc.a.run.app` |
| vowels | `wihy-alex-vowels` | `https://wihy-labat-vowels-n4l2vldq3q-uc.a.run.app` |
| cn | `wihy-alex-cn` | `https://wihy-labat-cn-n4l2vldq3q-uc.a.run.app` |
| pwc | `wihy-alex-pwc` | `https://wihy-labat-pwc-n4l2vldq3q-uc.a.run.app` |

### 2. Shania (Publishing Agent)
- **Cloud Run:** `wihy-shania-{brand}` (5 per-brand instances)
- **APP_MODULE:** `src.apps.shania_app:app`
- **Routes:** `/api/shania/*`, `/api/labat/posts/*`, `/api/labat/page/*`
- **Brand Scope:** `SHANIA_BRAND_SCOPE` env var
- **Role:** **FIND** — Publishes branded social content to Facebook, Instagram, Threads (and LinkedIn for WIHY). Drives organic reach and brand awareness.
- **Safety:** `_enforce_brand()` in `post_service.py` — rejects cross-brand page_id overrides. Each instance can ONLY post to its own brand's page.
- **Platforms by Brand:**

| Brand | Facebook | Instagram | Threads | LinkedIn |
|-------|----------|-----------|---------|----------|
| wihy | ✅ | ✅ | ✅ | ✅ |
| communitygroceries | ✅ | ✅ | ✅ | — |
| vowels | ✅ | ✅ | ✅ | — |
| childrennutrition | ✅ | ✅ | ✅ | — |
| parentingwithchrist | ✅ | ✅ | ✅ | — |

### 3. LABAT (Paid Ads Agent)
- **Cloud Run:** `wihy-labat-{brand}` (5 per-brand instances)
- **APP_MODULE:** `src.apps.labat_app:app`
- **Routes:** `/api/labat/*`
- **Brand Scope:** `LABAT_BRAND_SCOPE` env var
- **Role:** **FIND + CAPTURE** — Manages Meta ad campaigns, budgets, creatives, A/B testing, and lead form ads. Pulls insights, auto-pauses underperformers, auto-scales winners.
- **Hourly Automation (Cloud Scheduler cron):**
  1. Health check + anomaly alerts
  2. Auto-pause underperformers ($10 spend / 0 conversions or <0.5% CTR after 1000 impressions)
  3. Auto-scale winners (>1.5x ROAS with 2+ conversions, up to +20% / $500/day cap)
  4. A/B creative rotation (after 500 impressions, 20% win margin)
  5. Performance report
- **Lead Form Creation:** `POST /api/labat/leads/forms` — creates Facebook Lead Forms (email + first_name + last_name)
- **Lead Sync:** `POST /api/labat/leads/sync` — pulls leads from Meta → Firestore `launch_leads` → triggers welcome email
- **Scheduler Crons (staggered):**

| Brand | Cron | Time |
|-------|------|------|
| wihy | `labat-wihy-hourly` | `:00` past each hour |
| cg | `labat-cg-hourly` | `:02` past each hour |
| vowels | `labat-vowels-hourly` | `:04` past each hour |
| cn | `labat-cn-hourly` | `:06` past each hour |
| pwc | `labat-pwc-hourly` | `:08` past each hour |

### 4. Maya (Engagement Agent)
- **Cloud Run:** `wihy-maya`
- **APP_MODULE:** `src.apps.maya_app:app`
- **Routes:** `/api/engagement/*`, `/api/labat/comments/*`, `/api/labat/messenger/*`
- **Role:** **CAPTURE + CONVERT** — Monitors and replies to comments, DMs, Messenger conversations. Keeps leads warm through conversation.
- **Background Tasks:** Thread monitor (engagement reply watcher), social posting service (auto-posts every ~4h across all brands)
- **Auto-posting Topics:** Evergreen content for all 5 brands — health tips (WIHY), budget meals (CG), picky eater advice (CN), faith-based parenting (PWC), data storytelling (Vowels)

### 5. Shania Graphics (Creative Agent)
- **Cloud Run:** `wihy-shania-graphics`
- **Stack:** TypeScript (not Python)
- **Routes:** `/api/graphics/*`
- **Role:** **FIND** — Generates AI images (Imagen 4.0), captions (Gemini), and video thumbnails for social posting. Called by Shania and Maya for content creation.
- **Pipeline:** Brand prompt → Gemini caption → Imagen image → GCS upload → publish to social

### 6. Master Agent / Kortney (Orchestrator)
- **Cloud Run:** `wihy-master-agent`
- **APP_MODULE:** `src.apps.master_agent_app:app`
- **Routes:** `/api/kortney/*`, `/api/otaku/master/*`
- **Role:** System-wide orchestrator — monitors health of all agents, anomaly detection, alerting, blog/editorial content creation
- **Background Tasks:** Hourly status report → auth service, 5-min critical health checks

### 7. Book (Lead Capture Landing Page)
- **Cloud Run:** `wihy-ml-book`
- **APP_MODULE:** `src.apps.book_app:app`
- **Routes:** `/api/book/*`, `/api/launch/*`
- **Role:** **CAPTURE** — Serves whatishealthy.org landing page, captures email for free eBook download, delivers PDF, Stripe checkout for physical copy
- **Email:** Nurture drip from `info@vowels.org` ("Vowels" sender)
- **Static Assets:** `static_whatishealthy/` — landing page HTML, book covers, eBook PDF, thank you page, unsubscribe page

### 8. Amanda (Nutrition AI)
- **Cloud Run:** `wihy-amanda`
- **APP_MODULE:** `src.apps.amanda_app:app`
- **Routes:** `/api/meals/*`, `/api/school-meals/*`
- **Role:** **CONVERT** — RAG-grounded meal plan generation, shopping lists, nutritional analysis. The product that converts captured leads into active users.

### 9. Fitness (Fitness AI)
- **Cloud Run:** `wihy-ml-fitness`
- **APP_MODULE:** `src.apps.fitness_app:app`
- **Routes:** `/api/fitness/*`
- **Role:** **CONVERT** — RAG-grounded workout program generation. Part of the product that retains users.

### 10. RAG (Knowledge Base)
- **Cloud Run:** `wihy-ml-rag`
- **APP_MODULE:** `src.apps.rag_app:app`
- **Routes:** `/api/rag/*`
- **Role:** **CONVERT** — WIHY vector store queries. Powers health Q&A across the `/ask` endpoint and all AI services.
- **Vector Store:** `vs_69b0bd9387dc8191b9bc4d8d8f9c4cb1` (48M+ research articles)

### 11. Research (Scientific Research)
- **Cloud Run:** `wihy-ml-research`
- **APP_MODULE:** `src.apps.research_app:app`
- **Routes:** `/api/research/*`
- **Role:** **CONVERT** — Long-running PubMed + Claude-powered scientific research queries. Deep health question answering.

### 12. Internal (Admin Tools)
- **Cloud Run:** `wihy-internal`
- **APP_MODULE:** `src.apps.internal_app:app`
- **Routes:** `/api/training/*`, `/self-learning/*`, `/data/*`
- **Role:** Internal admin — ML training jobs, self-learning pipelines, conversation dashboard. Not public-facing.

### 13. Moltbook Bot
- **Cloud Run:** `wihy-moltbook`
- **APP_MODULE:** `src.apps.moltbook_bot:app`
- **Routes:** `/health`, `/run`
- **Role:** **FIND** — Autonomous @wihyhealthbot on moltbook.com. Replies to health comments, upvotes content, publishes research posts every ~160s heartbeat cycle.

---

## Lead Form Strategy — WIHY & Community Groceries

**Only WIHY and Community Groceries use Facebook Lead Form ads.** The other brands (Vowels, PWC, Children's Nutrition) do organic social posting only.

### Why Lead Forms?
- **Save money** — no landing page needed, form opens inside Facebook/Instagram
- **Higher conversion** — user never leaves the app, pre-filled fields
- **Automatic sync** — LABAT pulls leads via Meta API → Firestore → email nurture
- **Lower CPA** — Facebook optimizes for OUTCOME_LEADS objective

### Lead Form Fields
Every lead form captures exactly 3 fields:
1. **Email** (type: `EMAIL`)
2. **First Name** (type: `FIRST_NAME`)
3. **Last Name** (type: `LAST_NAME`)

### Video Assets for Lead Ads

Each brand has **two video cuts** — one per placement type:

| Brand | Video File | Platforms | Format |
|-------|-----------|-----------|--------|
| **WIHY** | `WIHYVIDEO_web.mp4` | YouTube, Facebook feed | Landscape |
| **WIHY** | `WIHYVIDEO_Mobile.mp4` | Reels, Stories, TikTok | Vertical 9:16 |
| **Community Groceries** | `CGHeader_fb.mp4` | YouTube, Facebook feed | Landscape |
| **Community Groceries** | `CGHeader_mobile.mp4` | Reels, Stories, TikTok | Vertical 9:16 |

### Lead Ad Pipeline
Alex orchestrates the full lead ad pipeline via `POST /api/alex/orchestrate-lead-ad`:
1. Create lead form on Facebook Page (email + first_name + last_name)
2. Create OUTCOME_LEADS campaign
3. Create LEAD_GENERATION adset with lead form attached
4. Create ad creative (video)
5. Create ad — PAUSED, ready to activate

### Lead Sync Flow
```
User fills Lead Form on Facebook/Instagram
        ↓
LABAT cron pulls new leads (hourly)
  POST /api/labat/leads/sync
        ↓
Check for duplicates in Firestore (launch_leads collection)
        ↓
Store new lead in Firestore
  { email, first_name, last_name, brand, source, created_at }
        ↓
Trigger welcome email
  → WIHY leads: welcome to wihy.ai
  → CG leads: welcome to communitygroceries.com
        ↓
LABAT retargets with conversion ads
```

---

## Organic Social Strategy — Vowels, PWC, Children's Nutrition

These three brands **do NOT run lead form ads.** Their social strategy is pure organic posting via Shania + Maya.

### Vowels (`vowels.org`)
- **Content Themes:** Data storytelling, food industry exposés, "What Is Healthy?" book promotion, health research insights
- **Auto-post topics:** Food label tricks, Big Food lies, award-winning nutrition guide, grocery store layout psychology, $14B food advertising industry, free eBook download
- **Goal:** Drive awareness → whatishealthy.org for book downloads (Children's Nutrition captures the lead)

### Parenting with Christ
- **Content Themes:** Jesus-modeled discipline, Biblical fasting, self-control as fruit of the Spirit, counter-cultural parenting, morning devotions, saying "no" in an anything-goes culture
- **Auto-post topics:** 40-day fasting lessons, training up children, impulse control from Scripture, delayed gratification, quality friendships over social media
- **Goal:** Build community and trust through consistent faith-based content

### Children's Nutrition Education (`whatishealthy.org`)
- **Content Themes:** Picky eaters, kids nutrition tips, hidden veggie recipes, school lunch ideas, healthy snacks, teaching kids about nutrition
- **Auto-post topics:** 5 strategies for picky eaters, food bridge method, reducing sugar, smoothie hacks, fun nutrition education
- **Goal:** Drive parents to whatishealthy.org → free eBook download → email capture → nurture

---

## Facebook Page IDs

| Brand | Page Name | Page ID | Instagram ID |
|-------|-----------|---------|--------------|
| WIHY | WiHy.ai | `937763702752161` | `17841478427607771` |
| Community Groceries | Community Groceries | `2051601018287997` | `17841445312259126` |
| Vowels | Vowels.Org | `100193518975897` | `17841448164085103` |
| Children's Nutrition | Childrens.Nutrition.Education | `269598952893508` | `17841470986083057` |
| Parenting with Christ | Parenting with Christ | `329626030226536` | `17841466415337829` |

**Shared Ad Account:** `act_218581359635343`
**Campaign Naming:** `{Brand} - {Funnel} - {Topic} - {Date}` (brand always first token for filtering)

---

## Cloud Run Service Count

| Agent | Instances | Pattern |
|-------|-----------|---------|
| Alex (SEO) | 5 | `wihy-alex-{wihy,cg,vowels,cn,pwc}` |
| Shania (Publishing) | 5 | `wihy-shania-{wihy,cg,vowels,cn,pwc}` |
| LABAT (Paid Ads) | 5 | `wihy-labat-{wihy,cg,vowels,cn,pwc}` |
| Maya (Engagement) | 1 | `wihy-maya` |
| Shania Graphics | 1 | `wihy-shania-graphics` |
| Master Agent | 1 | `wihy-master-agent` |
| Book (Landing Page) | 1 | `wihy-ml-book` |
| Amanda (Meals AI) | 1 | `wihy-amanda` |
| Fitness AI | 1 | `wihy-ml-fitness` |
| RAG | 1 | `wihy-ml-rag` |
| Research | 1 | `wihy-ml-research` |
| Internal | 1 | `wihy-internal` |
| Moltbook Bot | 1 | `wihy-moltbook` |
| Main (wihy-ml) | 1 | `wihy-ml` |
| **Total** | **26** | |

---

## Deployment Status (April 5, 2026)

| Service | Deployed | Cloudbuild |
|---------|----------|------------|
| `wihy-labat-wihy` | ✅ | `cloudbuild.labat-wihy.yaml` |
| `wihy-labat-cg` | ✅ | `cloudbuild.labat-cg.yaml` |
| `wihy-labat-vowels` | ✅ | `cloudbuild.labat-vowels.yaml` |
| `wihy-labat-cn` | ✅ | `cloudbuild.labat-cn.yaml` |
| `wihy-labat-pwc` | ✅ | `cloudbuild.labat-pwc.yaml` |
| `wihy-alex-wihy` | ✅ | `cloudbuild.alex-wihy.yaml` |
| `wihy-alex-cg` | ❌ | `cloudbuild.alex-cg.yaml` |
| `wihy-alex-vowels` | ❌ | `cloudbuild.alex-vowels.yaml` |
| `wihy-alex-cn` | ❌ | `cloudbuild.alex-cn.yaml` |
| `wihy-alex-pwc` | ❌ | `cloudbuild.alex-pwc.yaml` |
| `wihy-shania-wihy` | ❌ | `cloudbuild.shania-wihy.yaml` |
| `wihy-shania-cg` | ❌ | `cloudbuild.shania-cg.yaml` |
| `wihy-shania-vowels` | ❌ | `cloudbuild.shania-vowels.yaml` |
| `wihy-shania-cn` | ❌ | `cloudbuild.shania-cn.yaml` |
| `wihy-shania-pwc` | ❌ | `cloudbuild.shania-pwc.yaml` |

### Deploy Remaining Services
```powershell
# Alex (4 remaining)
$alexBrands = @("cg", "vowels", "cn", "pwc")
foreach ($b in $alexBrands) {
    gcloud builds submit --project=wihy-ai --config="cloudbuild.alex-$b.yaml" .
}

# Shania (all 5)
$shaniaBrands = @("wihy", "cg", "vowels", "cn", "pwc")
foreach ($b in $shaniaBrands) {
    gcloud builds submit --project=wihy-ai --config="cloudbuild.shania-$b.yaml" .
}
```

---

## Summary

| Brand | Find (SEO) | Find (Social) | Find (Ads) | Capture (Lead Form) | Capture (Landing) | Convert (Email) | Convert (Product) |
|-------|-----------|--------------|-----------|--------------------|--------------------|-----------------|-------------------|
| **WIHY** | Alex | Shania + Maya | LABAT | ✅ Video + Form | wihy.ai | ✅ Welcome email | Amanda, Fitness, RAG |
| **Community Groceries** | Alex | Shania + Maya | LABAT | ✅ Video + Form | communitygroceries.com | ✅ Welcome email | Amanda, Fitness, RAG |
| **Vowels** | Alex | Shania + Maya | LABAT (awareness) | ❌ Organic only | vowels.org | — | — |
| **Children's Nutrition** | Alex | Shania + Maya | LABAT (awareness) | ❌ Organic only | whatishealthy.org (Book) | ✅ eBook nurture | — |
| **Parenting with Christ** | Alex | Shania + Maya | LABAT (awareness) | ❌ Organic only | — | — | — |
