"""
Nurture Email Service
7-email drip campaign for What Is Healthy? book leads via SendGrid.
Dynamic content based on ad variant (stored as utm_content on the lead).

Schedule:
  Day 0:  book_delivery      — Book download + first check-in
  Day 1:  did_you_get_this    — Follow up, tease paperback
  Day 3:  big_benefit         — Value bullets, chapter tease, soft paperback
  Day 5:  got_questions       — Curse of knowledge, WIHY app mention
  Day 7:  social_proof        — Testimonial, paperback upsell
  Day 10: im_surprised        — Urgency, why haven't you ordered?
  Day 14: last_chance          — Final push, paperback + CG + WIHY
"""

import logging
import os
from datetime import datetime, timezone, timedelta

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
BOOK_EMAIL_BCC = (os.getenv("BOOK_EMAIL_BCC", "kortney@wihy.ai") or "").strip()

# Brand-specific sender configs (matches SendGrid verified senders)
BRAND_CONFIG = {
    "vowels": {
        "from_email": "info@vowels.org",
        "from_name": "Vowels",
        "team_name": "The Vowels Team",
        "brand_label": "Vowels",
    },
    "cg": {
        "from_email": "sales@communitygroceries.com",
        "from_name": "Community Groceries",
        "team_name": "The Community Groceries Team",
        "brand_label": "Community Groceries",
    },
    "wihy": {
        "from_email": "kortney@wihy.ai",
        "from_name": "WiHY AI",
        "team_name": "The WIHY Team",
        "brand_label": "WIHY",
    },
}
_DEFAULT_BRAND = "vowels"

BOOK_PDF_URL = "https://whatishealthy.org/WhatisHealthy_FreeIntroduction.pdf"
CONFIRM_DOWNLOAD_URL = "https://whatishealthy.org/confirm-download.html"
BOOK_IMAGE_URL = "https://storage.googleapis.com/wihy-web-assets/images/book-green.jpg"
WIHY_URL = "https://wihy.ai"
WIHY_SUB_URL = "https://wihy.ai/subscription"
WIHY_ICON_URL = "https://storage.googleapis.com/wihy-web-assets/images/eden/eden-icon.png"
BOOK_URL = "https://whatishealthy.org"
UNSUBSCRIBE_URL = "https://whatishealthy.org/unsubscribe"

CG_URL = "https://communitygroceries.com"
CG_SUB_URL = "https://communitygroceries.com/subscription"
CG_ICON_URL = "https://storage.googleapis.com/wihy-web-assets/images/cora/cora-icon.png"

PAPERBACK_URL_FEMALE = "https://buy.stripe.com/dRmbJ13cu4dYcdz5t0ejK0i"
PAPERBACK_URL_MALE = "https://buy.stripe.com/aFafZheVc7qacdzg7EejK0j"
AMAZON_PAPERBACK_URL = "https://www.amazon.com/dp/B0FJ2494LH"
AMAZON_HARDCOVER_URL = "https://www.amazon.com/dp/B0FJ23J6JQ"
AMAZON_KINDLE_URL = "https://www.amazon.com/dp/B0DL7Z7NFL"
AMAZON_AUDIBLE_URL = "https://www.amazon.com/dp/B0GVWM74FR"

# ── Variant copy — dynamic keyword inserts per ad variant ─────────────────

_DEFAULT_COPY = {
    "goal": "eating healthier and taking control of what goes into your body",
    "desired_result": "finally understanding what's in your food and what to do about it",
    "big_benefit": "A healthier life",
    "topic": "healthy eating",
    "topic_benefit": "take control of their health through better food choices",
    "chapter_hook": "Chapter 3 breaks down the ingredients food companies hide behind 'natural flavors' — and what they're actually doing to your body.",
    "bullet1": "Why 'natural flavors' isn't what you think it is",
    "bullet2": "The one ingredient that shows up in 68% of packaged food — and why it matters",
    "bullet3": "Simple swaps you can make at your next grocery run",
    "download_cta": "Download Your Life-Changing Book",
}

