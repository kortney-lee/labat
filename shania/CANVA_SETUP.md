# Canva Integration Setup Guide

## Overview

Shania now uses **Canva API** for 100% of post graphics instead of custom HTML templates. Each brand has its own Canva design template that can be customized with dynamic text and images.

## Prerequisites

- Canva Developer Account (create at https://www.canva.com/developers)
- GCP Project with Secret Manager enabled
- Node.js v24+ with npm v11+

## Step 1: Create Canva Design Templates

For each brand (WIHY, Community Groceries, Vowels, etc.), you need to create a design template in Canva:

### In Canva Developer Portal:

1. Go to **Apps** > **Create app**
2. Select **Design Editor** as the integration type
3. Create a design template with:
   - Brand colors and logos
   - Editable text fields (headline, subtext, cta, etc.)
   - Layout for social media posts (1200x1200px for Instagram/Facebook feeds)
   - Support for variable content:
     - `{{headline}}` - Main text
     - `{{subtext}}` - Secondary text
     - `{{photoUrl}}` - Image/photo embed
     - `{{statNumber}}` - Large stat number
     - `{{dataPoints}}` - Array of key findings
     - `{{cta}}` - Call-to-action text

4. Publish the template and note the **Template ID** (e.g., `dJAy1qz9x1Y`)

### Templates to Create (one per brand):

```
Brand ID                   Template Name                Description
─────────────────────────────────────────────────────────────────────────────
wihy                       WIHY Stats/Research Card     Orange + blue, modern design
communitygroceries         CG Recipe/Lifestyle Card     Warm colors, app screenshots
vowels                     Vowels Education Card        Purple/blue, book imagery
snackingwell               Snacking Well Product        Gold accents, snack focus
childrennutrition          Vowels (same as vowels)      Educational, family-friendly
parentingwithchrist        Family-Focused Card          Warm, faith-messaging
otakulounge                Otaku Design                 Purple, hot pink, anime vibes
```

## Step 2: Create GCP Secrets

### 2.1 Canva API Token Secret

Store your Canva API token in GCP Secret Manager:

```bash
# Set variables
PROJECT_ID="wihy-ai"
CANVA_API_TOKEN="your_canva_api_token_here"

# Create secret
gcloud secrets create canva-api-token \
  --project=$PROJECT_ID \
  --replication-policy="automatic" \
  --data-file=- <<< "$CANVA_API_TOKEN"

# Grant access to Shania services (Cloud Run service accounts)
gcloud secrets add-iam-policy-binding canva-api-token \
  --project=$PROJECT_ID \
  --member="serviceAccount:shania-runner@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2.2 Brand Template Mappings Secret

Create a JSON file mapping brands to their Canva template IDs:

```json
{
  "wihy": "dJAy1qz9x1Y_wihy_template",
  "communitygroceries": "dJAy1qz9x1Y_cg_template",
  "vowels": "dJAy1qz9x1Y_vowels_template",
  "snackingwell": "dJAy1qz9x1Y_snackingwell_template",
  "childrennutrition": "dJAy1qz9x1Y_vowels_template",
  "parentingwithchrist": "dJAy1qz9x1Y_pwc_template",
  "otakulounge": "dJAy1qz9x1Y_otaku_template"
}
```

```bash
# Create secret
gcloud secrets create canva-brand-templates \
  --project=$PROJECT_ID \
  --replication-policy="automatic" \
  --data-file=brand_templates.json

# Grant access
gcloud secrets add-iam-policy-binding canva-brand-templates \
  --project=$PROJECT_ID \
  --member="serviceAccount:shania-runner@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Step 3: Environment Configuration

In your deployment (Cloud Run, Kubernetes, etc.), set these environment variables:

```bash
# For development (loads from env vars instead of GCP)
CANVA_API_TOKEN="your_api_token_here"
CANVA_TEMPLATE_WIHY="template_id_here"
CANVA_TEMPLATE_CG="template_id_here"
CANVA_TEMPLATE_VOWELS="template_id_here"
CANVA_TEMPLATE_SNACKINGWELL="template_id_here"
CANVA_TEMPLATE_CHILDRENNUTRITION="template_id_here"
CANVA_TEMPLATE_PARENTINGWITHCHRIST="template_id_here"
CANVA_TEMPLATE_OTAKULOUNGE="template_id_here"

# For production (GCP loads from Secret Manager)
GCP_PROJECT="wihy-ai"
```

## Step 4: Update Shania Deployment

### Install Dependencies

```bash
cd shania
npm install
npm run build
```

### Deploy to Cloud Run

```bash
gcloud run deploy wihy-shania \
  --source . \
  --project=wihy-ai \
  --region=us-central1 \
  --service-account=shania-runner@wihy-ai.iam.gserviceaccount.com \
  --set-env-vars="CANVA_API_TOKEN=$(gcloud secrets versions access latest --secret='canva-api-token' --project=wihy-ai)" \
  --allow-unauthenticated
```

Or for all brand deployments:

```bash
brands=("wihy" "cg" "vowels" "pwc" "cn" "otaku-cg")
for brand in "${brands[@]}"; do
  gcloud run deploy wihy-shania-${brand} \
    --source . \
    --project=wihy-ai \
    --region=us-central1 \
    --set-env-vars="CANVA_API_TOKEN=$(gcloud secrets versions access latest --secret='canva-api-token' --project=wihy-ai)" \
    --allow-unauthenticated
done
```

## Step 5: Initialize Canva Client in Application

In your main application file (e.g., `src/index.ts`), initialize the Canva client:

```typescript
import { initCanvaClient } from "./services/canvaService";
import { initCanvaSecrets } from "./utils/canvaSecrets";

async function startApp() {
  try {
    // Load Canva secrets from GCP or environment
    const secrets = await initCanvaSecrets();
    
    // Initialize Canva client
    initCanvaClient(secrets.apiToken);
    
    logger.info("✅ Canva integration initialized");
  } catch (error) {
    logger.error("Failed to initialize Canva:", error);
    process.exit(1);
  }

  // ... rest of your app startup code
}

startApp();
```

## Step 6: Verify Integration

Test the integration:

```bash
# Test design creation and export
curl -X POST http://localhost:3000/api/test/canva \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "wihy",
    "headline": "Test Headline",
    "subtext": "Test subtext"
  }'
```

## Troubleshooting

### "Canva API token not configured"

- Check that `CANVA_API_TOKEN` is set in environment
- Or verify GCP Secret Manager has `canva-api-token` secret
- Verify service account has `roles/secretmanager.secretAccessor`

### "No Canva template configured for brand: X"

- Ensure template ID is set for the brand in `CANVA_TEMPLATE_X` env var
- Or verify `canva-brand-templates` secret has correct mapping
- Template IDs must be actual Canva design template IDs

### Design export fails with "rate limit"

- Canva API has rate limits; implement retry logic with exponential backoff
- Current implementation has 30-second timeout

### Images not showing in exported design

- Ensure `photoUrl` is a publicly accessible URL
- Canva needs to download the image during export
- Use base64 data URIs for small images, or upload to storage bucket

## Migration from HTML Templates

Old HTML template files in `src/templates/` are **deprecated** and no longer used:

```
src/templates/
├── stat-card/                 ← DEPRECATED
├── research-card/             ← DEPRECATED
├── hook-square/               ← DEPRECATED
├── photo-overlay/             ← DEPRECATED
└── ... (all others)           ← DEPRECATED
```

You can safely keep these for reference or historical purposes, but they're not active.

## Monitoring & Analytics

Monitor Canva API usage:

```bash
# Check secret access logs
gcloud secrets versions access latest --secret='canva-api-token' \
  --project=wihy-ai --log=cloud-logging

# View Cloud Run logs for Canva errors
gcloud run logs read wihy-shania \
  --project=wihy-ai \
  --limit=100 | grep -i canva
```

## Support

For Canva API issues, see:
- https://www.canva.com/developers/docs
- Canva Developer Portal support
- Canva API rate limits documentation

## Additional Resources

- [Canva API Documentation](https://www.canva.com/developers/docs)
- [Canva Design Editor Integration](https://www.canva.com/developers/docs/integrations/design-editor)
- [Canva Design Templates API](https://www.canva.com/developers/docs/design-templates-api)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)
