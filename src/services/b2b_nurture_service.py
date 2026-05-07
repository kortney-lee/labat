"""
B2B Nurture Service
5-email outreach sequence for: bookstores, libraries, podcasts, blogs, churches, schools.

Each Day 0 email:
  1. Why we're reaching out to THIS group specifically
  2. The specific ask (carry it / acquire it / interview me / review it)
  3. The preface — something real to read right now
  4. Book purchase links
  5. Reply CTA

Schedule: Day 0, 3, 7, 14, 21
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
FROM_EMAIL = os.getenv("B2B_FROM_EMAIL", "info@vowels.org")
FROM_NAME  = os.getenv("B2B_FROM_NAME",  "Kortney Lee")
BCC_EMAIL  = os.getenv("BOOK_EMAIL_BCC", "kortney@wihy.ai")

UNSUBSCRIBE_URL      = "https://whatishealthy.org/unsubscribe"
INGRAM_FEMALE_URL    = "https://shop.ingramspark.com/b/084?params=KdF9tI0DBCGxHsXvFp5EzonT2Vjy0qlWQPnReIEveSF"
INGRAM_MALE_URL      = "https://shop.ingramspark.com/b/084?params=ortH8rLGOSivIH3DLwamRSP1VHE5GqBpHxkPRViMMmp"
COVER_FEMALE_IMG     = "https://image-hub-cloud.lightningsource.com/2011-04-01/Images/front_cover/x200/sku/9798822989481.jpg?viewkey=cbe6f8e435b911f25bba9f623f1beeb0b63fe7797d202afd9ae0389ba174c2fd"
COVER_MALE_IMG       = "https://image-hub-cloud.lightningsource.com/2011-04-01/Images/front_cover/x200/sku/9798822981973.jpg?viewkey=6a6da316aacd73878e33dcdc077f227bfcc0f50c9d3bade6d01aeae2d7eae624"
AMAZON_PAPERBACK_URL = "https://www.amazon.com/dp/B0FJ2494LH"
AMAZON_HARDCOVER_URL = "https://www.amazon.com/dp/B0FJ23J6JQ"
AMAZON_KINDLE_URL    = "https://www.amazon.com/dp/B0DL7Z7NFL"
AMAZON_AUDIBLE_URL   = "https://www.amazon.com/dp/B0GVWM74FR"


# ── Shared layout components ──────────────────────────────────────────────────

def _wrap(content: str) -> str:
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
You received this because of your work in books, health, or community — topics this book speaks to directly.</p>
<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;">
<a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
&middot; Kortney Lee &middot; info@vowels.org
</p></td></tr>
</table></td></tr></table></body></html>"""


def _book_covers() -> str:
    def card(img: str, link: str, label: str) -> str:
        return (
            f'<td width="50%" style="padding:0 6px 0 0;vertical-align:top;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;">'
            f'<tr><td align="center" style="padding:10px 10px 6px;">'
            f'<a href="{link}" target="_blank">'
            f'<img src="{img}" width="72" alt="What Is Healthy?" style="display:block;border:0;"/></a></td></tr>'
            f'<tr><td style="padding:0 10px 4px;">'
            f'<p style="margin:0;font-size:12px;font-weight:700;color:#111827;">What Is Healthy?</p>'
            f'<p style="margin:1px 0 0;font-size:11px;color:#6b7280;font-style:italic;">Kortney O. Lee &mdash; {label}</p></td></tr>'
            f'<tr><td align="center" style="padding:6px 10px 10px;">'
            f'<a href="{link}" target="_blank" style="display:inline-block;background:#FEBE10;color:#000000;'
            f'font-size:13px;font-weight:700;text-decoration:none;padding:7px 18px;border-radius:8px;">Buy Now</a>'
            f'</td></tr></table></td>'
        )
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">'
        '<tr>'
        + card(COVER_FEMALE_IMG, INGRAM_FEMALE_URL, "Female cover")
        + card(COVER_MALE_IMG,   INGRAM_MALE_URL,   "Male cover")
        + '</tr></table>'
        f'<p style="margin:6px 0 0;font-size:13px;line-height:1.7;color:#6b7280;">'
        f'Also on <a href="{AMAZON_PAPERBACK_URL}" style="color:#1e40af;text-decoration:underline;">Amazon Paperback</a>'
        f' &middot; <a href="{AMAZON_HARDCOVER_URL}" style="color:#1e40af;text-decoration:underline;">Hardcover</a>'
        f' &middot; <a href="{AMAZON_KINDLE_URL}" style="color:#1e40af;text-decoration:underline;">Kindle</a>'
        f' &middot; <a href="{AMAZON_AUDIBLE_URL}" style="color:#1e40af;text-decoration:underline;">Audible</a></p>'
    )


