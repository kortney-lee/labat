"""
labat/services/intelligence_service.py — Gemini-powered reasoning engine for LABAT.

The intelligence layer that drives WIHY's growth loop:
  find → capture → convert → act

Uses Gemini to analyze campaign performance, user signals, and content
engagement to recommend what to scale, pause, or rewrite. Enables adaptive
learning, faster experimentation, and smarter automation.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.labat.services.strategy_rules import build_strategy_block

logger = logging.getLogger("labat.intelligence")

# Lazy singleton
_gemini_client = None

INTELLIGENCE_MODEL = os.getenv("LABAT_INTELLIGENCE_MODEL", "gemini-2.5-flash")


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


async def _call_gemini(
    system: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 3000,
    temperature: float = 0.4,
    json_mode: bool = False,
) -> str:
    """Core Gemini call shared by all intelligence functions."""
    client = _get_gemini()
    from google.genai import types

    contents = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]

    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=temperature,
    )
    if json_mode:
        config.response_mime_type = "application/json"

    response = await client.aio.models.generate_content(
        model=model or INTELLIGENCE_MODEL,
        contents=contents,
        config=config,
    )
    return response.text or ""


def _parse_json_response(text: str) -> Dict[str, Any]:
    """Best-effort JSON parse — handles markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # remove ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Campaign Analysis & Optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CAMPAIGN_ANALYSIS_SYSTEM = """You are LABAT — a multi-brand intelligent growth engine that manages the full 
find → capture → convert → act journey. You analyze Meta/Facebook campaign performance data 
and deliver actionable optimization recommendations.

You will receive product strategy context in the user prompt. Use it as the
primary source of truth for mission alignment and recommendation framing.

Your analysis must include:
1. Performance summary — key metrics, trends, what's working
2. Issues — underperforming elements with root cause analysis
3. Recommendations — specific actions: scale, pause, adjust budget, change targeting, rewrite creative
4. Budget allocation — how to redistribute spend for maximum conversions
5. A/B test suggestions — what to experiment with next

Be specific. Use numbers. Prioritize actions by expected impact.

