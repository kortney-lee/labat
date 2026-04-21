# SendGrid Email System — Complete Reference

## Overview

We use **SendGrid's v3 Mail Send API** to deliver all transactional and nurture emails. No SendGrid templates are used — all HTML is rendered server-side in Python (`nurture_service.py`) and sent as raw HTML via the API.

---

## Configuration

### Environment Variables

| Variable | Value | Where Set |
|----------|-------|-----------|
| `SENDGRID_API_KEY` | Secret Manager: `sendgrid-api-key:latest` | Cloud Run (book service) |
| `BOOK_FROM_EMAIL` | `info@vowels.org` | `cloudbuild.book.yaml` |
| `BOOK_FROM_NAME` | `Vowels` | `cloudbuild.book.yaml` |

### Cloud Build Config (`cloudbuild.book.yaml`)
```yaml
--set-env-vars: APP_MODULE=src.apps.book_app:app,BOOK_FROM_EMAIL=info@vowels.org,BOOK_FROM_NAME=Vowels
--set-secrets: SENDGRID_API_KEY=sendgrid-api-key:latest
```

### Sender Identity
- **From:** `info@vowels.org`
- **Display Name:** `Vowels`
- **Domain:** Authenticated in SendGrid for `vowels.org`

---

## Architecture

### Two Email Systems (Python is active)

| System | Status | Location | How it sends |
|--------|--------|----------|-------------|
| **Python nurture** (active) | ✅ LIVE | `src/services/nurture_service.py` | Direct SendGrid API call via `httpx` |
| **Shania nurture** (legacy) | ⚠️ Not used for book emails | `shania/src/services/nurture_dispatch.ts` | Routes through Otaku Master agent |
| **Legacy book email** | ⚠️ Superseded by nurture Day 0 | `src/services/book_email_service.py` | Direct SendGrid API call via `httpx` |

The **active system** is `src/services/nurture_service.py`. When a lead signs up at `whatishealthy.org`, the Day 0 nurture email fires immediately — this replaces the old `book_email_service.py` standalone email.

### Flow

```
User signs up at whatishealthy.org
  → POST /api/book/leads
    → save_lead() — Firestore (book_leads collection)
    → trigger_day0() — sends Day 0 email via SendGrid, sets nurture_stage=1
    → Meta CAPI Lead event (LABAT)

Cloud Scheduler (daily)
  → POST /api/book/nurture-cron (X-Admin-Token header)
    → process_pending_nurture()
      → queries Firestore for leads where nurture_next_at <= now
      → sends next email in sequence via SendGrid
      → advances nurture_stage and sets next nurture_next_at
```

---

## SendGrid API Integration

### How Emails Are Sent (`send_nurture_email`)

```python
payload = {
    "personalizations": [{"to": [{"email": to_email}]}],
    "from": {"email": "info@vowels.org", "name": "Vowels"},
    "subject": "Your free copy is here, Kortney",
    "content": [{"type": "text/html", "value": "<html>...</html>"}],
    "tracking_settings": {
        "click_tracking": {"enable": True, "enable_text": False},
        "open_tracking": {"enable": True},
    },
    "categories": ["nurture", "digital_book_delivery"],
    "custom_args": {"template_id": "digital_book_delivery", "lead_email": "user@example.com"},
}

# POST https://api.sendgrid.com/v3/mail/send
# Authorization: Bearer {SENDGRID_API_KEY}
```

### Tracking Features
- **Open tracking:** Enabled — SendGrid injects a tracking pixel
- **Click tracking:** Enabled for HTML links (not plain text)
- **Categories:** Each email is tagged with `["nurture", "{template_id}"]` for SendGrid analytics
- **Custom args:** `template_id` and `lead_email` are attached for webhook correlation

---

## SendGrid Webhook (Event Tracking)

### Endpoint
```
POST /api/book/sendgrid-webhook
```

