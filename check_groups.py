"""Check Facebook Groups for all brand Pages — tries multiple API approaches."""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from src.labat.brands import BRAND_PAGE_IDS
from src.labat.config import (
    SHANIA_PAGE_ACCESS_TOKEN,
    META_SYSTEM_USER_TOKEN,
    META_GRAPH_BASE_URL,
    META_BUSINESS_ID,
    SHANIA_LONG_LIVED_USER_TOKEN,
)
import httpx

# Check all possible env tokens
ALL_TOKENS = {}
for env_name in [
    "META_SYSTEM_USER_TOKEN",
    "SHANIA_PAGE_ACCESS_TOKEN",
    "SHANIA_LONG_LIVED_USER_TOKEN",
    "FACEBOOK_ACCESS_TOKEN",
    "META_PAGE_ACCESS_TOKEN",
    "INSTAGRAM_ACCESS_TOKEN",
]:
    val = os.getenv(env_name, "").strip()
    if val:
        ALL_TOKENS[env_name] = val


async def try_endpoint(client, url, params, label):
    """Try an endpoint and print results."""
    try:
        resp = await client.get(url, params=params)
        data = resp.json()
        if resp.status_code == 200:
            items = data.get("data", data)
            if isinstance(items, list) and items:
                print(f"  {label}: {len(items)} results")
                for item in items[:10]:
                    if isinstance(item, dict):
                        print(f"    - {item.get('name', item.get('id', item))}")
                        for k, v in item.items():
                            if k not in ("name", "id"):
                                print(f"      {k}: {v}")
                return items
            elif isinstance(items, dict) and not data.get("error"):
                print(f"  {label}: {items}")
                return items
            else:
                print(f"  {label}: empty")
        else:
            err = data.get("error", {})
            print(f"  {label}: Error {resp.status_code} — {err.get('message', '')[:150]}")
    except Exception as e:
        print(f"  {label}: Exception — {e}")
    return None


async def check_groups():
    print(f"Graph API: {META_GRAPH_BASE_URL}")
    print(f"Tokens available: {list(ALL_TOKENS.keys())}")
    print("=" * 70)

    token = (
        SHANIA_LONG_LIVED_USER_TOKEN
        or SHANIA_PAGE_ACCESS_TOKEN
        or META_SYSTEM_USER_TOKEN
    )

    async with httpx.AsyncClient(timeout=30) as client:

        # Who is /me?
        me = await try_endpoint(
            client,
            f"{META_GRAPH_BASE_URL}/me",
            {"access_token": token, "fields": "id,name"},
            "/me identity",
        )

        # 1) /me/groups — user's groups
        print("\n--- Approach 1: /me/groups ---")
        await try_endpoint(
            client,
            f"{META_GRAPH_BASE_URL}/me/groups",
            {"access_token": token, "fields": "id,name,member_count,privacy,administrator", "limit": "100"},
            "/me/groups",
        )

        # 2) /me/accounts — get all page tokens, then try each
        print("\n--- Approach 2: Per-page token → /me/groups ---")
        accounts_resp = await client.get(
            f"{META_GRAPH_BASE_URL}/me/accounts",
            params={"access_token": token, "fields": "id,name,access_token", "limit": "50"},
        )
        if accounts_resp.status_code == 200:
            pages = accounts_resp.json().get("data", [])
            print(f"  Found {len(pages)} pages")
            for page in pages:
                page_name = page.get("name", "?")
                page_id = page.get("id", "?")
                page_token = page.get("access_token", "")
                print(f"\n  Page: {page_name} ({page_id})")

                if page_token:
                    # Try multiple group-related edges with the page token
                    for edge in ["groups", "linked_page"]:
                        await try_endpoint(
                            client,
                            f"{META_GRAPH_BASE_URL}/{page_id}/{edge}",
                            {"access_token": page_token, "fields": "id,name,privacy,member_count", "limit": "100"},
                            f"  /{page_id}/{edge}",
                        )

        # 3) Try user_managed_groups if the token is a user token
        print("\n--- Approach 3: /me/managed_groups ---")
        me_id = me.get("id") if isinstance(me, dict) else None
        if me_id:
            await try_endpoint(
                client,
                f"{META_GRAPH_BASE_URL}/{me_id}/groups",
                {"access_token": token, "fields": "id,name,member_count,privacy,administrator", "admin_only": "false", "limit": "100"},
                f"/{me_id}/groups",
            )

        # 4) Check all permissions to see what we CAN do
        print("\n--- Approach 4: Full permissions list ---")
        perms_resp = await client.get(
            f"{META_GRAPH_BASE_URL}/me/permissions",
            params={"access_token": token},
        )
        if perms_resp.status_code == 200:
            perms = perms_resp.json().get("data", [])
            granted = [p["permission"] for p in perms if p.get("status") == "granted"]
            declined = [p["permission"] for p in perms if p.get("status") == "declined"]
            print(f"  Granted ({len(granted)}): {', '.join(sorted(granted))}")
            if declined:
                print(f"  Declined ({len(declined)}): {', '.join(sorted(declined))}")

        # 5) Use PAGE tokens to read feeds and find group activity
        print("\n--- Approach 5: Page token → feed + published_posts for group refs ---")
        if accounts_resp.status_code == 200:
            pages = accounts_resp.json().get("data", [])
            for page in pages:
                page_name = page.get("name", "?")
                page_id = page.get("id", "?")
                page_token = page.get("access_token", "")
                if not page_token:
                    continue
                print(f"\n  {page_name} ({page_id}):")

                # published_posts with page token
                posts = await try_endpoint(
                    client,
                    f"{META_GRAPH_BASE_URL}/{page_id}/published_posts",
                    {"access_token": page_token, "fields": "id,message,story,to,created_time,status_type", "limit": "20"},
                    f"  published_posts",
                )
                if posts and isinstance(posts, list):
                    for post in posts:
                        story = post.get("story", "")
                        to_data = post.get("to", {}).get("data", [])
                        msg = (post.get("message") or "")[:80]
                        if "group" in story.lower() or to_data:
                            print(f"    ** GROUP REF: story={story}, to={to_data}, msg={msg}")

                # Also try the feed
                feed = await try_endpoint(
                    client,
                    f"{META_GRAPH_BASE_URL}/{page_id}/feed",
                    {"access_token": page_token, "fields": "id,message,story,to,from,created_time", "limit": "20"},
                    f"  feed",
                )
                if feed and isinstance(feed, list):
                    for post in feed:
                        story = post.get("story", "")
                        to_data = post.get("to", {}).get("data", [])
                        from_data = post.get("from", {})
                        msg = (post.get("message") or "")[:80]
                        if "group" in story.lower() or to_data:
                            print(f"    ** GROUP REF: story={story}, to={to_data}, from={from_data}")
        
        # 6) Try searching for groups by keyword with user token
        print("\n--- Approach 6: Search for health/nutrition groups ---")
        for query in ["wihy", "nutrition education", "parenting", "community groceries"]:
            await try_endpoint(
                client,
                f"{META_GRAPH_BASE_URL}/search",
                {"access_token": token, "type": "group", "q": query, "fields": "id,name,privacy,member_count", "limit": "5"},
                f"  search '{query}'",
            )


asyncio.run(check_groups())
