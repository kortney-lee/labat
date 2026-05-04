import fs from "node:fs";
import path from "node:path";

const outDir = path.join(process.cwd(), "src", "content", "articles");

const topicPool = [
  {
    slugBase: "protein-targets-for-weight-loss",
    title: "Protein Targets for Weight Loss",
    description: "Simple protein targeting guidance to improve fullness and meal adherence during fat-loss phases.",
    category: "health-explained",
    takeaway: "Protein consistency supports satiety and plan adherence.",
    tags: ["protein", "weight loss", "satiety", "meal planning"],
  },
  {
    slugBase: "meal-prep-for-busy-parents",
    title: "Meal Prep for Busy Parents",
    description: "A fast, repeatable prep system for family meals without daily reinvention.",
    category: "nutrition-education",
    takeaway: "Simple meal templates reduce weekday friction.",
    tags: ["meal prep", "parents", "family nutrition", "planning"],
  },
  {
    slugBase: "blood-sugar-friendly-breakfasts",
    title: "Blood Sugar Friendly Breakfasts",
    description: "How to structure breakfast to support steadier post-meal energy.",
    category: "research-explained",
    takeaway: "Pair carbohydrates with protein and fiber for steadier mornings.",
    tags: ["blood sugar", "breakfast", "glucose", "metabolic health"],
  },
  {
    slugBase: "grocery-list-for-high-fiber-weeks",
    title: "Grocery List for High-Fiber Weeks",
    description: "Build a practical grocery list that helps increase fiber without complexity.",
    category: "food-systems",
    takeaway: "A fiber-first list changes weekly outcomes.",
    tags: ["fiber", "grocery", "budget", "food systems"],
  },
  {
    slugBase: "processed-food-swaps-that-save-money",
    title: "Processed Food Swaps That Save Money",
    description: "Lower-cost product swaps that improve nutrition quality over time.",
    category: "food-systems",
    takeaway: "Smarter swaps can improve quality and lower spend.",
    tags: ["processed food", "budget", "shopping", "labels"],
  },
  {
    slugBase: "sodium-checklist-for-eating-out",
    title: "Sodium Checklist for Eating Out",
    description: "Use this practical checklist to reduce sodium load in restaurant meals.",
    category: "health-explained",
    takeaway: "Ordering strategy matters more than perfection.",
    tags: ["sodium", "blood pressure", "restaurants", "health"],
  },
  {
    slugBase: "school-lunch-upgrades-for-kids",
    title: "School Lunch Upgrades for Kids",
    description: "Small upgrades to improve protein, fiber, and hydration in school lunches.",
    category: "perspective",
    takeaway: "Lunch quality improves with repeatable building blocks.",
    tags: ["kids nutrition", "school lunch", "protein", "fiber"],
  },
  {
    slugBase: "hydration-habits-for-hot-weeks",
    title: "Hydration Habits for Hot Weeks",
    description: "A practical hydration workflow for warm weather and higher activity days.",
    category: "from-the-data",
    takeaway: "Proactive hydration prevents avoidable dips in performance.",
    tags: ["hydration", "habits", "performance", "health"],
  },
  {
    slugBase: "high-protein-budget-breakfasts",
    title: "High-Protein Budget Breakfasts",
    description: "Affordable breakfast options with protein anchors for satiety and routine.",
    category: "nutrition-education",
    takeaway: "Protein-first breakfasts can be done on a budget.",
    tags: ["protein", "budget", "breakfast", "meal planning"],
  },
  {
    slugBase: "fiber-vs-calories-what-to-prioritize",
    title: "Fiber vs Calories What to Prioritize",
    description: "How fiber and calories work together in practical weight management.",
    category: "research-explained",
    takeaway: "Food quality and satiety often decide calorie consistency.",
    tags: ["fiber", "calories", "weight management", "nutrition"],
  },
  {
    slugBase: "healthy-snack-system-for-afternoons",
    title: "Healthy Snack System for Afternoons",
    description: "Design afternoon snack defaults that reduce overeating later at night.",
    category: "from-the-data",
    takeaway: "Planned snack windows reduce late-day decision fatigue.",
    tags: ["snacks", "appetite", "habits", "nutrition"],
  },
  {
    slugBase: "simple-carb-quality-guide",
    title: "Simple Carb Quality Guide",
    description: "A practical guide to selecting better carbohydrate sources in daily meals.",
    category: "health-explained",
    takeaway: "Carbohydrate quality matters more than fear-based elimination.",
    tags: ["carbohydrates", "blood sugar", "meal quality", "health"],
  },
  {
    slugBase: "budget-protein-shopping-playbook",
    title: "Budget Protein Shopping Playbook",
    description: "Use this playbook to source protein efficiently across different store formats.",
    category: "food-systems",
    takeaway: "Protein planning lowers both cost and last-minute takeout.",
    tags: ["protein", "budget", "shopping", "meal prep"],
  },
  {
    slugBase: "weight-loss-plate-method",
    title: "Weight Loss Plate Method",
    description: "A plate-building method to simplify portions without constant tracking.",
    category: "nutrition-education",
    takeaway: "Visual templates can outperform rigid meal rules.",
    tags: ["weight loss", "plate method", "portioning", "habits"],
  },
  {
    slugBase: "metabolic-health-walking-after-meals",
    title: "Metabolic Health Walking After Meals",
    description: "How brief post-meal walks can support glucose and appetite control.",
    category: "research-explained",
    takeaway: "Short movement after meals can create meaningful cumulative benefits.",
    tags: ["metabolic health", "walking", "blood sugar", "habits"],
  },
  {
    slugBase: "easy-family-dinners-with-fiber",
    title: "Easy Family Dinners with Fiber",
    description: "Family dinner templates that improve fiber intake without extra prep burden.",
    category: "perspective",
    takeaway: "Fiber can be built into familiar family meals.",
    tags: ["family nutrition", "fiber", "dinner", "meal prep"],
  },
  {
    slugBase: "high-intent-grocery-label-mistakes",
    title: "High-Intent Grocery Label Mistakes",
    description: "Common label-reading mistakes that confuse otherwise healthy shoppers.",
    category: "from-the-data",
    takeaway: "A fixed comparison order improves shopping decisions.",
    tags: ["labels", "grocery", "shopping", "nutrition"],
  },
  {
    slugBase: "salt-sugar-balance-in-packaged-foods",
    title: "Salt Sugar Balance in Packaged Foods",
    description: "How to review salt and added sugar trade-offs in everyday packaged products.",
    category: "health-explained",
    takeaway: "Comparing products side-by-side reveals better defaults.",
    tags: ["sodium", "added sugar", "packaged food", "labels"],
  },
  {
    slugBase: "protein-fiber-lunch-formula",
    title: "Protein Fiber Lunch Formula",
    description: "A formula for building lunch that supports afternoon productivity and fullness.",
    category: "nutrition-education",
    takeaway: "A repeatable lunch formula reduces afternoon cravings.",
    tags: ["protein", "fiber", "lunch", "meal planning"],
  },
  {
    slugBase: "anti-overeating-kitchen-setup",
    title: "Anti Overeating Kitchen Setup",
    description: "Use kitchen layout and food placement to reduce default overeating triggers.",
    category: "from-the-data",
    takeaway: "Environment design is a powerful nutrition lever.",
    tags: ["overeating", "habits", "environment", "behavior"],
  },
  {
    slugBase: "weeknight-meals-under-30-minutes",
    title: "Weeknight Meals Under 30 Minutes",
    description: "A practical framework to build healthier weeknight meals quickly.",
    category: "food-systems",
    takeaway: "Speed and nutrition can coexist with a simple system.",
    tags: ["weeknight meals", "meal prep", "budget", "nutrition"],
  },
  {
    slugBase: "hydration-and-hunger-confusion",
    title: "Hydration and Hunger Confusion",
    description: "How hydration status can affect hunger perception and meal timing.",
    category: "research-explained",
    takeaway: "Hydration checks can prevent unnecessary snacking.",
    tags: ["hydration", "hunger", "behavior", "health"],
  },
  {
    slugBase: "kid-friendly-high-protein-snacks",
    title: "Kid Friendly High Protein Snacks",
    description: "Practical snack combinations for children that balance convenience and fullness.",
    category: "perspective",
    takeaway: "Simple protein-forward snacks can stabilize after-school appetite.",
    tags: ["kids nutrition", "protein", "snacks", "family"],
  },
  {
    slugBase: "sponsored-healthy-kitchen-basics",
    title: "Sponsored Healthy Kitchen Basics",
    description: "An example sponsor-integrated educational format with transparent disclosure.",
    category: "sponsored",
    takeaway: "Sponsorship can coexist with editorial transparency.",
    tags: ["sponsored", "kitchen", "education", "transparency"],
  },
];

