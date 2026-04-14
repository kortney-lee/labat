# Client Frontend Blog SEO Plan (April 2026)
## Scope: wihy.ai + communitygroceries.com

## Backend Domain: labat.wihy.ai

All blog content, social distribution, and ad APIs are served through **labat.wihy.ai** — a single Firebase Hosting site that routes to the growth agents:

| Agent | Route Prefix | Cloud Run Service | Purpose |
|-------|-------------|-------------------|--------|
| **Kortney** | `labat.wihy.ai/api/kortney/*` | wihy-master-agent | Blog writing (RAG research → SEO keywords → GPT-4o draft → voice refinement → DALL-E hero → GCS publish) |
| **Kortney** | `labat.wihy.ai/api/content/*` | wihy-master-agent | Keyword store for SEO targeting |
| **Alex** | `labat.wihy.ai/api/alex/*` | wihy-alex | SEO keyword discovery, content orchestration |
| **Shania** | `labat.wihy.ai/api/engagement/*` | wihy-shania | Social posting (Twitter, Instagram, TikTok, Facebook) |
| **Shania Graphics** | `labat.wihy.ai/api/graphics/*` | wihy-shania-graphics | Image generation (Imagen 4.0), content approval queue |
| **Research Bot** | `labat.wihy.ai/research-bot/*` | wihy-shania-graphics | Public research article pages (Moltbook cross-posts) |
| **Labat** | `labat.wihy.ai/api/labat/*` | wihy-labat | Ads, leads, spend, conversions |

All API endpoints require `X-Admin-Token` header unless noted otherwise.
Research bot pages (`/research-bot`, `/research-bot/:slug`) are **public** — no auth required.

Fallback URL (before custom domain DNS): `https://labat-wihy-ai.web.app`

Master Agent direct URL: `https://wihy-master-agent-n4l2vldq3q-uc.a.run.app`

## Blog Content Source (GCS — Static JSON)

**Blog articles are published as static JSON files to public GCS buckets.** No API auth needed — the client fetches directly from GCS.

| Brand | Index URL | Article URL |
|-------|-----------|-------------|
| **WIHY** | `https://storage.googleapis.com/wihy-web-assets/blog/posts/index.json` | `https://storage.googleapis.com/wihy-web-assets/blog/posts/{slug}.json` |
| **Community Groceries** | `https://storage.googleapis.com/cg-web-assets/blog/posts/index.json` | `https://storage.googleapis.com/cg-web-assets/blog/posts/{slug}.json` |

**Hero images** are at:
- WIHY: `https://storage.googleapis.com/wihy-web-assets/images/blog/{slug}-hero.jpg`
- CG: `https://storage.googleapis.com/cg-web-assets/images/blog/{slug}-hero.jpg`

### Index response shape
```json
{
  "posts": [
    {
      "slug": "hidden-sugar-in-cereal",
      "title": "How Much Hidden Sugar is Really in Your 'Healthy' Breakfast Cereal?...",
      "meta_description": "Discover the surprising amount...",
      "author": "Kortney",
      "created_at": "2026-04-02T18:33:57.600158",
      "hero_image": "https://storage.googleapis.com/wihy-web-assets/images/blog/hidden-sugar-in-cereal-hero.jpg",
      "word_count": 707,
      "brand": "wihy"
    }
  ],
  "count": 1
}
```

### Article response shape
```json
{
  "slug": "hidden-sugar-in-cereal",
  "title": "How Much Hidden Sugar is Really in Your 'Healthy' Breakfast Cereal?...",
  "body": "# How Much Hidden Sugar...\n\n...",
  "hero_image": "https://storage.googleapis.com/.../hidden-sugar-in-cereal-hero.jpg",
  "author": "Kortney",
  "brand": "wihy",
  "seo_keywords": ["hidden sugar in breakfast cereal", "..."],
  "citations": [
    { "pmcid": "PMC12138960", "title": "...", "journal": "...", "year": 2025, "url": "https://pmc.ncbi.nlm.nih.gov/..." }
  ],
  "meta_description": "...",
  "word_count": 707,
  "created_at": "2026-04-02T18:33:57.600158"
}
```

**Key notes:**
- `body` is **Markdown** — parse with a markdown renderer (`react-markdown`, `marked`, etc.)
- `hero_image` is a full public URL — use directly in `<img src>`
- `citations[]` — render as footnotes/references at bottom of article
- `seo_keywords[]` — inject into `<meta name="keywords">` for SEO
- Both buckets have `allUsers: objectViewer` — no auth, no CORS issues

