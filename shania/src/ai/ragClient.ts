/**
 * ragClient.ts — Fetches health context from the WIHY RAG knowledge base.
 *
 * Calls ml.wihy.ai/api/rag/query (or localhost for local dev) to get
 * grounded health facts that inform post content.
 */

import { logger } from "../utils/logger";

const RAG_URL = process.env.RAG_URL || process.env.ML_URL || "https://ml.wihy.ai";

export interface RAGContext {
  facts: string;
  citations: string[];
}

/**
 * Query the WIHY RAG knowledge base for health context on a topic.
 * Returns grounded facts and citations, or null if unavailable.
 */
export async function getHealthContext(
  topic: string,
  topicHint?: string,
): Promise<RAGContext | null> {
  try {
    const url = `${RAG_URL}/api/rag/query`;
    const body = {
      question: topic,
      topic_hint: topicHint || null,
      max_snippets: 4,
    };

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      logger.warn(`RAG query failed: ${response.status}`);
      return null;
    }

    const data = (await response.json()) as { final?: string; answer?: string; citations?: string[] };
    if (data.final || data.answer) {
      const text = data.final || data.answer || "";
      logger.info(`RAG context retrieved: ${text.length} chars`);
      return {
        facts: text,
        citations: data.citations || [],
      };
    }

    return null;
  } catch (err) {
    logger.warn(`RAG context fetch failed (non-fatal): ${err}`);
    return null;
  }
}
