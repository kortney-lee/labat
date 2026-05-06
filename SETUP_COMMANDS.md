# Infrastructure Setup Commands

Run these once to connect all the missing wiring. Replace placeholder values with your actual secrets.

---

## 1. Generate META_WEBHOOK_VERIFY_TOKEN

Run this locally to generate a secure token:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Save the output — you'll use it in step 2 and step 5.

---

## 2. Update wihy-labat Cloud Run env vars

```bash
gcloud run services update wihy-labat \
  --region us-central1 \
  --project wihy-ai \
  --update-env-vars META_WEBHOOK_VERIFY_TOKEN=<your-generated-token>,\
LINKEDIN_ACCESS_TOKEN=<from-linkedin-dev-portal>,\
LINKEDIN_ORG_ID=<your-numeric-org-id>
```

---

## 3. Update wihy-maya Cloud Run env vars

```bash
gcloud run services update wihy-maya \
  --region us-central1 \
  --project wihy-ai \
  --update-env-vars \
SOCIAL_POSTING_DISABLED=false,\
SOCIAL_POSTING_LAUNCH_MODE=true,\
TWITTER_API_KEY=<from-developer.twitter.com>,\
TWITTER_API_SECRET=<from-developer.twitter.com>,\
TWITTER_ACCESS_TOKEN=<from-developer.twitter.com>,\
TWITTER_ACCESS_TOKEN_SECRET=<from-developer.twitter.com>,\
TWITTER_BOT_USERNAME=wihyhealthbot,\
TWITTER_MY_USER_ID=<your-bot-account-numeric-id>,\
INSTAGRAM_ACCESS_TOKEN=<long-lived-page-token>,\
INSTAGRAM_BUSINESS_USER_ID=<your-ig-business-numeric-id>,\
FACEBOOK_ACCESS_TOKEN=<page-access-token>,\
THREADS_ACCESS_TOKEN=<threads-api-token>
```

### How to get TWITTER_MY_USER_ID

```bash
# After setting Twitter keys, call the API to get your bot's numeric ID:
curl -s "https://api.twitter.com/2/users/by/username/wihyhealthbot" \
  -H "Authorization: Bearer <TWITTER_BEARER_TOKEN>" | python -m json.tool
```

### How to get INSTAGRAM_BUSINESS_USER_ID

```bash
curl -s "https://graph.facebook.com/v19.0/me/accounts?access_token=<PAGE_ACCESS_TOKEN>" \
  | python -m json.tool
# Then use the linked IG business account ID from:
curl -s "https://graph.facebook.com/v19.0/<PAGE_ID>?fields=instagram_business_account&access_token=<PAGE_ACCESS_TOKEN>"
```

---

## 4. Update wihy-shania Cloud Run env vars

```bash
gcloud run services update wihy-shania \
  --region us-central1 \
  --project wihy-ai \
  --update-env-vars \
SOCIAL_POSTING_DISABLED=false,\
LINKEDIN_ACCESS_TOKEN=<from-linkedin-dev-portal>,\
LINKEDIN_ORG_ID=<your-numeric-org-id>
```

---

## 5. Create Cloud Scheduler job for Labat hourly automation

```bash
gcloud scheduler jobs create http labat-automation-cron \
  --project wihy-ai \
  --location us-central1 \
  --schedule "0 * * * *" \
  --uri "https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/automation/cron" \
  --http-method POST \
  --headers "x-admin-token=<your-INTERNAL_ADMIN_TOKEN>,Content-Type=application/json" \
  --message-body "{}" \
  --time-zone "America/New_York" \
  --description "Labat hourly automation: auto-pause, auto-scale, A/B rotation"
```

**Test it immediately (dry run):**

```bash
curl -X POST \
  "https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/automation/cron?dry_run=true" \
  -H "x-admin-token: <your-INTERNAL_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{}"
```

---

## 6. Configure Meta Webhook (leads intake)

