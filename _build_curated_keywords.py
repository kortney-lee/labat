"""
Build a clean, curated keyword list from HIGH-VOLUME health search topics.

These are based on known search volume patterns for health/nutrition queries —
the kind people actually Google, not what got typed into our chat bot.

Output: data/health_keywords_curated.json
"""
import json
import re
from pathlib import Path
from datetime import date

# ── Curated high-value health keywords ────────────────────────────────────────
# Organized by topic. These are real queries people search on Google.
# Source: known search demand patterns in health/nutrition space.

KEYWORDS = {
    "nutrition": [
        # Diet comparisons (high volume)
        "is keto diet healthy",
        "mediterranean diet benefits",
        "plant based diet health benefits",
        "vegan diet pros and cons",
        "low carb diet vs low fat diet",
        "anti inflammatory diet foods",
        "dash diet for high blood pressure",
        "what is leaky gut diet",
        "carnivore diet health risks",
        "paleo diet benefits and risks",

        # Specific foods (very high volume)
        "is almond milk healthy",
        "is oatmeal healthy",
        "is coffee good or bad for you",
        "is red meat bad for you",
        "is processed meat bad for you",
        "are eggs healthy",
        "is white rice healthy",
        "is whole wheat bread healthy",
        "is dark chocolate healthy",
        "is soy milk healthy",
        "are seed oils bad for you",
        "is olive oil healthy",
        "is coconut oil healthy",
        "is butter bad for you",
        "is margarine bad for you",
        "are artificial sweeteners bad for you",
        "is diet soda bad for you",
        "is fruit juice healthy",
        "is honey better than sugar",
        "is brown sugar healthier than white sugar",

        # Conditions and food
        "what foods lower cholesterol",
        "what foods lower blood pressure",
        "what foods help with inflammation",
        "what foods help prevent heart disease",
        "foods to avoid with type 2 diabetes",
        "foods to avoid with high blood pressure",
        "foods to avoid with acid reflux",
        "foods that cause inflammation",
        "foods high in vitamin d",
        "foods high in iron",
        "foods high in potassium",
        "foods high in fiber",
        "foods high in antioxidants",
        "foods that boost immune system",
        "foods that boost metabolism",
        "foods that help with anxiety",
        "foods that improve gut health",
        "foods that reduce belly fat",
        "foods that lower blood sugar",
        "foods that increase energy",

        # General nutrition questions
        "how many calories should i eat per day",
        "how many calories in a pound of fat",
        "what is a calorie deficit",
        "how to count macros for weight loss",
        "how much sodium per day",
        "how much fiber per day",
        "how much sugar per day",
        "what is a good cholesterol level",
        "what is a healthy bmi",
        "what is metabolic syndrome",
        "what is insulin resistance",
        "what does the gut microbiome do",
        "how to improve gut health",
        "what is inflammation in the body",
        "how to reduce inflammation naturally",
        "what is the healthiest breakfast",
        "what is the healthiest diet",
        "is breakfast important",
        "is snacking bad for you",
        "how to read nutrition labels",
        "what is ultra processed food",
        "hidden sugar in food",
        "how much protein in chicken breast",
        "how many calories in an egg",
        "best foods for weight loss",
        "best foods for muscle building",
        "best foods for energy",
        "best foods for heart health",
        "best foods for brain health",
    ],

    "supplements": [
        "does vitamin d boost immune system",
        "vitamin d deficiency symptoms",
        "how much vitamin d should i take",
        "magnesium deficiency symptoms",
        "magnesium for anxiety and sleep",
        "omega 3 benefits for heart",
        "fish oil vs omega 3 supplements",
        "is creatine safe",
        "creatine benefits and side effects",
        "does berberine lower blood sugar",
        "berberine vs metformin comparison",
        "probiotics benefits evidence",
        "best probiotic for gut health",
        "collagen supplements evidence",
        "does collagen actually work",
        "vitamin b12 deficiency symptoms",
        "zinc for immune function",
        "ashwagandha benefits research",
        "does melatonin help sleep",
        "coq10 heart health benefits",
        "turmeric curcumin anti inflammatory",
        "glutamine supplement benefits",
        "vitamin c and immune system",
        "iron deficiency symptoms",
        "multivitamin worth taking",
        "is caffeine bad for you",
        "whey protein benefits",
        "protein powder safe to use",
        "appetite suppressants that work",
        "best supplements for weight loss",
    ],

    "sugar-and-blood-health": [
        "how to lower blood sugar naturally",
        "what causes high blood sugar",
        "symptoms of high blood sugar",
        "how to reverse insulin resistance",
        "what is glycemic index",
        "low glycemic foods list",
        "does sugar cause diabetes",
        "how much sugar is bad for you",
        "hidden sugar in healthy foods",
        "sugar vs artificial sweeteners",
        "how does sugar affect the brain",
        "sugar and inflammation connection",
        "sugar and heart disease risk",
        "sugar and liver damage",
        "best diet for type 2 diabetes",
        "can you reverse type 2 diabetes with diet",
        "blood sugar spikes and energy crashes",
        "cinnamon for blood sugar control",
        "apple cider vinegar blood sugar",
        "intermittent fasting blood sugar",
    ],

    "processed-foods": [
        "ultra processed foods health risks",
        "what are ultra processed foods",
        "seed oils inflammation evidence",
        "are seed oils toxic",
        "processed meat cancer risk",
        "nitrates in processed meat",
        "fast food health effects",
        "food additives to avoid",
        "high fructose corn syrup dangers",
        "trans fats health effects",
        "artificial food coloring risks",
        "preservatives in food health effects",
        "is processed cheese bad for you",
        "deli meat health risks",
        "hot dogs and cancer risk",
    ],

    "fasting": [
        "intermittent fasting weight loss",
        "intermittent fasting 16 8 results",
        "intermittent fasting benefits",
        "intermittent fasting side effects",
        "intermittent fasting and muscle loss",
        "intermittent fasting and diabetes",
        "intermittent fasting insulin resistance",
        "time restricted eating benefits",
        "best intermittent fasting schedule",
        "intermittent fasting for women",
        "intermittent fasting and cortisol",
        "water fasting health risks",
        "fasting and autophagy",
        "does fasting improve longevity",
    ],

    "protein-and-muscle": [
        "how much protein per day",
        "high protein diet benefits",
        "high protein diet kidney damage",
        "best protein sources for muscle",
        "protein for weight loss",
        "how much protein to build muscle",
        "plant protein vs animal protein",
        "complete protein sources",
        "protein and satiety",
        "what happens if you eat too much protein",
        "resistance training and longevity",
        "strength training benefits after 50",
        "how to build muscle after 40",
        "muscle loss with age sarcopenia",
        "best exercises to build muscle",
        "how much exercise per week",
        "cardio vs strength training for weight loss",
        "does protein timing matter",
        "leucine muscle protein synthesis",
    ],

    "fitness": [
        "exercise and depression treatment",
        "best exercise for weight loss",
        "best exercise for heart health",
        "walking benefits for health",
        "how much exercise per week recommended",
        "exercise and mental health evidence",
        "hiit workout benefits",
        "yoga health benefits",
        "resistance training vs cardio",
        "exercise and longevity research",
        "exercise and cancer prevention",
        "exercise and type 2 diabetes",
        "exercise and dementia prevention",
        "best time to exercise",
        "exercise and sleep quality",
        "sedentary lifestyle health risks",
        "sitting too much health effects",
        "exercise and anxiety research",
        "post workout nutrition",
        "recovery after exercise",
        "overtraining symptoms",
        "exercise for lower back pain",
        "exercise after heart attack",
        "low impact exercise options",
    ],

    "hydration": [
        "how much water should i drink per day",
        "signs of dehydration",
        "does drinking water help weight loss",
        "water vs sports drinks",
        "electrolytes for hydration",
        "coconut water electrolytes",
        "drinking water and skin health",
        "does coffee dehydrate you",
        "how much water during exercise",
        "best way to stay hydrated",
    ],

    "alcohol-and-health": [
        "is red wine good for your heart",
        "alcohol and cancer risk",
        "alcohol and liver damage",
        "how much alcohol is safe",
        "alcohol and heart disease",
        "alcohol and breast cancer risk",
        "does alcohol increase inflammation",
        "alcohol and sleep quality",
        "alcohol and mental health",
        "alcohol and weight gain",
        "benefits of not drinking alcohol",
        "dry january health benefits",
    ],
}

# ── Convert to keyword objects ────────────────────────────────────────────────
def to_slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s

keywords = []
seen_slugs = set()

for topic, queries in KEYWORDS.items():
    for q in queries:
        slug = to_slug(q)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        keywords.append({
            "keyword": q,
            "slug": slug,
            "title": q.title(),
            "topic_slug": topic,
            "ask_count": 0,
            "intent": "research",
            "source": "curated",
        })

# ── Stats ─────────────────────────────────────────────────────────────────────
from collections import Counter
by_topic = Counter(k["topic_slug"] for k in keywords)
print(f"Total curated keywords: {len(keywords)}")
print("\nBy topic:")
for topic, count in sorted(by_topic.items(), key=lambda x: -x[1]):
    print(f"  {topic:<30} {count}")

# ── Save ──────────────────────────────────────────────────────────────────────
out = {
    "generated_at": date.today().isoformat(),
    "source": "curated-high-volume-health-searches",
    "total": len(keywords),
    "keywords": keywords,
}

Path("data").mkdir(exist_ok=True)
path = Path("data/health_keywords_curated.json")
path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nSaved → {path}")
print("\nTo generate blog posts from this list:")
print("  python -m src.content.generate_health_posts --keywords data/health_keywords_curated.json")