VARIANT_COPY = {
    "weight": {
        "goal": "losing weight and keeping it off",
        "desired_result": "finally dropping the weight for good",
        "big_benefit": "A healthier body",
        "topic": "weight loss",
        "topic_benefit": "take control of their weight",
        "chapter_hook": "Chapter 5 breaks down why calories-in-calories-out is a myth — and what actually controls your weight.",
        "bullet1": "Why 'low-fat' and 'diet' labels may actually be making you gain weight",
        "bullet2": "The one ingredient in 68% of packaged food that keeps your body storing fat",
        "bullet3": "How to drop weight by changing WHAT you buy — not how much you eat",
        "download_cta": "Your Key to Finally Losing the Weight",
    },
    "kids": {
        "goal": "getting your kids eating healthy without the fights",
        "desired_result": "getting your kids off processed food for good",
        "big_benefit": "A healthier family",
        "topic": "kids and nutrition",
        "topic_benefit": "raise their kids on real food",
        "chapter_hook": "Chapter 7 exposes exactly how food companies engineer products to hook your children.",
        "bullet1": "Why your 'picky eater' isn't picky — they're addicted to engineered flavors",
        "bullet2": "3 simple swaps that make the transition painless for kids",
        "bullet3": "The after-school snack trick that changes everything",
        "download_cta": "Your Key to a Healthier Family",
    },
    "energy": {
        "goal": "getting your energy back and feeling like yourself again",
        "desired_result": "eliminating brain fog and afternoon crashes",
        "big_benefit": "All-day energy",
        "topic": "energy and nutrition",
        "topic_benefit": "stop feeling tired all the time",
        "chapter_hook": "Chapter 4 connects the dots between what you eat for breakfast and why you crash at 2pm.",
        "bullet1": "Why your morning 'healthy' cereal might be draining your energy by noon",
        "bullet2": "The blood-sugar trap hiding in foods you think are good for you",
        "bullet3": "One simple morning change that eliminates the afternoon crash",
        "download_cta": "Your Key to All-Day Energy",
    },
    "groceries": {
        "goal": "spending less on groceries while eating healthier",
        "desired_result": "cutting your grocery bill while eating better",
        "big_benefit": "Lower grocery bills",
        "topic": "grocery shopping and health",
        "topic_benefit": "stop overspending on food that isn't feeding their body",
        "chapter_hook": "Chapter 6 shows you exactly which 'premium' products are just repackaged junk — and what to buy instead.",
        "bullet1": "Why 'organic' and 'natural' labels cost you more but don't make you healthier",
        "bullet2": "The 5 grocery aisles where you're wasting the most money every week",
        "bullet3": "How to cut your food budget by 30% while eating better than before",
        "download_cta": "Your Key to Eating Better for Less",
    },
    "family": {
        "goal": "breaking the cycle of diet-related disease in your family",
        "desired_result": "protecting your family from the health problems you watched your parents go through",
        "big_benefit": "A healthier future",
        "topic": "family health",
        "topic_benefit": "make sure their family doesn't repeat the same health mistakes",
        "chapter_hook": "Chapter 8 shows why it was never genetics — it was habits passed down through food choices.",
        "bullet1": "Why the diseases you watched your parents fight weren't 'genetic' — they were dietary",
        "bullet2": "The 3 food habits silently being passed from generation to generation",
        "bullet3": "How one family dinner change can shift your kids' health trajectory",
        "download_cta": "Your Key to a Healthier Future",
    },
    "confused": {
        "goal": "finally understanding what's actually healthy",
        "desired_result": "cutting through the noise and knowing exactly what to eat",
        "big_benefit": "Clarity on health",
        "topic": "what's really healthy",
        "topic_benefit": "stop being confused about nutrition",
        "chapter_hook": "Chapter 2 explains why the advice keeps changing — and who profits when you stay confused.",
        "bullet1": "Why eggs, fat, and salt keep flip-flopping between 'good' and 'bad'",
        "bullet2": "The food industry's #1 strategy: keep you confused so you keep buying",
        "bullet3": "A dead-simple framework to know if something is actually healthy in 5 seconds",
        "download_cta": "Your Key to Knowing What's Actually Healthy",
    },
    "warning": {
        "goal": "knowing exactly what you're putting in your family's bodies",
        "desired_result": "never being fooled by a food label again",
        "big_benefit": "Label literacy",
        "topic": "food labels and marketing",
        "topic_benefit": "stop falling for food industry tricks",
        "chapter_hook": "Chapter 3 breaks down the 23 ingredients food companies hide behind 'natural flavors' — and what they do to your body.",
        "bullet1": "Why 'natural flavors' is the most misleading phrase on any food label",
        "bullet2": "The 5 'health foods' at your grocery store that are actually junk food in disguise",
        "bullet3": "How to read any food label in 10 seconds and know if it's real food",
        "download_cta": "Your Key to Reading Every Label Right",
    },
    "realfood": {
        "goal": "feeding your family real food without spending more money",
        "desired_result": "getting real food on your table this week without blowing your budget",
        "big_benefit": "Real food, same budget",
        "topic": "eating real food on a budget",
        "topic_benefit": "feed their family real food without going broke",
        "chapter_hook": "Chapter 6 proves you don't need a bigger grocery budget — you need to stop buying the foods the industry tricked you into thinking are healthy.",
        "bullet1": "Why the 'healthy' aisle is the most overpriced section of the grocery store",
        "bullet2": "5 real-food swaps that cost LESS than what you're buying now",
        "bullet3": "The meal planning shortcut that saves most families $200+ per month",
        "download_cta": "Your Key to Real Food on Any Budget",
    },
    "eliminate": {
        "goal": "losing weight and saving money by cutting the right foods",
        "desired_result": "dropping weight and grocery costs at the same time",
        "big_benefit": "Less weight, less spending",
        "topic": "hidden 'health' foods",
        "topic_benefit": "stop buying foods that sabotage their health and wallet",
        "chapter_hook": "Chapter 3 reveals the 10 'health' foods that are keeping you overweight and costing you a fortune.",
        "bullet1": "Why that granola bar is worse for you than the candy bar next to it",
        "bullet2": "The fruit juice truth: how '100% natural' became 100% sugar",
        "bullet3": "10 immediate cuts that save you money AND help you lose weight this month",
        "download_cta": "Your Key to Cutting the Weight & the Cost",
    },
    "biglie": {
        "goal": "seeing through the food industry's lies and protecting your family",
        "desired_result": "never being manipulated by food marketing again",
        "big_benefit": "The truth about food",
        "topic": "what the food industry hides from you",
        "topic_benefit": "protect their family from industry manipulation",
        "chapter_hook": "Chapter 1 traces exactly how food companies convinced an entire generation that processed food was normal — and what it's costing your family.",
        "bullet1": "The marketing trick that makes processed food look healthier than real food",
        "bullet2": "Why childhood obesity tripled in one generation — and it wasn't because of laziness",
        "bullet3": "How to break the cycle so your kids don't inherit the same health problems",
        "download_cta": "Your Key to the Truth About Food",
    },
    "mistakes": {
        "goal": "stopping the grocery mistakes that cost you your health and money",
        "desired_result": "fixing the shopping habits that are quietly draining your wallet and health",
        "big_benefit": "Smarter grocery trips",
        "topic": "grocery shopping mistakes",
        "topic_benefit": "stop making costly mistakes at the grocery store",
        "chapter_hook": "Chapter 6 breaks down the 5 biggest mistakes families make at the grocery store — and shows you how to fix them starting on your next trip.",
        "bullet1": "Mistake #1: Trusting the 'healthy' shelf at your grocery store",
        "bullet2": "Mistake #3: Buying 'organic' everything (it's not what you think)",
        "bullet3": "The checkout-line fix that saves most families $50+ per month",
        "download_cta": "Your Key to Smarter Grocery Trips",
    },
    "finally": {
        "goal": "getting your family eating healthy without dieting or spending more",
        "desired_result": "finally eating healthy without the stress, rules, or extra cost",
        "big_benefit": "Health without the hassle",
        "topic": "eating healthy without dieting",
        "topic_benefit": "get healthy without counting calories or buying expensive food",
        "chapter_hook": "The book strips away everything that makes 'eating healthy' feel hard — no calorie counting, no meal kits, no overpriced organic everything.",
        "bullet1": "Why diets fail 95% of the time — and what to do instead",
        "bullet2": "The 'no diet' approach that helps families eat better on the same budget",
        "bullet3": "How to make the switch to real food without changing your schedule",
        "download_cta": "Your Key to Health Without the Hassle",
    },
}


def _get_copy(variant: str) -> dict:
    """Return variant-specific copy or defaults."""
    return VARIANT_COPY.get(variant, _DEFAULT_COPY)


# Map variant → brand (all current variants are Vowels ads)
_VARIANT_BRAND = {v: "vowels" for v in VARIANT_COPY}
# Future CG variants: _VARIANT_BRAND["cg_healthy"] = "cg"  etc.


def _get_brand_config(variant: str = "") -> dict:
    """Return brand config (sender, team name) for a variant."""
    brand = _VARIANT_BRAND.get(variant, _DEFAULT_BRAND)
    return BRAND_CONFIG[brand]


def _team(variant: str) -> str:
    """Return team sign-off name for a variant."""
    return _get_brand_config(variant)["team_name"]


# Nurture sequence: (stage, days_after_signup, template_id, subject)
# 20 emails walking the full book story — runs until unsubscribe
NURTURE_SEQUENCE = [
    ( 0,   0, "book_delivery",    "Before you start reading this, {first_name}"),
    ( 1,   1, "did_you_get_this", "I failed spectacularly."),
    ( 2,   3, "big_benefit",      "What's actually in \"natural flavors\""),
    ( 3,   5, "got_questions",    "The 5-second test for any food label"),
    ( 4,   7, "social_proof",     "What changed after Chapter 6"),
    ( 5,  10, "im_surprised",     "The chapter everyone dog-ears"),
    ( 6,  14, "sugar_truth",      "What is sugar, really?"),
    ( 7,  18, "working_class",    "The system isn't built to reward wellness"),
    ( 8,  23, "reversible",       "The diseases you're afraid of are lifestyle diseases"),
    ( 9,  29, "what_is_nutrition","What food actually is"),
    (10,  36, "teeth",            "Teeth don't grow back — and neither do some choices"),
    (11,  44, "community",        "Does this serve us — or harm us?"),
    (12,  53, "psychology",       "How many no's before a yes?"),
    (13,  63, "mental_health",    "1 in 4 adults under 30 now reports this"),
    (14,  74, "disconnection",    "Overfed. Undernourished. Connected to nothing."),
    (15,  86, "real_food",        "You don't need perfection. You need direction."),
    (16, 100, "fasting",          "What fasting teaches us about love"),
    (17, 115, "breaking_cycle",   "The power of one generation"),
    (18, 130, "blue_zones",       "What people who live to 100 actually eat"),
    (19, 150, "where_next",       "Where do we go from here?"),
]


