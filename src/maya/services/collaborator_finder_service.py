"""
maya/services/collaborator_finder_service.py — Find potential collaborators in health/nutrition niche.

Searches Twitter for creators and accounts in the health/wellness space with
meaningful audiences (5K–500K followers). Scores them by engagement ratio and
content relevance, stores candidates in Firestore, and emails a report to
kortney@wihy.ai after each cycle.

Runs every 24 hours via maya_app.py background loop.
Firestore path: collaborators/{brand}/candidates/{user_id}

Required env vars:
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
  GCP_PROJECT          — defaults to "wihy-ai"
  COLLAB_MIN_FOLLOWERS — minimum followers to qualify (default 5000)
  COLLAB_MAX_FOLLOWERS — maximum followers to qualify (default 500000)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.maya.services.engagement_poster_service import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    _twitter_oauth1_header,
)

logger = logging.getLogger("maya.collaborator_finder")

GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")
COLLAB_MIN_FOLLOWERS = int(os.getenv("COLLAB_MIN_FOLLOWERS", "5000"))
COLLAB_MAX_FOLLOWERS = int(os.getenv("COLLAB_MAX_FOLLOWERS", "500000"))

# Search queries per brand — finds creators already talking about these topics
BRAND_SEARCH_QUERIES: Dict[str, List[str]] = {
    "wihy": [
        "healthy eating tips", "nutrition advice", "meal prep ideas",
        "weight loss nutrition", "gut health tips",
    ],
    "vowels": [
        "evidence based nutrition", "nutrition science", "dietitian advice",
        "metabolic health", "blood sugar control",
    ],
    "communitygroceries": [
        "budget meal prep", "affordable healthy food", "grocery tips",
        "cheap healthy meals", "frugal eating",
    ],
    "childrennutrition": [
        "kids nutrition", "healthy school lunch", "children diet",
        "family nutrition tips", "picky eater help",
    ],
}


def _get_firestore():
    from google.cloud import firestore
    return firestore.AsyncClient(project=GCP_PROJECT)


def _score_collaborator(followers: int, following: int, tweet_count: int, listed: int) -> float:
    """Score collaborator fitness 0–100. Returns 0 if outside follower range."""
    if followers < COLLAB_MIN_FOLLOWERS or followers > COLLAB_MAX_FOLLOWERS:
        return 0.0
    ratio = min(followers / max(following, 1), 20.0)
    authority = min(listed / 100, 10.0)
    activity = min(tweet_count / 1000, 5.0)
    return round(ratio * 4 + authority * 4 + activity * 2, 2)


async def _search_twitter_for_collaborators(
    client: httpx.AsyncClient,
    query: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Search recent tweets for a query. Returns unique authors with follower data."""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        return []

    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": f"{query} lang:en -is:retweet",
        "tweet.fields": "author_id",
        "user.fields": "id,username,name,description,public_metrics,verified,url",
        "expansions": "author_id",
        "max_results": str(max(10, min(max_results, 100))),
    }

    try:
        auth_header = _twitter_oauth1_header("GET", url, params)
        r = await client.get(
            url,
            headers={"Authorization": auth_header},
            params=params,
            timeout=20,
        )
        data = r.json()
        return data.get("includes", {}).get("users", [])
    except Exception as e:
        logger.error("Twitter collaborator search error (%r): %s", query, e)
        return []