def _reply_cta(question: str) -> str:
    return (
        '<table width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td style="padding:20px 0 0;border-top:1px solid #f3f4f6;">'
        f'<p style="margin:0;font-size:15px;line-height:1.7;color:#374151;">'
        f'<strong>{question}</strong> Hit reply &mdash; I read every response.</p>'
        '</td></tr></table>'
    )


def _sig(short: bool = False) -> str:
    if short:
        return '<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">— Kortney</p>'
    return (
        '<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">'
        'Talk soon,<br/><strong>Kortney Lee</strong><br/>'
        '<span style="font-size:14px;color:#6b7280;">Author, <em>What Is Healthy?</em></span></p>'
    )


# ── The preface (included in every Day 0) ────────────────────────────────────

_PREFACE = """
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 4px;font-size:13px;font-weight:700;letter-spacing:0.08em;
   text-transform:uppercase;color:#9ca3af;">From the Preface</p>
<p style="margin:0 0 20px;font-size:20px;font-weight:700;line-height:1.3;color:#111827;">
What is healthy?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Is it the absence of disease? Daily trips to the gym? A fridge full of organic food?
A number on the scale? A strict diet? Or is it glowing skin and visible abs?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Ask ten people and you&rsquo;ll likely get ten different answers. Even among those who seem
healthy, definitions differ. But one truth is clear: health is foundational. It
influences how we live, how we feel, and how we care for those around us.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
And yet, somewhere along the way, we&rsquo;ve lost clarity. We didn&rsquo;t stop believing in real
food &mdash; we just stopped recognizing it. Today, we trust the packaged over the perishable,
defend what&rsquo;s convenient, and market what&rsquo;s artificial as if it&rsquo;s nourishment. The truth
is many of us don&rsquo;t even know what real food is anymore.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
But let&rsquo;s be honest: if fruits and vegetables weren&rsquo;t real, they wouldn&rsquo;t rot. And if
processed foods were harmless, we wouldn&rsquo;t see a rise in diet-related illnesses like
type 2 diabetes, heart disease, and obesity year after year &mdash; especially among children.
The industry tells one story. The numbers tell another.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Meanwhile, a generation of children is growing up more fatigued, more overweight, and
more dependent on medication than ever before. 60% of American adults have at least one
chronic illness. 51% have two or more. My grandmother was one of them &mdash; she lived with
type 2 diabetes, high blood pressure, and cancer for years before she died. Three chronic
illnesses at once. That didn&rsquo;t have to be her story. And it doesn&rsquo;t have to be ours.</p>
<p style="margin:0 0 4px;font-size:14px;line-height:1.6;color:#9ca3af;text-align:right;font-style:italic;">
&mdash; Kortney O. Lee, <em>What Is Healthy?</em></p>
</td></tr>"""


# ── Day 0 templates — one per target group ───────────────────────────────────