## Important Correction
- Do not use /research as a public frontend URL.
- Use a public blog system instead:
  - /blog
  - /blog/[slug]
  - /blog/topic/[topic-slug]
  - /blog/tag/[tag-slug]

This keeps research as an internal evidence source while exposing human-readable SEO pages publicly.

## What Searches Are Asking Now (Accessible Demand Signals)
Direct search-query endpoints are protected in this environment, so current demand is based on the latest accessible signals from your running stack:

1. ALEX keyword/topic routing inputs
- Source: labat.wihy.ai/api/alex/keywords, labat.wihy.ai/api/alex/content-queue (used by ALEX cycles)
- Topic classes already prioritized in production logic:
  - nutrition
  - exercise
  - processed_meat
  - supplements
  - fasting
  - sugar
  - alcohol

2. Live assistant follow-up intent patterns (ml.wihy.ai)
- Frequently suggested follow-up themes:
  - macro balance
  - calorie intake
  - hydration
  - protein planning

3. Existing query-pattern guidance in repo routing logic
- Strong recurring user intent buckets:
  - is it healthy (food/habit safety)
  - ingredient effects
  - alternatives/swap recommendations
  - calories/macros and weight-management questions
  - chronic risk topics (diabetes, heart disease, inflammation)

## Frontend Blog Information Architecture

### Core public routes
- /blog
  - Main blog index with featured post, latest posts, topic cards, and search.
- /blog/[slug]
  - Individual article page.
- /blog/topic/[topic-slug]
  - Topic landing page that clusters related posts.
- /blog/tag/[tag-slug]
  - Lightweight taxonomy pages for long-tail filtering.

### Optional authority routes
- /evidence/[slug]
  - Optional deep evidence summaries (if you want a public research style page without using /research).
- /guides/[slug]
  - Evergreen guide format for pillar content.

## Blog Taxonomy To Launch

### Primary topics (launch first)
1. nutrition
2. sugar-and-blood-health
3. processed-foods
4. protein-and-muscle
5. hydration
6. fasting
7. supplements
8. alcohol-and-health
9. food-swaps
10. weight-management

### Tag examples
- high-protein
- blood-sugar
- ultra-processed
- meal-planning
- grocery-labels
- gut-health
- anti-inflammatory
- beginner-friendly

## Content Model For Frontend

