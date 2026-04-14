# What Is Healthy — Sales Page + Growth Playbook

## The Landing Page (Done)

**File:** `static_whatishealthy/index.html`  
**Live:** `whatishealthy.web.app` (needs domain mapping to `whatishealthy.org`)

### Page Structure (Direct-Response Sales Page)
| Section | Conversion Purpose |
|---------|-------------------|
| **Sticky Nav** | CTA always visible on scroll |
| **Hero** | Pattern interrupt headline + free offer + trust micro-copy |
| **Problem** | Agitate pain points (recognition → emotional buy-in) |
| **Solution (Chapters)** | Show what's inside (build perceived value) |
| **Social Proof** | Testimonials (trust + credibility) |
| **What's Included** | Stack the value (free + bonuses) |
| **FAQ** | Handle objections before they stop the click |
| **Final CTA** | Last urgency push with dark background contrast |

### SEO Elements Built In
- Title tag with primary keyword: "What Is Healthy"
- Meta description targeting book download intent
- Meta keywords for long-tail SEO
- Canonical URL
- Open Graph tags (book type)
- Twitter Card tags
- **JSON-LD structured data**: `Book` schema (free ebook) + `FAQPage` schema
- Semantic HTML (`<main>`, `<section>`, `<article>`, `<nav>`, `<footer>`)

---

## Step-by-Step: Using Alex + LABAT to Drive Traffic

### Phase 1: SEO Keyword Discovery (Alex)

**Goal:** Find high-intent keywords people search when looking for nutrition/label guidance.

```bash
# 1. Trigger Alex keyword discovery for whatishealthy brand
curl -X POST https://labat.wihy.ai/api/alex/trigger/keywords \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# 2. Get real-time SEO signals for landing page topics
curl "https://labat.wihy.ai/api/alex/realtime-signals?query=food+label+reading&brand=whatishealthy&limit=10" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

curl "https://labat.wihy.ai/api/alex/realtime-signals?query=healthy+eating+book&brand=whatishealthy&limit=10" \
  -H "X-Admin-Token: $ADMIN_TOKEN"

curl "https://labat.wihy.ai/api/alex/realtime-signals?query=ingredient+label+guide&brand=whatishealthy&limit=10" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

**Target keyword clusters:**
- "how to read food labels"
- "what is healthy food"
- "healthy eating guide book"
- "decode food ingredients"
- "nutrition misinformation"
- "processed food alternatives"
- "food label tricks"

### Phase 2: Content Generation (Alex)

**Goal:** Auto-generate SEO blog articles that link back to the book download.

```bash
# Trigger content queue — Alex will generate pages for high-priority keywords
curl -X POST https://labat.wihy.ai/api/alex/trigger/content-queue \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

Alex generates full pages with:
- SEO title, meta description, keywords
- FAQ sections with JSON-LD schema
- Related links back to the book landing page
- Content types: `is_it_healthy`, `ingredient`, `alternative`, `topic`

**Example generated articles that funnel to book:**
- "Is Canola Oil Healthy?" → ends with "Learn more in our free book"
- "Hidden Sugars in 'Healthy' Snacks" → CTA to download
- "How to Read Nutrition Facts in 10 Seconds" → excerpt from book chapter

### Phase 3: Ad Copy Generation (LABAT)

**Goal:** Create high-converting ad variants for Facebook/Instagram/Google.

#### Awareness Ads (Top of Funnel)
```bash
curl -X POST https://labat.wihy.ai/api/labat/ai/generate/ad-copy \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "Free digital book that teaches you how to decode food labels, spot misleading health claims, and make smarter nutrition decisions in 10 seconds. Includes 50+ ingredient swap cards and a weekly meal planning template.",
    "target_audience": "Health-conscious adults 25-55 who buy groceries regularly, frustrated by confusing labels and contradictory nutrition advice. Parents who want better food for their families.",
    "campaign_goal": "Drive free book downloads to whatishealthy.org",
    "num_variants": 5,
    "tone": "Direct, empowering, slightly provocative — not preachy. Evidence-backed urgency.",
    "product": "whatishealthy",
    "funnel_stage": "awareness"
  }'
```

#### Consideration Ads (Retargeting)
```bash
curl -X POST https://labat.wihy.ai/api/labat/ai/generate/ad-copy \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "Free evidence-based nutrition book with 50+ ingredient swaps and a 10-second label decoding system. Over 10,000 readers. Cited peer-reviewed research throughout.",
    "target_audience": "People who visited whatishealthy.org but did not download. Also: followers of nutrition/health pages, people who engage with food content.",
    "campaign_goal": "Convert warm visitors to book downloads with social proof and objection handling",
    "num_variants": 5,
    "tone": "Trustworthy, proof-heavy, specific outcomes",
    "product": "whatishealthy",
    "funnel_stage": "consideration"
  }'
```

