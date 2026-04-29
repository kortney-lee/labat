import type { MetadataRoute } from "next";

import { getAllArticles } from "@/lib/articles";
import { allStaticRoutes, articleRoutes, categoryRoutes } from "@/lib/sitemap";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vowels.org";

export default function sitemap(): MetadataRoute.Sitemap {
  const articles = getAllArticles();
  const routes = [
    ...allStaticRoutes(),
    ...articleRoutes(articles),
    ...categoryRoutes(articles),
  ];

  return routes.map((route) => ({
    url: `${siteUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: route.startsWith("/article") ? "weekly" : "daily",
    priority: route === "/" ? 1 : 0.7,
  }));
}