def _day0_bookstore(name: str, company: str) -> str:
    co = f", and specifically your store{f' &mdash; {company}' if company else ''}" if company else ""
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to independent bookstores{co} because I believe
this is the kind of book your customers are already walking through the door looking for
&mdash; they just don&rsquo;t know it exists yet.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why I came to you specifically: independent bookstores are where readers discover
books that don&rsquo;t have a $5 million marketing budget behind them. Your staff recommendations,
your curated shelves, your community of regulars &mdash; that&rsquo;s how books like this find their
audience. A major chain won&rsquo;t hand-sell this book. You will.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> Take a look at the book. Read the preface below.
If it feels like something your customers would connect with &mdash; particularly in your
health, wellness, or self-help section &mdash; I&rsquo;d love to talk about getting it on your
shelves. That&rsquo;s the whole ask. No pressure beyond that.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
The book is 264 pages, written for a general audience (not a medical one), and covers
the food industry, what&rsquo;s actually in processed food, how to read a label, and what
families can realistically do about it. It resonates especially with adults 30&ndash;65
who are frustrated with conflicting health advice and want something research-backed and
honest.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
Order a copy to review:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Does this feel like a fit for your store?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_library(name: str, company: str) -> str:
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to public libraries because this book was written
for the communities you serve.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why libraries specifically: the people who need this information most &mdash; working
families, people managing chronic illness on limited budgets, adults trying to make better
choices without expensive programs or gym memberships &mdash; are exactly who walks through
your doors. They can&rsquo;t always buy a $28 hardcover. But they can borrow it. And that
matters to me.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> Consider the book for acquisition. I&rsquo;m happy to
provide a review copy at no cost, along with a reading group discussion guide (12
questions, chapter by chapter) and a 6-session community health program curriculum for
any programs your library already runs. No speaking fee for author events at libraries
&mdash; this matters too much to put a price tag on that.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
264 pages. Research-backed. Written for a general audience &mdash; not a textbook, not a
diet book. Something people will actually read, mark up, and bring back to discuss.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
For your personal review:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would a review copy help with your acquisition decision?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_podcast(name: str, company: str) -> str:
    show = f"<em>{company}</em>" if company else "your show"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to {show} because I think this conversation
is one your listeners are ready to have.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why I came to you specifically: podcasts are where people go when they&rsquo;re trying
to figure something out &mdash; not just be entertained. Your listeners are paying attention.
They&rsquo;re looking for honest information. The question at the center of this book &mdash;
<em>what is healthy, and why is it so hard to achieve?</em> &mdash; is a question your
audience is living with right now.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> An interview. I&rsquo;m a natural conversationalist and
I come with real research, a personal story (my grandmother died from cancer after years
of type 2 diabetes and high blood pressure &mdash; three chronic illnesses at once), and
practical takeaways your listeners can actually use. I don&rsquo;t lecture. I talk with people.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
Topics I cover well: label deception and what &ldquo;natural flavors&rdquo; actually means,
why the working class carries a disproportionate chronic illness burden, what Blue Zones
research actually shows, and why changing your eating habits is about so much more than
willpower. I adapt to whatever angle resonates most with your audience.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
The book &mdash; in case you&rsquo;d like to read it first:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would this be a good fit for your listeners?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_blog(name: str, company: str) -> str:
    blog = f"<em>{company}</em>" if company else "your blog"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to {blog} because your readers trust you to
put meaningful books in front of them &mdash; and I think this one earns that.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why I came to you specifically: book bloggers and reviewers are the reason
readers find books that matter. Not the algorithm, not the bestseller list &mdash; a real
person saying &ldquo;I read this and you should too.&rdquo; That kind of recommendation is
worth more than any ad I could run. And your audience trusts you because you&rsquo;ve
earned it.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> A review, a feature, or a mention &mdash; whatever
format fits your style. I can send a digital or physical review copy, provide an
exclusive excerpt for your readers, or do a written Q&amp;A if you prefer that format.
No requirement to be positive &mdash; I just want the book to reach people who are
ready for it.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
The book covers the food industry, label deception, ultra-processed food, chronic illness,
community health, and the psychology of why change is hard. It&rsquo;s not a diet book.
It&rsquo;s an honest conversation about a system that wasn&rsquo;t built to help most people
be well &mdash; and what to do about it.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
Order or request a review copy:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would you be interested in covering the book?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_church(name: str, company: str) -> str:
    org = f"<em>{company}</em>" if company else "your community"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to {org} because faith communities are doing
some of the most important health work in this country &mdash; and most of it goes
unrecognized.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why I came to you specifically: churches and faith organizations reach people
in the moments that matter most &mdash; times of loss, transition, and seeking. Chronic
illness touches almost every family in your congregation. 60% of American adults have
at least one chronic illness. 51% have two or more. My grandmother was one of them &mdash;
type 2 diabetes, high blood pressure, and cancer. She died from the cancer. That loss
drove me to write this book.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> Consider using the book in a small group study,
health ministry, or community wellness program. I&rsquo;ve written a 6-session discussion
guide that works well for groups of 8&ndash;15. And I&rsquo;m available to speak at community
health events, wellness weekends, or any gathering where this conversation would land.
No speaker fee for faith communities doing this work.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
The book is 264 pages, written for a general audience. It covers the food industry,
what&rsquo;s in the food most families eat, chronic illness, community health, and the
generational patterns we pass down &mdash; whether we mean to or not.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
Read it yourself first:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Does this resonate with what your community is already working on?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_school(name: str, company: str) -> str:
    org = f"<em>{company}</em>" if company else "your school"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to {org} because the students and parents
