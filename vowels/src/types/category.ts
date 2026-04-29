import type { ArticleCategory } from "@/types/article";

export interface Category {
  slug: ArticleCategory;
  name: string;
  description: string;
}