1. Go to [Meta for Developers](https://developers.facebook.com) → Your App → Webhooks
2. Click **Add Subscription** → Object: `leadgen`
3. Callback URL: `https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/webhook`
4. Verify Token: paste the token you generated in step 1
5. Subscribe to fields: `leadgen`
6. Click Verify and Save

**Test with Meta's webhook test tool:**
- In the developer dashboard, go to Webhooks → Send Test Notification
- Choose `leadgen` and send — you should see a log entry in Cloud Run for `wihy-labat`

---

## 7. LinkedIn OAuth (get access token)

LinkedIn tokens don't have an automated flow — you need to do this manually:

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) → Create App
2. Add products: **Marketing Developer Platform** + **Share on LinkedIn**
3. Request scopes: `w_member_social`, `r_organization_social`, `w_organization_social`
4. Go to Auth tab → OAuth 2.0 Tools → Generate token
5. Copy the access token — it's valid for 60 days

**Get your Org ID:**

```bash
curl -s "https://api.linkedin.com/v2/organizationAcls?q=roleAssignee&count=10" \
  -H "Authorization: Bearer <your-linkedin-token>" | python -m json.tool
# Look for the organization URN — numeric ID is at the end
```

**Set a calendar reminder to refresh the LinkedIn token every 55 days.**

---

## 8. Verify everything is working

```bash
# Labat health check
curl https://wihy-labat-n4l2vldq3q-uc.a.run.app/health

# Maya health check — should show all services running
curl https://wihy-maya-<your-url>.run.app/health

# Trigger audience discovery dry-run
curl -X GET \
  "https://wihy-maya-<your-url>.run.app/api/engagement/discover/preview?hashtag=nutrition&brand=wihy" \
  -H "x-admin-token: <INTERNAL_ADMIN_TOKEN>"

# Check collaborator candidates
curl "https://wihy-maya-<your-url>.run.app/api/engagement/collaborators?brand=wihy" \
  -H "x-admin-token: <INTERNAL_ADMIN_TOKEN>"

# Check auto-engage daily status
curl "https://wihy-maya-<your-url>.run.app/api/engagement/auto-engage/status" \
  -H "x-admin-token: <INTERNAL_ADMIN_TOKEN>"
```

---

## 9. Add Amazon affiliate vars (book promotion MVP)

```bash
gcloud run services update wihy-labat \
  --region us-central1 \
  --project wihy-ai \
  --update-env-vars \
AMAZON_ASSOCIATE_TAG=<your-associate-tag>,\
AMAZON_MARKETPLACE=amazon.com,\
BOOK_PRIMARY_ASIN=B0DL7Z7NFL,\
BOOK_PROMO_AUTOMATION_ENABLED=true
```

**Manual dry run (no publish):**

```bash
curl -X POST \
  "https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/book-affiliate/publish" \
  -H "x-admin-token: <your-INTERNAL_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true}'
```

**Trigger affiliate cron endpoint:**

```bash
curl -X POST \
  "https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/automation/book-affiliate-cron?dry_run=true" \
  -H "x-admin-token: <your-INTERNAL_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{}"
```

---

## 10. Add Amazon Ads API credentials (scaffolding)

```bash
gcloud run services update wihy-labat \
  --region us-central1 \
  --project wihy-ai \
  --update-env-vars \
AMAZON_ADS_CLIENT_ID=<amazon-ads-client-id>,\
AMAZON_ADS_CLIENT_SECRET=<amazon-ads-client-secret>,\
AMAZON_ADS_REFRESH_TOKEN=<amazon-ads-refresh-token>,\
AMAZON_ADS_SCOPE_PROFILE_ID=<amazon-profile-id>,\
AMAZON_ADS_REGION=na
```

**Check scaffold health endpoint:**

```bash
curl "https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/amazon-ads/health" \
  -H "x-admin-token: <your-INTERNAL_ADMIN_TOKEN>"
```

**List Amazon Ads profiles:**

```bash
curl "https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/amazon-ads/profiles" \
  -H "x-admin-token: <your-INTERNAL_ADMIN_TOKEN>"
```