#### Conversion Ads (Hardcover Upsell)
```bash
curl -X POST https://labat.wihy.ai/api/labat/ai/generate/ad-copy \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "Hardcover edition of What Is Healthy — the physical book that sits on your kitchen counter as a daily reference. Premium quality, full-color swap cards, and a quick-reference label guide on the back cover.",
    "target_audience": "People who already downloaded the free digital book and engaged with it. Email list subscribers who opened 2+ emails.",
    "campaign_goal": "Sell hardcover book upgrade",
    "num_variants": 5,
    "tone": "Premium, tangible value, gift-worthy — slight urgency on limited print run",
    "product": "whatishealthy",
    "funnel_stage": "conversion"
  }'
```

### Phase 4: Social Media Posts (LABAT)

**Goal:** Organic reach on Facebook, Instagram, LinkedIn.

```bash
# Facebook awareness posts
curl -X POST https://labat.wihy.ai/api/labat/ai/generate/posts \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Most people cant tell the difference between a healthy food label and a misleading one. Here is what to look for.",
    "platform": "facebook",
    "num_posts": 5,
    "content_pillar": "nutrition",
    "product": "whatishealthy"
  }'

# Instagram carousel-style posts
curl -X POST https://labat.wihy.ai/api/labat/ai/generate/posts \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "5 ingredients hiding in your healthy snacks that are actually harmful",
    "platform": "instagram",
    "num_posts": 5,
    "content_pillar": "nutrition",
    "product": "whatishealthy"
  }'
```

### Phase 5: Content Calendar (LABAT)

**Goal:** 4-week content plan across all platforms.

```bash
curl -X POST https://labat.wihy.ai/api/labat/ai/generate/calendar \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "weeks": 4,
    "focus_areas": ["label decoding tips", "ingredient swaps", "marketing lies exposed", "reader success stories", "book excerpts"],
    "existing_content": "Free digital book available at whatishealthy.org. Hardcover upsell available. WIHY scanner app for product scanning."
  }'
```

### Phase 6: Campaign Intelligence (LABAT)

Once ads are running, use LABAT intelligence to optimize:

```bash
# Analyze which ads perform best
curl -X POST https://labat.wihy.ai/api/labat/ai/analyze/campaigns \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "insights_data": [...],  # Paste Meta Ads insights JSON here
    "product": "whatishealthy"
  }'

# Get audience recommendations
curl -X POST https://labat.wihy.ai/api/labat/ai/analyze/audiences \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_context": "Free nutrition book download campaign targeting health-conscious grocery shoppers",
    "performance_data": [...],
    "product": "whatishealthy"
  }'

# Optimize budget allocation
curl -X POST https://labat.wihy.ai/api/labat/ai/analyze/budget \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_performance": [...],
    "total_budget": 500,
    "product": "whatishealthy"
  }'
```

### Phase 7: Nurture Sequences (Shania)

After book download, Shania templates handle the nurture flow:

| Day | Template | Action |
|-----|----------|--------|
| 0 | `digital_book_delivery` | Deliver PDF + welcome |
| 3 | Follow-up | Reading check-in + tip from book |
| 5 | `hardcopy_upsell` | Offer physical book |
| 7 | Value email | Ingredient swap highlight |
| 10 | `final_urgency` | Last-chance hardcover offer |

### Phase 8: Analytics Loop (Alex)

```bash
# Check page performance
curl -X POST https://labat.wihy.ai/api/alex/trigger/analytics \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# Get comprehensive report
curl https://labat.wihy.ai/api/alex/report \
  -H "X-Admin-Token: $ADMIN_TOKEN"

# Refresh underperforming pages (CTR < 2%)
curl -X POST https://labat.wihy.ai/api/alex/trigger/page-refresh \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

---

## Deployment Checklist

- [x] Landing page rewritten with direct-response conversion structure
- [x] SEO: title, meta, canonical, OG, Twitter Card, JSON-LD (Book + FAQ)
- [x] Mobile responsive design
- [x] Sticky nav with CTA
- [x] FAQ accordion with objection handling
- [x] Firebase hosting config (whatishealthy site)
- [ ] Deploy to whatishealthy.web.app: `firebase deploy --only hosting:whatishealthy --config firebase.whatishealthy.json`
- [ ] Map whatishealthy.org domain in Firebase Console
- [ ] Add OG image (`og-book.png`) to `static_whatishealthy/`
- [ ] Run Alex keyword discovery for whatishealthy brand
- [ ] Generate first batch of ad copy variants via LABAT
- [ ] Generate 4-week content calendar via LABAT
- [ ] Set up Meta pixel / conversion tracking on the page
- [ ] Configure Shania nurture templates for post-download flow

## Key Metrics to Track

| Metric | Target | Tool |
|--------|--------|------|
| Page load time | < 2s | Firebase Hosting (CDN) |
| Bounce rate | < 45% | Google Analytics |
| CTA click rate | > 8% | Meta Pixel |
| Book download conversion | > 5% | payment.wihy.ai |
| Hardcover upsell rate | > 3% of downloaders | Shania tracking |
| SEO page CTR | > 2% | Alex analytics |
| Ad CPA (cost per acquisition) | < $2 | LABAT campaign analysis |
