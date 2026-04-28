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

BOOK_PDF_URL = "https://whatishealthy.org/WhatisHealthy_eBook.pdf"
CONFIRM_DOWNLOAD_URL = "https://whatishealthy.org/confirm-download.html"
BOOK_IMAGE_URL = "https://storage.googleapis.com/wihy-web-assets/images/book/BookGreen.jpg"
WIHY_URL = "https://wihy.ai"
BOOK_URL = "https://whatishealthy.org"
UNSUBSCRIBE_URL = "https://whatishealthy.org/unsubscribe"

CG_URL = "https://communitygroceries.com"

PAPERBACK_URL_FEMALE = "https://buy.stripe.com/dRmbJ13cu4dYcdz5t0ejK0i"
PAPERBACK_URL_MALE = "https://buy.stripe.com/aFafZheVc7qacdzg7EejK0j"

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
NURTURE_SEQUENCE = [
    (0, 0,  "book_delivery",    "Your free copy is here, {first_name}"),
    (1, 1,  "did_you_get_this", "Did you get this?"),
    (2, 3,  "big_benefit",      "{big_benefit} waiting inside..."),
    (3, 5,  "got_questions",    "Got questions about {topic}?"),
    (4, 7,  "social_proof",     "Hundreds of readers can't be wrong..."),
    (5, 10, "im_surprised",     "Frankly, I'm a little surprised..."),
    (6, 14, "last_chance",      "Last chance..."),
]


# ── Email wrapper ─────────────────────────────────────────────────────────────

def _email_wrap(content: str, variant: str = "") -> str:
    """Lightweight, personal email wrapper — white bg, no colored banner."""
    b = _get_brand_config(variant)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;">
{content}
<tr><td style="padding:24px 32px;border-top:1px solid #f0f0f0;">
<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;text-align:center;">
Sent by {b['brand_label']} &middot; <a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
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


# ── Template builders ─────────────────────────────────────────────────────────

def _render_book_delivery(first_name: str, variant: str = "", **kw) -> str:
    """Day 0 — warm welcome + download link."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 16px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Thanks for grabbing a copy of <strong>What Is Healthy</strong>. I wrote this book because I got tired of seeing people get misled by food labels and marketing. I wanted to put the real research in one place — no fluff, no agenda.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
This book is a great first step towards {c['goal']}. And I'm sure you're going to get a lot out of it.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Your free digital copy is ready right now:</p>
</td></tr>
<tr><td style="padding:0 32px 16px;text-align:center;">
{_cta_button(c['download_cta'], CONFIRM_DOWNLOAD_URL)}
</td></tr>
<tr><td style="padding:16px 32px 12px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
I hope you enjoy it. And if you're the kind of person who likes to highlight, dog-ear, and keep a book on the kitchen counter — a lot of our readers prefer the physical copy. You can see what's inside and grab one here:</p>
</td></tr>
<tr><td style="padding:0 32px 16px;text-align:center;">
{_cta_button("See What's Inside", BOOK_URL)}
</td></tr>
<tr><td style="padding:8px 32px 32px;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
I'll check in with you tomorrow.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_did_you_get_this(first_name: str, variant: str = "", **kw) -> str:
    """Day 1 — check-in, tease paperback."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Yesterday you requested a copy of my free book, <strong>What Is Healthy?</strong>, and I just wanted to check in and see if you had a chance to read it yet.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
This book is a great first step towards {c['goal']}. And I'm sure you're going to get a lot out of it.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
But I also wanted to make sure you saw this — if you're really serious about {c['desired_result']}, a lot of our readers have found that having the physical copy on their kitchen counter changes everything.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
There's something about reaching for it right before a grocery trip that makes the information stick. It's $24.99 and we cover shipping. Same content you already have, just in a format you can highlight, dog-ear, and share with family.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
No pressure — the free digital copy is yours to keep either way.</p>
{_paperback_buttons()}
<p style="margin:24px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Hope to talk to you soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_big_benefit(first_name: str, variant: str = "", **kw) -> str:
    """Day 3 — value bullets, chapter tease, soft paperback mention."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
You recently grabbed a free copy of <strong>What Is Healthy?</strong></p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
And I'm glad you did. Because I'm always happy to connect with someone who wants to {c['topic_benefit']}.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
If you haven't started reading yet, here's what's waiting for you inside:</p>
{_bullets(c)}
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
And that's just the beginning. {c['chapter_hook']}</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
And whatever else we could pack into 200+ pages of real research — no filler.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
If you want the full experience, a lot of readers tell us the physical copy makes it easier to highlight, flip through before grocery runs, and keep handy in the kitchen. It's $24.99 with free shipping.</p>
{_paperback_buttons()}
<p style="margin:24px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Talk soon,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_got_questions(first_name: str, variant: str = "", **kw) -> str:
    """Day 5 — curse of knowledge angle, WIHY app mention."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
