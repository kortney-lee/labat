"""
Centralized OpenAI model configuration for the WIHY ML backend.

ALL model references should import from here — no more scattered os.getenv() calls.

Model roles:
  CHAT_MODEL      – Fine-tuned on WIHY health Q&A. Used for conversational health
                    answers, meal planning, tone detection, and any chat.completions
                    call that does NOT use file_search.
  RAG_MODEL       – Base gpt-4o. Required for file_search / Assistants API (fine-tuned
                    models don't support OpenAI tools like file_search).
  EXTRACTION_MODEL – Base gpt-4o-mini. Used when we need strict instruction-following
                     for structured extraction (e.g., recipe → ingredient list).
                     The fine-tuned model tends to ignore extraction prompts.
  FITNESS_MODEL   – gpt-4o (full). Workout generation needs stronger reasoning for
                     complex multi-day program design.
"""

import os
import logging

logger = logging.getLogger(__name__)

# ── Core models ──────────────────────────────────────────────────────────────

# Fine-tuned health/meal model (chat.completions, NO file_search)
CHAT_MODEL: str = os.getenv(
    "WIHY_FINE_TUNED_MODEL", "gpt-4o-mini"
)

# RAG / file_search model (Assistants API, Responses API — must be base model)
RAG_MODEL: str = os.getenv(
    "OPENAI_RAG_MODEL", "gpt-4o"
)

# Structured extraction model (recipe parsing, JSON extraction)
EXTRACTION_MODEL: str = os.getenv("WIHY_EXTRACTION_MODEL", "gpt-4o-mini")

# Meal plan generation model: base gpt-4o-mini (NOT fine-tuned).
# Fine-tuned models are ~10x slower for structured JSON and provide no benefit
# over the base model when the schema is fully specified in the system prompt.
# Fine-tuning is reserved for health Q&A conversational answers (CHAT_MODEL).
MEAL_PLANS_MODEL: str = os.getenv("WIHY_MEAL_PLANS_MODEL", "gpt-4o-mini")

# Fitness workout generation (needs stronger reasoning)
FITNESS_MODEL: str = os.getenv("WIHY_FITNESS_MODEL", "gpt-4o")


def log_model_config() -> None:
    """Log active model configuration at startup."""
    logger.info(
        "Model config: CHAT=%s  RAG=%s  EXTRACTION=%s  MEAL_PLANS=%s  FITNESS=%s",
        CHAT_MODEL,
        RAG_MODEL,
        EXTRACTION_MODEL,
        MEAL_PLANS_MODEL,
        FITNESS_MODEL,
    )
