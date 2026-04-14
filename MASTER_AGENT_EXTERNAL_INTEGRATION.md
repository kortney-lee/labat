# Otaku Master Agent External Integration Guide

This document explains how agents outside this repository can communicate with the WIHY Otaku Master Agent.

## 1. Base URL

Use your deployed Cloud Run URL for the Master Agent service.

Example:
- `https://wihy-master-agent-<hash>-uc.a.run.app`

If the agent is running behind a gateway or custom domain, use that base URL instead.

## 2. Authentication

Most operational endpoints require the admin header:

- Header name: `X-Admin-Token`
- Header value: value of `INTERNAL_ADMIN_TOKEN`

Example:

```http
X-Admin-Token: <your-internal-admin-token>
```

Notes:
- `GET /health` is public in current implementation.
- All `/api/otaku/master/*` routes require `X-Admin-Token`.

## 3. External API Surface

Public/basic:
- `GET /health`
- `GET /`

Operational (admin token required):
- `GET /api/otaku/master/health`
- `GET /api/otaku/master/status`
- `GET /api/otaku/master/metrics/{service_name}` where `service_name` is `labat` or `shania`
- `GET /api/otaku/master/anomalies`
- `GET /api/otaku/master/report`
- `POST /api/otaku/master/alert`
- `POST /api/otaku/master/report/send`
- `POST /api/otaku/master/check`
- `POST /api/otaku/master/notify`

## 4. Request/Response Contracts

### 4.1 Service status

`GET /api/otaku/master/status`

Response example:

```json
{
  "timestamp": "2026-03-27T18:20:00.000000",
  "services": {
    "labat": {
      "status": "healthy",
      "response_time_ms": 122.1,
      "role": "ads_money_leads",
      "health_data": {"status": "healthy"}
    },
    "shania": {
      "status": "healthy",
      "response_time_ms": 145.7,
      "role": "engagement_social_facebook",
      "health_data": {"status": "healthy"}
    }
  },
  "overall_status": "healthy"
}
```

### 4.2 Metrics by service

`GET /api/otaku/master/metrics/labat`

Response fields may include:
- `spend_today`
- `impressions_today`
- `clicks_today`
- `cpm`
- `cpc`
- `conversions`
- `purchase_roas`

`GET /api/otaku/master/metrics/shania`

Response fields may include:
- `monitor_running`
- `tracked_threads`
- `total_auto_replies`
- `last_poll`
- `poll_interval_seconds`

### 4.3 Anomaly detection

`GET /api/otaku/master/anomalies`

Response:

```json
{
  "timestamp": "2026-03-27T18:21:00.000000",
  "anomalies": [
    {
      "timestamp": "2026-03-27T18:20:59.000000",
      "service": "labat",
      "type": "low_conversion_rate",
      "severity": "warning",
      "message": "Conversion rate below expected",
      "metrics": {"conversion_rate": 0.4}
    }
  ]
}
```

### 4.4 Manual alert dispatch

`POST /api/otaku/master/alert`

Body:

```json
{
  "severity": "critical",
  "title": "Campaign Delivery Failure",
  "message": "No active ad sets delivering in last 30m",
  "service": "labat",
  "details": {
    "campaign_id": "120243213143990272",
    "window_minutes": 30
  }
}
```

Immediate response:

```json
{"status": "alert_sent"}
```

### 4.5 Trigger report generation + delivery

`POST /api/otaku/master/report/send`

Response:

```json
{"status": "report_generation_started"}
```

### 4.6 Trigger critical check

`POST /api/otaku/master/check`

Response:

```json
{"status": "critical_check_started"}
```

### 4.7 Customer-facing notification relay

`POST /api/otaku/master/notify`

Body:

```json
{
  "severity": "info",
  "title": "System Update",
  "message": "Engagement monitor restarted successfully",
  "service": "shania",
  "details": {
    "restart_reason": "manual_recover"
  }
}
```

Response:

```json
{"status": "notification_queued"}
```

## 5. Copy/Paste Examples

### 5.1 cURL

```bash
MASTER_URL="https://wihy-master-agent-<hash>-uc.a.run.app"
ADMIN_TOKEN="<your-internal-admin-token>"

curl -s "$MASTER_URL/api/otaku/master/status" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

```bash
curl -s "$MASTER_URL/api/otaku/master/metrics/labat" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

```bash
curl -s -X POST "$MASTER_URL/api/otaku/master/alert" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{
    "severity": "critical",
    "title": "Spend Spike",
    "message": "Spend increased > 50% in 1h",
    "service": "labat",
    "details": {"window_minutes": 60}
  }'
```

### 5.2 Python (httpx)

