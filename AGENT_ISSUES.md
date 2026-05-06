# Agent Issues & Fix Plan

Audit date: 2026-05-04  
Agents covered: **Labat** (paid ads), **Maya** (community engagement), **Shania** (publishing)

---

## Quick Summary

| Problem | Agent | Severity | Status |
|---|---|---|---|
| Cloud Scheduler not configured — automation never fires | Labat | Critical | Not fixed |
| Leads not flowing in — `META_WEBHOOK_VERIFY_TOKEN` missing | Labat | Critical | Not fixed |
| Social posting blocked by default — `SOCIAL_POSTING_DISABLED=true` | Maya + Shania | Critical | Not fixed |
| All social API keys empty — every engagement attempt fails | Maya | Critical | Not fixed |
| Follower/friend/collaborator discovery — never built | Maya | Major | Not built |
| LinkedIn not configured — `LINKEDIN_ACCESS_TOKEN` missing | Labat + Shania | Major | Not fixed |
| Reply monitoring only works on Twitter — other platforms skipped | Maya | Minor | Not built |

---

## Problem 1 — Labat: Automation Never Fires

### Root Cause
Labat's full automation cycle (auto-pause underperformers, auto-scale winners, A/B rotation) is triggered by an HTTP call to:

```
POST /api/labat/automation/cron
```

This endpoint is designed to be called by **Google Cloud Scheduler** on an hourly schedule. If that Cloud Scheduler job does not exist in GCP, the automation **never runs at all.** The service just sits idle.

**Relevant file:** [src/labat/routers/automation_routes.py](src/labat/routers/automation_routes.py)

### Fix Steps

1. **Go to GCP Console → Cloud Scheduler → Create Job**
   - Name: `labat-automation-cron`
   - Frequency: `0 * * * *` (every hour)
   - Target type: HTTP
   - URL: `https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/automation/cron`
   - HTTP method: POST
   - Headers: `x-admin-token: <your INTERNAL_ADMIN_TOKEN value>`
   - Body: `{}`

2. **Test immediately** with a dry run to confirm it works before enabling live mode:
   ```
   POST /api/labat/automation/cron?dry_run=true
   ```
   Response will show what would have been paused/scaled without taking action.

3. **Verify automation status** at any time:
   ```
   GET /api/labat/automation/status
   ```

### What the Automation Does (When Running)

Every hour, `run_full_cycle()` executes these steps in order:

| Step | Logic | Threshold |
|---|---|---|
| **Health check** | Pings all services, detects anomalies | — |
| **Auto-pause** | Pauses adsets with spend > $10 + zero conversions | `AUTOMATION_PAUSE_SPEND_THRESHOLD=10.0` |
| **Auto-pause** | Pauses adsets with CTR < 0.5% after 1,000 impressions | `AUTOMATION_PAUSE_CTR_FLOOR=0.5` |
| **Auto-scale** | Increases budget +20% for adsets with ROAS > 1.5 | `AUTOMATION_SCALE_ROAS_THRESHOLD=1.5` |
| **Auto-scale** | Budget ceiling capped at $500/day | `AUTOMATION_SCALE_BUDGET_CEILING=50000` (cents) |
| **A/B rotation** | Pauses losing ads when winner beats by 20%+ score margin | `AUTOMATION_AB_WIN_MARGIN=1.2` |
| **Report** | Sends full results to master agent + email via SendGrid | — |

All thresholds are configurable via Cloud Run env vars.

---

## Problem 2 — Labat: Leads Not Flowing In

### Root Cause
Facebook Lead Ads deliver form submissions via **webhooks**. Meta requires a one-time webhook verification handshake using a secret verify token. When `META_WEBHOOK_VERIFY_TOKEN` is not set, the verification fails and **Meta never sends lead events** to the service.

Result: leads fill out Facebook lead forms but they never reach Firestore. The lead pipeline is broken at the intake point.

**Relevant file:** [src/labat/config.py](src/labat/config.py) — `META_WEBHOOK_VERIFY_TOKEN` (line 47)

### Fix Steps

1. **Generate a verify token** — any secret string works, e.g.:
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Set it in Cloud Run** for `wihy-labat`:
   ```
   META_WEBHOOK_VERIFY_TOKEN=<your generated token>
   ```