# ── Email wrapper ─────────────────────────────────────────────────────────────

def _email_wrap(content: str, variant: str = "") -> str:
    """Lightweight, personal email wrapper — white bg, no colored banner."""
    b = _get_brand_config(variant)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;">
{content}
<tr><td style="padding:16px 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:0 0 6px;font-size:13px;line-height:1.6;color:#6b7280;">
You're receiving this because you subscribed to Vowels. We send real research, real stories,
and no sponsored content.</p>
<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;">
<a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
&middot; Sent by {b['brand_label']}
</p></td></tr>
</table></td></tr></table></body></html>"""


def _cta_button(label: str, url: str, color: str = "#1e40af") -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;'
        f'font-size:16px;font-weight:600;text-decoration:none;padding:14px 28px;'
        f'border-radius:6px;">{label}</a>'
    )


def _bullets(c: dict) -> str:
    return f"""<ul style="margin:0 0 24px;padding-left:20px;font-size:16px;line-height:2;color:#374151;">
<li>{c['bullet1']}</li>
<li>{c['bullet2']}</li>
<li>{c['bullet3']}</li>
</ul>"""


def _paperback_buttons() -> str:
    return f"""<div style="text-align:center;margin-bottom:8px;">
{_cta_button("Order Paperback &mdash; Female Cover", PAPERBACK_URL_FEMALE, "#16a34a")}
</div>
<div style="text-align:center;margin-top:12px;">
{_cta_button("Order Paperback &mdash; Male Cover", PAPERBACK_URL_MALE, "#16a34a")}
</div>"""


def _all_format_buttons() -> str:
    """2-column pill-button grid for all 6 purchase formats. Email-safe tables."""
    def cell(label: str, url: str, color: str) -> str:
        return (
            f'<td width="50%" style="padding:0 4px 8px;">'
            f'<table width="100%" cellpadding="0" cellspacing="0"><tr>'
            f'<td align="center" bgcolor="{color}" style="border-radius:6px;">'
            f'<a href="{url}" target="_blank"'
            f' style="display:block;padding:13px 10px;color:#ffffff;font-size:14px;'
            f'font-weight:700;text-decoration:none;line-height:1.3;'
            f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
            f'{label}</a></td></tr></table></td>'
        )
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 4px;">'
        '<tr>'
        + cell("Ship Paperback<br/>Female Cover", PAPERBACK_URL_FEMALE, "#15803d")
        + cell("Ship Paperback<br/>Male Cover",   PAPERBACK_URL_MALE,   "#15803d")
        + '</tr><tr>'
        + cell("Amazon Paperback",                AMAZON_PAPERBACK_URL, "#c45000")
        + cell("Amazon Hardcover",                AMAZON_HARDCOVER_URL, "#1f2937")
        + '</tr><tr>'
        + cell("Kindle Edition",                  AMAZON_KINDLE_URL,    "#1a5c8a")
        + cell("Audible Audiobook",               AMAZON_AUDIBLE_URL,   "#b45309")
        + '</tr></table>'
    )


def _soft_buy_section() -> str:
    """Compact, low-pressure book mention. Information-first newsletters."""
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">'
        f'<tr><td style="padding:20px 0 0;">'
        f'<p style="margin:0 0 12px;font-size:14px;line-height:1.7;color:#6b7280;">'
        f'This is an excerpt from <em>What Is Healthy?</em> by Kortney O. Lee &mdash; '
        f'264 pages on what the food industry doesn\'t want you to understand, and what to do about it. '
        f'Available in paperback, hardcover, Kindle, and Audible.</p>'
        f'<p style="margin:0;font-size:14px;line-height:1.7;color:#6b7280;">'
        f'<a href="{PAPERBACK_URL_FEMALE}" style="color:#1e40af;text-decoration:underline;">Paperback (female cover)</a>'
        f' &middot; '
        f'<a href="{PAPERBACK_URL_MALE}" style="color:#1e40af;text-decoration:underline;">Paperback (male cover)</a>'
        f' &middot; '
        f'<a href="{AMAZON_KINDLE_URL}" style="color:#1e40af;text-decoration:underline;">Kindle</a>'
        f' &middot; '
        f'<a href="{AMAZON_AUDIBLE_URL}" style="color:#1e40af;text-decoration:underline;">Audible</a>'
        f' &middot; '
        f'<a href="{AMAZON_HARDCOVER_URL}" style="color:#1e40af;text-decoration:underline;">Hardcover</a>'
        f'</p></td></tr></table>'
    )


def _reply_cta(question: str = "") -> str:
    """Conversational reply invitation. Makes it a dialogue, not a broadcast."""
    q = question or "What do you think?"
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0">'
        f'<tr><td style="padding:20px 0 0;border-top:1px solid #f3f4f6;">'
        f'<p style="margin:0;font-size:15px;line-height:1.7;color:#374151;">'
        f'<strong>{q}</strong> Hit reply &mdash; we read every response.</p>'
        f'</td></tr></table>'
    )


def _brand_cards() -> str:
    """Stacked Eden + Cora rows: logo left, name + description + link right. No backgrounds."""
    def card(icon_url: str, name: str, tagline: str, description: str, cta: str, link: str) -> str:
        return (
            f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 16px;">'
            f'<tr>'
            f'<td width="56" valign="top" style="padding:0 14px 0 0;">'
            f'<img src="{icon_url}" width="48" height="48" alt="{name}"'
            f' style="display:block;border:0;border-radius:8px;" /></td>'
            f'<td valign="top">'
            f'<p style="margin:0 0 2px;font-size:15px;font-weight:700;color:#111827;'
            f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
            f'{name} &mdash; <span style="font-weight:400;color:#6b7280;">{tagline}</span></p>'
            f'<p style="margin:0 0 6px;font-size:14px;line-height:1.7;color:#4b5563;'
            f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
            f'{description}</p>'
            f'<a href="{link}" target="_blank"'
            f' style="font-size:14px;font-weight:600;color:#1e40af;text-decoration:underline;'
            f'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
            f'{cta}</a>'
            f'</td></tr></table>'
        )
    return (
        card(
            WIHY_ICON_URL,
            "Eden by WIHY",
            "for your overall health goals",
            "Ask any food or health question, scan labels, and get straight answers. "
            "Eden is for people who want to understand their health from the inside out.",
            "Try Eden free",
            WIHY_SUB_URL,
        ) +
        card(
            CG_ICON_URL,
            "Cora by Community Groceries",
            "for singles &amp; empty nesters",
            "Real food at fair prices, sized for one or two. No bulk, no waste. "
            "Built for people who want to eat well without shopping for a household "
            "they no longer have.",
            "Try Cora free",
            CG_SUB_URL,
        )
    )


# ── Template builders ─────────────────────────────────────────────────────────

def _render_book_delivery(first_name: str, variant: str = "", **kw) -> str:
    """Day 0 — Preface. Conversational, info-first, soft sell, reply CTA."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Before you read this, I want to be upfront: this is an excerpt from a book I wrote.
