export type AiModeCitation = {
  title: string;
  journal?: string | null;
  year?: number | string | null;
  pmcid?: string | null;
  pmid?: string | null;
  doi?: string | null;
  url?: string | null;
  study_type?: string | null;
};

export type AiModeArticle = {
  title: string;
  abstract?: string | null;
  journal?: string | null;
  year?: number | null;
  pmcid?: string | null;
  pmid?: string | null;
  doi?: string | null;
  study_type?: string | null;
  url?: string | null;
};

export type AiModeResponse = {
  success: boolean;
  mode: "ai";
  query: string;
  answer: {
    verdict?: string | null;
    evidence_grade?: string | null;
    confidence?: string | null;
    quick_answer?: string | null;
    summary?: string | null;
    key_findings: string[];
    limitations?: string | null;
  };
  research: {
    articles: AiModeArticle[];
    article_count: number;
    from_user_articles: boolean;
  };
  citations: AiModeCitation[];
  related: {
    total: number;
    intent?: string | null;
    results: unknown[];
    facets: Record<string, unknown>;
  };
  follow_up_questions: string[];
  llm: {
    provider: "gemini";
    used: boolean;
    reason?: string | null;
  };
  safety: {
    educational_only: boolean;
    medical_advice: boolean;
    note: string;
  };
  timing_ms: number;
  timestamp: string;
};

export type AiModeRequest = {
  query: string;
  context?: string;
  limit?: number;
  include_related?: boolean;
  use_gemini?: boolean;
  articles?: Array<{
    title: string;
    abstract?: string;
    journal?: string;
    year?: number;
    pmcid?: string;
    pmid?: string;
    doi?: string;
    url?: string;
    study_type?: string;
  }>;
};