you work with are living the questions this book answers.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why I came to you specifically: schools are where habits get formed and where
health literacy &mdash; or the lack of it &mdash; takes root. A generation of children is
growing up more overweight, more fatigued, and more dependent on medication than any
before them. That&rsquo;s not a willpower problem. It&rsquo;s a knowledge and system problem. And
it starts getting solved in schools.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> Consider the book for a parent education workshop,
a health class supplemental reading unit, or a student assembly. Chapters 1&ndash;3 work as
a standalone unit on label reading and food industry basics for high school health
classes. Parent workshops drawing on the book run about 60&ndash;90 minutes and draw well
because the topic is something every parent is already thinking about. And I&rsquo;m
available for student assemblies at no charge for Title I schools.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
The goal is simple: students should leave knowing how to read a label, understanding
why certain foods are marketed to them the way they are, and feeling like good choices
are actually possible for them &mdash; not just for people with more money or more time.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
Read it yourself:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would this work for your students or parents?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_other(name: str, company: str) -> str:
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em> &mdash; a 264-page, research-backed look at the food industry, what&rsquo;s
actually in processed food, chronic illness, and what people can realistically do about
it. Written for a general audience, not a medical one.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
I&rsquo;m reaching out because I think there&rsquo;s a connection between what you do and who
this book is for. The people reading it are adults frustrated with conflicting health
advice who want something honest, research-backed, and actually applicable to their
lives.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
I&rsquo;d love to explore whether there&rsquo;s a way to work together &mdash; whether that&rsquo;s a
conversation, a review copy, or something I haven&rsquo;t thought of yet. Read the preface
below and let me know what you think.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Does this feel like something worth a conversation?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_christian_blog(name: str, company: str) -> str:
    blog = f"<em>{company}</em>" if company else "your blog"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to {blog} because your readers are already
thinking about health &mdash; they&rsquo;re just not finding content that speaks to it with
the honesty and depth they&rsquo;re looking for.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why I came to you specifically: Christian bloggers reach readers who think
about health in the context of the whole person &mdash; body, mind, community, and legacy.
That&rsquo;s exactly the frame this book lives in. It&rsquo;s not a diet book. It&rsquo;s a
research-backed conversation about why chronic illness has become a near-universal
experience, what the food system has done to create it, and what people can realistically
do &mdash; especially families and communities already paying attention.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> A review, a feature, or a mention if the book
resonates with you. I can send a digital or physical review copy. I can also provide an
exclusive excerpt, a guest post on any of the topics the book covers, or a written Q&amp;A
&mdash; whatever format fits your audience. No requirement to be positive; I just want the
conversation to reach people who are ready for it.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
My grandmother lived with type 2 diabetes, high blood pressure, and cancer for years
before she died. Three chronic illnesses at once. That&rsquo;s the personal reason behind
this book &mdash; and why I care about getting it into communities that are paying attention
to more than just the physical side of health.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
Order or request a review copy:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would this resonate with your readers?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _day0_christian_podcast(name: str, company: str) -> str:
    show = f"<em>{company}</em>" if company else "your show"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee. I wrote a book called <em>What Is Healthy? And Why Is It So Hard
to Achieve</em>, and I&rsquo;m reaching out to {show} because I think your listeners are
carrying a question this book answers directly: why is it so hard to take care of
ourselves and the people we love, even when we know we should?</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Here&rsquo;s why I came to you specifically: Christian podcast audiences think about health
as more than fitness &mdash; they think about stewardship, community, and what we pass
down to the next generation. The chronic illness epidemic is a community and family
issue, not just an individual one. 60% of American adults have at least one chronic
illness. 51% have two or more. My grandmother was one of them &mdash; she lived with
type 2 diabetes, high blood pressure, and cancer for years before she died. That didn&rsquo;t
have to be her story. The book is about why it became her story, and what we can do
differently.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
<strong>What I&rsquo;m asking:</strong> An interview on your show. I bring real research,
personal story, and practical takeaways &mdash; and I adapt the conversation to what lands
best with your audience. I don&rsquo;t lecture. I talk with people. Topics I cover well
include the generational patterns of chronic illness, what the food industry has done
to working families, the stewardship of our bodies as a spiritual and community practice,
and what it looks like to actually change &mdash; not with a 30-day challenge, but for real.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
Read the preface below &mdash; it&rsquo;ll give you a feel for the conversation we could have
with your listeners.</p>
</td></tr>
{_PREFACE}
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
The book &mdash; read it before we talk:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would this be a good fit for your listeners?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