I'm sharing it here because I think the question at the center of it is one worth
sitting with — and because this newsletter exists to have exactly this kind of
conversation.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
Take a few minutes with this one.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 4px;font-size:13px;font-weight:700;letter-spacing:0.08em;
   text-transform:uppercase;color:#9ca3af;">From the Preface</p>
<p style="margin:0 0 20px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
What is healthy?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Is it the absence of disease? Daily trips to the gym? A fridge full of organic food?
A number on the scale? A strict diet? Or is it glowing skin and visible abs?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Ask ten people and you'll likely get ten different answers. Even among those who seem
healthy, definitions differ. But one truth is clear: health is foundational. It
influences how we live, how we feel, and how we care for those around us.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
And yet, somewhere along the way, we've lost clarity. We didn't stop believing in real
food — we just stopped recognizing it. Today, we trust the packaged over the perishable,
defend what's convenient, and market what's artificial as if it's nourishment. The truth
is many of us don't even know what real food is anymore.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
But let's be honest: if fruits and vegetables weren't real, they wouldn't rot. And if
processed foods were harmless, we wouldn't see a rise in diet-related illnesses like
type 2 diabetes, heart disease, and obesity year after year — especially among children.
The industry tells one story. The numbers tell another.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Meanwhile, a generation of children is growing up more fatigued, more overweight, and
more dependent on medication than ever before. In this series of emails, we'll explore
what it truly means to be healthy, how our environment and habits shape that reality,
and what it takes to reclaim our well-being — not just for ourselves but for the
generations that follow.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#9ca3af;text-align:right;font-style:italic;">
— Kortney O. Lee, <em>What Is Healthy?</em></p>
</td></tr>
<tr><td style="padding:0 40px 24px;">
{_reply_cta("What's your answer to that question?")}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Tomorrow — the night that started all of this.</p>
<p style="margin:20px 0 0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_did_you_get_this(first_name: str, variant: str = "", **kw) -> str:
    """Day 1 — the bathroom incident, Hello World. Exact book passages. Buy CTA."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 16px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
Here is the introduction to <strong>What Is Healthy?</strong> — the night that
started everything.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
Introduction</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
It was the middle of the night, and I woke up with an urgent need to pee. I raced up
the eight steps toward the bathroom, fueled by sheer panic and determination not to
have an accident. Spoiler alert: I failed spectacularly.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Despite my best efforts, I lost control — peeing on myself, the walls, the floor —
everywhere but the toilet. It felt like a scene from a poorly scripted comedy, except
I wasn't laughing. I was gasping for air, my heart pounding like I'd run a marathon.
My vision blurred. I felt lightheaded. And to make matters worse, I slipped and fell —
landing in a position that can only be described as undignified.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The commotion didn't even wake my wife. No one came rushing to my side. I just sat
there, a grown man, alone in a puddle of my own mess — out of breath, embarrassed,
and utterly defeated.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
It was as if my body had finally staged an intervention and said, "Enough is enough,
buddy. Time to get it together."</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
In that moment, as shame and humiliation washed over me — along with, well, other
things — I realized something had to change. Just a few weeks earlier, a friend had
given me a blunt assessment: "You're fat as F—." I played it off with a laugh, but
the truth is, it got to me. I did what most people do — I denied it. But now, I
couldn't ignore it. My body was screaming for help, and it was time I started
listening. This wasn't just an inconvenient wake-up call — it was a blaring siren
demanding action.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My thoughts turned to my children. They were too young to understand what was
happening, too small to remember that night. But one day, they would grow up watching
me. Learning from me. Being shaped by the habits I passed down — whether I meant to
or not.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
That moment, as humiliating as it was, became a turning point. This wasn't about
quick fixes or crash diets anymore. It was about change. Real lasting change. Not
just for me — but for the legacy I was shaping.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
So who am I?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Hello, World. My name is Kortney Lee.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
When you're first taught to write code, the introduction often begins with a simple
program that prints one phrase: Hello, World. That single line represents the start
of something new — simple on the surface, but full of possibility. That's how this
began for me. Not with a perfect plan. But with a line. A choice. A moment of
clarity. And a lot of questions.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
In my life, that line got printed the night I found myself lying on the floor —
confused, winded, and unsure of how it got that bad. That was my Hello, World moment.
Not the start of another diet or fitness plan, but the first real interruption in the
script I had been living on autopilot. It was the moment I knew I had to break the
cycle — or at least figure out how it started. What caused it. What was keeping it alive.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, Introduction, pp. 1–3</p>
</td></tr>
<tr><td style="padding:20px 40px 24px;border-top:2px solid #111827;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Chapter 1 asks the question Kortney couldn't stop asking after that night:</p>
<p style="margin:0 0 16px;font-size:17px;font-weight:600;line-height:1.85;color:#111827;">
"How did we get here?"</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.</p>
<p style="margin:20px 0 0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_big_benefit(first_name: str, variant: str = "", **kw) -> str:
    """Day 3 — natural flavors deep dive + variant-specific callout."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Here is something from the book I think about every time I walk through a grocery store.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Pick up any packaged food and find the ingredients list. Look for the words <strong>natural flavors</strong>.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
You will find it on almost everything — granola bars, yogurt, flavored water, crackers, baby food. It sounds harmless. The word "natural" is right there.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Here is what the label does not tell you: "natural flavors" is a legal catch-all that covers over 3,000 approved additives. Under FDA rules, any substance originally derived from a plant or animal — no matter how extensively processed — qualifies. The term was not created to inform you. It was created to satisfy disclosure requirements while revealing as little as possible.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
This is not an accident. It is a design decision made by an industry that spent decades lobbying for label language that sounds reassuring while saying nothing.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#fffbeb"
       style="border-left:3px solid #d97706;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 8px;font-weight:700;color:#92400e;">What this means for {c['topic']}:</p>