How are you finding <strong>What Is Healthy?</strong> so far?</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
I hope it's been useful. But maybe it provoked even more questions about {c['topic']}.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
That's what I call the curse of knowledge — the more information you get on a topic, the more confusing it can become. Because information alone isn't that useful.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Without something to help you sort through it, prioritize and actually use it, you can get lost down a rabbit hole of conflicting health advice.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
But there's a way out — and that's through experience.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
I've spent years researching what happened to our food system, working with real families, and building tools to make {c['goal']} as simple as possible. And during that time I've learned exactly what it takes to get results — without fad diets or expensive organic everything.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
That's why we built <strong>WIHY</strong> — a free app that lets you ask health questions, scan food labels, and get straight answers backed by real research. Think of it as having the book's knowledge in your pocket at the grocery store.</p>
<div style="text-align:center;margin-bottom:16px;">
{_cta_button("Try WIHY Free", WIHY_URL)}
</div>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
And here are a few things worth revisiting in the book:</p>
{_bullets(c)}
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
If you want to keep the book handy — on your counter, in your bag, wherever — the paperback is $24.99 with free shipping.</p>
{_paperback_buttons()}
<p style="margin:24px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_social_proof(first_name: str, variant: str = "", **kw) -> str:
    """Day 7 — testimonial, paperback upsell."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Since releasing <strong>What Is Healthy?</strong>, hundreds of readers have grabbed their copy — and the feedback has been incredible.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Here's what one reader had to say:</p>
<blockquote style="margin:0 0 20px;padding:16px 24px;background:#f9fafb;border-left:4px solid #1e40af;border-radius:4px;font-size:16px;line-height:1.8;color:#4b5563;font-style:italic;">
"I had no idea how much the food industry was manipulating what I thought was healthy. This book opened my eyes. I've already changed the way I shop for my family."
</blockquote>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Before I even wrote this book, I wanted to make sure the information would actually help real families make better choices. That's why every page is backed by research — not opinions, not trends, not sponsored advice.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
A lot of readers have told us that having the physical copy makes a huge difference. Something about holding it, flipping to a chapter before a grocery run, handing it to your partner — it just sticks.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
It's $24.99 and we cover shipping. Same content you already have, just in a format that lasts.</p>
{_paperback_buttons()}
<p style="margin:24px 0 0;font-size:17px;line-height:1.8;color:#374151;">
I hope the book is making a difference for you.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_im_surprised(first_name: str, variant: str = "", **kw) -> str:
    """Day 10 — urgency, why haven't you ordered?"""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Call me crazy, but I'm a little surprised you still haven't ordered the physical copy of <strong>What Is Healthy?</strong></p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
If you really want to start {c['desired_result']} (and I'm guessing you do — or you wouldn't have downloaded the book), then having it in your kitchen is the easiest way to make it happen.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Here's what you'll keep coming back to:</p>
{_bullets(c)}
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
And whatever else you find inside that changes the way you eat, shop, and feed your family.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
If you're serious about {c['goal']}, this should be a no-brainer for you.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
$24.99. Free shipping. Same book, just in your hands.</p>
{_paperback_buttons()}
<p style="margin:24px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_last_chance(first_name: str, variant: str = "", **kw) -> str:
    """Day 14 — final push. Paperback + CG + WIHY."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Are you still interested in {c['goal']}?</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
I'm asking because this is my last email to you.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Over the last two weeks I've been writing to you about <strong>What Is Healthy?</strong> — the book you downloaded for free. A lot of readers have ordered the physical copy and we're running through inventory faster than expected.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
If you'd still like the paperback — the version you can keep on your counter, flip through before grocery trips, and share with family — just click below. $24.99 with free shipping.</p>
{_paperback_buttons()}
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
If not, no hard feelings. Your free digital copy is yours to keep forever:</p>
<div style="text-align:center;margin-bottom:16px;">
{_cta_button("Re-download the Book", CONFIRM_DOWNLOAD_URL)}
</div>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Before we go, I also wanted to mention two things we've been building that connect directly to what the book is all about:</p>
<p style="margin:0 0 8px;font-size:17px;line-height:1.8;color:#374151;">
<strong>Community Groceries</strong> (<a href="{CG_URL}" style="color:#1e40af;">{CG_URL}</a>) — healthier products, better prices, delivered to your door.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
<strong>WIHY</strong> (<a href="{WIHY_URL}" style="color:#1e40af;">{WIHY_URL}</a>) — scan labels, ask health questions, and get real answers backed by research.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Whatever you decide — keep reading those labels.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
All the best,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


def _render_buy_now_offer(first_name: str, variant: str = "", **kw) -> str:
    """Immediate buyer-intent push for paid book leads."""
    c = _get_copy(variant)
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
You clicked because you want real answers now. If you are serious about {c['goal']},
get the physical copy of <strong>What Is Healthy?</strong> today.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
This is the same research-backed framework people use to clean up grocery decisions,
drop the confusion, and make better choices fast. No fluff. No food-industry spin.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
$24.99. Free shipping. Choose your cover below:</p>
{_paperback_buttons()}
<p style="margin:24px 0 0;font-size:17px;line-height:1.8;color:#374151;">
To your health,<br/>{_team(variant)}</p>
</td></tr>""", variant=variant)


# Template renderer lookup
_RENDERERS = {
    "book_delivery": _render_book_delivery,
    "did_you_get_this": _render_did_you_get_this,
    "big_benefit": _render_big_benefit,
    "got_questions": _render_got_questions,
    "social_proof": _render_social_proof,
    "im_surprised": _render_im_surprised,
    "last_chance": _render_last_chance,
    "buy_now_offer": _render_buy_now_offer,
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
            **({"bcc": [{"email": BOOK_EMAIL_BCC}]} if BOOK_EMAIL_BCC else {}),
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
