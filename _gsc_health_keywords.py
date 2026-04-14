"""Pull health & nutrition keyword data from Google Search Console API."""
import json
from googleapiclient.discovery import build
from google.auth import default

credentials, project = default(scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
service = build("searchconsole", "v1", credentials=credentials)

SITES = [
    "https://wihy.ai/",
    "https://communitygroceries.com/",
]

# Health/nutrition related filters - broad enough to catch everything
HEALTH_TERMS = [
    "health", "healthy", "nutrition", "diet", "calorie", "protein", "weight",
    "vitamin", "supplement", "food", "meal", "eat", "recipe", "fitness",
    "exercise", "workout", "sugar", "fat", "carb", "cholesterol", "blood pressure",
    "diabetes", "heart", "cancer", "inflammation", "gut", "probiotic", "organic",
    "keto", "fasting", "vegan", "gluten", "allergy", "grocery", "cooking",
    "ingredient", "nutrient", "mineral", "omega", "fiber", "antioxidant",
]

for site_url in SITES:
    print(f"\n{'='*80}")
    print(f"  SITE: {site_url}")
    print(f"{'='*80}")

    # Pull ALL keywords with decent data (no filter - get everything, filter locally)
    try:
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": "2025-01-01",
                "endDate": "2026-04-07",
                "dimensions": ["query"],
                "rowLimit": 5000,
                "dataState": "all",
            },
        ).execute()
    except Exception as e:
        print(f"  Error: {e}")
        continue

    rows = response.get("rows", [])
    if not rows:
        print("  No data found.")
        continue

    print(f"\n  Total keywords in GSC: {len(rows)}")

    # Show ALL keywords first
    print(f"\n  --- ALL KEYWORDS (sorted by impressions) ---")
    all_sorted = sorted(rows, key=lambda r: r["impressions"], reverse=True)
    for i, row in enumerate(all_sorted[:100]):
        q = row["keys"][0]
        clicks = int(row["clicks"])
        impressions = int(row["impressions"])
        ctr = row["ctr"] * 100
        pos = row["position"]
        print(f"  {i+1:3}. {q:<60} clicks={clicks:>4}  impr={impressions:>6}  ctr={ctr:>5.1f}%  pos={pos:>5.1f}")

    # Filter for health/nutrition related
    health_rows = []
    for row in rows:
        query = row["keys"][0].lower()
        if any(term in query for term in HEALTH_TERMS):
            health_rows.append(row)

    print(f"\n  --- HEALTH/NUTRITION KEYWORDS ({len(health_rows)} found) ---")
    health_sorted = sorted(health_rows, key=lambda r: r["impressions"], reverse=True)
    for i, row in enumerate(health_sorted[:80]):
        q = row["keys"][0]
        clicks = int(row["clicks"])
        impressions = int(row["impressions"])
        ctr = row["ctr"] * 100
        pos = row["position"]
        print(f"  {i+1:3}. {q:<60} clicks={clicks:>4}  impr={impressions:>6}  ctr={ctr:>5.1f}%  pos={pos:>5.1f}")

    # Also pull by page to see which pages get health traffic
    print(f"\n  --- TOP PAGES ---")
    try:
        page_response = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": "2025-01-01",
                "endDate": "2026-04-07",
                "dimensions": ["page"],
                "rowLimit": 500,
                "dataState": "all",
            },
        ).execute()
        page_rows = page_response.get("rows", [])
        page_sorted = sorted(page_rows, key=lambda r: r["impressions"], reverse=True)
        for i, row in enumerate(page_sorted[:30]):
            pg = row["keys"][0]
            clicks = int(row["clicks"])
            impressions = int(row["impressions"])
            ctr = row["ctr"] * 100
            pos = row["position"]
            print(f"  {i+1:3}. {pg:<70} clicks={clicks:>4}  impr={impressions:>6}  ctr={ctr:>5.1f}%  pos={pos:>5.1f}")
    except Exception as e:
        print(f"  Error: {e}")

print("\n\nDone.")
