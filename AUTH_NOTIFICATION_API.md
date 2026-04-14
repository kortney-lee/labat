# WIHY Notification & Report API Guide

Base URL: `https://auth.wihy.ai`

All endpoints require the `X-Admin-Token` header set to the value of `INTERNAL_ADMIN_TOKEN` from GCP Secret Manager.

```
X-Admin-Token: <your-internal-admin-token>
Content-Type: application/json
```

---

## 1. Send Alert — `POST /api/notifications/alert`

Send an email and/or SMS notification from any WIHY agent (Otaku Master, LABAT, Shania, etc.).

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | **Yes** | Alert headline |
| `message` | string | **Yes** | Alert body text |
| `severity` | string | No | `info` (default), `warning`, or `critical` |
| `agent` | string | No | Agent name (e.g. `otaku-master`, `labat`, `shania`) — used for rate-limit tracking |
| `service` | string | No | Originating service name |
| `timestamp` | string | No | ISO 8601 timestamp (defaults to now) |
| `details` | object | No | Arbitrary JSON payload included in the email body |
| `channels` | string[] | No | `["email"]`, `["sms"]`, or `["email","sms"]`. Defaults to `["email"]` for info/warning, `["email","sms"]` for critical |
| `recipient` | object | No | Who to send to (see below) |

### Recipient Resolution

The `recipient` object controls who receives the alert. Omit it entirely to send to the admin fallback email.

| Field | Type | Description |
|-------|------|-------------|
| `recipient.user_id` | string (UUID) | Look up email/phone from the `users` table |
| `recipient.email` | string | Explicit email override (skips DB lookup) |
| `recipient.phone` | string | Explicit phone override (skips DB lookup) |

**Priority order:**
1. Explicit `email`/`phone` in the recipient object
2. DB lookup by `user_id`
3. Admin fallback (`NOTIFICATION_ADMIN_EMAIL` env var → `support@wihy.ai`)

### Examples

#### Minimal — info email to admin

```bash
curl -X POST https://auth.wihy.ai/api/notifications/alert \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_TOKEN" \
  -d '{
    "title": "Daily sync complete",
    "message": "All user records synchronized successfully.",
    "agent": "labat"
  }'
```

#### Critical — email + SMS to a specific user

```bash
curl -X POST https://auth.wihy.ai/api/notifications/alert \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_TOKEN" \
  -d '{
    "severity": "critical",
    "title": "Payment failed",
    "message": "Stripe charge for subscription renewal was declined.",
    "agent": "shania",
    "service": "payment-service",
    "channels": ["email", "sms"],
    "recipient": {
      "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    },
    "details": {
      "stripe_charge_id": "ch_xxx",
      "amount": 1999,
      "currency": "usd"
    }
  }'
```

#### Warning — email to an explicit address

```bash
curl -X POST https://auth.wihy.ai/api/notifications/alert \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_TOKEN" \
  -d '{
    "severity": "warning",
    "title": "High error rate detected",
    "message": "auth-service 5xx rate exceeded 5% in the last 10 minutes.",
    "agent": "otaku-master",
    "service": "auth-service",
    "recipient": {
      "email": "oncall@wihy.ai"
    },
    "details": {
      "error_rate": "7.2%",
      "window": "10m"
    }
  }'
```

#### SMS-only to a phone number

```bash
curl -X POST https://auth.wihy.ai/api/notifications/alert \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_TOKEN" \
  -d '{
    "severity": "critical",
    "title": "Server down",
    "message": "user-service is unreachable.",
    "agent": "otaku-master",
    "channels": ["sms"],
    "recipient": {
      "phone": "+15551234567"
    }
  }'
```

### Response

**200 OK** — all channels delivered:

```json
{
  "success": true,
  "status": "delivered",
  "data": {
    "agent": "otaku-master",
    "severity": "critical",
    "channels": ["email", "sms"],
    "delivered": { "email": true, "sms": true },
    "recipient": { "email": "user@example.com", "phone": "***" }
  }
}
```

**200 OK** — partial delivery (e.g. SMS failed, email succeeded):

```json
{
  "success": true,
  "status": "queued",
  "data": {
    "delivered": { "email": true, "sms": false }
  }
}
```

**500** — all channels failed:

```json
{
  "success": false,
  "status": "failed",
  "error": "Notification dispatch failed"
}
```

**429** — rate limit exceeded (60 requests/min per agent):

```json
{
  "success": false,
  "error": "Rate limit exceeded for agent otaku-master"
}
```

---

## 2. Master Agent Report — `POST /api/reports/master-agent`

Send an Otaku Master Agent report digest email. The entire request body is rendered as formatted JSON in a styled HTML email.

### Request Body

Send any JSON object — the full body is included in the report email.

```bash
curl -X POST https://auth.wihy.ai/api/reports/master-agent \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_TOKEN" \
  -d '{
    "report_type": "daily_summary",
    "generated_at": "2026-03-27T18:00:00Z",
    "agents": {
      "labat": { "status": "healthy", "tasks_completed": 42 },
      "shania": { "status": "healthy", "tasks_completed": 18 }
    },
    "metrics": {
      "total_users": 12450,
      "active_today": 3210,
      "errors_24h": 7
    }
  }'
```

### Response

**200 OK:**

```json
{ "success": true, "status": "delivered" }
```

**500:**

```json
{ "success": false, "status": "failed", "error": "Report email failed" }
```

The report email is sent to `OTAKU_REPORT_EMAIL` (env var) or falls back to `NOTIFICATION_ADMIN_EMAIL` → `support@wihy.ai`.

---

## Python Helper

Drop this into any agent codebase for easy integration:

```python
import requests
import os

AUTH_BASE_URL = "https://auth.wihy.ai"
ADMIN_TOKEN = os.environ["INTERNAL_ADMIN_TOKEN"]

HEADERS = {
    "Content-Type": "application/json",
    "X-Admin-Token": ADMIN_TOKEN,
}

def send_alert(title, message, severity="info", agent="unknown",
               service="", channels=None, recipient=None, details=None):
    payload = {
        "title": title,
        "message": message,
        "severity": severity,
        "agent": agent,
        "service": service,
    }
    if channels:
        payload["channels"] = channels
    if recipient:
        payload["recipient"] = recipient
    if details:
        payload["details"] = details

    resp = requests.post(
        f"{AUTH_BASE_URL}/api/notifications/alert",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

def send_report(report_data):
    resp = requests.post(
        f"{AUTH_BASE_URL}/api/reports/master-agent",
        json=report_data,
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
```

**Usage:**

```python
# Info email to admin
send_alert("Sync complete", "All records synced.", agent="labat")

# Critical alert to a user
send_alert(
    "Payment declined",
    "Your subscription payment failed.",
    severity="critical",
    agent="shania",
    service="payment-service",
    recipient={"user_id": "a1b2c3d4-..."},
    details={"charge_id": "ch_xxx"},
)

# Master agent report
send_report({
    "report_type": "daily_summary",
    "agents": {"labat": {"status": "healthy"}},
})
```

---

## Node.js Helper

```javascript
const ADMIN_TOKEN = process.env.INTERNAL_ADMIN_TOKEN;
const BASE = 'https://auth.wihy.ai';

async function sendAlert({ title, message, severity, agent, service, channels, recipient, details }) {
  const res = await fetch(`${BASE}/api/notifications/alert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
    body: JSON.stringify({ title, message, severity, agent, service, channels, recipient, details }),
  });
  return res.json();
}

async function sendReport(reportData) {
  const res = await fetch(`${BASE}/api/reports/master-agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Admin-Token': ADMIN_TOKEN },
    body: JSON.stringify(reportData),
  });
  return res.json();
}
```

---

## PowerShell Quick Test

```powershell
$token = gcloud secrets versions access latest --secret="internal-admin-token"
$headers = @{ "X-Admin-Token" = $token; "Content-Type" = "application/json" }

# Send info alert
$body = '{"title":"Test alert","message":"Hello from PowerShell","agent":"manual-test","severity":"info"}'
Invoke-RestMethod -Uri "https://auth.wihy.ai/api/notifications/alert" -Method POST -Headers $headers -Body $body

# Send report
$report = '{"report_type":"test","status":"ok"}'
Invoke-RestMethod -Uri "https://auth.wihy.ai/api/reports/master-agent" -Method POST -Headers $headers -Body $report
```

---

## Rate Limits

| Endpoint | Default | Env Override |
|----------|---------|-------------|
| `/api/notifications/alert` | 60 req/min per agent | `NOTIFICATION_RATE_LIMIT_PER_MINUTE` |
| `/api/reports/master-agent` | 20 req/min per agent | `REPORT_RATE_LIMIT_PER_MINUTE` |

---

## Environment Variables (auth-service Cloud Run)

These should be set on the auth-service Cloud Run instance:

| Variable | Purpose | Default |
|----------|---------|---------|
| `INTERNAL_ADMIN_TOKEN` | **Required** — authenticates all requests | *(Secret Manager)* |
| `SENDGRID_API_KEY` | **Required** — SendGrid API key for email | *(Secret Manager)* |
| `SENDGRID_FROM_EMAIL` | Sender address for emails | `noreply@wihy.ai` |
| `TWILIO_ACCOUNT_SID` | **Required for SMS** — Twilio account SID | *(Secret Manager)* |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | *(Secret Manager)* |
| `TWILIO_PHONE_NUMBER` | Twilio sender phone number | *(Secret Manager)* |
| `NOTIFICATION_ADMIN_EMAIL` | Fallback recipient for alerts with no recipient | `support@wihy.ai` |
| `NOTIFICATION_ADMIN_PHONE` | Fallback phone for SMS alerts | *(none)* |
| `OTAKU_REPORT_EMAIL` | Where master-agent reports are sent | Falls back to admin email |
| `NOTIFICATION_RATE_LIMIT_PER_MINUTE` | Alert rate limit per agent | `60` |
| `REPORT_RATE_LIMIT_PER_MINUTE` | Report rate limit per agent | `20` |

---

## Which Agent Sends What

### Otaku Master Agent

| Trigger | `severity` | `channels` |
|---------|-----------|-----------|
| Any service health check fails | `critical` | `email`, `sms` |
| Anomaly detected (critical) | `critical` | `email`, `sms` |
| Anomaly detected (warning) | `warning` | `email` |
| Hourly digest | — | `email` (via `/api/reports/master-agent`) |

### LABAT

| Trigger | `severity` | `channels` | When |
|---------|-----------|-----------|------|
| Spend spike > 50% in 1h | `warning` | `email`, `sms` | Real-time |
| Campaign delivery stopped | `critical` | `email`, `sms` | Real-time |
| New lead form submission | `info` | `email` | On event |
| ROAS drops below threshold | `warning` | `email` | Hourly check |
| Ad account spend limit reached | `critical` | `email`, `sms` | Real-time |

### Shania

| Trigger | `severity` | `channels` | When |
|---------|-----------|-----------|------|
| Thread monitor goes offline | `critical` | `email`, `sms` | Real-time |
| Engagement rate drops > 30% | `warning` | `email` | Per poll cycle |
| New high-priority DM received | `info` | `email` | On event |
| Post receives negative sentiment spike | `warning` | `email` | Per poll cycle |
| Auto-reply volume spike | `info` | `email` | Hourly |