### Handled Events
| Event | Action |
|-------|--------|
| `open` | Records `last_opened_at` + appends to `opens` array in Firestore |
| `click` | Records `last_clicked_at` + appends to `clicks` array in Firestore |
| `unsubscribe` / `group_unsubscribe` | Sets `sequence_status = "unsubscribed"` |

### Firestore Document After Events
```json
{
  "email": "user@example.com",
  "last_opened_at": "2026-04-01T...",
  "opens": [
    {"at": "2026-04-01T...", "template": "digital_book_delivery"},
    {"at": "2026-04-03T...", "template": "paperback_upsell"}
  ],
  "last_clicked_at": "2026-04-01T...",
  "clicks": [
    {"at": "2026-04-01T...", "template": "digital_book_delivery"}
  ]
}
```

---

## Nurture Sequence

### Schedule

| Stage | Day | Template ID | Subject Line |
|-------|-----|-------------|-------------|
| 0 | 0 (immediate) | `digital_book_delivery` | "Your free copy is here, {first_name}" |
| 1 | 2 | `paperback_upsell` | "A quick thought about the book" |
| 2 | 5 | `value_reminder` | "Did you get to Chapter 3 yet?" |
| 3 | 7 | `early_reader` | "Something special for early readers" |
| 4 | 10 | `final_intro_cg_wihy` | "One last thing before we go" |

### Conditional Logic (Day 10)
The Day 10 email has two variants:
- **Engaged reader** (has any opens recorded): Mentions Community Groceries and WIHY in plain text — no logos, no subscription links, no branding
- **Not engaged** (no opens): Simple farewell with book download link

---

## Email Templates — Full Copy

### Email Wrapper (shared by all templates)
```
- White background (#f9fafb), clean card layout (560px max-width)
- No colored header bar — personal, lightweight
- Font: system stack (-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial)
- Footer: "Sent by Vowels · Unsubscribe" (12px gray, centered)
- Unsubscribe link: https://whatishealthy.org/unsubscribe
```

---

### Day 0 — `digital_book_delivery`
**Subject:** Your free copy is here, {first_name}

