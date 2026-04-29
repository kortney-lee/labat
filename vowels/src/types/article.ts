export type ArticleCategory =
  | "nutrition-education"
  | "health-explained"
  | "food-systems"
  | "research-explained"
  | "from-the-data"
  | "perspective"
  | "sponsored";

export type ArticleStatus = "draft" | "published" | "archived";

export interface Article {
  slug: string;
  title: string;
  description: string;
  category: ArticleCategory;
  author: string;
  publishedAt: string;
  updatedAt?: string;
  image?: string;
  readingTime: number;
  takeaway: string;
  tags: string[];
  status: ArticleStatus;
  isSponsored?: boolean;
  sponsorName?: string;
  sourceLinks?: string[];
}

export interface ArticleWithContent extends Article {
  body: string;
}
