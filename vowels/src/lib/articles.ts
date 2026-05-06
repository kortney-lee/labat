import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";

import type { Article, ArticleCategory, ArticleWithContent } from "@/types/article";

const ARTICLES_DIR = path.join(process.cwd(), "src", "content", "articles");

function toArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  return [];
}

function toOptionalString(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function readingTimeMinutes(text: string): number {
  const words = text.trim().split(/\s+/).length;
  return Math.max(1, Math.round(words / 220));
}

function parseArticleFile(filePath: string): ArticleWithContent {
  const raw = fs.readFileSync(filePath, "utf8");
  const { data, content } = matter(raw);
  const wihyData = typeof data.wihyData === "object" && data.wihyData !== null ? (data.wihyData as Record<string, unknown>) : undefined;

  const slug = String(data.slug || path.basename(filePath, path.extname(filePath)));
  const article: ArticleWithContent = {
    slug,
    title: String(data.title || slug),
    description: String(data.description || ""),
    category: (data.category || "nutrition-education") as ArticleCategory,
    author: String(data.author || "Vowels Editorial Desk"),
    publishedAt: String(data.publishedAt || new Date().toISOString()),
    updatedAt: data.updatedAt ? String(data.updatedAt) : undefined,
    image: data.image ? String(data.image) : undefined,
    imageAlt: data.imageAlt ? String(data.imageAlt) : undefined,
    imageCaption: data.imageCaption ? String(data.imageCaption) : undefined,
    readingTime: Number(data.readingTime || readingTimeMinutes(content)),
    takeaway: String(data.takeaway || "Use data to make practical nutrition decisions."),
    tags: toArray(data.tags),
    status: (data.status || "published") as Article["status"],
    isSponsored: Boolean(data.isSponsored || false),
    sponsorName: data.sponsorName ? String(data.sponsorName) : undefined,
    sourceLinks: toArray(data.sourceLinks),
    quickTake: toOptionalString(data.quickTake),
    wihyData:
      wihyData || data.wihyDataIntakeTrend || data.wihyDataMostCommonSource || data.wihyDataCommonIssue
        ? {
            intakeTrend: toOptionalString(wihyData?.intakeTrend ?? data.wihyDataIntakeTrend),
            mostCommonSource: toOptionalString(wihyData?.mostCommonSource ?? data.wihyDataMostCommonSource),
            commonIssue: toOptionalString(wihyData?.commonIssue ?? data.wihyDataCommonIssue),
          }
        : undefined,
    midArticleCtaLabel: toOptionalString(data.midArticleCtaLabel),
    midArticleCtaHref: toOptionalString(data.midArticleCtaHref),
    whatToDo: toArray(data.whatToDo),
    continueLearning: toArray(data.continueLearning),
    body: content,
  };

  return article;
}

export function getAllArticles(): Article[] {
  const files = fs.readdirSync(ARTICLES_DIR).filter((f) => f.endsWith(".mdx"));
  const articles = files
    .map((file) => parseArticleFile(path.join(ARTICLES_DIR, file)))
    .filter((article) => article.status === "published")
    .sort((a, b) => +new Date(b.publishedAt) - +new Date(a.publishedAt));

  return articles.map(({ body: _body, ...meta }) => meta);
}

export function getArticleBySlug(slug: string): ArticleWithContent | null {
  const filePath = path.join(ARTICLES_DIR, `${slug}.mdx`);
  if (!fs.existsSync(filePath)) return null;
  const article = parseArticleFile(filePath);
  if (article.status !== "published") return null;
  return article;
}

export function getArticlesByCategory(category: ArticleCategory): Article[] {
  return getAllArticles().filter((article) => article.category === category);
}

export function searchArticles(query: string): Article[] {
  const q = query.trim().toLowerCase();
  if (!q) return getAllArticles();
  return getAllArticles().filter((article) => {
    const haystack = [
      article.title,
      article.description,
      article.takeaway,
      article.tags.join(" "),
      article.category,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(q);
  });
}

export function getRelatedArticles(slug: string, limit = 5): Article[] {
  const current = getAllArticles().find((a) => a.slug === slug);
  const all = getAllArticles().filter((a) => a.slug !== slug);
  if (!current) return all.slice(0, limit);

  const sameCategory = all.filter((a) => a.category === current.category);
  const fallback = all.filter((a) => a.category !== current.category);
  return [...sameCategory, ...fallback].slice(0, limit);
}
