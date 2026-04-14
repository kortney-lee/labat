# WIHY Engagement API

The `wihy-engagement` service generates and posts WIHY-toned, evidence-backed comments to posts discovered by the lead-service. It uses the WIHY RAG knowledge base to produce personalized, research-grounded responses.

**Service URL:** `https://wihy-engagement-12913076533.us-central1.run.app`

---

## Authentication

All endpoints except `/health` require an `X-Admin-Token` header using the same `INTERNAL_ADMIN_TOKEN` shared with the lead-service.

```
X-Admin-Token: <INTERNAL_ADMIN_TOKEN>
```

---

## Supported Platforms

| Platform | Posts comments | Thread monitor (auto-reply) | Credential required |
|---|---|---|---|
| `twitter` | ✅ | ✅ polls every 5 min, auto-replies | `twitter-api-key/secret/access-token/access-token-secret` |
| `instagram` | ✅ | ❌ no public reply-read API | `INSTAGRAM_ACCESS_TOKEN` |
| `facebook` | ✅ | ❌ | `FACEBOOK_ACCESS_TOKEN` |
| `tiktok` | ✅ | ❌ | `TIKTOK_ACCESS_TOKEN` |
| `generic` | Content only | ❌ | — |

If a platform's credentials are not configured the request returns `success: false, error: "<Platform> not configured"`. All credentials default to empty strings — the service always starts.

---

## Endpoints

### `POST /api/engagement/engage`

Generate a WIHY comment and post it to the lead's post. For Twitter, the posted comment is automatically registered with the thread monitor to watch for replies.

**Request body:**