_DAY0_RENDERERS = {
    "bookstore":        _day0_bookstore,
    "library":          _day0_library,
    "podcast":          _day0_podcast,
    "blog":             _day0_blog,
    "church":           _day0_church,
    "school":           _day0_school,
    "christian_blog":   _day0_christian_blog,
    "christian_podcast":_day0_christian_podcast,
}


def _render_b2b_day0(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    fn = _DAY0_RENDERERS.get(business_type, _day0_other)
    return fn(name, company_name or "")


# ── Follow-up templates (Days 3, 7, 14, 21) — same for all types ─────────────

def _render_b2b_day3(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Following up on my note from a few days ago &mdash; I wanted to add a little more context
about who the book actually reaches.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The readers who connect with it most are adults 30&ndash;65 who are tired of conflicting
health advice and want something research-backed and honest. Strong resonance with
families, faith communities, and people who feel like the system hasn&rsquo;t been built
with their health in mind. Which, based on the data, is most people.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
It covers the food industry, what&rsquo;s actually in ultra-processed food, how to read a
label, the psychology of why changing eating habits is hard, and what people can
realistically do about it at different income levels. 264 pages. Written for a general
audience &mdash; not a textbook.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
Just wanted to give you a fuller picture in case my first note was light on detail.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Any questions I can answer?")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _render_b2b_day7(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
A few things readers have shared after finishing the book:</p>
<table width="100%" cellpadding="16" cellspacing="0" style="margin:0 0 20px;background:#f9fafb;border-left:3px solid #e5e7eb;">
<tr><td>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#374151;font-style:italic;">
&ldquo;I went straight to the store and started reading labels differently.&rdquo;</p>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#374151;font-style:italic;">
&ldquo;I bought copies for my whole family.&rdquo;</p>
<p style="margin:0;font-size:15px;line-height:1.8;color:#374151;font-style:italic;">
&ldquo;This is the book I keep sending people.&rdquo;</p>
</td></tr></table>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
I wrote it for people who are paying attention but don&rsquo;t have the time or money to make
wellness a full-time job. That&rsquo;s most people. I suspect that&rsquo;s who you work with too.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
Still here if you want to connect.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would love to hear what you think.")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">{_sig()}</td></tr>""")


def _render_b2b_day14(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Just checking in &mdash; no pressure at all.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
If you had a chance to look at the book and there&rsquo;s something I can help with &mdash;
a conversation, a copy to review, any questions &mdash; just hit reply. I&rsquo;m here.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
And if the timing isn&rsquo;t right, that&rsquo;s okay too.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_book_covers()}
</td></tr>
<tr><td style="padding:20px 40px 32px;border-top:1px solid #e5e7eb;">{_sig()}</td></tr>""")


def _render_b2b_day21(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 32px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Last note from me &mdash; I don&rsquo;t want to fill your inbox.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
If the timing wasn&rsquo;t right or things got busy, no problem at all. The book is there
whenever it makes sense, and so am I.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.85;color:#374151;">
info@vowels.org &mdash; reach out any time.</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 32px;border-top:1px solid #e5e7eb;">{_sig(short=True)}</td></tr>""")


# ── Subject lines ─────────────────────────────────────────────────────────────

_SUBJECTS = {
    "bookstore": [
        "A book your customers are already looking for",
        "What readers are saying about What Is Healthy?",
        "Still here if you want to know more",
        "Checking in — What Is Healthy?",
        "Last note from me",
    ],
    "library": [
        "A book for your community — What Is Healthy?",
        "A little more about What Is Healthy?",
        "What readers are taking away",
        "Still available if you'd like to know more",
        "Last note from me",
    ],
    "podcast": [
        "Podcast guest — What Is Healthy? with Kortney Lee",
        "More on what I cover — What Is Healthy?",
        "What audiences say after these conversations",
        "Still interested in booking?",
        "Last note from me",
    ],
    "blog": [
        "What Is Healthy? — a book worth covering",
        "More context on What Is Healthy?",
        "What other writers have done with the book",
        "Still here if you're interested",
        "Last note from me",
    ],
    "church": [
        "What Is Healthy? — a book for your community",
        "More on What Is Healthy? and faith communities",
        "What readers are saying",
        "Still here if you'd like to connect",
        "Last note from me",
    ],
    "school": [
        "What Is Healthy? — a book for your students and parents",
        "More on What Is Healthy? for schools",
        "What students and parents are taking away",
        "Still here if you'd like to know more",
        "Last note from me",
    ],
    "christian_blog": [
        "What Is Healthy? — a book for your faith community readers",
        "More on What Is Healthy? and whole-person health",
        "What readers are saying",
        "Still here if you're interested",
        "Last note from me",
    ],
    "christian_podcast": [
        "Podcast guest — What Is Healthy? with Kortney Lee",
        "More on what I cover for faith audiences",
        "What listeners say after these conversations",
        "Still interested in booking?",
        "Last note from me",
    ],
    "other": [
        "What Is Healthy? — wanted to put this on your radar",
        "More about What Is Healthy?",
        "What readers are saying",
        "Still here if you're interested",
        "Last note from Kortney",
    ],
}


def _subject(bt: str, day_index: int) -> str:
    return _SUBJECTS.get(bt, _SUBJECTS["other"])[day_index]


_B2B_SEQUENCE = [
    (0,  0,  "b2b_day0",  lambda bt: _subject(bt, 0), _render_b2b_day0),
    (1,  3,  "b2b_day3",  lambda bt: _subject(bt, 1), _render_b2b_day3),
    (2,  7,  "b2b_day7",  lambda bt: _subject(bt, 2), _render_b2b_day7),
    (3,  14, "b2b_day14", lambda bt: _subject(bt, 3), _render_b2b_day14),
    (4,  21, "b2b_day21", lambda bt: _subject(bt, 4), _render_b2b_day21),
]


# ── Sending ───────────────────────────────────────────────────────────────────

async def _send(to_email: str, subject: str, html: str) -> bool:
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping B2B email")
        return False
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
        "categories": ["b2b-nurture"],
    }
    if BCC_EMAIL and BCC_EMAIL.lower() != to_email.lower():
        payload["personalizations"][0]["bcc"] = [{"email": BCC_EMAIL}]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            )
        if r.status_code in (200, 201, 202):
            logger.info("B2B email sent: %s subject=%r", to_email, subject)
            return True
        logger.error("B2B SendGrid error %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("B2B email send failed: %s", e)
    return False


async def trigger_b2b_day0(
    email: str, first_name: str, business_type: str, company_name: str = ""
) -> bool:
    bt = business_type or "other"
    return await _send(email, _subject(bt, 0), _render_b2b_day0(first_name, bt, company_name))


async def process_pending_b2b_nurture() -> dict:
    """Cron: send follow-ups for book_leads B2B leads."""
    from datetime import datetime, timezone, timedelta
    from google.cloud import firestore

    db  = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))
    now = datetime.now(timezone.utc)
    sent = skipped = errors = 0

    query = (
        db.collection("book_leads")
        .where("lead_type", "==", "b2b")
        .where("sequence_status", "==", "active")
        .where("nurture_next_at", "<=", now)
        .limit(50)
    )
    async for doc in query.stream():
        d = doc.to_dict()
        stage = d.get("nurture_stage", 0)
        if stage >= len(_B2B_SEQUENCE):
            await doc.reference.update({"sequence_status": "completed"})
            continue
        _, days, tmpl_id, subject_fn, render_fn = _B2B_SEQUENCE[stage]
        email = d.get("email", ""); first_name = d.get("first_name", "")
        bt = d.get("business_type", "other"); company = d.get("company_name", "")
        try:
            ok = await _send(email, subject_fn(bt), render_fn(first_name, bt, company))
            next_stage = stage + 1
            upd: dict = {"nurture_stage": next_stage, f"nurture_{tmpl_id}_sent_at": now}
            if next_stage < len(_B2B_SEQUENCE):
                upd["nurture_next_at"] = now + timedelta(days=_B2B_SEQUENCE[next_stage][1])
            else:
                upd["sequence_status"] = "completed"
            await doc.reference.update(upd)
            sent += 1 if ok else 0; errors += 0 if ok else 1
        except Exception as e:
            logger.error("B2B nurture error %s: %s", email, e); errors += 1
    return {"sent": sent, "skipped": skipped, "errors": errors}


