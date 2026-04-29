# VOWELS.ORG System PRD

## Vision
Vowels is a nutrition education publication operated like a newsroom.

Core identity:
- Newsroom: timely nutrition updates
- Research interpreter: translate studies into plain language
- Public health hub: evidence-based education
- Editorial principle: content is powered by data, not opinions

Master editor:
- Kortney (Otaku)

## Product Requirements

### 1. Revenue and Ads
Phase 1:
- Google AdSense auto ads
- Display ads
- In-article ads

Phase 2:
- Google Ad Manager
- Direct ad sales
- Sponsored inventory controls

Ad placements:
- Homepage: leaderboard, in-feed, sidebar
- Article: top banner, mid-article, bottom sponsored/native, sticky mobile banner

Sponsored content:
- Sponsored article type
- Mandatory Sponsored label
- Distinct visual treatment

Affiliate system:
- Healthy foods
- Kitchen tools
- Books
- Amazon Associates tracking

### 2. Editorial and CMS Workflow
Editorial roles:
- Editor-in-chief
- Writer (AI + human)
- Data analyst (WIHY)
- Reviewer

Content types:
- nutrition-education
- news-update
- data-insight
- opinion-editorial
- sponsored

### 3. Distribution
Platform distribution:
- Google News
- Microsoft Start

Feed distribution:
- RSS for Feedly, Flipboard, Inoreader
- News sitemap for Google News

Social distribution (automatic per article):
- Instagram
- Facebook
- LinkedIn
- X

### 4. Engagement
- Newsletter capture and drip (Mailchimp or ConvertKit)
- Push notifications (phase 2)
- Optional reader accounts (saved content, interest tracking)

### 5. SEO and Growth
Technical SEO:
- Article schema
- sitemap.xml
- news-sitemap.xml
- RSS feed

Content strategy:
- High-intent nutrition search terms

Internal linking:
- Every article links to 3-5 related articles

### 6. Data Layer (WIHY Differentiator)
- "From the Data" section in articles
- Weekly trend snapshots
- Pattern insights
- Behavior-informed practical recommendations

### 7. Design System
Layout:
- Header with logo, categories, search
- Homepage with featured story, feed, category blocks, data block
- Article page with uninterrupted reading flow and natural ad insertion

Style:
- Light blue background
- White cards
- Minimal clutter
- Fast load and mobile-first

### 8. Analytics and Trust
Analytics:
- Page views
- Time on page
- CTA CTR
- Scroll depth

Legal pages:
- Privacy Policy
- Terms of Use
- Editorial Policy
- Health Disclaimer

### 9. Performance Targets
- Page load under 2s
- Fully mobile optimized
- SEO optimized

### 10. Monetization Roadmap
Phase 1:
- Free content
- Traffic growth

Phase 2:
- AdSense
- Affiliate links

Phase 3:
- Sponsored content and partnerships

Phase 4:
- Route qualified readers to WIHY

## Implemented Backend Foundation (This Repo)
- Vowels newsroom route group:
  - /api/vowels/newsroom/health
  - /api/vowels/newsroom/blueprint
  - /api/vowels/newsroom/content-types
  - /api/vowels/newsroom/queue
  - /api/vowels/newsroom/run-autonomous
  - /api/vowels/newsroom/rss.xml
  - /api/vowels/newsroom/news-sitemap.xml
- Vowels editorial queue added to Kortney writer pipeline
- Content type metadata added to article publishing and index data
- Vowels autonomous cycle available through run-autonomous endpoint

## Next Build Steps
1. Frontend site shell for vowels.org homepage/article/category pages.
2. Article schema + sponsored schema rendering on live pages.
3. Ad slot components (desktop/mobile) with placement policy.
4. Newsletter provider integration (Mailchimp/ConvertKit).
5. Social fan-out per published article via Shania posting workflows.
6. Google News and Microsoft Start submission operations.
7. Editorial dashboard for queue state and approval overrides.