```python
import httpx

MASTER_URL = "https://wihy-master-agent-<hash>-uc.a.run.app"
ADMIN_TOKEN = "<your-internal-admin-token>"
HEADERS = {"X-Admin-Token": ADMIN_TOKEN}

with httpx.Client(timeout=20.0) as client:
    status = client.get(f"{MASTER_URL}/api/otaku/master/status", headers=HEADERS)
    status.raise_for_status()
    print("overall:", status.json().get("overall_status"))

    anomalies = client.get(f"{MASTER_URL}/api/otaku/master/anomalies", headers=HEADERS)
    anomalies.raise_for_status()
    print("anomalies:", len(anomalies.json().get("anomalies", [])))
```

## 6. Recommended External-Agent Integration Pattern

For external agents (different repos/services), use this pattern:

1. Poll `GET /api/otaku/master/status` every 1-5 minutes.
2. Poll `GET /api/otaku/master/anomalies` for event-like detection.
3. Call `POST /api/otaku/master/alert` when your agent detects critical issues.
4. Trigger `POST /api/otaku/master/report/send` on schedule (for example hourly).
5. Use `POST /api/otaku/master/notify` for user/customer-facing updates.

## 7. Error Handling

Expected status codes:
- `200`: success
- `401`: missing/invalid `X-Admin-Token`
- `400`: bad request (example: invalid `service_name`)
- `5xx`: upstream/internal failure

Suggested retry strategy:
- Retry on `429` and `5xx` with exponential backoff.
- Do not retry `401` or `400` blindly.

## 8. Security Notes For External Teams

- Never hardcode `X-Admin-Token` in source control.
- Store token in a secret manager.
- If exposing publicly, place API Gateway/IAP in front of Master Agent.
- Restrict by IP/service identity where possible.

## 9. Service Discovery Metadata (Optional)

The root endpoint can be used to discover API shape dynamically:
- `GET /`

It returns service name, version, and canonical endpoint paths.

---

## 10. Auth Service Integration — Email & Text Notifications

> **Full spec:** See [AUTH_NOTIFICATION_API.md](AUTH_NOTIFICATION_API.md) for the complete contract including request/response shapes, recipient resolution, rate limits, environment variables, and Python/Node/PowerShell helpers.

**All three agents (Otaku, LABAT, Shania) route email and SMS through `auth.wihy.ai`.** Agents never send email or SMS directly — auth.wihy.ai is the single delivery point.

### Summary

| Endpoint | Purpose |
|----------|---------|
| `POST https://auth.wihy.ai/api/notifications/alert` | Send email and/or SMS from any agent |
| `POST https://auth.wihy.ai/api/reports/master-agent` | Send hourly Otaku digest email |

### Auth Header (all requests)

```
X-Admin-Token: <INTERNAL_ADMIN_TOKEN from GCP Secret Manager: wihy-internal-admin-token>
Content-Type: application/json
```

No OAuth. No Bearer JWT. All internal service communication uses `X-Admin-Token` only.

### Minimal alert example

```json
{
  "title": "Campaign delivery stopped",
  "message": "No impressions in the last 30 minutes.",
  "severity": "critical",
  "agent": "labat",
  "service": "labat",
  "channels": ["email", "sms"],
  "details": { "campaign_id": "120243213143990272" }
}
```

Omit `recipient` to route to the admin fallback address. Add `"recipient": {"user_id": "uuid"}` to target a specific user — auth looks up their email/phone from the users table.

### Channel defaults

| `severity` | Default channels if `channels` omitted |
|-----------|---------------------------------------|
| `info` | `["email"]` |
| `warning` | `["email"]` |
| `critical` | `["email", "sms"]` |

### Required env vars on every agent Cloud Run service

```bash
AUTH_SERVICE_URL=https://auth.wihy.ai
INTERNAL_ADMIN_TOKEN=<from GCP Secret Manager: wihy-internal-admin-token>
```

### Required env vars on auth.wihy.ai Cloud Run service

```bash
INTERNAL_ADMIN_TOKEN=<same secret>
SENDGRID_API_KEY=<Secret Manager>
TWILIO_ACCOUNT_SID=<Secret Manager>
TWILIO_AUTH_TOKEN=<Secret Manager>
TWILIO_PHONE_NUMBER=<Secret Manager>
NOTIFICATION_ADMIN_EMAIL=support@wihy.ai
OTAKU_REPORT_EMAIL=<admin digest recipient>
```

See [AUTH_NOTIFICATION_API.md](AUTH_NOTIFICATION_API.md) for the full environment variable table, response shapes, rate limits, and what each agent (Otaku, LABAT, Shania) sends and when.