3. **Set it in Meta App Dashboard:**
   - Go to Meta for Developers → Your App → Webhooks
   - Subscribe to the `leads` object
   - Callback URL: `https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/webhook`
   - Verify Token: paste the same token

4. **Subscribe the lead form** to webhooks in Meta Business Suite → Lead Ads → Forms → select form → Webhook.

5. **Test** by submitting a test lead through Meta's webhook test tool in the developer dashboard.

---

## Problem 3 — Labat + Shania: LinkedIn Completely Disabled

### Root Cause
Both the Labat analytics routes and Shania's LinkedIn posting routes require:
- `LINKEDIN_ACCESS_TOKEN`
- `LINKEDIN_ORG_ID`

Both are unset. LinkedIn features fail gracefully (routes load but return errors).

**Relevant files:**
- [src/labat/linkedin_client.py](src/labat/linkedin_client.py)
- [src/labat/routers/linkedin_analytics_routes.py](src/labat/routers/linkedin_analytics_routes.py)
- [src/labat/routers/linkedin_posting_routes.py](src/labat/routers/linkedin_posting_routes.py)

### Fix Steps

1. **Create a LinkedIn App** at [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
   - Products needed: **Marketing Developer Platform** + **Share on LinkedIn**
   - Scopes needed: `w_member_social`, `r_organization_social`, `w_organization_social`, `r_basicprofile`

2. **Get your Organization ID** from your LinkedIn Company Page URL:
   - `https://www.linkedin.com/company/12345678/` → ID is `12345678`

3. **Set in Cloud Run** for both `wihy-labat` and `wihy-shania`:
   ```
   LINKEDIN_ACCESS_TOKEN=<token from OAuth flow>
   LINKEDIN_ORG_ID=<numeric org id>
   ```

4. LinkedIn access tokens expire every 60 days. Set a reminder to refresh or implement the OAuth refresh flow.

---

## Problem 4 — Maya: Social Posting Is Off by Default

### Root Cause
Both Maya and Shania have this hardcoded default in their post service:

```python
# src/labat/services/post_service.py — line 19
SOCIAL_POSTING_DISABLED = os.getenv("SOCIAL_POSTING_DISABLED", "true")
```

Unless this env var is explicitly set to `"false"`, every post attempt returns a 403 error. Neither agent is publishing anything right now.

**Relevant files:**
- [src/labat/services/post_service.py](src/labat/services/post_service.py) — line 19
- [src/labat/services/linkedin_posting_service.py](src/labat/services/linkedin_posting_service.py) — line 30

### Fix Steps

1. **Set in Cloud Run** for both `wihy-maya` and `wihy-shania`:
   ```
   SOCIAL_POSTING_DISABLED=false
   ```

2. **Optional: enable launch mode** (posts 2x per cycle, 75% launch-hype content):
   ```
   SOCIAL_POSTING_LAUNCH_MODE=true
   ```

3. **Adjust posting interval** (default is every 4 hours):
   ```
   SHANIA_SOCIAL_POSTING_INTERVAL=14400   # seconds (4 hours)
   SHANIA_MAX_POSTS_PER_CYCLE=1           # posts per cycle (2 in launch mode)
   ```

---

## Problem 5 — Maya: All Social API Keys Are Empty

### Root Cause
Every social platform token is unset in the environment. Maya logs warnings and skips engagement rather than crashing, so this is silent — no errors are surfaced to the user.

**Relevant file:** [src/maya/services/engagement_poster_service.py](src/maya/services/engagement_poster_service.py)

### Fix Steps — Set All Tokens in Cloud Run for `wihy-maya`

#### Twitter / X
```
TWITTER_API_KEY=<from developer.twitter.com>
TWITTER_API_SECRET=<from developer.twitter.com>
TWITTER_ACCESS_TOKEN=<from developer.twitter.com>
TWITTER_ACCESS_TOKEN_SECRET=<from developer.twitter.com>
TWITTER_BOT_USERNAME=wihyhealthbot
```
- App needs **Read + Write** permissions
- Uses OAuth 1.0a for posting

#### Instagram
```
INSTAGRAM_ACCESS_TOKEN=<long-lived page token with instagram_manage_comments scope>
```
- Must be a **Business or Creator** Instagram account linked to your Facebook Page

#### Facebook
```
FACEBOOK_ACCESS_TOKEN=<same as SHANIA_PAGE_ACCESS_TOKEN or a page token>
```

#### Threads
```
THREADS_ACCESS_TOKEN=<Threads API token — falls back to INSTAGRAM_ACCESS_TOKEN if not set>
```

#### TikTok
```
TIKTOK_ACCESS_TOKEN=<from developers.tiktok.com with tt.user.comment scope>
```

---

## Problem 6 — Maya: Follower/Friend/Collaborator Discovery Not Built

### Root Cause
This is the largest gap. Maya was built as a **reactive comment-posting agent** — she only engages leads that are fed to her externally (from Facebook Lead Ads). There is **zero code** for:

- Finding new followers or potential customers
- Scanning hashtags or keywords
- Auto-following, auto-liking, or DMing users
- Identifying collaborators or influencers
- Any form of outbound community growth

### What Needs to Be Built

The following modules need to be created from scratch under `src/maya/services/`:

---

#### Module A: `audience_discovery_service.py`
Scans social platforms for target-audience users based on keywords and hashtags.

**Logic:**
1. Define seed hashtags per brand (e.g. `#nutrition`, `#healthyeating`, `#mealprep` for WIHY)
2. Call Twitter Search API v2 to find recent posts using those hashtags
3. Filter for users who: have >100 followers, are not bots, posted in last 7 days, have public accounts
4. Score users by engagement rate and relevance
5. Store discovered users in Firestore under `audience_discovery/{platform}/{user_id}`
6. Deduplicate — never re-process a user already in Firestore

**APIs needed:**
- Twitter Search API v2 (`GET /2/tweets/search/recent`) — requires Elevated access
- Instagram Hashtag Search (Meta Graph API) — requires `instagram_basic` + `pages_read_engagement` scope

---

#### Module B: `collaborator_finder_service.py`
Identifies influencers and complementary accounts for potential partnerships.

**Logic:**
1. Search for accounts in health/nutrition/wellness niche with 5K–500K followers
2. Score by: engagement rate, content relevance (keyword match in bio/posts), follower growth trend
3. Rank top 10 per brand per week
4. Send weekly collaborator report via SendGrid to `kortney@wihy.ai`
5. Store in Firestore under `collaborators/{brand}/{user_id}`

**APIs needed:**
- Twitter User Search API v2
- Instagram account lookup via Meta Graph API
- Manual review workflow: surface candidates, don't auto-DM without approval

---

#### Module C: `auto_engage_service.py`
Proactively likes and follows discovered users to build organic reach.

**Logic:**
1. Pull unengaged users from `audience_discovery` Firestore collection
2. Like their most recent relevant post (keyword-matched)
3. Follow account (Twitter only — Instagram/TikTok require special API access)
4. Mark as engaged in Firestore — never re-engage the same user
5. Enforce daily rate limits to avoid platform spam triggers:
   - Twitter: max 400 follows/day, max 1,000 likes/day
   - Respect platform-specific cooldowns

**APIs needed:**
- Twitter v2: `POST /2/users/:id/following`, `POST /2/tweets/:id/like`
- Instagram: Like endpoint requires `instagram_manage_comments` (limited to owned content only — cannot like other users' posts via API)

---

#### Module D: `dm_outreach_service.py`
Sends personalized DMs to high-scoring discovered users. **Requires manual approval gate.**

**Logic:**
1. Pull top-scored collaborators from Firestore
2. Generate personalized DM using Gemini based on their recent posts and WIHY brand voice
3. **Queue for human review** — send draft to `kortney@wihy.ai` with approve/reject link before sending
4. On approval: send DM via Twitter DM API
5. Log all DMs sent to Firestore

**APIs needed:**
- Twitter v2: `POST /2/dm_conversations` — requires DM permissions

---

#### New Background Loop in `maya_app.py`

Once the above services exist, add these loops to the lifespan manager in [src/apps/maya_app.py](src/apps/maya_app.py):

```python
# Audience discovery — run every 6 hours
asyncio.create_task(_loop(audience_discovery_service.run_once, interval=21600, label="audience-discovery"))

# Collaborator finder — run every 24 hours
asyncio.create_task(_loop(collaborator_finder_service.run_once, interval=86400, label="collaborator-finder"))

# Auto-engage discovered users — run every 2 hours
asyncio.create_task(_loop(auto_engage_service.run_once, interval=7200, label="auto-engage"))
```

---

#### New API Routes in `src/maya/routers/`

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/engagement/discover` | POST | Manually trigger audience discovery |
| `/api/engagement/collaborators` | GET | List top-scored collaborator candidates |
| `/api/engagement/collaborators/{id}/approve` | POST | Approve a DM outreach |
| `/api/engagement/auto-engage/status` | GET | See follow/like counts and rate limit headroom |
| `/api/engagement/discover/preview` | GET | Dry-run — show who would be discovered without acting |

---

## Problem 7 — Maya: Reply Monitoring Only Works on Twitter

### Root Cause
The `ThreadMonitor` class explicitly skips non-Twitter threads:

```python
# src/maya/services/engagement_poster_service.py — line 567
if thread.platform == "twitter":
    new_replies = await self._get_twitter_replies(client, thread)
else:
    continue  # Instagram/Facebook/TikTok: no reply API available
```

Instagram, Facebook, and TikTok do not expose public reply/comment APIs that allow polling third-party posts. This is a platform limitation, not a code bug.

### Fix Options

**Option A (Recommended): Facebook/Instagram — Poll Comments on Owned Posts**
- Meta Graph API allows fetching comments on posts owned by your page
- Can poll `/{post_id}/comments` every 5 minutes for new replies
- Limited to your own page posts — cannot monitor replies on user posts where you commented

**Option B: Threads**
- Threads API supports `GET /threads/{id}/replies` — already has the data model
- Just needs a `_get_threads_replies()` method mirroring the Twitter implementation

**Option C: Accept the Limitation**
- Twitter monitoring is the most valuable (real-time, two-way conversations)
- Instagram/TikTok monitoring is largely impractical via API
- Focus dev effort on the discovery modules instead

---

## Fix Priority Order

| Priority | Fix | Effort | Impact |
|---|---|---|---|
| 1 | Set `SOCIAL_POSTING_DISABLED=false` in Cloud Run (Maya + Shania) | 5 min | Immediately starts posting content |
| 2 | Create Cloud Scheduler job for Labat `/automation/cron` | 10 min | Starts hourly ad optimization |
| 3 | Set `META_WEBHOOK_VERIFY_TOKEN` + configure Meta webhook | 20 min | Leads start flowing into Firestore |
| 4 | Set all social API keys in Cloud Run (Maya) | 30 min | Enables engagement on all platforms |
| 5 | Set LinkedIn keys in Cloud Run (Labat + Shania) | 30 min | Enables LinkedIn posting and analytics |
| 6 | Build audience discovery + auto-engage modules in Maya | ~3 days | Organic follower growth begins |
| 7 | Build collaborator finder + DM outreach in Maya | ~2 days | Partnership pipeline opens |
| 8 | Add Threads reply monitoring to ThreadMonitor | ~4 hours | Closes reply gap on Threads |

---

## Cloud Run Environment Variables — Master Checklist

### `wihy-labat`
```
META_WEBHOOK_VERIFY_TOKEN=<generate with secrets.token_hex(32)>
LINKEDIN_ACCESS_TOKEN=<from LinkedIn Developer Portal>
LINKEDIN_ORG_ID=<numeric org id>
```

### `wihy-maya`
```
SOCIAL_POSTING_DISABLED=false
SOCIAL_POSTING_LAUNCH_MODE=true        # optional, 2x posts + launch messaging
TWITTER_API_KEY=<from developer.twitter.com>
TWITTER_API_SECRET=<from developer.twitter.com>
TWITTER_ACCESS_TOKEN=<from developer.twitter.com>
TWITTER_ACCESS_TOKEN_SECRET=<from developer.twitter.com>
TWITTER_BOT_USERNAME=wihyhealthbot
INSTAGRAM_ACCESS_TOKEN=<long-lived page token>
FACEBOOK_ACCESS_TOKEN=<page token>
THREADS_ACCESS_TOKEN=<Threads API token>
TIKTOK_ACCESS_TOKEN=<from developers.tiktok.com>
```

### `wihy-shania`
```
SOCIAL_POSTING_DISABLED=false
LINKEDIN_ACCESS_TOKEN=<from LinkedIn Developer Portal>
LINKEDIN_ORG_ID=<numeric org id>
```