<p style="margin:0 0 8px;">{c['bullet1']}</p>
<p style="margin:0 0 8px;">{c['bullet2']}</p>
<p style="margin:0;">{c['bullet3']}</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<p style="margin:20px 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['chapter_hook']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
There are 22 more chapters like this in the book. Each one changes how you read a label and what ends up in your cart.</p>
{_reply_cta("What label surprised you most recently?")}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_got_questions(first_name: str, variant: str = "", **kw) -> str:
    """Day 5 — the 5-second label test framework. Eden by WIHY plug."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
One of the most practical things in the book is a framework I call the 5-second label test. Here is the short version:</p>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#f0fdf4"
       style="border-left:3px solid #16a34a;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 12px;font-weight:700;color:#166534;">The 5-Second Label Test</p>
<p style="margin:0 0 10px;"><strong>1.</strong> Flip the package. Find the ingredients list, not the nutrition facts panel.</p>
<p style="margin:0 0 10px;"><strong>2.</strong> Count how many ingredients have names you could not say out loud in a normal conversation. Not technical abbreviations — just: would a person ever call this an ingredient at home?</p>
<p style="margin:0 0 10px;"><strong>3.</strong> If more than two fail that test, put it back.</p>
<p style="margin:0;">That is it. No chemistry degree needed. Five seconds and the back of the package.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<p style="margin:20px 0 20px;font-size:16px;line-height:1.8;color:#374151;">
The book has 11 more frameworks like this — for reading labels quickly, spotting hidden sugars across 61 different names, and identifying which products in the health food aisle are not what they claim to be.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{_reply_cta("What's a food habit you've questioned lately?")}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 12px;font-size:15px;line-height:1.8;color:#6b7280;">
Two tools I built alongside the book — both free to start:</p>
{_brand_cards()}
<p style="margin:14px 0 0;font-size:13px;line-height:1.7;color:#9ca3af;">
Eden is for anyone working on their overall health. Cora is for people cooking for one
or two who want real food without the bulk-store quantities.</p>
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Best,<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_social_proof(first_name: str, variant: str = "", **kw) -> str:
    """Day 7 — reader story as narrative. Specific outcome. Clean quote block."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
A reader named Sarah sent me a message a few weeks after reading the book.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
She had just finished Chapter 6 — the one about how grocery stores are physically designed to push you toward high-margin processed items — and walked into a store the next day. She noticed the end-cap displays. The eye-level shelf placement. The sale signage positioned exactly where foot traffic is highest.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
She wrote: "I walked out with half the things I normally buy and spent $40 less. I wasn't even trying. I just couldn't un-see it."</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
That is what the book is built to do. Not rules. Not a diet. Just the kind of understanding that, once you have it, changes every food decision automatically.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#f9fafb"
       style="border-left:3px solid #9ca3af;font-size:15px;line-height:1.9;color:#4b5563;">
<tr><td>
<p style="margin:0 0 8px;font-style:italic;">"I had my husband read Chapter 3 while I made dinner. He came downstairs and said: we have been lied to for 30 years. We cleared out half the pantry that night."</p>
<p style="margin:0;font-weight:600;color:#6b7280;">Marcus, reader</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 40px 24px;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_im_surprised(first_name: str, variant: str = "", **kw) -> str:
    """Day 10 — dog-eared chapter tease with specific grocery store insight."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
There is one chapter in <strong>What Is Healthy?</strong> that readers dog-ear more than any other.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
It is not the natural flavors chapter. It is not the one about the food industry's lobbying history. It is called "What the Grocery Store Doesn't Want You to Know" — and it is the most immediately useful chapter in the book.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">One insight from it:</p>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<table width="100%" cellpadding="20" cellspacing="0" bgcolor="#eff6ff"
       style="border-left:3px solid #1e40af;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 12px;">The average grocery store stocks 40,000 items. Research shows shoppers make 60 to 70 percent of purchase decisions in the store, not at home from a list.</p>
<p style="margin:0;">The layout — produce at the entrance, dairy at the back, end-caps and eye-level shelving throughout — is not designed for your convenience. It is designed by category managers whose job is to maximize impulse purchases of high-margin processed products.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<p style="margin:20px 0 20px;font-size:16px;line-height:1.8;color:#374151;">
The chapter walks through how this works aisle by aisle and gives you a shopping approach that routes around it. Most readers say they save $30 to $50 per trip just by changing how they walk through the store.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
That chapter alone is worth the cost of the book. There are 18 more like it.</p>
{_reply_cta("Have you ever noticed how a store was laid out against you?")}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_last_chance(first_name: str, variant: str = "", **kw) -> str:
    """Day 14 — honest final email. No hard sell. Eden + CG close."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">This is my last email.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Over the past two weeks I shared why I wrote this book, the opening chapter, what is actually in "natural flavors," a framework for reading any label in five seconds, a reader who saved $40 her first grocery trip, and the chapter that changes how people walk through a store.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
