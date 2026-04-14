"""
Broad GSC pull — uses ALL health/nutrition/wellness/fitness/medical terms
including the exact topics users are asking about.
"""
import json

data = json.load(open('data/gsc_all_queries.json', encoding='utf-8'))
queries = data['queries']

print(f'Total queries in GSC (2024-2026): {len(queries)}')
print(f'Sites: {list(data["sites"].keys())}')
print()

food_terms = ['food','eat','healthy','health','nutrition','diet','calor','protein','vitamin','organic','fresh','veget','fruit','grain','meat','dairy','sugar','fat','fiber','sodium','ingredient','recipe','meal','cook','produce','grocery list']
loc_terms = ['near me','store','delivery','shop','market','kansas','kc','troost','community grocer']

food_health = []
grocery_location = []
other = []

for r in queries:
    q = r['query'].lower()
    if any(t in q for t in food_terms):
        food_health.append(r)
    elif any(t in q for t in loc_terms):
        grocery_location.append(r)
    else:
        other.append(r)

print(f'Food/health queries:    {len(food_health)}')
print(f'Location/store queries: {len(grocery_location)}')
print(f'Other:                  {len(other)}')

print('\n=== FOOD/HEALTH QUERIES (by impressions) ===')
food_health.sort(key=lambda x: x['impressions'], reverse=True)
for r in food_health:
    print(f"{r['impressions']:>6} impr  {r['clicks']:>4} clicks  pos {r['position']:>5}  {r['query']}")

print('\n=== OTHER QUERIES ===')
other.sort(key=lambda x: x['impressions'], reverse=True)
for r in other[:30]:
    print(f"{r['impressions']:>6} impr  {r['clicks']:>4} clicks  {r['query']}")
from googleapiclient.discovery import build
import google.auth

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
creds, _ = google.auth.default(scopes=SCOPES)
service = build("searchconsole", "v1", credentials=creds)

SITES = ["https://wihy.ai/", "https://communitygroceries.com/"]

# Massive keyword list: generic health + specific user topics
HEALTH_TERMS = [
    # Generic health/nutrition/wellness
    "health", "healthy", "nutrition", "nutritional", "nutrient", "diet", "dietary",
    "calorie", "calories", "protein", "carb", "carbs", "carbohydrate", "fat", "fats",
    "fiber", "vitamin", "mineral", "supplement", "supplements", "antioxidant",
    "weight", "weight loss", "obesity", "bmi", "body fat",
    "food", "foods", "meal", "meals", "recipe", "recipes", "eat", "eating",
    "fitness", "exercise", "workout", "training", "hiit", "cardio", "strength",
    "sugar", "sodium", "cholesterol", "trans fat", "saturated",
    "organic", "processed", "ultra-processed", "whole food", "plant-based",
    "vegan", "vegetarian", "keto", "paleo", "mediterranean",
    "wellness", "wellbeing", "well-being", "self-care",
    "mental health", "anxiety", "depression", "stress", "sleep",
    "gut", "microbiome", "probiotic", "prebiotic", "digestion",
    "immune", "immunity", "inflammation", "anti-inflammatory",
    "heart", "cardiovascular", "blood pressure", "hypertension",
    "diabetes", "insulin", "blood sugar", "glucose", "a1c",
    "cancer", "tumor", "oncology",
    "kidney", "liver", "fatty liver",
    "bone", "osteoporosis", "calcium",
    "thyroid", "hormone", "hormones", "testosterone", "estrogen", "cortisol",
    "longevity", "aging", "anti-aging", "lifespan",
    # Specific user topics (top queries from production DB)
    "statin", "statins", "muscle damage",
    "omega-3", "omega 3", "fish oil",
    "seed oil", "seed oils",
    "intermittent fasting", "fasting", "time-restricted",
    "berberine", "metformin",
    "creatine", "magnesium", "zinc", "iron",
    "cognitive", "brain", "alzheimer", "dementia",
    "coffee", "caffeine",
    "alcohol", "wine", "beer",
    "red meat", "processed meat", "colorectal",
    "gluten", "celiac", "lactose", "dairy",
    "soy", "tofu",
    "almond milk", "oat milk",
    "collagen", "biotin",
    "ashwagandha", "turmeric", "curcumin",
    "blood thinner", "warfarin", "grapefruit",
    "broccoli", "spinach", "kale", "avocado", "blueberry", "salmon",
    "protein powder", "whey",
    "meal plan", "meal planning", "grocery list", "shopping list",
    "is it healthy", "is-it-healthy", "health benefits", "side effects",
    "how much protein", "how many calories",
    "chronic kidney", "type 2 diabetes", "heart disease",
    "resistance training", "weightlifting", "bodyweight",
    "home workout", "no equipment",
    "apple cider vinegar", "acv",
    "electrolyte", "hydration", "dehydration",
    "metabolism", "metabolic", "metabolic syndrome",
    "ozempic", "semaglutide", "glp-1", "wegovy",
    "carnivore", "whole30", "dash diet",
    "detox", "cleanse", "juice cleanse",
    "artificial sweetener", "aspartame", "sucralose", "stevia",
    "msg", "preservative", "additive",
    "gmo", "pesticide",
    "bpa", "microplastic",
    "circadian", "melatonin",
    "dopamine", "serotonin",
    "ptsd", "adhd", "autism",
    "fertility", "pregnancy", "prenatal",
    "menopause", "perimenopause", "pcos",
    "prostate", "breast cancer",
    "eczema", "psoriasis", "acne", "skin",
    "hair loss", "alopecia",
    "ibs", "ibd", "crohn", "ulcerative colitis",
    "gerd", "acid reflux", "heartburn",
    "migraine", "headache",
    "arthritis", "joint pain", "inflammation",
    "back pain", "sciatica",
    "blood test", "lab results",
    "cholesterol levels", "ldl", "hdl", "triglycerides",
    "hemoglobin", "anemia",
    "sodium", "potassium",
]