```json
{
  "platform":               "twitter",
  "action":                 "comment",
  "target_id":              "1234567890123456789",
  "post_content":           "I've been struggling with my diet for months and nothing works.",
  "topic":                  "healthy eating weight loss",
  "lead_id":                "uuid-from-leads-table",
  "author":                 "username_of_original_poster",
  "conversation_tweet_id":  "1234567890123456789",
  "dry_run":                false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | ✅ | `twitter` \| `instagram` \| `facebook` \| `tiktok` \| `generic` |
| `action` | string | | `comment` (reply to a post) or `reply` (reply to a comment). Default: `comment` |
| `target_id` | string | ✅ | Platform ID to reply to. See [Target IDs](#target-ids) |
| `post_content` | string | | Original post text — used to personalize the WIHY response |
| `topic` | string | ✅ | Clean health keywords for WIHY RAG query (see [Topic Tips](#topic-tips)) |
| `lead_id` | string | | Lead UUID from your `leads` table — passed through for tracking |
| `author` | string | | Original poster's username (for logging) |
| `conversation_tweet_id` | string | | Twitter root tweet ID — improves thread monitor accuracy. If omitted, `target_id` is used |
| `dry_run` | bool | | If `true`, generates content but does **not** post or register with monitor. Default: `false` |

**Response:**

```json
{
  "success":          true,
  "platform":         "twitter",
  "action":           "comment",
  "content":          "The research on this is nuanced...",
  "platform_post_id": "9876543210",
  "lead_id":          "uuid-from-leads-table",
  "dry_run":          false,
  "error":            null
}
```

Store `platform_post_id` in your `outreach_log` table to prevent re-engaging the same post.

**Error cases:**

| `success` | `error` | Meaning |
|-----------|---------|---------|
| `false` | `"Twitter not configured"` | Twitter secrets not in Cloud Run |
| `false` | `"Instagram not configured"` | Instagram token not in Cloud Run |
| `false` | `"Facebook not configured"` | Facebook token not in Cloud Run |
| `false` | `"TikTok not configured"` | TikTok token not in Cloud Run |
| `false` | `"WIHY returned empty response"` | WIHY `/ask` returned nothing usable |

---

### `POST /api/engagement/engage/batch`

Engage up to 10 leads in a single call. Each lead is processed independently — partial failures don't block others.

**Request body:**

```json
{
  "leads": [
    {
      "platform":              "twitter",
      "target_id":             "1234567890123456789",
      "post_content":          "Any app recommendations for tracking macros?",
      "topic":                 "macro tracking nutrition app",
      "lead_id":               "lead-uuid-1",
      "conversation_tweet_id": "1234567890123456789"
    },
    {
      "platform":     "instagram",
      "target_id":    "17841400123456789",
      "post_content": "Struggling with energy after workouts",
      "topic":        "post-workout recovery nutrition",
      "lead_id":      "lead-uuid-2"
    },
    {
      "platform":     "facebook",
      "target_id":    "123456789012345_987654321098765",
      "post_content": "Trying to eat healthier but meal prep feels overwhelming",
      "topic":        "meal prep healthy eating",
      "lead_id":      "lead-uuid-3"
    }
  ]
}
```

**Response:**

```json
{
  "total":     3,
  "succeeded": 3,
  "failed":    0,
  "results": [
    { "success": true, "platform": "twitter",   "platform_post_id": "9876543210",        "content": "...", "lead_id": "lead-uuid-1", "dry_run": false, "error": null },
    { "success": true, "platform": "instagram", "platform_post_id": "17841400987654321", "content": "...", "lead_id": "lead-uuid-2", "dry_run": false, "error": null },
    { "success": true, "platform": "facebook",  "platform_post_id": "123456_789012",     "content": "...", "lead_id": "lead-uuid-3", "dry_run": false, "error": null }
  ]
}
```

---

### `GET /api/engagement/preview`

Generate a comment without posting — useful for QA.

**Query params:** `platform`, `topic`, `post_content` (optional)

```
GET /api/engagement/preview?platform=twitter&topic=intermittent+fasting&post_content=tried+IF+for+a+month
X-Admin-Token: <token>
```

**Response:**

```json
{
  "platform": "twitter",
  "topic":    "intermittent fasting",
  "content":  "IF research shows real results, but timing matters…\n\n— WIHY health research | wihy.ai",
  "success":  true,
  "error":    null
}
```

---

### `GET /api/engagement/monitor`

Thread monitor statistics. Requires `X-Admin-Token`.

```json
{
  "running":               true,
  "tracked_threads":       12,
  "total_auto_replies":    4,
  "last_poll":             "2026-03-07T01:29:03.359774+00:00",
  "poll_interval_seconds": 300,
  "max_depth":             2
}
```

| Field | Description |
|-------|-------------|
| `running` | Whether the background poll loop is active |
| `tracked_threads` | Twitter comments currently being watched for replies |
| `total_auto_replies` | Replies auto-posted since last service restart |
| `last_poll` | ISO timestamp of last platform poll |
| `poll_interval_seconds` | Seconds between polls (default: 300) |
| `max_depth` | Max reply chain depth before monitor stops replying (default: 2) |

---

### `GET /health` and `GET /api/engagement/health`

Liveness check — no auth required. Both include monitor status.

```json
{
  "status":  "ok",
  "service": "wihy-engagement",
  "monitor": {
    "running": true,
    "tracked_threads": 12,
    "total_auto_replies": 4,
    "last_poll": "2026-03-07T01:29:03+00:00",
    "poll_interval_seconds": 300,
    "max_depth": 2
  }
}
```

---

## Thread Monitor

When a comment is successfully posted to **Twitter**, the service automatically registers it with a background thread monitor. The monitor:

1. Polls every 5 minutes for new replies to any comment WIHY has posted
2. For each new reply, queries WIHY `/ask` to generate a response and posts it
3. Registers the new auto-reply for monitoring as well (up to `THREAD_MAX_DEPTH` levels)
4. Prunes threads older than 7 days automatically

**Twitter** — polls `GET /2/tweets/search/recent?query=in_reply_to_tweet_id:{our_tweet_id}`

> Auto-replies stop at depth 2 by default (our comment → their reply → our reply → stops). Configure with `THREAD_MAX_DEPTH`.

**To enable thread monitoring, pass `conversation_tweet_id` in your engage request:**

```json
{
  "conversation_tweet_id": "1234567890123456789"
}
```

---

## Target IDs

### Twitter

Pass the tweet ID string as-is from the Twitter API. Pass the same value as `conversation_tweet_id`:

```json
{ "target_id": "1234567890123456789", "conversation_tweet_id": "1234567890123456789" }
```

### Instagram

Pass the **media object ID** (numeric string from the Graph API), not the URL shortcode:
```
"17841400123456789"
```
Get it from: `GET https://graph.facebook.com/v19.0/me/media?access_token=…`

### Facebook

Pass the **post or comment object ID**. To reply to a specific comment, pass its ID:
```
"123456789012345_987654321098765"
```

### TikTok

Pass the **video ID** from the TikTok API:
```
"7234567890123456789"
```

---

## Comment Formats by Platform

### Twitter (≤270 chars)

```
IF research shows real results, but timing matters — breaking a fast with 
high-glycemic foods can spike insulin worse than eating continuously…

— WIHY health research | wihy.ai
```

### Instagram / Facebook (plain text, no markdown, hashtags)

```
The research here is more nuanced than mainstream advice suggests. A 2024 
meta-analysis found that time-restricted eating (16:8 IF) produces comparable 
weight loss to continuous calorie restriction.

Sources:
• Time-restricted eating and metabolic outcomes – ncbi.nlm.nih.gov/pmc/articles/PMC11136966/

Powered by WIHY – evidence-based health | wihy.ai
#healthresearch #nutrition #wellness #WIHY
```

### TikTok (≤150 chars, plain text)

```
IF works, but timing matters — high-glycemic meals right after fasting spike insulin harder. The 2024 data is eye-opening via wihy.ai
```