**Body:**
> Hey {first_name},
>
> Thanks for grabbing a copy of **What Is Healthy**. I wrote this book because I got tired of seeing people get misled by food labels and marketing. I wanted to put the real research in one place — no fluff, no agenda.
>
> Your free digital copy is ready right now:
>
> **[Download Your Free Book]** (blue button → https://whatishealthy.org/WhatisHealthy_eBook.pdf)
>
> I hope you enjoy it. I'll check in with you in a couple of days.
>
> Talk soon,
> The Vowels Team

**Design notes:** No book cover image. Single blue CTA button (#1e40af). Personal tone.

---

### Day 2 — `paperback_upsell`
**Subject:** A quick thought about the book

**Body:**
> Hey {first_name},
>
> Quick thought — a lot of readers who downloaded the free book have told us they ended up ordering the paperback too. There's something about having it on your counter or nightstand that makes the information stick.
>
> It's $24.99 and we cover shipping. Same content you already have, just in a format you can highlight, dog-ear, and share with family.
>
> If you're interested:
>
> **[Order Paperback — Female Cover]** (green button → Stripe link)
> **[Order Paperback — Male Cover]** (green button → Stripe link)
>
> No pressure at all — the free version is yours to keep either way.
>
> — The Vowels Team

**Design notes:** Two green CTA buttons (#16a34a) — one per cover variant. Soft sell, no urgency.

**Stripe Links:**
- Female cover: `https://buy.stripe.com/dRmbJ13cu4dYcdz5t0ejK0i`
- Male cover: `https://buy.stripe.com/aFafZheVc7qacdzg7EejK0j`

---

### Day 5 — `value_reminder`
**Subject:** Did you get to Chapter 3 yet?

**Body:**
> Hey {first_name},
>
> Did you get to Chapter 3 yet? That's the one where we break down the 23 ingredients food companies use that most people can't even pronounce — let alone understand what they do to your body.
>
> If you're like most readers, that chapter alone changes the way you look at a food label.
>
> Here are a few things you'll find inside:
> - Why "natural flavors" isn't what you think it is
> - The one ingredient that shows up in 68% of packaged food
> - Simple swaps you can make at your next grocery run
>
> In case you need the link again:
>
> **[Re-download the Book]** (blue button → PDF link)
>
> Happy reading,
> The Vowels Team

**Design notes:** Content-focused, re-engagement. References specific book content to spark curiosity.

---

### Day 7 — `early_reader`
**Subject:** Something special for early readers

**Body:**
> Hey {first_name},
>
> It's been about a week since you downloaded *What Is Healthy* and I just wanted to say thanks for being one of the early readers. It means a lot.
>
> If you've found anything useful in the book, the best thing you can do is share it with someone you care about. A friend, a parent, a partner — anyone who'd benefit from knowing what's actually in their food.
>
> Here's the link so you can pass it along:
>
> **[Share the Book]** (blue button → https://whatishealthy.org)
>
> We'll be in touch one more time. Until then — keep reading those labels.
>
> — The Vowels Team

**Design notes:** No product push. Encourages organic sharing. Links to whatishealthy.org landing page (not the PDF directly — drives traffic).

---

### Day 10 — `final_intro_cg_wihy` (Engaged variant)
**Subject:** One last thing before we go

**Body (if user opened any prior email):**
> Hey {first_name},
>
> This is the last email in this series — thanks for reading along.
>
> Before we go, I wanted to mention two things we've been building that connect to what the book is all about:
>
> **Community Groceries** — a new way to shop. Healthier products, better prices, delivered to your door.
>
> **WIHY** — a new way to capture what you eat, shop smarter, and get answers to your health questions.
>
> Both are still early, and we'd love for you to check them out when you're ready. No rush.
>
> In the meantime, your book is always here:
>
> **[Download the Book]** (blue button → PDF link)
>
> All the best,
> The Vowels Team

**Design notes:** Plain text mentions of CG and WIHY only. No logos, no subscription links, no branding. Low-pressure intro.

---

### Day 10 — `final_intro_cg_wihy` (Not engaged variant)
**Subject:** One last thing before we go

**Body (if user never opened any email):**
> Hey {first_name},
>
> This is the last email in this series. We just want to make sure you still have access to your free copy of **What Is Healthy**.
>
> Here's your download link one more time — it won't expire:
>
> **[Download the Book]** (blue button → PDF link)
>
> We won't fill your inbox after this. If you ever want to come back, the book is yours to keep.
>
> All the best,
> The Vowels Team

**Design notes:** No product mentions at all. Clean exit — respects the reader's inbox.

---

## Admin Endpoints

### Preview All 5 Emails
```bash
POST https://whatishealthy.org/api/book/preview-all
Headers: X-Admin-Token: {INTERNAL_ADMIN_TOKEN}, Content-Type: application/json
Body: {"email": "kortney@wihy.ai", "first_name": "Kortney"}
```
Sends all 5 nurture emails to the specified address with `[PREVIEW Day X]` prefix on subject lines.

### Resend Day 0
```bash
POST https://whatishealthy.org/api/book/resend
Headers: X-Admin-Token: {INTERNAL_ADMIN_TOKEN}, Content-Type: application/json
Body: {"email": "user@example.com"}
```
Resets lead to stage 0 and re-sends the Day 0 email.

### Trigger Cron Manually
```bash
POST https://whatishealthy.org/api/book/nurture-cron
Headers: X-Admin-Token: {INTERNAL_ADMIN_TOKEN}
```
Processes all pending nurture emails immediately.

### Funnel Stats
```bash
GET https://whatishealthy.org/api/book/stats
Headers: X-Admin-Token: {INTERNAL_ADMIN_TOKEN}
```
Returns lead counts by stage, open/click rates, unsubscribes.

### Unsubscribe
```bash
POST https://whatishealthy.org/api/book/unsubscribe
Body: {"email": "user@example.com"}
```
Marks lead as unsubscribed — stops all future nurture emails.

---

## Firestore Data Model

**Collection:** `book_leads`

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Lowercase, trimmed |
| `first_name` | string | From signup form |
| `last_name` | string | From signup form |
| `source` | string | Always `"whatishealthy"` |
| `sequence_status` | string | `active` → `completed` or `unsubscribed` or `buyer` |
| `nurture_stage` | number | 0–5 (5 = done) |
| `nurture_next_at` | timestamp | When next email is due |
| `created_at` | timestamp | Lead capture time |
| `delivered` | boolean | Book marked as delivered |
| `paperback_purchased` | boolean | Stripe purchase recorded |
| `utm_source` | string | UTM tracking (optional) |
| `utm_campaign` | string | UTM tracking (optional) |
| `utm_content` | string | UTM tracking (optional) |
| `utm_medium` | string | UTM tracking (optional) |
| `fbclid` | string | Facebook click ID (optional) |
| `opens` | array | `[{at, template}]` — from SendGrid webhooks |
| `clicks` | array | `[{at, template}]` — from SendGrid webhooks |
| `last_opened_at` | timestamp | Most recent open |
| `last_clicked_at` | timestamp | Most recent click |
| `unsubscribed_at` | timestamp | If unsubscribed |
| `nurture_{template}_sent_at` | timestamp | When each email was sent |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/services/nurture_service.py` | All 5 email templates, wrapper, send function, cron processor |
| `src/services/book_leads_service.py` | Firestore CRUD: save_lead, mark_delivered, record_email_event, get_funnel_stats |
| `src/services/book_email_service.py` | Legacy standalone book email (superseded by nurture Day 0) |
| `src/routers/book_routes.py` | API routes: /leads, /preview-all, /resend, /nurture-cron, /sendgrid-webhook, /unsubscribe |
| `src/apps/book_app.py` | FastAPI app entry point for the book Cloud Run service |
| `cloudbuild.book.yaml` | Cloud Build config — sets FROM_EMAIL, FROM_NAME, injects SENDGRID_API_KEY from Secret Manager |
| `static_whatishealthy/index.html` | Landing page with email capture form + UTM parameter extraction |

---

## Asset URLs

| Asset | URL |
|-------|-----|
| Book PDF | `https://whatishealthy.org/WhatisHealthy_eBook.pdf` |
| Book cover (green) | `https://storage.googleapis.com/wihy-web-assets/images/book/BookGreen.jpg` |
| Landing page | `https://whatishealthy.org` |
| Unsubscribe | `https://whatishealthy.org/unsubscribe` |
| Paperback (female cover) | `https://buy.stripe.com/dRmbJ13cu4dYcdz5t0ejK0i` |
| Paperback (male cover) | `https://buy.stripe.com/aFafZheVc7qacdzg7EejK0j` |

---

## Deployment

```bash
# Deploy book service (includes SendGrid email system)
gcloud builds submit --config cloudbuild.book.yaml --project wihy-ai

# Deploy Firebase hosting (serves whatishealthy.org landing page)
firebase deploy --only hosting:whatishealthy --config firebase.whatishealthy.json
```

---

## Shania Nurture System (Legacy/Separate)

Shania has its own nurture email/SMS template system in TypeScript. This is **not** the active system for book emails but exists for potential future multi-brand nurture campaigns.

**Files:**
- `shania/src/templates/nurture_email.ts` — 7 email templates with `{{placeholder}}` tokens
- `shania/src/templates/nurture_sms.ts` — 7 SMS templates (under 160 chars)
- `shania/src/services/nurture_dispatch.ts` — Dispatch logic, brand defaults, placeholder resolution
- `shania/src/api/routes/nurture.ts` — `/nurture/dispatch` and `/nurture/trigger` endpoints

**Key difference:** Shania's nurture routes through the Otaku Master agent for delivery, while the Python system calls SendGrid directly. The Python system is the one actually sending the whatishealthy.org book emails.
