"""
LinkedIn Integration Setup Guide

This guide explains how to set up LinkedIn OAuth integration for LABAT (analytics/reporting)
and Shania (posting/scheduling).
"""

# LinkedIn Integration for LABAT & Shania
## Overview

**LABAT (Analytics & Reporting)**
- Route: `/api/labat/linkedin/*`
- Purpose: Report on LinkedIn post performance, organization insights, engagement trends
- Auth: `X-Admin-Token` (internal service-to-service)
- Endpoints:
  - `GET /api/labat/linkedin/insights` — Organization insights
  - `GET /api/labat/linkedin/posts/stats` — Posts with stats
  - `GET /api/labat/linkedin/posts/{id}/stats` — Single post stats
  - `GET /api/labat/linkedin/trends` — Engagement trends
  - `GET /api/labat/linkedin/followers` — Follower count

**Shania (Posting & Scheduling)**
- Route: `/api/engagement/linkedin/*`
- Purpose: Create, schedule, update, delete LinkedIn posts
- Auth: `X-Admin-Token` (internal service-to-service)
- Endpoints:
  - `POST /api/engagement/linkedin/posts` — Create/schedule post
  - `PATCH /api/engagement/linkedin/posts/{id}` — Update post
  - `DELETE /api/engagement/linkedin/posts/{id}` — Delete post
  - `GET /api/engagement/linkedin/posts` — List posts
  - `GET /api/engagement/linkedin/posts/{id}` — Get post metadata
  - `GET /api/engagement/linkedin/posts/{id}/stats` — Get post stats

## Setup Steps

### 1. Register LinkedIn OAuth App

1. Go to https://www.linkedin.com/developers/apps
2. Click "Create app"
3. Fill in:
   - App name: "WIHY ML" (or similar)
   - LinkedIn Page: Select WIHY's company page
   - App logo: Upload WIHY logo
   - Legal agreement: Accept
4. Click "Create app"

### 2. Generate Access Token

From your app's "Auth" tab in the LinkedIn Developer Portal:
1. Request the required scopes: `w_organization_social`, `r_organization_social`
2. Click "Generate access token" (valid for 60 days)
3. Copy the token

### 3. Store in GCP Secret Manager

```bash
# One-time: create the secret
echo -n "YOUR_ACCESS_TOKEN" | gcloud secrets create linkedin-access-token --data-file=- --project=wihy-ai
```

`LINKEDIN_ORG_ID` is set directly in cloudbuild env vars (currently `111401973`).

### 4. Environment Variables

Only two values needed:

```bash
# Access token (from Developer Portal — stored in Secret Manager)
LINKEDIN_ACCESS_TOKEN=<from Developer Portal>

# Organization ID (set in cloudbuild env vars, not a secret)
LINKEDIN_ORG_ID=111401973

# Optional: Adjust timeouts
LINKEDIN_API_TIMEOUT=30
LINKEDIN_RATE_LIMIT_PER_HOUR=280  # LinkedIn's limit is 300/hour
```

### 5. Deploy

```bash
# Deploy Shania (includes LinkedIn posting)
gcloud builds submit --config cloudbuild.shania.yaml

# Deploy LABAT (includes LinkedIn analytics)
gcloud builds submit --config cloudbuild.labat.yaml
```

### 6. Update Firebase Routing (if needed)

If you want public routes for LinkedIn, add to `firebase.json`:

```json
{
  "hosting": {
    "rewrites": [
      {
        "source": "/api/labat/linkedin/**",
        "destination": "https://wihy-labat-xxxx.run.app"
      },
      {
        "source": "/api/engagement/linkedin/**",
        "destination": "https://wihy-shania-xxxx.run.app"
      }
    ]
  }
}
```

Then deploy:
```bash
firebase deploy --only hosting
```

## Usage Examples

### Create a LinkedIn Post (Shania)

```bash
curl -X POST https://ml.wihy.ai/api/engagement/linkedin/posts \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check out our new blog on nutrition and plant-based eating!",
    "schedule_hours_from_now": null
  }'
```

Response:
```json
{
  "id": "urn:li:post:7245937859...",
  "message_preview": "Check out our new blog on nutrition and plant-based eating!",
  "scheduled": false
}
```

### Schedule a LinkedIn Post

```bash
curl -X POST https://ml.wihy.ai/api/engagement/linkedin/posts \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "New fitness guide available now!",
    "schedule_hours_from_now": 24
  }'
```

### Get LinkedIn Analytics (LABAT)

```bash
curl -X GET https://ml.wihy.ai/api/labat/linkedin/insights \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

Response:
```json
{
  "organization_name": "WIHY",
  "follower_count": 1250,
  "industry": "Health & Wellness",
  "company_size": "50-200"
}
```

### Get Recent Posts with Stats

```bash
curl -X GET "https://ml.wihy.ai/api/labat/linkedin/posts/stats?limit=10" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