for site in SITES:
    print("=" * 100)
    print(f"  SITE: {site}")
    print("=" * 100)

    # Pull ALL keywords (max 25000)
    all_kws = []
    for start_row in range(0, 25000, 5000):
        resp = service.searchanalytics().query(
            siteUrl=site,
            body={
                "startDate": "2024-01-01",  # Go back further
                "endDate": "2026-04-07",
                "dimensions": ["query"],
                "rowLimit": 5000,
                "startRow": start_row,
            },
        ).execute()
        rows = resp.get("rows", [])
        if not rows:
            break
        all_kws.extend(rows)

    print(f"\n  Total keywords in GSC: {len(all_kws)}")

    # Filter for health-related
    health_kws = []
    for r in all_kws:
        q = r["keys"][0].lower()
        for term in HEALTH_TERMS:
            if term in q:
                health_kws.append(r)
                break

    # Sort by impressions
    all_kws.sort(key=lambda x: x["impressions"], reverse=True)
    health_kws.sort(key=lambda x: x["impressions"], reverse=True)

    # Show top 100 all keywords
    print(f"\n  --- ALL KEYWORDS (top 100 by impressions) ---")
    for i, r in enumerate(all_kws[:100], 1):
        q = r["keys"][0]
        print(f"    {i:3d}. {q:60s} clicks={r['clicks']:4d}  impr={r['impressions']:6d}  ctr={r['ctr']*100:5.1f}%  pos={r['position']:5.1f}")

    # Show ALL health keywords
    print(f"\n  --- HEALTH/NUTRITION/WELLNESS KEYWORDS ({len(health_kws)} found) ---")
    for i, r in enumerate(health_kws[:200], 1):
        q = r["keys"][0]
        print(f"    {i:3d}. {q:60s} clicks={r['clicks']:4d}  impr={r['impressions']:6d}  ctr={r['ctr']*100:5.1f}%  pos={r['position']:5.1f}")

    # NON-grocery health keywords (exclude generic grocery terms for CG)
    if "communitygroceries" in site:
        grocery_noise = ["grocery", "grocer", "supermarket", "store near", "stores near",
                         "near me", "kansas city", "delivery", "shop near", "discount",
                         "cheap", "order groceries", "where is", "where's", "closest",
                         "nearest", "what's the", "online grocer", "food mart",
                         "community grocer", "community food", "community good",
                         "community natural", "axtell", "woodville", "troost"]
        pure_health = []
        for r in health_kws:
            q = r["keys"][0].lower()
            if not any(noise in q for noise in grocery_noise):
                pure_health.append(r)

        print(f"\n  --- PURE HEALTH KEYWORDS (excluding grocery noise) ({len(pure_health)} found) ---")
        for i, r in enumerate(pure_health[:100], 1):
            q = r["keys"][0]
            print(f"    {i:3d}. {q:60s} clicks={r['clicks']:4d}  impr={r['impressions']:6d}  ctr={r['ctr']*100:5.1f}%  pos={r['position']:5.1f}")

    # Pull page-level data
    resp = service.searchanalytics().query(
        siteUrl=site,
        body={
            "startDate": "2024-01-01",
            "endDate": "2026-04-07",
            "dimensions": ["page"],
            "rowLimit": 50,
        },
    ).execute()
    pages = resp.get("rows", [])
    pages.sort(key=lambda x: x["impressions"], reverse=True)
    print(f"\n  --- TOP PAGES ---")
    for i, r in enumerate(pages[:20], 1):
        p = r["keys"][0]
        print(f"    {i:3d}. {p:80s} clicks={r['clicks']:4d}  impr={r['impressions']:6d}  ctr={r['ctr']*100:5.1f}%  pos={r['position']:5.1f}")

    print()

print("\nDone.")
