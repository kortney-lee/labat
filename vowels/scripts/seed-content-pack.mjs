import fs from "node:fs";
import path from "node:path";

const outDir = path.join(process.cwd(), "src", "content", "articles");

const contentPack = [
  {
    slug: "protein-breakfast-foundation",
    title: "Protein at Breakfast: A Better Start for Appetite Control",
    description: "A simple protein-first breakfast framework to reduce snacking and improve meal consistency.",
    category: "nutrition-education",
    takeaway: "Starting with protein and fiber makes later choices easier.",
    tags: ["protein", "breakfast", "appetite", "meal planning"],
    sourceLinks: [
      "https://www.dietaryguidelines.gov",
      "https://www.cdc.gov/nutrition/index.html",
    ],
    body: [
      "# Protein at Breakfast: A Better Start for Appetite Control",
      "",
      "Many people try to fix nutrition at dinner, but the first meal often determines how the day goes. A breakfast with protein and fiber can lower the chance of reactive snacking later.",
      "",
      "## What to build",
      "",
      "- one protein anchor such as eggs, Greek yogurt, tofu, or cottage cheese",
      "- one fiber source such as oats, berries, or chia",
      "- one hydration habit before caffeine",
      "",
      "## Weekly execution",
      "",
      "Use the same breakfast three weekdays in a row. Repeat what works, then adjust one variable at a time.",
      "",
      "## Related reads",
      "",
      "- [Fiber for Appetite Control](/article/fiber-for-appetite-control)",
      "- [High-Protein Snacks That Actually Help](/article/high-protein-snacks-that-actually-help)",
    ].join("\n"),
  },
  {
    slug: "high-protein-snacks-that-actually-help",
    title: "High-Protein Snacks That Actually Help",
    description: "Choose protein snacks for satiety and convenience without turning snack time into another sugar spike.",
    category: "nutrition-education",
    takeaway: "Good snacks are planned tools, not random decisions.",
    tags: ["protein", "snacks", "satiety", "habits"],
    sourceLinks: [
      "https://www.myplate.gov",
      "https://www.cdc.gov/healthy-weight-growth/losing-weight/index.html",
    ],
    body: [
      "# High-Protein Snacks That Actually Help",
      "",
      "Not all snacks solve hunger. Many only delay it. Protein-forward snacks can be useful when meals are far apart and schedules are inconsistent.",
      "",
      "## Build your short list",
      "",
      "- yogurt and fruit",
      "- roasted chickpeas",
      "- string cheese and apple",
      "- tuna packet with whole-grain crackers",
      "",
      "## Keep it operational",
      "",
      "Pre-portion two to three default snack options each week so decisions are fast.",
      "",
      "## Related reads",
      "",
      "- [Protein at Breakfast: A Better Start for Appetite Control](/article/protein-breakfast-foundation)",
      "- [Healthy Convenience Foods Guide](/article/healthy-convenience-foods-guide)",
    ].join("\n"),
  },
  {
    slug: "fiber-for-appetite-control",
    title: "Fiber for Appetite Control: Practical Targets and Food Picks",
    description: "How fiber improves fullness and what to add this week without overcomplicating your meals.",
    category: "health-explained",
    takeaway: "Consistency beats intensity when increasing fiber intake.",
    tags: ["fiber", "appetite", "digestion", "health"],
    sourceLinks: [
      "https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/nutrition-basics/fiber",
      "https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/dietary-fiber",
    ],
    body: [
      "# Fiber for Appetite Control: Practical Targets and Food Picks",
      "",
      "Fiber slows digestion and can make meals more satisfying. For many households, the challenge is not knowing this. The challenge is daily execution.",
      "",
      "## Simple additions",
      "",
      "- add beans to one meal daily",
      "- swap refined grains for whole grains when available",
      "- include fruit with at least one snack",
      "",
      "## Avoid the common mistake",
      "",
      "Increase fiber gradually and pair it with hydration.",
      "",
      "## Related reads",
      "",
      "- [Protein at Breakfast: A Better Start for Appetite Control](/article/protein-breakfast-foundation)",
      "- [Grocery Cart Audit: One Weekly System for Better Nutrition](/article/grocery-cart-audit-weekly)",
    ].join("\n"),
  },
  {
    slug: "sodium-blood-pressure-basics",
    title: "Sodium and Blood Pressure: What Actually Matters Day to Day",
    description: "A practical look at sodium awareness, label checks, and meal adjustments for blood pressure support.",
    category: "health-explained",
    takeaway: "Most sodium reduction comes from routine product swaps.",
    tags: ["sodium", "blood pressure", "labels", "meal planning"],
    sourceLinks: [
      "https://www.cdc.gov/salt/index.htm",
      "https://www.heart.org/en/health-topics/high-blood-pressure/changes-you-can-make-to-manage-high-blood-pressure",
    ],
    body: [
      "# Sodium and Blood Pressure: What Actually Matters Day to Day",
      "",
      "Sodium awareness is less about cooking with zero salt and more about reducing hidden sodium in packaged and restaurant foods.",
      "",
      "## High-impact checks",
      "",
      "- compare two versions of bread, soup, and sauces",
      "- review serving sizes before comparing sodium",
      "- combine lower-sodium packaged foods with whole ingredients",
      "",
      "## Related reads",
      "",
      "- [Nutrition Labels in 5 Minutes: A Repeatable Shopping Method](/article/nutrition-labels-5-minute-check)",
      "- [Healthy Convenience Foods Guide](/article/healthy-convenience-foods-guide)",
    ].join("\n"),
  },
  {
    slug: "budget-meal-prep-system",
    title: "Budget Meal Prep System for Busy Weeks",
    description: "A low-friction weekly prep workflow that prioritizes cost, protein, and repeatable meals.",
    category: "food-systems",
    takeaway: "A short prep loop can reduce both food waste and takeout spend.",
    tags: ["budget", "meal prep", "grocery", "food systems"],
    sourceLinks: [
      "https://www.myplate.gov/eat-healthy/healthy-eating-budget",
      "https://www.usda.gov/food-and-nutrition",
    ],
    body: [
      "# Budget Meal Prep System for Busy Weeks",
      "",
      "Meal prep works when it is realistic. The goal is not perfect variety. The goal is dependable meals at lower cost.",
      "",
      "## Base workflow",
      "",
      "- choose two proteins",
      "- choose two carbohydrate bases",
      "- choose two vegetables",
      "- prep one fallback meal for chaotic days",
      "",
      "## Related reads",
      "",
      "- [Grocery Cart Audit: One Weekly System for Better Nutrition](/article/grocery-cart-audit-weekly)",
      "- [Healthy Convenience Foods Guide](/article/healthy-convenience-foods-guide)",
    ].join("\n"),
  },
  {
    slug: "healthy-convenience-foods-guide",
    title: "Healthy Convenience Foods Guide: What to Buy When Time Is Tight",
    description: "How to use convenience foods strategically while preserving nutrition quality.",
    category: "food-systems",
    takeaway: "Convenience can support health when paired with simple selection rules.",
    tags: ["convenience foods", "grocery", "time", "food systems"],
    sourceLinks: [
      "https://www.fda.gov/food",
      "https://www.cdc.gov/nutrition/about-nutrition/why-it-matters.html",
    ],
    body: [
      "# Healthy Convenience Foods Guide: What to Buy When Time Is Tight",
      "",
      "Convenience foods are not automatically low quality. The better question is which products support your weekly goals with less friction.",
      "",
      "## Better convenience defaults",
      "",
      "- frozen vegetables",
      "- canned beans",
      "- pre-cooked whole grains",
      "- rotisserie chicken plus salad kit",
      "",
      "## Related reads",
      "",
      "- [Budget Meal Prep System for Busy Weeks](/article/budget-meal-prep-system)",
      "- [What Is Processed Food, Really?](/article/what-is-processed-food)",
    ].join("\n"),
  },
  {
    slug: "nutrition-labels-5-minute-check",
    title: "Nutrition Labels in 5 Minutes: A Repeatable Shopping Method",
    description: "A simple sequence for reading labels quickly and making better comparisons in-store.",
    category: "research-explained",
    takeaway: "Label reading works best with a fixed order and product comparisons.",
    tags: ["labels", "research", "shopping", "nutrition"],
    sourceLinks: [
      "https://www.fda.gov/food/nutrition-education-resources-materials/overview-nutrition-facts-label",
      "https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods",
    ],
    body: [
      "# Nutrition Labels in 5 Minutes: A Repeatable Shopping Method",
      "",
      "Most label confusion comes from inconsistent reading order. Use a fixed method and compare similar products side by side.",
      "",
      "## Five-minute method",
      "",
      "1. check serving size",
      "2. compare calories per serving",
      "3. scan sodium and added sugars",
      "4. review fiber and protein",
      "5. compare ingredient list length and clarity",
      "",
      "## Related reads",
      "",
      "- [Sodium and Blood Pressure: What Actually Matters Day to Day](/article/sodium-blood-pressure-basics)",
      "- [What Is Processed Food, Really?](/article/what-is-processed-food)",
    ].join("\n"),
  },
  {
    slug: "blood-sugar-after-meals-what-matters",
    title: "Blood Sugar After Meals: What Matters Most",
    description: "A plain-language guide to meal composition, movement, and consistency for better post-meal glucose patterns.",
    category: "research-explained",
    takeaway: "Meal composition and daily routines influence glucose trends more than single meals.",
    tags: ["blood sugar", "glucose", "meal composition", "metabolic health"],
    sourceLinks: [
      "https://www.cdc.gov/diabetes/prevent-type-2/index.html",
      "https://www.niddk.nih.gov/health-information/diabetes/overview/preventing-problems",
    ],
    body: [
      "# Blood Sugar After Meals: What Matters Most",
      "",
      "Post-meal glucose is influenced by portion size, carbohydrate quality, protein pairing, and movement. Focusing on one variable at a time is usually easier than rebuilding everything at once.",
      "",
      "## Useful levers",
      "",
      "- pair carbohydrates with protein or fiber",
      "- reduce liquid sugar intake",
      "- walk after meals when possible",
      "",
      "## Related reads",
      "",
      "- [Fiber for Appetite Control: Practical Targets and Food Picks](/article/fiber-for-appetite-control)",
      "- [Hydration Myths from the Data](/article/hydration-myths-from-the-data)",
    ].join("\n"),
  },
  {
    slug: "hydration-myths-from-the-data",
    title: "Hydration Myths from the Data",
    description: "Common hydration myths, what the evidence says, and how to build better hydration habits.",
    category: "from-the-data",
    takeaway: "Hydration strategy should match climate, activity, and routine, not internet rules.",
    tags: ["hydration", "data", "habits", "performance"],
    sourceLinks: [
      "https://www.cdc.gov/healthy-weight-growth/water-healthy-drinks/index.html",
      "https://www.nhlbi.nih.gov/health/educational/wecan/eat-right/pack-a-healthy-lunch.htm",
    ],
    body: [
      "# Hydration Myths from the Data",
      "",
      "Hydration advice often becomes one-size-fits-all. In practice, needs vary by activity, environment, and diet quality.",
      "",
      "## Better hydration rules",
      "",
      "- drink consistently across the day",
      "- adjust intake during heat and exercise",
      "- use urine color trends as a simple signal",
      "",
      "## Related reads",
      "",
      "- [Blood Sugar After Meals: What Matters Most](/article/blood-sugar-after-meals-what-matters)",
      "- [Protein at Breakfast: A Better Start for Appetite Control](/article/protein-breakfast-foundation)",
    ].join("\n"),
  },
  {
    slug: "grocery-cart-audit-weekly",
    title: "Grocery Cart Audit: One Weekly System for Better Nutrition",
    description: "Use a 10-minute review to improve cart quality, reduce waste, and align spending with goals.",
    category: "from-the-data",
    takeaway: "Weekly audits create compounding gains in food quality and budget efficiency.",
    tags: ["grocery", "data", "budget", "shopping"],
    sourceLinks: [
      "https://www.myplate.gov/eat-healthy/healthy-eating-budget",
      "https://www.ers.usda.gov/topics/food-nutrition-assistance/food-security-in-the-u-s/",
    ],
    body: [
      "# Grocery Cart Audit: One Weekly System for Better Nutrition",
      "",
      "Households improve fastest when they audit recurring purchases rather than chase perfect one-time choices.",
      "",
      "## Weekly audit questions",
      "",
      "- did this purchase improve satiety and meal quality",
      "- was this product used before expiration",
      "- can a lower-cost equivalent meet the same purpose",
      "",
      "## Related reads",
      "",
      "- [Budget Meal Prep System for Busy Weeks](/article/budget-meal-prep-system)",
      "- [Nutrition Labels in 5 Minutes: A Repeatable Shopping Method](/article/nutrition-labels-5-minute-check)",
    ].join("\n"),
  },
  {
    slug: "mediterranean-pattern-without-expensive-ingredients",
    title: "Mediterranean Pattern Without Expensive Ingredients",
    description: "How to apply Mediterranean-style principles using affordable staples and local grocery options.",
    category: "perspective",
    takeaway: "A diet pattern is about structure, not imported specialty foods.",
    tags: ["mediterranean", "budget", "pattern", "perspective"],
    sourceLinks: [
      "https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/nutrition-basics/mediterranean-diet",
      "https://www.dietaryguidelines.gov",
    ],
    body: [
      "# Mediterranean Pattern Without Expensive Ingredients",
      "",
      "Mediterranean-style eating can be adapted to many cultures and budgets. The pattern is more important than exact product lists.",
      "",
      "## Structure to copy",
      "",
      "- vegetables and legumes as meal anchors",
      "- fish or poultry in realistic rotation",
      "- nuts, seeds, and olive-based fats in workable portions",
      "",
      "## Related reads",
      "",
      "- [Healthy Convenience Foods Guide](/article/healthy-convenience-foods-guide)",
      "- [Budget Meal Prep System for Busy Weeks](/article/budget-meal-prep-system)",
    ].join("\n"),
  },
  {
    slug: "kids-lunchbox-protein-fiber",
    title: "Kids Lunchbox Protein and Fiber Playbook",
    description: "Build balanced school lunches with practical combinations that improve fullness and reduce after-school overeating.",
    category: "perspective",
    takeaway: "Balanced lunchboxes are easier when you use a repeatable template.",
    tags: ["kids nutrition", "lunchbox", "protein", "fiber"],
    sourceLinks: [
      "https://www.myplate.gov/life-stages/kids",
      "https://www.cdc.gov/nutrition/index.html",
    ],
    body: [
      "# Kids Lunchbox Protein and Fiber Playbook",
      "",
      "Families do better with templates than daily reinvention. A protein-plus-fiber lunch structure improves consistency and reduces afternoon hunger crashes.",
      "",
      "## Lunchbox template",
      "",
      "- one protein source",
      "- one fiber-rich produce item",
      "- one whole-grain or legume-based option",
      "- one hydration plan",
      "",
      "## Related reads",
      "",
      "- [High-Protein Snacks That Actually Help](/article/high-protein-snacks-that-actually-help)",
      "- [Fiber for Appetite Control: Practical Targets and Food Picks](/article/fiber-for-appetite-control)",
    ].join("\n"),
  },
];

function toFrontmatterArray(values) {
  return values.map((v) => `  - ${v}`).join("\n");
}

function toMdx(article, index) {
  const publishedAt = new Date(Date.UTC(2026, 4, 1 + index, 12, 0, 0)).toISOString();

  return `---
slug: ${article.slug}
title: "${article.title}"
description: "${article.description}"
category: ${article.category}
author: Vowels Editorial Desk
publishedAt: ${publishedAt}
readingTime: 7
takeaway: "${article.takeaway}"
tags:
${toFrontmatterArray(article.tags)}
status: published
sourceLinks:
${toFrontmatterArray(article.sourceLinks)}
---

${article.body}
`;
}

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const force = process.argv.includes("--force");

let created = 0;
let skipped = 0;

for (let i = 0; i < contentPack.length; i += 1) {
  const article = contentPack[i];
  const filePath = path.join(outDir, `${article.slug}.mdx`);

  if (fs.existsSync(filePath) && !force) {
    skipped += 1;
    continue;
  }

  fs.writeFileSync(filePath, toMdx(article, i), "utf8");
  created += 1;
}

console.log(`Seed complete: created=${created}, skipped=${skipped}`);
