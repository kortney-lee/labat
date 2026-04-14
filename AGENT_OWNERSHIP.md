# Agent Ownership Matrix

> **Rule**: Each agent owns exactly one responsibility. Cross-role endpoints are prohibited.
> Routes MUST resolve to the owning agent only. No silent fallbacks across agents.

## Agent Registry

| Agent | Cloud Run Service | APP_MODULE | Responsibility | Route Prefix |
|-------|-------------------|------------|----------------|--------------|
| **Astra** | `wihy-astra` | `src.apps.astra_app:app` | Discovery & organic opportunity intelligence (keywords, trends, SEO) | `/api/astra/*` |
| **Shania** | `wihy-shania` | `src.apps.shania_app:app` | Publishing & scheduled posting (FB Page, LinkedIn, social channels) | `/api/shania/*`, `/api/labat/posts/*`, `/api/labat/page/*` |
| **Maya** | `wihy-maya` | `src.apps.maya_app:app` | Community engagement & conversations (replies, comments, threads, Messenger) | `/api/engagement/*`, `/api/labat/comments/*`, `/api/labat/messenger/*` |
| **Labat-WIHY** | `wihy-labat` | `src.apps.labat_app:app` | Paid campaigns for WIHY brand | `/api/labat/wihy/*` |
| **Labat-CG** | `wihy-labat-cg` | `src.apps.labat_app:app` | Paid campaigns for Community Groceries | `/api/labat/cg/*` |
| **Labat-Vowels** | `wihy-labat-vowels` | `src.apps.labat_app:app` | Paid campaigns for Vowels/Book | `/api/labat/vowels/*` |
| **Kortney** | `wihy-master-agent` | `src.apps.master_agent_app:app` | Long-form editorial creation (blog posts, articles) | `/api/kortney/*` |
| **Shania Graphics** | `wihy-shania-graphics` | N/A (TypeScript) | Image/video asset generation + approval queue | `/api/graphics/*` |

## Ownership Rules

1. **Single Responsibility**: Each agent owns exactly ONE domain. No engagement on Shania. No posting on Maya. No ads on Astra.
2. **Route Determinism**: Every route prefix resolves to exactly one Cloud Run service at the Firebase edge. No ambiguity.
3. **Brand Isolation (Labat)**: Each Labat brand service runs with its own `META_AD_ACCOUNT_ID`, `META_PAGE_ID`, and credentials. Brand is determined by deployment, not request body.
4. **No Silent Fallback**: If a route receives an unknown brand or out-of-scope request, it returns 400/403 — never defaults to another brand.
5. **Identity Contract**: Every agent exposes `GET /identity` returning `{ "agent", "service", "brand_scope", "version" }`.

## Legacy Compatibility (Deprecation Window)

During migration, old routes remain as aliases with deprecation logging:
- `/api/alex/*` → forwards to Astra (2-week deprecation window)
- `/api/engagement/*` on Shania → returns 301 to Maya (immediate)

## Route Migration Map

| Old Route | Old Owner | New Owner | New Route | Status |
|-----------|-----------|-----------|-----------|--------|
| `/api/alex/*` | Alex (wihy-alex) | **Astra** | `/api/astra/*` | Alias active |
| `/api/engagement/engage` | Shania | **Maya** | `/api/engagement/engage` | Migrated |
| `/api/engagement/engage/batch` | Shania | **Maya** | `/api/engagement/engage/batch` | Migrated |
| `/api/engagement/preview` | Shania | **Maya** | `/api/engagement/preview` | Migrated |
| `/api/engagement/monitor` | Shania | **Maya** | `/api/engagement/monitor` | Migrated |
| `/api/engagement/social-posting` | Shania | **Maya** | `/api/engagement/social-posting` | Migrated |
| `/api/labat/comments/*` | Shania | **Maya** | `/api/labat/comments/*` | Migrated |
| `/api/labat/messenger/*` | Shania | **Maya** | `/api/labat/messenger/*` | Migrated |
| `/api/labat/webhooks` | Shania | **Maya** | `/api/labat/webhooks` | Migrated |
| `/api/labat/compliance/*` | Shania | **Maya** | `/api/labat/compliance/*` | Migrated |
| `/api/labat/posts/*` | Labat/Shania | **Shania** | `/api/labat/posts/*` | Stays |
| `/api/labat/page/*` | Labat/Shania | **Shania** | `/api/labat/page/*` | Stays |
| `/api/labat/ads/*` | Labat | **Labat-{brand}** | `/api/labat/{brand}/ads/*` | Phase 2 |
| `/api/labat/creatives/*` | Labat | **Labat-{brand}** | `/api/labat/{brand}/creatives/*` | Phase 2 |
| `/api/labat/insights/*` | Labat | **Labat-{brand}** | `/api/labat/{brand}/insights/*` | Phase 2 |
