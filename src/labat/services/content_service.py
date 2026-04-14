"""
labat/services/content_service.py — Gemini-powered content generation for LABAT.

Generates ad creatives, social media posts, outreach messaging, and comment
replies. All content aligns with WIHY's mission of clarity and better health
choices.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.labat.services.strategy_rules import build_strategy_block

logger = logging.getLogger("labat.content")

# Reuse the shared Gemini client from intelligence_service
_gemini_client = None

CONTENT_MODEL = os.getenv("LABAT_CONTENT_MODEL", "gemini-2.5-flash")


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
    max_tokens: int = 2000,
    temperature: float = 0.7,
    json_mode: bool = False,
) -> str:
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
        model=model or CONTENT_MODEL,
        contents=contents,
        config=config,
    )
    return response.text or ""


def _parse_json_response(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Ad Copy Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AD_COPY_SYSTEM = """You are LABAT's creative engine for multi-brand growth.

You will receive product strategy context in the user prompt. Use it as the
primary source of truth for positioning, offer framing, and messaging.

Generate high-converting ad copy for Meta (Facebook/Instagram) ads. Follow Meta Ads 
policies strictly:
- No misleading health claims or before/after promises
- No clickbait or sensationalized language
- No targeting based on personal attributes (health conditions, race, etc.)
- Compliant with Meta's advertising standards

Brand voice: Clear, empowering, science-backed, approachable. Not preachy.