Response:
```json
{
  "posts_count": 10,
  "posts": [
    {
      "id": "urn:li:post:7245937859...",
      "text_preview": "Check out our new blog...",
      "impressions": 450,
      "clicks": 23,
      "comments": 5,
      "shares": 2,
      "likes": 15,
      "engagement": 22
    }
  ],
  "summary": {
    "total_impressions": 4500,
    "total_engagement": 220,
    "avg_engagement_rate": 4.89
  }
}
```

### Get Engagement Trends

```bash
curl -X GET "https://ml.wihy.ai/api/labat/linkedin/trends?days=7" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

Response:
```json
{
  "period_days": 7,
  "daily_stats": {
    "2026-03-24": {
      "impressions": 650,
      "clicks": 32,
      "comments": 8,
      "shares": 3,
      "likes": 25
    },
    "2026-03-25": {
      "impressions": 720,
      "clicks": 38,
      "comments": 10,
      "shares": 4,
      "likes": 30
    }
  }
}
```

## Error Handling

### Common Errors

**401 Unauthorized — Invalid Access Token**
- Refresh `LINKEDIN_ACCESS_TOKEN` via OAuth flow
- Ensure token scope includes `w_organization_social` (for posting) and `r_organization_social` (for reading)

**400 Bad Request — Invalid Organization ID**
- Verify `LINKEDIN_ORG_ID` format: should be numeric company ID, not display name
- Use LinkedIn API to fetch: `GET https://api.linkedin.com/v2/organizations`

**429 Too Many Requests — Rate Limit Exceeded**
- Standard tier: 300 calls/hour
- Implement backoff/retry logic
- Queue requests if spike expected

**403 Forbidden — Missing Permission**
- Ensure OAuth app has necessary permissions:
  - `w_organization_social` — Write posts to organization page
  - `r_organization_social` — Read organization posts
  - `w_member_social` — Write posts as member
  - `r_member_social` — Read member posts

## Integration with Blog System

When publishing blog posts, automatically cross-post to LinkedIn:

```python
from src.labat.services.linkedin_posting_service import create_post

async def publish_blog_post(blog_post):
    blog_post.save()
    
    # Cross-post to LinkedIn
    message = f"{blog_post.title}\n\n{blog_post.excerpt}\n\nRead more: {blog_post.canonical_url}"
    await create_post(message)
```

Or schedule 24 hours later:
```python
async def publish_blog_post(blog_post):
    blog_post.save()
    
    from src.labat.services.linkedin_posting_service import schedule_post
    message = f"{blog_post.title}\n\n{blog_post.excerpt}\n\nRead more: {blog_post.canonical_url}"
    await schedule_post(message, hours_from_now=24)
```

## Integration with ALEX

ALEX keyword discovery can feed LinkedIn posting strategy:

```python
# In ALEX keyword discovery cycle
async def process_discovered_keywords():
    keywords = await get_discovered_keywords()
    
    for keyword in keywords:
        # Generate LinkedIn post for high-priority keywords
        if keyword['priority_score'] > 0.8:
            message = f"New insight: {keyword['topic']}\n\nRead our latest research..."
            await schedule_post(message, hours_from_now=2)
```

## Troubleshooting

### LinkedIn API Returns 400 "Invalid POST URN"

**Issue**: POST payload with incorrect `actor` field format.

**Solution**: Ensure `actor` is formatted as:
- Organization: `urn:li:organization:12345`
- Person: `urn:li:person:ACoABC1D2E3F4`

Not: `12345` or `linkedin:org:12345`

### Posts Not Appearing

**Issue**: Draft posts scheduled but not published, or no lifecycle state tracked.

**Solution**: 
- Check `lifecycleState` in response (should be `DRAFT` if scheduled, `PUBLISHED` if live)
- Verify token scope includes `w_organization_social`
- Ensure organization ID is correct

### Rate Limit Throttling

**Issue**: 429 responses after many requests.

**Solution**:
- LinkedIn Standard access: 300 calls/hour
- Use Cloud Tasks or job queue to batch operations
- Implement exponential backoff retry
- Monitor with `/api/labat/linkedin/insights` — check `calls_in_window()`

## Next Steps

1. **Configure OAuth**: Complete steps 1-4 above
2. **Test Posting**: Use `POST /api/engagement/linkedin/posts` with sample message
3. **Test Analytics**: Use `GET /api/labat/linkedin/insights` to verify read access
4. **Set up Blog Cross-Posting**: Integrate with blog publishing workflow
5. **Monitor Engagement**: Schedule daily analytics reports via `/api/labat/linkedin/trends`
6. **Optimize Content**: Use engagement data to refine WIHY's LinkedIn strategy

## References

- LinkedIn Official API Docs: https://learn.microsoft.com/en-us/linkedin/shared/api-reference/api-reference?context=linkedin%2Fcontext
- LinkedIn OAuth: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication?context=linkedin%2Fcontext
- V2 API Scopes: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication?context=linkedin%2Fcontext#scopes