# ── outreach_leads collection ─────────────────────────────────────────────────

_SLUG_TO_BTYPE = {
    "libraries":            "library",
    "bookstores":           "bookstore",
    "christian_blogs":      "christian_blog",
    "book_review_blogs":    "blog",
    "christian_podcasts":   "christian_podcast",
    "book_review_podcasts": "podcast",
}

_OUTREACH_DELAYS = [0, 3, 7, 14, 21]

_OUTREACH_STAGES = [
    (0, "outreach_day0",  _render_b2b_day0,  0),
    (1, "outreach_day3",  _render_b2b_day3,  1),
    (2, "outreach_day7",  _render_b2b_day7,  2),
    (3, "outreach_day14", _render_b2b_day14, 3),
    (4, "outreach_day21", _render_b2b_day21, 4),
]


async def process_outreach_leads(batch: int = 100) -> dict:
    """Cron: send emails to outreach_leads. Day 0 for new, follow-ups for contacted."""
    from datetime import datetime, timezone, timedelta
    from google.cloud import firestore

    db  = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))
    now = datetime.now(timezone.utc)
    sent = skipped = errors = 0
    COLL = "outreach_leads"

    # Day 0 — new leads
    async for doc in (
        db.collection(COLL)
        .where("remarketing_status", "==", "new")
        .where("sequence_status", "==", "active")
        .limit(batch)
        .stream()
    ):
        d = doc.to_dict()
        if d.get("do_not_contact") or d.get("sendgrid_suppressed") or d.get("unsubscribed"):
            skipped += 1; continue
        email = d.get("email", ""); first_name = d.get("first_name", "")
        bt = _SLUG_TO_BTYPE.get(d.get("target_slug", ""), "other")
        company = d.get("company_name", "")
        try:
            ok = await _send(email, _subject(bt, 0), _render_b2b_day0(first_name, bt, company))
            await doc.reference.update({
                "remarketing_status": "contacted",
                "nurture_stage": 1,
                "nurture_next_at": now + timedelta(days=3),
                "outreach_day0_sent_at": now,
            })
            sent += 1 if ok else 0; errors += 0 if ok else 1
        except Exception as e:
            logger.error("Outreach Day0 error %s: %s", email, e); errors += 1

    # Follow-ups
    async for doc in (
        db.collection(COLL)
        .where("remarketing_status", "==", "contacted")
        .where("sequence_status",    "==", "active")
        .where("nurture_next_at",    "<=", now)
        .limit(batch)
        .stream()
    ):
        d = doc.to_dict()
        if d.get("do_not_contact") or d.get("sendgrid_suppressed") or d.get("unsubscribed"):
            skipped += 1; continue
        stage = d.get("nurture_stage", 1)
        if stage >= len(_OUTREACH_STAGES):
            await doc.reference.update({"sequence_status": "completed"}); continue
        _, tmpl_id, render_fn, day_idx = _OUTREACH_STAGES[stage]
        email = d.get("email", ""); first_name = d.get("first_name", "")
        bt = _SLUG_TO_BTYPE.get(d.get("target_slug", ""), "other")
        company = d.get("company_name", "")
        try:
            ok = await _send(email, _subject(bt, day_idx), render_fn(first_name, bt, company))
            next_stage = stage + 1
            upd: dict = {"nurture_stage": next_stage, f"{tmpl_id}_sent_at": now}
            if next_stage < len(_OUTREACH_STAGES):
                upd["nurture_next_at"] = now + timedelta(days=_OUTREACH_DELAYS[next_stage])
            else:
                upd["sequence_status"] = "completed"
            await doc.reference.update(upd)
            sent += 1 if ok else 0; errors += 0 if ok else 1
        except Exception as e:
            logger.error("Outreach followup error %s: %s", email, e); errors += 1

    return {"sent": sent, "skipped": skipped, "errors": errors, "ran_at": now.isoformat()}