Respond in JSON:
{
  "variants": [
    {
      "headline": "max 40 chars",
      "primary_text": "the main ad body (max 125 chars for best performance)",
      "description": "optional link description (max 30 chars)",
      "cta": "LEARN_MORE|SIGN_UP|SHOP_NOW|GET_OFFER|SUBSCRIBE|DOWNLOAD",
      "hook": "what makes this variant different",
      "target_emotion": "curiosity|empowerment|urgency|social_proof|health_aspiration"
    }
  ]
}"""


async def generate_ad_copy(
    product_description: str,
    target_audience: str,
    campaign_goal: str,
    num_variants: int = 3,
    tone: Optional[str] = None,
    product: str = "wihy",
    funnel_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate multiple ad copy variants for A/B testing."""
    strategy_block = build_strategy_block(product=product, funnel_stage=funnel_stage)

    prompt = (
        f"{strategy_block}\n\n"
        f"Generate {num_variants} ad copy variants for Meta Ads.\n\n"
        f"Product/Service: {product_description}\n"
        f"Target Audience: {target_audience}\n"
        f"Campaign Goal: {campaign_goal}\n"
    )
    if tone:
        prompt += f"Tone: {tone}\n"
    prompt += "\nCreate diverse variants that test different hooks and emotional angles."

    result = await _call_gemini(
        system=AD_COPY_SYSTEM,
        user_prompt=prompt,
        max_tokens=2500,
        temperature=0.8,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        return {"variants": [], "raw_response": result}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Social Media Post Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POST_SYSTEM = """You are LABAT's social media content engine for multi-brand growth.

You will receive product strategy context in the user prompt. Use it as the
primary source of truth for positioning and messaging priorities.

Generate engaging Facebook/Instagram posts that build community and drive meaningful action.

Content pillars:
- Nutrition education (myth-busting, ingredient transparency)
- Healthy living tips (actionable, science-backed)
- Community stories and engagement prompts
- Product highlights (natural, non-pushy)

Each post should include:
- The post body (conversational, use line breaks for readability)
- Relevant hashtags (5-10, mix of branded + discovery)
- Best posting time suggestion
- Engagement hook (question, poll, or call to comment)

Respond in JSON:
{
  "posts": [
    {
      "body": "the full post text including emojis and line breaks",
      "hashtags": ["#WIHY", "#HealthyChoices", "..."],
      "suggested_time": "e.g. Tuesday 11am EST",
      "content_pillar": "nutrition|fitness|community|product",
      "engagement_hook": "question or prompt at the end",
      "platform_notes": "any platform-specific tips"
    }
  ]
}"""


async def generate_posts(
    topic: str,
    platform: str = "facebook",
    num_posts: int = 3,
    content_pillar: Optional[str] = None,
    product: str = "wihy",
    funnel_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate social media posts for a given topic."""
    strategy_block = build_strategy_block(product=product, funnel_stage=funnel_stage)

    prompt = (
        f"{strategy_block}\n\n"
        f"Generate {num_posts} {platform} posts about: {topic}\n"
    )
    if content_pillar:
        prompt += f"Content pillar: {content_pillar}\n"
    prompt += "Make each post unique with a different angle or hook."

    result = await _call_gemini(
        system=POST_SYSTEM,
        user_prompt=prompt,
        max_tokens=3000,
        temperature=0.8,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        return {"posts": [], "raw_response": result}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Outreach Messaging
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTREACH_SYSTEM = """You are LABAT's outreach messaging engine for WIHY. Generate personalized 
messaging for different audience segments — influencer outreach, partnership pitches, 
community engagement, and lead nurturing.

Messaging must be:
- Personalized (reference the recipient's context)
- Value-first (lead with what's in it for them)
- Concise (respect people's time)
- Authentic (not template-feeling)

Respond in JSON:
{
  "messages": [
    {
      "subject": "for email/DM subject line",
      "body": "the message text",
      "follow_up": "suggested follow-up message if no response",
      "personalization_notes": "what to customize per recipient",
      "channel": "dm|email|comment",
      "best_send_time": "timing suggestion"
    }
  ]
}"""


async def generate_outreach(
    recipient_type: str,
    context: str,
    goal: str,
    num_variants: int = 2,
) -> Dict[str, Any]:
    """Generate outreach messages for a specific audience segment."""
    prompt = (
        f"Generate {num_variants} outreach message variants.\n\n"
        f"Recipient Type: {recipient_type}\n"
        f"Context: {context}\n"
        f"Goal: {goal}\n"
    )

    result = await _call_gemini(
        system=OUTREACH_SYSTEM,
        user_prompt=prompt,
        max_tokens=2500,
        temperature=0.7,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        return {"messages": [], "raw_response": result}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Comment Reply Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPLY_SYSTEM = """You are LABAT's community engagement engine for WIHY. Generate contextual 
replies to comments on social media posts. Replies should:
- Be warm, helpful, and on-brand
- Answer questions accurately (health/nutrition context)
- Drive engagement (ask follow-up questions when appropriate)
- Handle negative comments gracefully (empathy first, facts second)
- Never make unsubstantiated health claims

For negative or complaint comments, acknowledge the concern and offer to help.
Keep replies concise — 1-3 sentences max."""


async def generate_reply(
    comment_text: str,
    post_context: Optional[str] = None,
    sentiment: Optional[str] = None,
) -> str:
    """Generate a contextual reply to a social media comment."""
    prompt = f"Comment: \"{comment_text}\"\n"
    if post_context:
        prompt += f"Post context: {post_context}\n"
    if sentiment:
        prompt += f"Detected sentiment: {sentiment}\n"
    prompt += "\nGenerate a single reply (1-3 sentences)."

    return await _call_gemini(
        system=REPLY_SYSTEM,
        user_prompt=prompt,
        max_tokens=300,
        temperature=0.6,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Content Calendar
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CALENDAR_SYSTEM = """You are LABAT's content planning engine for WIHY. Create a content calendar 
that balances different content pillars, optimizes posting frequency, and aligns with 
WIHY's brand strategy.

Content pillars: Nutrition Education, Fitness & Wellness, Community Engagement, 
Product Highlights, Seasonal/Trending.

Respond in JSON:
{
  "calendar": [
    {
      "day": "Monday",
      "date_suggestion": "relative like 'Week 1 Monday'",
      "platform": "facebook|instagram|both",
      "content_pillar": "pillar name",
      "topic": "specific topic",
      "format": "text|image|video|carousel|reel|story",
      "brief": "2-3 sentence content brief",
      "time": "suggested posting time",
      "goal": "awareness|engagement|conversion|community"
    }
  ],
  "strategy_notes": "overall content strategy recommendations",
  "posting_frequency": "recommended posts per week per platform"
}"""


async def generate_content_calendar(
    weeks: int = 1,
    focus_areas: Optional[List[str]] = None,
    existing_content: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate a content calendar for the specified period."""
    prompt = f"Create a {weeks}-week content calendar for WIHY's social media.\n"
    if focus_areas:
        prompt += f"Focus areas: {', '.join(focus_areas)}\n"
    if existing_content:
        prompt += f"Recently posted (avoid repetition): {', '.join(existing_content[:10])}\n"

    result = await _call_gemini(
        system=CALENDAR_SYSTEM,
        user_prompt=prompt,
        max_tokens=4000,
        temperature=0.7,
        json_mode=True,
    )

    try:
        return _parse_json_response(result)
    except json.JSONDecodeError:
        return {"calendar": [], "raw_response": result}