All of it comes from one 264-page book built on two years of research.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
I am not going to push hard here. If any of this made you think differently about a label, a grocery aisle, or what you are feeding your family, the book is worth it. If none of it landed, it is probably not the right time, and that is fine.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">{_soft_buy_section()}
</td></tr>
<tr><td style="padding:0 40px 16px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 6px;font-size:15px;line-height:1.8;color:#374151;">
Before I go — two things I built that come directly out of the same research as this book.</p>
<p style="margin:0 0 16px;font-size:15px;line-height:1.8;color:#6b7280;">
I started working on both of these the same year I started writing. They are different tools
for different people, but they come from the same place this book does.</p>
{_brand_cards()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Whatever you decide — keep reading those labels.</p>
<p style="margin:20px 0 0;font-size:16px;line-height:1.8;color:#374151;">
All the best,<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_buy_now_offer(first_name: str, variant: str = "", **kw) -> str:
    """Immediate buyer-intent push — short, direct, all formats."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 0;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
<strong>What Is Healthy?</strong> is 264 pages on what the food industry doesn't want
you to understand — and exactly what to do about it. No diet. No rules. Just the research
that changes how you see every food decision.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
</td></tr>
<tr><td style="padding:0 40px 8px;">
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:20px 40px 32px;border-top:1px solid #f3f4f6;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
To your health,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_sugar_truth(first_name: str, variant: str = "", **kw) -> str:
    """Day 14 — Sugar chapter from the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — the chapter on sugar.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
What Is Sugar, Really?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Sugar isn't just the white stuff in your kitchen. It's a category — and food companies
have become experts at hiding it under names most people don't recognize. Dextrose.
Maltodextrin. High-fructose corn syrup. Agave nectar. Cane juice. Rice syrup. Barley
malt. More than 61 names for the same molecule — all of them legal, all of them
designed to keep the ingredient from appearing at the top of the list.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The average American consumes 17 teaspoons of added sugar every day. The American
Heart Association recommends no more than 6 teaspoons for women and 9 for men.
That gap doesn't come from dessert. It comes from products marketed as healthy —
flavored yogurt, granola bars, pasta sauce, whole-grain bread, and "natural" fruit
drinks that contain more sugar per serving than a can of soda.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Why is sugar so addictive? Because it triggers dopamine — the same reward pathway
activated by other addictive substances. Food companies know this. The ratio of
sugar, fat, and salt in ultra-processed food is not accidental. It is engineered,
tested, and refined to hit what the industry calls the "bliss point" — the exact
combination that makes you want more before you've finished what's in front of you.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The silent strain: two in five American adults have prediabetes right now — and
eight in ten don't know it. Their insulin is working overtime every single day,
responding to blood sugar spikes from foods labeled "healthy." The damage accumulates
quietly, for years, before a diagnosis arrives.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, Sugar chapter</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_working_class(first_name: str, variant: str = "", **kw) -> str:
    """Day 18 — The working-class trade-off from the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — the chapter on convenience culture and the working-class trade-off.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
The System Isn't Built to Reward Wellness</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
For working-class Americans, the equation is brutal. If you're working two jobs,
managing a household, or standing on your feet all day in a labor-intensive role,
healthy living isn't just difficult — it feels out of reach.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The system isn't set up to reward wellness. It's built to extract labor.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
More than 36% of adults consume fast food on any given day — with the highest rates
among full-time workers. That statistic isn't a reflection of poor values. It's a
predictable outcome of a life built around survival, not sustainability. Breakfast
is skipped or grabbed from a drive-thru. Lunch is eaten in a car between jobs or
skipped entirely. Dinner is whatever's fast, cheap, and available — because
exhaustion rarely leaves room for intention.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
These aren't isolated decisions. They're what happens when a food environment is
designed for profit, not people — when convenience is marketed as a solution while
the underlying problem goes unaddressed.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "The Working-Class Trade-Off"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_reversible(first_name: str, variant: str = "", **kw) -> str:
    """Day 23 — Lifestyle diseases are reversible. From the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
Something important from the book — something most doctors don't say clearly enough.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
The Diseases You're Afraid of Are Lifestyle Diseases</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Conditions like type 2 diabetes, cardiovascular disease, obesity, and hypertension
are diet-related chronic illnesses. What we eat, how we move, how we manage stress,
and what we do consistently over time — these don't happen overnight. They build up.
They are lifestyle-driven.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Which means they are also lifestyle-reversible.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
This is not a guarantee and it is not a replacement for medical care. But it is a
truth that gets buried under the weight of pharmaceutical marketing, insurance
incentives, and a healthcare system that profits more from treating illness than
preventing it. The research is clear: consistent changes to diet and movement can
reverse prediabetes, reduce blood pressure, and dramatically lower cardiovascular risk
— in some cases more effectively than medication alone.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
You were not born with a destiny to be sick. You inherited habits. And habits can change.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "Medications That Cured — Not Just Treated"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_what_is_nutrition(first_name: str, variant: str = "", **kw) -> str:
    """Day 29 — What food actually is. Nutrition 101 from the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the Nutrition 101 chapter — what food actually is, stripped of the marketing.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
Food as Fuel vs. Food as Habit</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The body doesn't care what a label says. It responds to what you give it. Macronutrients
— proteins, carbohydrates, and fats — are the three categories of food your body uses
for energy, repair, and function. Every meal is a combination of them. The question is
whether the combination you're eating is doing the work your body needs, or working
against it.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Most Americans have been taught to think about food in terms of calories — but calories
are a measure of energy, not nutrition. A 200-calorie snack of almonds and a 200-calorie
serving of crackers hit the body very differently. One sustains. One spikes. The label
doesn't tell you which is which. The macronutrient breakdown does.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The NOVA food classification system, developed by researchers at the University of
Sao Paulo, sorts food not by calories but by how it's processed — and the research
is clear: the more processed a food is, the more likely it is to drive inflammation,
disrupt hunger signals, and contribute to chronic disease — regardless of its
calorie count.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Students in the US receive fewer than eight hours of nutrition education per year.
Eight hours. That gap has consequences that last a lifetime.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, Nutrition 101</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_teeth(first_name: str, variant: str = "", **kw) -> str:
    """Day 36 — Teeth and systemic health. From the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
This one surprises people. From the book.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
Teeth Don't Grow Back — and Neither Do Some Choices</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Most people don't connect their teeth to their heart. They should.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Oral health is one of the clearest windows into systemic health. The bacteria that
accumulate in an unhealthy mouth don't stay there — they enter the bloodstream and
have been linked to cardiovascular disease, diabetes complications, and cognitive
decline. The mouth is not a separate system. It is part of the whole.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Enamel erosion — caused by acid from sugary and processed foods — cannot be
reversed. Once decay progresses, restoration becomes the only option. Root canals.
Extractions. Implants. Thousands of dollars, and years of damage, from a pattern
of eating that was never questioned.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Flossing may feel small. In the book, I use it as a metaphor for the whole problem:
we know what to do, we know the consequences of not doing it, and we still delay —
because there's no immediate pain. Until there is.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "Teeth Don't Grow Back"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_community(first_name: str, variant: str = "", **kw) -> str:
    """Day 44 — Community and culture chapter from the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — the chapter on community, culture, and the hardest question to ask.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
Does This Serve Us — or Harm Us?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Some of the most damaging norms go unchallenged simply because they're familiar.
Pizza on Fridays becomes pizza every day. The church potluck becomes the template
for what celebration looks like. The food at funerals, at holidays, at baby showers —
it's all comfort, all tradition, and in many cases, all disease.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Change starts by asking one simple question: Does this serve us — or does it harm us?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
When a community starts asking that together, they don't just reject what's broken.
They build something better: access, equity, and long-term well-being. The solution
doesn't start with policy. It starts at the table — with one family deciding to
ask a different question about what they're eating and why.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
You are a product of your environment — until you decide not to be. That decision
is yours. And the next generation deserves the version of you that chooses differently.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "The Role of Community"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_psychology(first_name: str, variant: str = "", **kw) -> str:
    """Day 53 — Psychology of change. From the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — the chapter on why change is hard, and what actually makes it happen.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
How Many No's Before a Yes?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Most people don't change when they learn something new. They change when the pain of
staying the same becomes greater than the fear of changing. That gap — between knowing
what to do and actually doing it — is where most health journeys stall.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
I've learned that the number of times someone says no to change before they say yes
has less to do with willpower and more to do with environment. Who's around them.
What's available. What's been normalized. What story they were told about who they are.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The psychology of change isn't about motivation. It's about identity. People don't
sustain behaviors that conflict with how they see themselves. The first step isn't a
diet — it's a different answer to the question: who am I, and what do people like me do?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
What matters is what you do next. Not what you've done. Not what you should have done.
What happens in the next meal, the next grocery trip, the next moment you're tired and
it's easier to grab something fast. That's where health is actually made.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "The Psychology of Change"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_mental_health(first_name: str, variant: str = "", **kw) -> str:
    """Day 63 — Mental health and food as coping. From the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
A chapter from the book that doesn't get talked about enough.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
1 in 4 Adults Under 30 Now Reports This</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Rates of anxiety and depression have climbed sharply over the past two decades —
especially among teens and young adults. According to the CDC, nearly one in four
adults under thirty now reports symptoms of anxiety or depression. That number was
not always this high. Something changed.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The research connecting diet and mental health is growing fast. The gut-brain axis —
the direct communication pathway between your digestive system and your brain — means
that what you eat affects not just your body but your mood, your focus, your
resilience under stress. Ultra-processed food disrupts the gut microbiome. A disrupted
microbiome produces less serotonin. And 90% of the body's serotonin is made in the gut,
not the brain.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Real health is mental health. And mental health doesn't come from pills alone. It comes
from nourishment. From movement. From connection. From a system that stops selling
stimulation and starts offering support.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "Addiction, Anxiety, and the Hidden Cost of Coping"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_disconnection(first_name: str, variant: str = "", **kw) -> str:
    """Day 74 — Overfed but undernourished. Disconnection chapter from the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — the part that hit me hardest to write.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
Overfed. Undernourished. Connected to Nothing.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
We are overstimulated but under-touched. Overfed but undernourished. Exposed to
everything — connected to nothing.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Food used to be the center of connection. It was how families gathered, how communities
celebrated, how cultures preserved identity. Something happened between that version of
food and the one we live with now — and it wasn't just a change in ingredients. It was
a change in relationship. We stopped eating together and started eating at screens.
We stopped cooking as a practice and started ordering as a convenience. We lost the
ritual, and with it, some of the meaning.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
If we want our health — and our relationships — to thrive, the healing has to start
within. Not with a number on a scale. Not with a quick fix. But with a willingness to
be present again. To turn off the screen. To make time. To say no to what numbs —
and yes to what restores.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "How Disconnection Replaces Love"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_real_food(first_name: str, variant: str = "", **kw) -> str:
    """Day 86 — Rediscovering real food. From the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — the chapter that tells you what to actually do.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
You Don't Need Perfection. You Need Direction.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
By now, you've seen the whole picture — how tradition became habit, how comfort
replaced intention, and how generations inherited the consequences. You've seen how
misinformation, culture, access, and marketing shape what ends up on our plates and
in our lives. You've seen how we make peace with illness and call it genetics — when
in reality, it's often modeled behavior, normalized dysfunction, and quiet surrender.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
But awareness disrupts that pattern. Awareness gives you the power to pause before
the next bite. To ask why. To choose differently. Because the future isn't written yet.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Real food isn't complicated. It's food that spoils. Food with ingredients you can
pronounce. Food that looks like what it is. The simplest rule in the book: if it
wouldn't exist without a factory, be suspicious of it. If it came from the ground, a
tree, or an animal without a five-step manufacturing process, your body knows what
to do with it.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
You don't need to be perfect. You need a direction. One meal at a time.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "Rediscovering Real Food"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_fasting(first_name: str, variant: str = "", **kw) -> str:
    """Day 100 — Fasting: spiritual and health perspectives. From the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
One of the chapters I didn't expect to love writing. From the book.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
What Fasting Teaches Us About Love</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Fasting has been practiced for thousands of years across every major religion and
culture. It is one of the oldest tools for clarity, discipline, and spiritual focus.
It is also, increasingly, one of the most well-researched interventions in metabolic
health.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Time-restricted eating — eating within a defined window and fasting the rest — has been
shown to improve insulin sensitivity, reduce inflammation, support cellular repair
through a process called autophagy, and reduce the risk of metabolic disease. Not
because it's a trick. Because it's how humans ate for most of history. Three meals a
day plus snacks is a modern invention, driven more by food industry revenue than by
biology.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
But the chapter isn't really about the science. It's about what happens when you
create space — from food, from noise, from constant consumption. Fasting creates
space. And healing fills it. That's true whether you're approaching it from faith,
from health, or simply from a desire to understand your relationship with food
at a deeper level.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "When Did Fasting Lose Its True Meaning?"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
More in a few days.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_breaking_cycle(first_name: str, variant: str = "", **kw) -> str:
    """Day 115 — Breaking the cycle. Power of one generation. From the book."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — the chapter that brings it all together.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
The Power of One Generation</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The habits we pass down are not inevitable. They feel inevitable because they are familiar,
because they were modeled for us before we could question them, and because the systems
around us are designed to keep them in place. But they are habits. Not destiny.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
One generation that asks different questions changes the trajectory for every generation
that follows. Not by being perfect. Not by having all the answers. But by refusing to
pass the confusion and the silence down unchanged.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
What we accept as normal becomes their starting point. What we don't question becomes
their burden to explain, solve, and fix. The most powerful thing you can do for the
people who come after you is to do the work now — imperfectly, openly, visibly —
so they inherit something different than what you were given.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "Breaking the Cycle"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Two more emails coming.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_blue_zones(first_name: str, variant: str = "", **kw) -> str:
    """Day 130 — Blue Zones: what people who live to 100 actually eat."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
From the book — Lessons from the Blue Zones.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
What People Who Live to 100 Actually Eat</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The Blue Zones are five regions of the world where people live measurably longer,
healthier lives — Okinawa, Japan; Sardinia, Italy; Nicoya, Costa Rica; Ikaria, Greece;
and Loma Linda, California. Researchers have studied these populations for decades.
What they found was not what the supplement industry hoped for.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
They eat mostly plants. They eat until they're 80% full — a practice the Okinawans
call hara hachi bu. They don't diet. They don't count calories. They eat the foods
their grandparents ate, prepared the way their grandparents prepared them, at a
table with people they care about.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
They also move naturally — not through gym memberships but through lives built around
walking, gardening, and physical work. They belong to communities that provide meaning
and accountability. They have a reason to get up in the morning.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The lesson from the Blue Zones isn't a diet. It's a way of life — and most of it has
nothing to do with supplements or superfoods. It has everything to do with what we've
traded away in the name of convenience.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "Lessons from the Blue Zones"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta()}
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
One more email after this.<br/>Kortney</p>
</td></tr>""", variant=variant)


def _render_where_next(first_name: str, variant: str = "", **kw) -> str:
    """Day 150 — Final email. Where do we go from here? All CTAs. Eden + Cora."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 16px;font-size:16px;line-height:1.8;color:#374151;">Hey {first_name},</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.8;color:#374151;">
