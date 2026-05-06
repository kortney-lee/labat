import type { Article } from "@/types/article";

const siteName = "Vowels.org";
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://vowels.org";
const defaultOgImage = "/vowels-brand.png";

function toAbsoluteUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  return `${siteUrl}${url.startsWith("/") ? "" : "/"}${url}`;
}

export function baseMetadata() {
  return {
    metadataBase: new URL(siteUrl),
    title: `${siteName} | Nutrition Education`,
    description: "Evidence-based nutrition education powered by WIHY data.",
    icons: {
      icon: [{ url: "/vowels-brand.png", type: "image/png" }],
      shortcut: "/vowels-brand.png",
      apple: "/vowels-brand.png",
    },
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
      images: [{ url: toAbsoluteUrl(defaultOgImage) }],
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title: `${siteName} | Nutrition Education`,
      description: "Evidence-based nutrition education powered by WIHY data.",
      images: [toAbsoluteUrl(defaultOgImage)],
    },
    robots: {
      index: true,
      follow: true,
    },
  };
}

export function articleMetadata(article: Article) {
  const canonicalPath = `/article/${article.slug}`;
  const socialImage = toAbsoluteUrl(article.image || defaultOgImage);

  return {
    title: `${article.title} | ${siteName}`,
    description: article.description,
    alternates: {
      canonical: canonicalPath,
    },
    openGraph: {
      type: "article",
      title: article.title,
      description: article.description,
      url: canonicalPath,
      images: [{ url: socialImage }],
      publishedTime: article.publishedAt,
      modifiedTime: article.updatedAt,
      tags: article.tags,
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.description,
      images: [socialImage],
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
