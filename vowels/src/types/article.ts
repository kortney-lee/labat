export type ArticleCategory =
  | "nutrition-education"
  | "health-explained"
  | "food-systems"
  | "research-explained"
  | "from-the-data"
  | "perspective"
  | "sponsored";

export type ArticleStatus = "draft" | "published" | "archived";

export interface WIHYDataSummary {
  intakeTrend?: string;
  mostCommonSource?: string;
  commonIssue?: string;
}

export interface Article {
  slug: string;
  title: string;
  description: string;
  category: ArticleCategory;
  author: string;
  publishedAt: string;
  updatedAt?: string;
  image?: string;
  imageAlt?: string;
  imageCaption?: string;
  readingTime: number;
  takeaway: string;
  tags: string[];
  status: ArticleStatus;
  isSponsored?: boolean;
  sponsorName?: string;
  sourceLinks?: string[];
  quickTake?: string;
  wihyData?: WIHYDataSummary;
  midArticleCtaLabel?: string;
  midArticleCtaHref?: string;
  whatToDo?: string[];
  continueLearning?: string[];
}

export interface ArticleWithContent extends Article {
  body: string;
}