The last chapter of <strong>What Is Healthy?</strong></p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
Where Do We Go from Here?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Not: "What's healthy?" But: "What's true — for you, your family, and your future?"</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Not: "How do I fix everything overnight?" But: "What do I need to keep, question,
or let go of — on purpose?"</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Rewriting the narrative doesn't mean rejecting who you are. It means questioning
everything you were taught — because future generations are learning from your example.
What we accept as normal becomes their starting point. What we don't question becomes
their burden.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
I started this book on the floor of a bathroom at two in the morning. I didn't know
then that the question I was asking about myself — how did I get here? — would become
the question I'd spend years trying to answer for my family, my community, and anyone
willing to listen.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The answer isn't a diet. It isn't a supplement. It isn't a program. It's a decision —
made again every day, imperfectly, intentionally — to choose something better than
what was handed to you.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#6b7280;text-align:right;font-style:italic;">
— <em>What Is Healthy?</em>, "Where Do We Go from Here?"</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 12px;font-size:16px;line-height:1.8;color:#374151;">
{_soft_buy_section()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 16px;font-size:15px;line-height:1.8;color:#374151;">
Two tools I built that come from the same place this book does:</p>
{_brand_cards()}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Whatever you decide — keep reading those labels.</p>
<p style="margin:20px 0 0;font-size:16px;line-height:1.8;color:#374151;">
All the best,<br/>Kortney</p>
</td></tr>""", variant=variant)


# Template renderer lookup
_RENDERERS = {
    "book_delivery":    _render_book_delivery,
    "did_you_get_this": _render_did_you_get_this,
    "big_benefit":      _render_big_benefit,
    "got_questions":    _render_got_questions,
    "social_proof":     _render_social_proof,
    "im_surprised":     _render_im_surprised,
    "last_chance":      _render_last_chance,
    "sugar_truth":      _render_sugar_truth,
    "working_class":    _render_working_class,
    "reversible":       _render_reversible,
    "what_is_nutrition":_render_what_is_nutrition,
    "teeth":            _render_teeth,
    "community":        _render_community,
    "psychology":       _render_psychology,
    "mental_health":    _render_mental_health,
    "disconnection":    _render_disconnection,
    "real_food":        _render_real_food,
    "fasting":          _render_fasting,
    "breaking_cycle":   _render_breaking_cycle,
    "blue_zones":       _render_blue_zones,
    "where_next":       _render_where_next,
    "buy_now_offer":    _render_buy_now_offer,
}


# ── Sending ───────────────────────────────────────────────────────────────────

async def send_nurture_email(to_email: str, first_name: str, template_id: str, subject: str, **kwargs) -> bool:
    """Send a single nurture email via SendGrid."""
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping nurture email")
        return False

    renderer = _RENDERERS.get(template_id)
    if not renderer:
        logger.error(f"Unknown nurture template: {template_id}")
        return False

    name = first_name or "there"
    # Resolve dynamic subject placeholders
    variant = kwargs.pop("variant", "")
    c = _get_copy(variant)
    rendered_subject = (
        subject
        .replace("{first_name}", name)
        .replace("{big_benefit}", c["big_benefit"])
        .replace("{topic}", c["topic"])
    )
    html_body = renderer(name, variant=variant, **kwargs)

    # Resolve brand-specific sender
    brand = _get_brand_config(variant)
    payload = {
        "personalizations": [{
            "to": [{"email": to_email}],
            **({"bcc": [{"email": BOOK_EMAIL_BCC}]} if BOOK_EMAIL_BCC and BOOK_EMAIL_BCC.lower() != to_email.lower() else {}),
        }],
        "from": {"email": brand["from_email"], "name": brand["from_name"]},
        "subject": rendered_subject,
        "content": [{"type": "text/html", "value": html_body}],
        "tracking_settings": {
            "click_tracking": {"enable": True, "enable_text": False},
            "open_tracking": {"enable": True},
        },
        "categories": ["nurture", template_id],
        "custom_args": {"template_id": template_id, "lead_email": to_email},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201, 202):
                logger.info(f"Nurture email [{template_id}] sent to {to_email}")
                return True
            elif resp.status_code == 401 and "credits" in resp.text.lower():
                logger.error(f"SendGrid credit limit exceeded — aborting cron run")
                raise _SendGridCreditExhausted(resp.text)
            else:
                logger.error(f"SendGrid nurture error {resp.status_code}: {resp.text}")
                return False
        except _SendGridCreditExhausted:
            raise
        except Exception as e:
            logger.error(f"Nurture email delivery failed: {e}")
            return False


async def trigger_day0(email: str, first_name: str, variant: str = "") -> bool:
    """Send the Day 0 book_delivery nurture email and advance stage."""
    sent = await send_nurture_email(
        to_email=email,
        first_name=first_name,
        template_id="book_delivery",
        subject="Your free copy is here, {first_name}",
        variant=variant,
    )
    if sent:
        # Advance to stage 1 so cron doesn't resend Day 0
        try:
            from src.services.book_leads_service import _get_firestore, COLLECTION, mark_delivered

            await mark_delivered(email)
            db = _get_firestore()
            now = datetime.now(timezone.utc)
            query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
            async for doc in query.stream():
                created_at = doc.to_dict().get("created_at", now)
                await doc.reference.update({
                    "nurture_stage": 1,
                    "nurture_next_at": created_at + timedelta(days=1),
                    "nurture_book_delivery_sent_at": now,
                })
        except Exception as e:
            logger.warning(f"Failed to advance nurture stage after Day 0: {e}")
    return sent


async def trigger_buy_now(email: str, first_name: str, variant: str = "") -> bool:
    """Send immediate buy-now email and close free-book nurture for this lead."""
    sent = await send_nurture_email(
        to_email=email,
        first_name=first_name,
        template_id="buy_now_offer",
        subject="Start now, {first_name} - your copy is ready",
        variant=variant,
    )
    if sent:
        try:
            from src.services.book_leads_service import _get_firestore, COLLECTION

            db = _get_firestore()
            now = datetime.now(timezone.utc)
            query = (
                db.collection(COLLECTION)
                .where("email", "==", email.lower().strip())
                .limit(1)
            )
            async for doc in query.stream():
                await doc.reference.update({
                    "funnel_stage": "buyer_intent_contacted",
                    "sequence_status": "completed",
                    "nurture_buy_now_offer_sent_at": now,
                })
        except Exception as e:
            logger.warning(f"Failed to update buy-now status: {e}")
    return sent


# ── Cron processor ────────────────────────────────────────────────────────────

class _SendGridCreditExhausted(Exception):
    """Raised when SendGrid returns 401 credit limit exceeded — aborts the cron loop."""


async def process_pending_nurture() -> dict:
    """Process all leads with pending nurture emails. Called by cron."""
    from src.services.book_leads_service import _get_firestore, COLLECTION

    db = _get_firestore()
    now = datetime.now(timezone.utc)
    stats = {"processed": 0, "sent": 0, "errors": 0, "completed": 0}

    # Find active leads whose next nurture is due
    query = (
        db.collection(COLLECTION)
        .where("sequence_status", "==", "active")
        .where("nurture_next_at", "<=", now)
        .limit(50)
    )

    async for doc in query.stream():
        data = doc.to_dict()
        stats["processed"] += 1
        email = data.get("email", "")
        first_name = data.get("first_name", "")
        current_stage = data.get("nurture_stage", 0)
        variant = data.get("utm_content", "")

        # Find the next stage to send
        next_entry = None
        for stage, days, template_id, subject in NURTURE_SEQUENCE:
            if stage == current_stage:
                next_entry = (stage, days, template_id, subject)
                break

        if not next_entry:
            # Sequence complete
            await doc.reference.update({"sequence_status": "completed"})
            stats["completed"] += 1
            continue

        _, _, template_id, subject = next_entry

        try:
            sent = await send_nurture_email(
                email, first_name, template_id, subject, variant=variant,
            )
        except _SendGridCreditExhausted:
            stats["credit_exhausted"] = True
            logger.error("SendGrid credits exhausted — stopping cron run early")
            break

        if sent:
            stats["sent"] += 1
            # Advance to next stage
            next_stage = current_stage + 1
            # Find next stage's delay
            next_delay_days = None
            for stage, days, _, _ in NURTURE_SEQUENCE:
                if stage == next_stage:
                    next_delay_days = days
                    break

            if next_delay_days is not None:
                created_at = data.get("created_at", now)
                next_at = created_at + timedelta(days=next_delay_days)
                await doc.reference.update({
                    "nurture_stage": next_stage,
                    "nurture_next_at": next_at,
                    "send_failure_count": 0,
                    f"nurture_{template_id}_sent_at": now,
                })
            else:
                # No more stages — mark completed
                await doc.reference.update({
                    "nurture_stage": next_stage,
                    "sequence_status": "completed",
                    "send_failure_count": 0,
                    f"nurture_{template_id}_sent_at": now,
                })
                stats["completed"] += 1
        else:
            stats["errors"] += 1
            failure_count = data.get("send_failure_count", 0) + 1
            try:
                from src.services.book_leads_service import mark_send_failed
                await mark_send_failed(doc.reference, failure_count)
            except Exception as fe:
                logger.warning(f"Failed to record send failure for {email}: {fe}")

    logger.info(f"Nurture cron: {stats}")
    return stats