const sourceLinks = [
  "https://www.cdc.gov/nutrition/index.html",
  "https://www.myplate.gov",
  "https://www.dietaryguidelines.gov",
];

function parseArg(flag, fallback) {
  const match = process.argv.find((arg) => arg.startsWith(`${flag}=`));
  if (!match) return fallback;
  return match.split("=").slice(1).join("=");
}

function isoWeek(date = new Date()) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return `${d.getUTCFullYear()}w${String(weekNo).padStart(2, "0")}`;
}

function simpleHash(input) {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash << 5) - hash + input.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function yamlQuoted(value) {
  return JSON.stringify(String(value));
}

function toFrontmatterArray(values) {
  return values.map((v) => `  - ${v}`).join("\n");
}

function toMdx(topic, slug, publishedAt, batchLabel) {
  const sponsoredFields = topic.category === "sponsored"
    ? "isSponsored: true\nsponsorName: Brand Partner\n"
    : "";

  return `---
slug: ${slug}
title: ${yamlQuoted(`${topic.title} (${batchLabel.toUpperCase()})`)}
description: ${yamlQuoted(topic.description)}
category: ${topic.category}
author: Vowels Editorial Desk
publishedAt: ${publishedAt.toISOString()}
readingTime: 7
takeaway: ${yamlQuoted(topic.takeaway)}
tags:
${toFrontmatterArray(topic.tags)}
status: published
${sponsoredFields}sourceLinks:
${toFrontmatterArray(sourceLinks)}
---

# ${topic.title}

This guide is part of the ${batchLabel.toUpperCase()} growth coverage cycle focused on practical, evidence-based nutrition education.

## Why this topic matters

Search demand for this subject is persistent because people need clear, repeatable actions they can use in daily life.

## What to do this week

1. Choose one default routine from this topic and run it for three days.
2. Track one outcome metric such as hunger stability, grocery spend, or meal consistency.
3. Keep what works and remove one friction point before next week.

## Practical notes

- prioritize consistency over perfection
- compare like-for-like products when shopping
- design meal defaults before busy days begin

## Explore related coverage

- [Nutrition Education](/category/nutrition-education)
- [Health Explained](/category/health-explained)
- [From the Data](/category/from-the-data)
`;
}

if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

const batch = parseArg("--batch", isoWeek());
const count = Number(parseArg("--count", "8"));
const maxCount = Number.isFinite(count) ? Math.max(1, Math.min(24, Math.round(count))) : 8;
const force = process.argv.includes("--force");
const offset = simpleHash(batch) % topicPool.length;

let created = 0;
let skipped = 0;

for (let i = 0; i < maxCount; i += 1) {
  const topic = topicPool[(offset + i) % topicPool.length];
  const slug = `${topic.slugBase}-${batch}`;
  const filePath = path.join(outDir, `${slug}.mdx`);

  if (fs.existsSync(filePath) && !force) {
    skipped += 1;
    continue;
  }

  const publishedAt = new Date(Date.UTC(2026, 4, 10 + i, 12, 0, 0));
  fs.writeFileSync(filePath, toMdx(topic, slug, publishedAt, batch), "utf8");
  created += 1;
}

console.log(`Weekly growth seed complete: batch=${batch}, created=${created}, skipped=${skipped}`);
