import type { Metadata } from "next";
import Link from "next/link";

import { searchArticles } from "@/lib/articles";

export const metadata: Metadata = {
  title: "Subjects | Vowels.org",
  description: "Explore high-impact nutrition subjects across practical, evidence-based topic clusters.",
};

const subjectClusters = [
  {
    title: "Weight Management",
    description: "Search behavior around appetite, sustainable fat loss, and meal consistency.",
    category: "health-explained",
    seeds: ["weight management", "protein", "fiber", "meal prep"],
  },
  {
    title: "Metabolic Health",
    description: "High-value topics for blood sugar, insulin awareness, and meal timing questions.",
    category: "from-the-data",
    seeds: ["blood sugar", "insulin", "carb quality", "post meal"],
  },
  {
    title: "Family Nutrition",
    description: "Parent-focused nutrition intent with actionable lunchbox and snack planning.",
    category: "nutrition-education",
    seeds: ["kids nutrition", "lunchbox", "healthy snacks", "school meals"],
  },
  {
    title: "Budget Grocery Strategy",
    description: "Commercially relevant content around price-sensitive healthy shopping and prep.",
    category: "food-systems",
    seeds: ["budget meals", "grocery list", "processed food", "food labels"],
  },
  {
    title: "Evidence Explained",
    description: "Trust-building explainers translating studies into practical guidance.",
    category: "research-explained",
    seeds: ["nutrition labels", "sodium", "hydration", "diet pattern"],
  },
];

export default function SubjectsPage() {
  return (
    <section className="space-y-6">
      <header className="news-card p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Growth Engine</p>
        <h1 className="mt-3 font-serif text-4xl text-slate-950 md:text-5xl">High-Intent Subjects</h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-700">
          These topic clusters are designed for recurring search demand and ad-friendly educational coverage.
          Each cluster links to current indexed stories and search terms you can expand weekly.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {subjectClusters.map((cluster) => {
          const indexedCount = cluster.seeds.reduce((count, seed) => count + searchArticles(seed).length, 0);

          return (
            <article key={cluster.title} className="news-card p-6">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-serif text-3xl text-slate-950">{cluster.title}</h2>
                <span className="rounded-full bg-mist px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-600">
                  {indexedCount} matched stories
                </span>
              </div>
              <p className="mt-3 text-sm leading-7 text-slate-700">{cluster.description}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {cluster.seeds.map((seed) => (
                  <Link
                    key={seed}
                    href={`/?q=${encodeURIComponent(seed)}`}
                    className="rounded-full border border-black/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-700 transition hover:border-brand/40 hover:text-brand"
                  >
                    {seed}
                  </Link>
                ))}
              </div>
              <Link href={`/category/${cluster.category}`} className="mt-5 inline-block text-xs font-semibold uppercase tracking-[0.12em] text-brand hover:underline">
                Explore category
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}
