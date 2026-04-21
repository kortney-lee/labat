#!/bin/bash

# setup-canva-secrets.sh - Create GCP secrets for Canva integration
#
# Usage:
#   ./setup-canva-secrets.sh <canva_api_token> [gcp_project_id]
#
# Example:
#   ./setup-canva-secrets.sh "cnv_1234567890abcdef" wihy-ai

set -e

if [ -z "$1" ]; then
  echo "❌ Error: Canva API token required"
  echo ""
  echo "Usage: $0 <canva_api_token> [gcp_project_id]"
  echo ""
  echo "Example:"
  echo "  $0 'cnv_1234567890abcdef' wihy-ai"
  exit 1
fi

CANVA_API_TOKEN="$1"
PROJECT_ID="${2:-wihy-ai}"
SERVICE_ACCOUNT="shania-runner@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Setting up Canva secrets for GCP project: $PROJECT_ID"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Create Canva API Token Secret
# ─────────────────────────────────────────────────────────────────────────────

echo "📝 Creating Canva API Token secret..."

if gcloud secrets describe canva-api-token --project="$PROJECT_ID" &>/dev/null; then
  echo "   ℹ️  Secret 'canva-api-token' already exists, creating new version..."
  echo -n "$CANVA_API_TOKEN" | gcloud secrets versions add canva-api-token \
    --project="$PROJECT_ID" \
    --data-file=-
else
  echo "$CANVA_API_TOKEN" | gcloud secrets create canva-api-token \
    --project="$PROJECT_ID" \
    --replication-policy="automatic" \
    --data-file=-
  echo "   ✅ Secret created"
fi

# Grant access to service account
echo "🔐 Granting Secret Manager access to service account: $SERVICE_ACCOUNT"
gcloud secrets add-iam-policy-binding canva-api-token \
  --project="$PROJECT_ID" \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

echo "   ✅ Access granted"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Create Brand Template Mappings Secret
# ─────────────────────────────────────────────────────────────────────────────

echo "📋 Creating Canva Brand Template Mappings secret..."

# Create temporary JSON file with template mappings
# Replace with actual template IDs once Canva templates are created
TEMPLATES_JSON=$(cat <<'EOF'
{
  "wihy": "REPLACE_WITH_WIHY_TEMPLATE_ID",
  "communitygroceries": "REPLACE_WITH_CG_TEMPLATE_ID",
  "vowels": "REPLACE_WITH_VOWELS_TEMPLATE_ID",
  "snackingwell": "REPLACE_WITH_SNACKINGWELL_TEMPLATE_ID",
  "childrennutrition": "REPLACE_WITH_CHILDRENNUTRITION_TEMPLATE_ID",
  "parentingwithchrist": "REPLACE_WITH_PWC_TEMPLATE_ID",
  "otakulounge": "REPLACE_WITH_OTAKU_TEMPLATE_ID"
}
EOF
)

TEMP_FILE=$(mktemp)
echo "$TEMPLATES_JSON" > "$TEMP_FILE"

if gcloud secrets describe canva-brand-templates --project="$PROJECT_ID" &>/dev/null; then
  echo "   ℹ️  Secret 'canva-brand-templates' already exists, creating new version..."
  gcloud secrets versions add canva-brand-templates \
    --project="$PROJECT_ID" \
    --data-file="$TEMP_FILE"
else
  gcloud secrets create canva-brand-templates \
    --project="$PROJECT_ID" \
    --replication-policy="automatic" \
    --data-file="$TEMP_FILE"
  echo "   ✅ Secret created"
fi

# Grant access to service account
gcloud secrets add-iam-policy-binding canva-brand-templates \
  --project="$PROJECT_ID" \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

echo "   ✅ Access granted"
rm -f "$TEMP_FILE"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Verify Secrets
# ─────────────────────────────────────────────────────────────────────────────

echo "✅ Verifying secrets..."

echo ""
echo "Canva API Token secret:"
gcloud secrets describe canva-api-token \
  --project="$PROJECT_ID" \
  --format="value(created)"

echo ""
echo "Brand Templates secret:"
gcloud secrets describe canva-brand-templates \
  --project="$PROJECT_ID" \
  --format="value(created)"

echo ""
echo "✅ All secrets created successfully!"
echo ""
echo "📌 Next Steps:"
echo "   1. Create Canva design templates in Canva Developer Portal"
echo "   2. Get the template IDs and update the canva-brand-templates secret:"
echo ""
echo "      gcloud secrets versions add canva-brand-templates \\"
echo "        --project=$PROJECT_ID \\"
echo "        --data-file=brand_templates.json"
echo ""
echo "   3. Deploy Shania to Cloud Run with Canva initialization"
echo ""
