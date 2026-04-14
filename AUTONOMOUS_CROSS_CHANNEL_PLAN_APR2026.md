# Autonomous Cross-Channel Growth Plan (Saved for Later)

Date: 2026-04-04
Owner: Astra/Maya/Shania/Labat stack
Status: Deferred (ready to start)

## Goal
Build a fully autonomous cross-channel growth loop that:
- Ingests trends and intent signals
- Generates deployable ad plans for Google and Microsoft Ads
- Enforces budget and safety guardrails
- Optimizes hourly from performance feedback
- Optionally supports PR/news outlet distribution workflows

## Why This Order
1. Shared schema first prevents duplicated logic and drift between channels.
2. Google adapter first gives fastest measurable ROI.
3. Microsoft adapter next adds lower-CPC scale (Bing + Yahoo inventory).
4. Rules and feedback loop close autonomy and control cost.

## Target Architecture
1. Trend Intake (Astra)
- Inputs: Google Trends, Reddit, X
- Output: ranked trend objects with confidence, freshness, and source counts

2. Intent + Cluster Engine (Astra)
- Output clusters:
  - theme
  - audience
  - angle
  - core keyword set
  - mandatory negative keywords
  - policy risk hints

3. Creative Generator (Maya/Shania)
- Generates:
  - headlines
  - descriptions
  - image/video variants
  - channel-safe metadata

4. Channel Translators
- google_ads_adapter
- microsoft_ads_adapter
- Both consume one shared campaign_spec

5. Budget + Rules Engine
- Daily budget caps
- CPA and ROAS thresholds
- CTR floor checks
- Pause/boost logic

6. Feedback Loop
- Pull metrics hourly
- Feed normalized performance back into Astra
- Re-rank clusters and update bids/creatives

## Phase Plan

### Phase 1 (First Buildable Slice)
Implement now:
1. Shared campaign_spec schema
2. ads_channel_router service
3. google_ads_adapter scaffold + first working deploy path
4. Safety gates (minimum set):
- daily budget cap
- mandatory negative keywords
- creative policy checks
- auto-pause on bad CPA/CTR

Definition of done:
- One campaign_spec can be validated and routed to Google deploy path
- Dry-run mode returns full mapped payload
- Live mode creates campaign and ad group safely (behind admin token)

### Phase 2
1. microsoft_ads_adapter implementation
2. Mapping parity with Google objects
3. Cross-channel deployment from same campaign_spec

Definition of done:
- Same campaign_spec deploys to both Google and Microsoft
- Per-channel mapping differences isolated in adapters only

### Phase 3
1. Hourly performance ingestor
2. Optimization actions:
- bid adjust
- creative rotation
- pause/boost rules
3. Confidence-aware rollback protections

Definition of done:
- End-to-end autonomous cycle runs hourly with auditable decisions

## Shared campaign_spec (Draft)
Required fields:
- plan_id
- brand
- objective (leads | sales | awareness)
- channels (google | microsoft)
- budget:
  - daily_cap
  - channel_allocations
- targeting:
  - geo
  - language
  - device modifiers
  - audience segments
- clusters[]:
  - cluster_id
  - theme
  - angle
  - keywords[]
  - negatives[]
  - bid_hint
  - landing_url
- creatives[]:
  - creative_id
  - format (rsa | image | video)
  - headlines[]
  - descriptions[]
  - assets[]
- rules:
  - max_cpa
  - min_ctr
  - min_roas
  - auto_pause
- execution:
  - mode (dry_run | live)
  - schedule

## Cost and Performance Guidance
Expected pattern:
1. Highest intent/performance: Google Search
2. Lower-cost incremental volume: Microsoft Ads (Bing + Yahoo)
3. Best blended efficiency start:
- 50% Google
- 25% Microsoft
- 20% Meta
- 5% TikTok
Then rebalance weekly by blended CPA, qualified leads, and ROAS.

## Optional PR/News Endpoint Track
If adding PR distribution in the same autonomous system, create:
1. POST /api/pr/pitches/generate
2. POST /api/pr/media-list/sync
3. POST /api/pr/distribution/send
4. POST /api/pr/followups/run
5. GET /api/pr/coverage
6. GET /api/pr/health

Recommended: implement PR as a parallel module after Phase 2 unless urgent.

## Risks to Control
1. Policy violations from auto-generated creative
2. Budget runaway from bad loops
3. Overfitting to short-term signals
4. Cross-channel schema drift

Mitigations:
- strict policy validator before deploy
- hard daily caps and kill switch
- confidence thresholds for optimization actions
- adapter contract tests against campaign_spec

## Kickoff Checklist (When You Resume)
1. Create campaign_spec Pydantic models
2. Add ads_channel_router service + route
3. Build Google adapter dry-run mapping
4. Add safety middleware and rule evaluator
5. Add first live deploy call path (admin protected)
6. Add unit tests for schema and rule enforcement
7. Add integration test for end-to-end dry_run

## Notes
- Keep aliases/canonical brand handling consistent with current Vowels canonical mapping.
- Keep all autonomous live actions gated by admin token and environment flags.