### Generic (plain text, up to 2000 chars)

```
The research here is more nuanced than mainstream advice suggests. A 2024 
meta-analysis found that time-restricted eating (16:8 IF) produces comparable 
weight loss to continuous calorie restriction.

Sources:
• Time-restricted eating and metabolic outcomes – ncbi.nlm.nih.gov/pmc/articles/PMC11136966/

Powered by WIHY – evidence-based health | wihy.ai
```

---

## Topic Tips

Use clean health keywords — strip platform noise, hashtags, and usernames.

| Original post | Good `topic` |
|---|---|
| `"#mealprep anyone have ideas for high protein lunches?"` | `"high protein meal prep lunch"` |
| `"@user I've been trying IF but always feel tired"` | `"intermittent fasting fatigue energy"` |
| `"Any recs for gut health? My digestion has been rough"` | `"gut health digestion probiotics"` |
| `"Does creatine actually work or is it hype?"` | `"creatine muscle performance"` |
| `"Trying to lose weight but doctor said cholesterol is high"` | `"weight loss cholesterol diet"` |

Use the same keyword extraction logic as your lead scorer's `keyword` component.

---

## Integration Pattern

```javascript
const WIHY_ENGAGEMENT_URL   = process.env.WIHY_ENGAGEMENT_URL;   // https://wihy-engagement-...run.app
const WIHY_ENGAGEMENT_TOKEN = process.env.WIHY_ENGAGEMENT_TOKEN; // same as INTERNAL_ADMIN_TOKEN

async function engageLeadsWithWIHY(qualifiedLeads) {
  const engageable = qualifiedLeads.filter(lead =>
    lead.platform_post_id &&
    lead.status !== 'contacted' &&
    ['twitter', 'instagram', 'facebook', 'tiktok'].includes(lead.platform)
  );
  if (engageable.length === 0) return;

  for (const batch of chunk(engageable, 10)) {
    const payload = {
      leads: batch.map(lead => ({
        platform:              lead.platform,
        target_id:             lead.platform_post_id,
        post_content:          lead.content?.substring(0, 500) || '',
        topic:                 lead.matched_keywords?.join(' ') || lead.intent_signals?.[0] || 'health wellness',
        lead_id:               lead.id,
        author:                lead.username,
        conversation_tweet_id: lead.twitter_tweet_id,        // Twitter: for thread monitoring
        dry_run:               false,
      }))
    };

    const res = await fetch(`${WIHY_ENGAGEMENT_URL}/api/engagement/engage/batch`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Token': WIHY_ENGAGEMENT_TOKEN },
      body:    JSON.stringify(payload),
    });
    const data = await res.json();

    for (const result of data.results) {
      if (result.success) {
        await db.query(`
          INSERT INTO outreach_log (lead_id, channel, status, external_id, message_content)
          VALUES ($1, $2, 'sent', $3, $4)
        `, [result.lead_id, result.platform, result.platform_post_id, result.content]);

        await db.query(
          `UPDATE leads SET status = 'contacted', updated_at = NOW() WHERE id = $1`,
          [result.lead_id]
        );
      } else {
        console.warn(`WIHY engage failed for lead ${result.lead_id}: ${result.error}`);
      }
    }
    await sleep(5000); // respect rate limits between batches
  }
}
```

---

## Environment Variables

### lead-service `.env`

```bash
WIHY_ENGAGEMENT_URL=https://wihy-engagement-12913076533.us-central1.run.app
WIHY_ENGAGEMENT_TOKEN=<same value as INTERNAL_ADMIN_TOKEN>
```

### wihy-engagement Cloud Run secrets

Add with `echo -n "VALUE" | gcloud secrets create <name> --data-file=- --project=wihy-ai`, then uncomment in `cloudbuild.engagement.yaml` and redeploy.

| Secret name | Platform | Required for |
|---|---|---|
| `twitter-api-key` | Twitter | Posting + thread monitoring |
| `twitter-api-secret` | Twitter | Posting + thread monitoring |
| `twitter-access-token` | Twitter | Posting + thread monitoring |
| `twitter-access-token-secret` | Twitter | Posting + thread monitoring |
| `twitter-bot-username` | Twitter | Prevents monitor replying to itself |
| `instagram-access-token` | Instagram | Posting (long-lived token, `instagram_manage_comments` scope) |
| `facebook-access-token` | Facebook | Posting (page token, `pages_manage_engagement` scope) |
| `tiktok-access-token` | TikTok | Posting (`tt.user.comment` scope) |

### Optional Cloud Run env vars

```bash
THREAD_POLL_INTERVAL=300   # Seconds between reply polls (default: 300 = 5 min)
THREAD_MAX_DEPTH=2          # Max auto-reply chain depth (default: 2)
```
