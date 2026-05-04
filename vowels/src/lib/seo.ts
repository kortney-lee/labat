import type { Article } from "@/types/article";

const siteName = "Vowels.org";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vowels.org";

export function baseMetadata() {
  return {
    metadataBase: new URL(siteUrl),
    title: `${siteName} | Nutrition Education`,
    description: "Evidence-based nutrition education powered by WIHY data.",
    alternates: {
      canonical: "/",
      types: {
        "application/rss+xml": "/rss.xml",
        "application/feed+json": "/feed",
      },
    },
    openGraph: {
      type: "website",
      url: siteUrl,
      siteName,
      title: `${siteName} | Nutrition Education`,
      description: "Evidence-based nutrition education powered by WIHY data.",
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title: `${siteName} | Nutrition Education`,
      description: "Evidence-based nutrition education powered by WIHY data.",
    },
  };
}

export function articleMetadata(article: Article) {
  return {
    title: `${article.title} | ${siteName}`,
    description: article.description,
    alternates: {
      canonical: `/article/${article.slug}`,
    },
    openGraph: {
      type: "article",
      title: article.title,
      description: article.description,
      url: `/article/${article.slug}`,
      images: article.image ? [article.image] : [],
      publishedTime: article.publishedAt,
      modifiedTime: article.updatedAt,
      tags: article.tags,
    },
  };
}

export function articleJsonLd(article: Article) {
  return {
    "@context": "https://schema.org",
    "@type": article.category === "research-explained" ? "NewsArticle" : "Article",
    headline: article.title,
    description: article.description,
    datePublished: article.publishedAt,
    dateModified: article.updatedAt || article.publishedAt,
    author: {
      "@type": "Person",
      name: article.author,
    },
    publisher: {
      "@type": "Organization",
      name: "Vowels.org",
      url: siteUrl,
    },
    mainEntityOfPage: `${siteUrl}/article/${article.slug}`,
    isAccessibleForFree: true,
    keywords: article.tags.join(", "),
  };
}