Respond in JSON with this structure:
{
  "summary": "brief performance overview",
  "top_performers": [{"id": "...", "name": "...", "reason": "..."}],
  "underperformers": [{"id": "...", "name": "...", "issue": "...", "action": "scale_down|pause|rewrite"}],
  "recommendations": [{"priority": 1-5, "action": "...", "expected_impact": "...", "reasoning": "..."}],
  "budget_reallocation": [{"campaign_id": "...", "current_pct": N, "recommended_pct": N, "reason": "..."}],
  "ab_tests": [{"hypothesis": "...", "variant_a": "...", "variant_b": "...", "metric": "..."}]
}"""


async def analyze_campaigns(
    insights_data: List[Dict[str, Any]],
    product: str = "wihy",
    funnel_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze campaign performance data and return optimization recommendations."""
    strategy_block = build_strategy_block(product=product, funnel_stage=funnel_stage)

    prompt = (
        f"{strategy_block}\n\n"
        "Analyze this Meta Ads campaign performance data and provide optimization "
        "recommendations. Focus on ROI, conversion efficiency, and audience quality.\n\n"
        f"Campaign Data:\n{json.dumps(insights_data, indent=2)}"
    )

    result = await _call_gemini(
        system=CAMPAIGN_ANALYSIS_SYSTEM,
        user_prompt=prompt,
        max_tokens=4000,
        temperature=0.3,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        logger.warning("Campaign analysis returned non-JSON, wrapping as text")
        return {"summary": result, "recommendations": [], "raw": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Audience Intelligence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUDIENCE_SYSTEM = """You are LABAT's audience intelligence engine. Given performance data and 
product context, recommend targeting strategies for Meta Ads.

You will receive product strategy context in the user prompt. Use it as the
primary source of truth for segment priorities and messaging angles.

Respond in JSON:
{
  "segments": [
    {
      "name": "segment name",
      "description": "who they are",
      "targeting": {
        "interests": ["..."],
        "behaviors": ["..."],
        "demographics": {"age_min": N, "age_max": N, "genders": [1,2]},
        "custom_audiences": ["suggestion for lookalike/custom"]
      },
      "messaging_angle": "what resonates with this segment",
      "estimated_priority": "high|medium|low"
    }
  ],
  "exclusions": ["audiences to exclude"],
  "lookalike_recommendations": ["seed audience suggestions"]
}"""


async def recommend_audiences(
    campaign_context: str,
    performance_data: Optional[List[Dict[str, Any]]] = None,
    product: str = "wihy",
    funnel_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Recommend audience segments and targeting strategies."""
    strategy_block = build_strategy_block(product=product, funnel_stage=funnel_stage)

    prompt = f"{strategy_block}\n\nCampaign/Product Context:\n{campaign_context}\n"
    if performance_data:
        prompt += f"\nHistorical Performance Data:\n{json.dumps(performance_data, indent=2)}"

    result = await _call_gemini(
        system=AUDIENCE_SYSTEM,
        user_prompt=prompt,
        max_tokens=3000,
        temperature=0.5,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        return {"segments": [], "raw_response": result}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Creative Optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CREATIVE_OPTIMIZATION_SYSTEM = """You are LABAT's creative optimization engine. Analyze ad creative 
performance and recommend which creatives to scale, pause, iterate on, or replace.

You will receive product strategy context in the user prompt. Use it when
judging fit, clarity, and offer-message alignment.

Consider: CTR, conversion rate, cost per result, frequency, relevance score, fatigue signals.

Respond in JSON:
{
  "creative_rankings": [
    {"creative_id": "...", "name": "...", "verdict": "scale|maintain|iterate|pause|replace", "reasoning": "..."}
  ],
  "fatigue_alerts": [{"creative_id": "...", "signal": "...", "suggested_action": "..."}],
  "iteration_ideas": [{"based_on": "creative_id", "variation": "description of what to change"}],
  "general_insights": "overall creative strategy observations"
}"""


async def optimize_creatives(
    creative_performance: List[Dict[str, Any]],
    product: str = "wihy",
    funnel_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze creative performance and recommend optimizations."""
    strategy_block = build_strategy_block(product=product, funnel_stage=funnel_stage)

    prompt = (
        f"{strategy_block}\n\n"
        "Analyze these ad creative performance metrics and recommend optimizations:\n\n"
        f"{json.dumps(creative_performance, indent=2)}"
    )

    result = await _call_gemini(
        system=CREATIVE_OPTIMIZATION_SYSTEM,
        user_prompt=prompt,
        max_tokens=3000,
        temperature=0.3,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        return {"creative_rankings": [], "general_insights": result}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Budget Advisor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUDGET_SYSTEM = """You are LABAT's budget optimization engine. Given campaign performance data and 
total budget constraints, recommend optimal budget allocation across campaigns and ad sets.

You will receive product strategy context in the user prompt. Use it to keep
budget recommendations aligned with brand priorities and funnel stage.

Principles:
- Maximize conversions per dollar (not just clicks)
- Gradual scaling (never more than 20% daily budget increase to avoid learning phase reset)
- Kill waste early — pause campaigns with high spend and zero conversions after sufficient data
- Reserve 15-20% of budget for experimentation

Respond in JSON:
{
  "total_daily_budget": N,
  "allocations": [
    {"id": "campaign/adset id", "name": "...", "current_budget": N, "recommended_budget": N, "change_pct": N, "reason": "..."}
  ],
  "waste_alerts": [{"id": "...", "spend": N, "conversions": 0, "action": "pause|reduce"}],
  "experiment_budget": N,
  "experiment_suggestions": ["what to test with the experiment budget"]
}"""


async def optimize_budget(
    performance_data: List[Dict[str, Any]],
    total_daily_budget: Optional[int] = None,
    product: str = "wihy",
    funnel_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Recommend budget allocation across campaigns."""
    strategy_block = build_strategy_block(product=product, funnel_stage=funnel_stage)

    prompt = f"{strategy_block}\n\nCampaign Performance:\n{json.dumps(performance_data, indent=2)}\n"
    if total_daily_budget:
        prompt += f"\nTotal daily budget constraint: ${total_daily_budget / 100:.2f}"

    result = await _call_gemini(
        system=BUDGET_SYSTEM,
        user_prompt=prompt,
        max_tokens=3000,
        temperature=0.2,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        return {"allocations": [], "raw_response": result}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Performance Digest
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DIGEST_SYSTEM = """You are LABAT, WIHY's growth intelligence engine. Generate a concise executive 
performance digest from campaign data. Write in clear, actionable language suitable for a 
business owner or marketing lead.

Structure your digest as:
1. TL;DR — one sentence summary
2. Key Metrics — spend, reach, clicks, conversions, ROAS
3. What's Working — top 2-3 wins
4. What Needs Attention — top 2-3 concerns
5. Recommended Next Steps — 3-5 specific actions for this week

Keep it concise. Use bullet points. No fluff."""


async def generate_digest(
    performance_data: List[Dict[str, Any]],
    period: str = "last_7d",
) -> str:
    """Generate a human-readable performance digest."""
    prompt = (
        f"Generate a performance digest for the {period} period.\n\n"
        f"Data:\n{json.dumps(performance_data, indent=2)}"
    )

    return await _call_gemini(
        system=DIGEST_SYSTEM,
        user_prompt=prompt,
        max_tokens=2000,
        temperature=0.5,
    )