### Fields published by Kortney (available now)
- `slug` — URL-safe identifier
- `title` — full article title
- `body` — article content in **Markdown**
- `author` — always "Kortney"
- `brand` — "wihy" or "communitygroceries"
- `hero_image` — full public GCS URL to hero image (DALL-E 3 generated)
- `seo_keywords` — array of 6-12 SEO keywords (generated by Alex's LLM)
- `citations` — array of PubMed/PMC citation objects (`pmcid`, `title`, `journal`, `year`, `url`)
- `meta_description` — for `<meta name="description">` and OG tags
- `word_count` — integer
- `created_at` — ISO timestamp

### Fields the client should derive or add
- `excerpt` — generate from first 200 chars of `body` (strip markdown)
- `reading_minutes` — calculate from `word_count` (÷ 250)
- `topic` — infer from `seo_keywords` or add to Kortney output (future)
- `tags` — derive from `seo_keywords` (future)
- `canonical_url` — build from slug: `https://wihy.ai/blog/{slug}` or `https://communitygroceries.com/blog/{slug}`
- `og_image_url` — same as `hero_image`
- `related_posts` — match by overlapping `seo_keywords` across index
- `faq_items` — extract from article `## FAQ` sections if present (future)
- `schema_type` — always "Article" for blog posts

## Page Templates Client Should Build

### 1) Blog Index Page (/blog)
Build components:
- Hero section (featured article)
- Topic tiles (10 launch topics)
- Latest posts feed
- Trending posts strip (last 30 days views)
- Newsletter/app CTA block
- Pagination

SEO requirements:
- Static title and meta description for index
- ItemList schema for post cards

### 2) Topic Hub Page (/blog/topic/[topic-slug])
Build components:
- Topic intro paragraph
- Pillar article highlight
- Related articles grid
- Related topics links
- FAQ snippet for topic

SEO requirements:
- Unique title/description per topic
- Breadcrumb schema + ItemList schema
- Internal links to at least 5 post URLs

### 3) Article Page (/blog/[slug])
Build components:
- Hero image + title + metadata row
- Quick answer summary box (for snippet capture)
- Main content body
- Key takeaways box
- Related posts section (3-5)
- FAQ accordion
- CTA footer (scan app, meal plan, or community groceries)

SEO requirements:
- Article schema
- FAQPage schema when faq_items present
- Canonical URL
- OG/Twitter metadata

### 4) Tag Page (/blog/tag/[tag-slug])
Build components:
- Tag heading + description
- Post list
- Topic shortcuts

SEO requirements:
- Prevent thin pages: noindex tags with < 3 posts

## Frontend SEO Component Contract
Create one reusable SEO head component and use it across all blog templates.

Required fields:
- title
- meta description
- canonical
- og:title
- og:description
- og:image
- og:url
- twitter:card=summary_large_image
- twitter:title
- twitter:description
- twitter:image
- JSON-LD schema block

## Internal Linking Rules (Critical)
1. Every new blog article must link to 3-5 related internal pages.
2. Every topic hub must link to all key cluster posts.
3. Every article links back to its topic hub.
4. Every article includes one conversion link:
- app signup
- meal planning
- community groceries action page

## 12-Week Blog Rollout Plan (Frontend + Content)

### Weeks 1-2 (Foundation)
- Build /blog index template
- Build /blog/[slug] template
- Build SEO head component
- Build JSON-LD injection utility
- Build sitemap generation for blog URLs

### Weeks 3-4 (Topic hubs)
- Build /blog/topic/[topic-slug]
- Launch 5 topic hubs:
  - nutrition
  - sugar-and-blood-health
  - processed-foods
  - protein-and-muscle
  - hydration

### Weeks 5-8 (Content scale)
- Publish 3 posts per week (12 posts total)
- Enforce internal linking rules
- Add FAQ schema blocks
- Add related-post algorithm (topic + tag + recency)

### Weeks 9-12 (Optimization)
- Add /blog/tag/[tag-slug]
- Add noindex guard for thin tag pages
- Improve snippet formatting (quick answer box)
- Tune titles and meta descriptions for CTR

## Editorial Queue (Kortney — Live)

These 13 articles are loaded in Kortney's editorial queue and can be triggered via `POST labat.wihy.ai/api/kortney/blog/write` or `POST labat.wihy.ai/api/kortney/blog/write-all`.

### WIHY Articles (8)
| # | Slug | Topic | Status |
|---|------|-------|--------|
| 1 | `hidden-sugar-in-cereal` | Hidden sugar in 'healthy' breakfast cereals — worst offenders | ✅ Published |
| 2 | `ultra-processed-foods-cancer-risk` | Ultra-processed foods and cancer risk — what 48M+ articles show | Queued |
| 3 | `protein-needs-debunked` | How much protein do you actually need? | Queued |
| 4 | `added-sugar-healthy-swaps` | 5 'healthy' foods with more sugar than candy — and swaps | Queued |
| 5 | `seed-oils-truth` | Seed oils: toxic or fine? 30 years of research | Queued |
| 6 | `gut-microbiome-mental-health` | Gut-brain axis: what science says | Queued |
| 7 | `natural-flavors-exposed` | What 'natural flavors' actually means on labels | Queued |
| 8 | `multivitamin-waste-of-money` | Is your multivitamin doing anything? | Queued |

### Community Groceries Articles (5)
| # | Slug | Topic | Status |
|---|------|-------|--------|
| 1 | `budget-meal-prep-under-75` | Weekly meal prep for family of four under $75 | ✅ Published |
| 2 | `healthy-school-lunches-kids-eat` | 10 school lunch ideas kids will actually eat | Queued |
| 3 | `seasonal-produce-save-money` | Buying seasonal produce saves $200/month | Queued |
| 4 | `weeknight-dinners-30-minutes` | 15 weeknight dinners in 30 minutes or less | Queued |
| 5 | `grocery-budget-strategies` | Smart grocery shopping strategies that cut your bill | Queued |

### Previous Backlog (for future queue additions)
These demand-signal topics can be added to Kortney's editorial queue as the blog scales:

Priority A
1. Macros vs calories: what matters most for weight loss
2. Is intermittent fasting healthy for most adults
3. Hydration myths: how much water do you actually need

Priority B
4. Best high-protein breakfast options with simple macros
5. Red meat vs processed meat: what evidence says
6. Alcohol and recovery: what happens to sleep and metabolism

Priority C
7. Grocery label decoding in under 60 seconds
8. Healthier alternatives for pizza, tacos, and burgers
9. Blood sugar-friendly meal planning for beginners
10. Fasting and workout timing: what to know first

## Social Distribution Loop (Shania Integration)

All social distribution flows through `labat.wihy.ai`.

**Content creation vs social distribution are now separate:**
- **Kortney** writes the blog article → publishes to GCS (static JSON + hero image)
- **Alex + Shania** handle social amplification of the published article

For each published blog post:
1. **Generate social post draft:**
   - `POST labat.wihy.ai/api/alex/orchestrate-post`
   - Body: `{ "prompt": "...", "brand": "wihy", "platforms": ["queue"], "dry_run": false }`
   - Alex signals SEO data → Shania Graphics generates content + **AI-generated image (Imagen 4.0)** → queued for approval
2. **Review in approval queue:**
   - Dashboard: `labat.wihy.ai/api/graphics/approval`
   - Queue API: `GET labat.wihy.ai/api/graphics/approval/queue`
   - Vote: `POST labat.wihy.ai/api/graphics/approval/{id}/vote` — `{ "voter": "otaku_master", "vote": "like" }`
   - Both `otaku_master` and `labat` must approve before delivery
3. **Approval email notification** is sent automatically when a post enters the queue (via auth.wihy.ai alerts)
4. **Publish only approved posts** — delivery routes to Facebook, Instagram, Twitter, LinkedIn, TikTok via Shania
5. Always link to the target blog URL with UTM tags.

UTM pattern:
- utm_source=facebook|instagram|x
- utm_medium=social
- utm_campaign=blog_launch_q2
- utm_content={approval_id}

## Frontend Analytics Requirements
Track these at page and topic levels:
- impressions
- clicks
- ctr
- avg_position
- sessions
- engaged_time
- scroll_depth
- cta_clicks

Dashboard slices:
- by topic
- by article
- by source/medium
- by device

## Build Checklist For Client Team
- **Fetch blog content from GCS** — `GET storage.googleapis.com/{bucket}/blog/posts/index.json` (no auth)
- **Parse article body as Markdown** — use `react-markdown`, `marked`, or equivalent
- **Render citations** from `citations[]` array as footnotes with PubMed links
- **Inject SEO meta** from `seo_keywords[]`, `meta_description`, and `hero_image`
- Build public blog routes (/blog, /blog/[slug], /blog/topic/[topic-slug], /blog/tag/[tag-slug])
- Build reusable SEO component
- Build schema utility (Article, FAQPage, BreadcrumbList, ItemList)
- Build related-links block on article pages (match by overlapping `seo_keywords`)
- Build dynamic sitemap for blog URLs (built from index.json slugs)
- Build noindex rules for thin tag pages
- Integrate Shania approval flow via `labat.wihy.ai/api/graphics/approval`
- Add UTM link builder for social posts
- Wire `POST labat.wihy.ai/api/alex/orchestrate-post` for social amplification (now generates unique AI images per post)
- Use `labat.wihy.ai/api/labat/*` for ad campaign and lead tracking integration
- Link to research bot articles: `labat.wihy.ai/research-bot/{slug}` for evidence-based content pages
- Embed research bot feed on blog via `GET labat.wihy.ai/research-bot/posts`

## API Quick Reference

### Alex (SEO + Content)
```
GET  labat.wihy.ai/api/alex/health              → service health
GET  labat.wihy.ai/api/alex/status              → cycle status + stats
POST labat.wihy.ai/api/alex/orchestrate-post    → trigger content pipeline
POST labat.wihy.ai/api/alex/trigger/{cycle}     → manual cycle trigger
```

### Shania (Engagement + Approval)
```
GET  labat.wihy.ai/api/engagement/monitor       → engagement monitor status
POST labat.wihy.ai/api/engagement/engage        → post to social platforms
GET  labat.wihy.ai/api/graphics/approval         → approval dashboard (HTML)
GET  labat.wihy.ai/api/graphics/approval/queue   → queued posts (JSON)
POST labat.wihy.ai/api/graphics/approval/{id}/vote → vote on post
```

### Research Bot (Public Pages)
```
GET  labat.wihy.ai/research-bot                 → HTML index page (all research articles)
GET  labat.wihy.ai/research-bot/:slug           → HTML individual article page (SEO-ready, with JSON-LD)
GET  labat.wihy.ai/research-bot/:slug/json      → JSON single post
GET  labat.wihy.ai/research-bot/posts           → JSON list of all posts (filterable by ?topic=)
POST labat.wihy.ai/research-bot/posts           → Create research post (requires X-Admin-Token)
```

Research posts are auto-created by the **Moltbook bot** (@wihyhealthbot) every time it publishes
a new research article on Moltbook. Each post includes title, body, PubMed citations, and topic.

### Kortney (Blog Writer — Master Agent)
```
GET  labat.wihy.ai/api/kortney/blog/health      → blog writer health
GET  labat.wihy.ai/api/kortney/blog/queue        → editorial queue (13 articles, status per article)
POST labat.wihy.ai/api/kortney/blog/write        → write single article { "slug": "..." } (background task)
POST labat.wihy.ai/api/kortney/blog/write-all    → write all queued articles (background task)
```

### Content / Keywords (Master Agent)
```
GET  labat.wihy.ai/api/content/keywords          → list all SEO keywords
POST labat.wihy.ai/api/content/keywords          → add single keyword
POST labat.wihy.ai/api/content/keywords/bulk     → bulk add keywords
POST labat.wihy.ai/api/content/keywords/{id}/status → update keyword status
GET  labat.wihy.ai/api/content/keywords/for-topic → keywords matching topic query
```

### Blog Content (GCS — Public, No Auth)
```
GET  storage.googleapis.com/wihy-web-assets/blog/posts/index.json     → WIHY blog index
GET  storage.googleapis.com/wihy-web-assets/blog/posts/{slug}.json    → WIHY article
GET  storage.googleapis.com/cg-web-assets/blog/posts/index.json       → CG blog index
GET  storage.googleapis.com/cg-web-assets/blog/posts/{slug}.json      → CG article
```

### Labat (Ads + Leads)
```
GET  labat.wihy.ai/api/labat/health             → service health
GET  labat.wihy.ai/api/labat/ads/*              → ad campaigns
GET  labat.wihy.ai/api/labat/insights/*         → ad insights
GET  labat.wihy.ai/api/labat/leads/*            → lead management
POST labat.wihy.ai/api/labat/conversions/*      → conversion tracking
```

## Image Generation

The `orchestrate-post` pipeline now generates **unique AI images** for every social/blog post:

1. Gemini plans the post → writes a detailed Imagen prompt describing subject, camera angle, lighting
2. **Imagen 4.0** generates a photorealistic image (no text in images, editorial photography style)
3. Image is uploaded to GCS and attached to the approval queue
4. If Imagen is unavailable, falls back to brand logo asset

Image format maps to post type:
| Output Format | Imagen Aspect Ratio | Use Case |
|--------------|--------------------|-----------|
| `feed_square` | 1:1 | Instagram, Facebook feed |
| `story_vertical` | 9:16 | Stories, Reels, TikTok |
| `blog_hero` | 16:9 | Blog hero images |
| `ad_landscape` | 16:9 | Ads, social share cards |

For blog posts, use `outputSize: "blog_hero"` in `orchestrate-post` to get a 16:9 hero image.

## Notes
- **Blog content is static JSON on GCS** — no dynamic API calls needed for reading. Client fetches index.json + {slug}.json directly.
- **Kortney writes articles** → publishes to GCS. Alex provides SEO keywords. Shania handles social distribution. Each agent has a distinct role.
- Keep /api/research as backend data source only (served via ml.wihy.ai).
- Do not expose /research as public UI route. Use `/research-bot` for public evidence pages instead.
- All growth/marketing APIs go through **labat.wihy.ai**, not ml.wihy.ai.
- ml.wihy.ai remains the domain for user-facing AI (chat, RAG, meals, fitness).
- DNS setup needed: CNAME `labat.wihy.ai` → `labat-wihy-ai.web.app`, then add custom domain in Firebase Console.
- Master Agent (Kortney + keywords) is at `wihy-master-agent-n4l2vldq3q-uc.a.run.app` — exposed via labat.wihy.ai Firebase routing.
- 2 articles already published and live (hidden-sugar-in-cereal on WIHY, budget-meal-prep-under-75 on CG) as of April 2, 2026.
- To write remaining articles: `POST labat.wihy.ai/api/kortney/blog/write-all` (requires X-Admin-Token).
- If direct query telemetry is needed for a tighter plan, grant access to:
  - labat.wihy.ai/api/alex/keywords
  - labat.wihy.ai/api/alex/content-queue
  Then refresh this backlog using the last 30 days of real terms.