async def run_once(brand: str = "all") -> Dict[str, Any]:
    """
    Run one collaborator discovery cycle. Stores candidates in Firestore
    and emails a report. Returns summary.
    """
    brands = list(BRAND_SEARCH_QUERIES.keys()) if brand == "all" else [brand]
    total_new = 0
    top_candidates: List[Dict[str, Any]] = []
    errors: List[str] = []

    db = _get_firestore()

    async with httpx.AsyncClient() as client:
        for b in brands:
            for query in BRAND_SEARCH_QUERIES.get(b, []):
                try:
                    users = await _search_twitter_for_collaborators(client, query)
                    for u in users:
                        metrics = u.get("public_metrics", {})
                        followers = metrics.get("followers_count", 0)
                        following = metrics.get("following_count", 0)
                        tweet_count = metrics.get("tweet_count", 0)
                        listed = metrics.get("listed_count", 0)
                        score = _score_collaborator(followers, following, tweet_count, listed)
                        if score <= 0:
                            continue

                        flat = {
                            "platform": "twitter",
                            "brand": b,
                            "discovery_query": query,
                            "platform_user_id": u.get("id"),
                            "username": u.get("username", ""),
                            "name": u.get("name", ""),
                            "description": u.get("description", ""),
                            "url": u.get("url", ""),
                            "followers_count": followers,
                            "following_count": following,
                            "tweet_count": tweet_count,
                            "listed_count": listed,
                            "verified": u.get("verified", False),
                            "score": score,
                        }

                        ref = (
                            db.collection("collaborators")
                            .document(b)
                            .collection("candidates")
                            .document(str(u.get("id")))
                        )
                        existing = await ref.get()
                        if not existing.exists:
                            await ref.set({
                                **flat,
                                "status": "pending",
                                "outreach_approved": False,
                                "discovered_at": datetime.now(timezone.utc).isoformat(),
                            })
                            total_new += 1
                        else:
                            await ref.update({
                                "score": score,
                                "last_seen": datetime.now(timezone.utc).isoformat(),
                            })

                        top_candidates.append({
                            "brand": b,
                            "username": flat["username"],
                            "followers": followers,
                            "score": score,
                            "description": flat["description"][:120],
                        })

                    await asyncio.sleep(1)

                except Exception as e:
                    msg = f"Collaborator search error brand={b} query={query!r}: {e}"
                    logger.error(msg)
                    errors.append(msg)

    if top_candidates:
        top_candidates.sort(key=lambda x: x["score"], reverse=True)
        await _send_report(top_candidates[:20], total_new)

    result = {
        "brands_scanned": brands,
        "total_new": total_new,
        "top_candidates": top_candidates[:10],
        "errors": errors,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Collaborator discovery complete: %s", result)
    return result


def _candidate_card(c: Dict[str, Any], approve_base_url: str, admin_token: str) -> str:
    """Build one HTML card for a collaborator candidate."""
    username    = c.get("username", "")
    name        = c.get("name", username)
    brand       = c.get("brand", "")
    followers   = c.get("followers_count", 0)
    description = (c.get("description") or "No bio available.")[:180]
    score       = c.get("score", 0)
    user_id     = str(c.get("platform_user_id", ""))
    url         = c.get("url", "")
    tweet_count = c.get("tweet_count", 0)

    approve_url = (
        f"{approve_base_url}/api/engagement/collaborators/approve"
        f"?user_id={user_id}&brand={brand}&token={admin_token}"
    )
    twitter_url = f"https://x.com/{username}"

    brand_colors = {
        "wihy": "#2563eb",
        "vowels": "#7c3aed",
        "communitygroceries": "#16a34a",
        "childrennutrition": "#d97706",
    }
    brand_color = brand_colors.get(brand, "#6b7280")
    brand_label = {
        "wihy": "WIHY / Eden",
        "vowels": "Vowels",
        "communitygroceries": "Community Groceries / Cora",
        "childrennutrition": "Children Nutrition",
    }.get(brand, brand.title())

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0"
           style="margin-bottom:16px;border:1px solid #e2e8f0;border-radius:10px;
                  overflow:hidden;background:#fff;">
      <tr>
        <td style="padding:18px 20px;">
          <!-- Name row -->
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <a href="{twitter_url}" style="color:#0f172a;text-decoration:none;
                   font-size:16px;font-weight:700;">@{username}</a>
                <span style="color:#64748b;font-size:14px;"> &middot; {name}</span>
              </td>
              <td align="right">
                <span style="display:inline-block;padding:3px 10px;border-radius:20px;
                      background:{brand_color}18;color:{brand_color};
                      font-size:11px;font-weight:700;">{brand_label}</span>
              </td>
            </tr>
          </table>
          <!-- Stats row -->
          <table cellpadding="0" cellspacing="0" style="margin:10px 0;">
            <tr>
              <td style="padding-right:20px;">
                <span style="color:#64748b;font-size:12px;">Followers</span><br/>
                <span style="color:#0f172a;font-size:15px;font-weight:700;">{followers:,}</span>
              </td>
              <td style="padding-right:20px;">
                <span style="color:#64748b;font-size:12px;">Tweets</span><br/>
                <span style="color:#0f172a;font-size:15px;font-weight:700;">{tweet_count:,}</span>
              </td>
              <td>
                <span style="color:#64748b;font-size:12px;">Score</span><br/>
                <span style="color:#0f172a;font-size:15px;font-weight:700;">{score}</span>
              </td>
            </tr>
          </table>
          <!-- Bio -->
          <p style="margin:0 0 14px;color:#475569;font-size:13px;line-height:1.6;">
            {description}
          </p>
          <!-- Buttons -->
          <table cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding-right:10px;">
                <a href="{approve_url}"
                   style="display:inline-block;padding:9px 20px;background:#16a34a;
                          color:#fff;font-size:13px;font-weight:700;border-radius:6px;
                          text-decoration:none;">✅ Approve for Outreach</a>
              </td>
              <td>
                <a href="{twitter_url}"
                   style="display:inline-block;padding:9px 20px;background:#f1f5f9;
                          color:#334155;font-size:13px;font-weight:600;border-radius:6px;
                          text-decoration:none;">View Profile →</a>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>"""


async def _send_report(candidates: List[Dict[str, Any]], total_new: int) -> None:
    """Send a rich HTML collaborator report to kortney@wihy.ai via SendGrid."""
    import httpx

    sendgrid_key = os.getenv("SENDGRID_API_KEY", "").strip()
    admin_token  = os.getenv("INTERNAL_ADMIN_TOKEN", "").strip()
    from_email   = os.getenv("NOTIFICATION_FROM_EMAIL", "noreply@wihy.ai")
    to_email     = os.getenv("NOTIFICATION_TO_EMAIL", "kortney@wihy.ai")
    approve_base = "https://maya.wihy.ai"

    if not sendgrid_key:
        logger.warning("SENDGRID_API_KEY not set — collaborator report skipped")
        return

    cards_html = "".join(
        _candidate_card(c, approve_base, admin_token) for c in candidates
    )

    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f1f5f9;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 16px;background:#f1f5f9;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0"
       style="max-width:620px;width:100%;background:#fff;border-radius:12px;
              overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,.07);">

  <!-- Header -->
  <tr><td style="padding:20px 32px;background:#0f172a;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td><span style="color:#fff;font-size:16px;font-weight:700;">WIHY</span>
          <span style="color:#64748b;font-size:14px;"> · Maya Collaborator Report</span></td>
      <td align="right"><span style="color:#94a3b8;font-size:12px;">{timestamp}</span></td>
    </tr></table>
  </td></tr>

  <!-- Summary banner -->
  <tr><td style="padding:20px 32px;background:#eff6ff;border-bottom:1px solid #e2e8f0;">
    <h1 style="margin:0 0 4px;color:#1e40af;font-size:22px;font-weight:700;">
      🤝 {total_new} New Collaborator Candidate{"s" if total_new != 1 else ""} Found
    </h1>
    <p style="margin:0;color:#3730a3;font-size:14px;">
      Review each candidate below and click <strong>Approve for Outreach</strong>
      to queue them for a personalized DM from Maya.
    </p>
  </td></tr>

  <!-- Cards -->
  <tr><td style="padding:24px 32px;">
    {cards_html}
    <p style="margin:20px 0 0;color:#94a3b8;font-size:12px;text-align:center;">
      Approvals are one-click — no login required. Links expire after 30 days.
    </p>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;">
    <span style="color:#94a3b8;font-size:11px;">
      Sent by Maya · WIHY Agent System · Do not reply
    </span>
  </td></tr>

</table></td></tr></table></body></html>"""

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "Maya · WIHY Agents"},
        "subject": f"🤝 {total_new} New Collaborator Candidate{'s' if total_new != 1 else ''} — Review & Approve",
        "content": [{"type": "text/html", "value": html}],
        "categories": ["agent-notification", "maya-collaborator-finder", "maya"],
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {sendgrid_key}",
                    "Content-Type": "application/json",
                },
            )
        if r.status_code in (200, 201, 202):
            logger.info("Collaborator report sent to %s (%d candidates)", to_email, len(candidates))
        else:
            logger.error("SendGrid error %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("Failed to send collaborator report: %s", e)
