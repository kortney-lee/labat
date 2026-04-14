import asyncio, json, sys
sys.path.insert(0, ".")
from src.labat.services.content_insights_service import get_blog_overview

async def test():
    r = await get_blog_overview("communitygroceries", "365d")
    print(f"ALL: total={r['total']}, in_period={r['in_period']}")

    types = {}
    for a in r["articles"]:
        pt = a.get("page_type", "missing")
        types[pt] = types.get(pt, 0) + 1
    print(f"By type: {json.dumps(types, indent=2)}")

    for pt in ["topic", "meals", "comparison", "alternative", "guide"]:
        r2 = await get_blog_overview("communitygroceries", "365d", page_type=pt)
        print(f"{pt:15s}: total={r2['total']}, in_period={r2['in_period']}")
        if r2["articles"]:
            print(f"  sample: {r2['articles'][0]['slug']}")

asyncio.run(test())
