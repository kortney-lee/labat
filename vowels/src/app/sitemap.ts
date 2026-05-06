import type { MetadataRoute } from "next";

import { getAllArticles } from "@/lib/articles";
import { allStaticRoutes } from "@/lib/sitemap";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vowels.org";

export default function sitemap(): MetadataRoute.Sitemap {
  const articles = getAllArticles();
  const generatedAt = new Date();
  const staticEntries: MetadataRoute.Sitemap = allStaticRoutes().map((route) => ({
    url: `${siteUrl}${route}`,
    lastModified: generatedAt,
    changeFrequency: route === "/" ? "daily" : "weekly",
    priority: route === "/" ? 1 : 0.7,
  }));

  const articleEntries: MetadataRoute.Sitemap = articles.map((article) => ({
    url: `${siteUrl}/article/${article.slug}`,
    lastModified: new Date(article.updatedAt || article.publishedAt),
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  const categoryToLastModified = new Map<string, Date>();
  for (const article of articles) {
    const articleUpdatedAt = new Date(article.updatedAt || article.publishedAt);
    const current = categoryToLastModified.get(article.category);
    if (!current || articleUpdatedAt > current) {
      categoryToLastModified.set(article.category, articleUpdatedAt);
    }
  }

  const categoryEntries: MetadataRoute.Sitemap = Array.from(categoryToLastModified.entries()).map(([category, lastModified]) => ({
    url: `${siteUrl}/category/${category}`,
    lastModified,
    changeFrequency: "daily",
    priority: 0.75,
  }));

  return [...staticEntries, ...categoryEntries, ...articleEntries];
}
