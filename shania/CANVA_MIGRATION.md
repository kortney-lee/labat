# Shania Canva Migration Status

**Status**: ✅ **Implementation Complete** — Ready for Canva credential setup

**Date**: April 20, 2026  
**Target**: 100% Canva API for all post graphics (replacing custom HTML templates)

## What Changed

### Before (HTML Templates)
```
User Input
    ↓
Gemini generates content
    ↓
Select HTML template (stat_card, hook_square, etc.)
    ↓
Render HTML with Puppeteer
    ↓
Screenshot to PNG/JPEG
    ↓
Upload to social media
```

**Problems:**
- 20+ custom HTML templates to maintain
- Puppeteer screenshot inconsistencies across browsers
- Limited design flexibility
- CSS/styling bugs in production
- Hard to iterate on designs

### Now (Canva API)
```
User Input
    ↓
Gemini generates content
    ↓
Call Canva API with brand template + dynamic data
    ↓
Canva exports design as PNG/JPEG
    ↓
Upload to social media
```

**Benefits:**
- ✅ Professional, consistent designs
- ✅ No more Puppeteer dependencies
- ✅ Brand-specific templates (7 brands, 7 templates)
- ✅ Easy to update designs without code changes
- ✅ Unlimited design flexibility
- ✅ Built-in Canva templates & asset library
- ✅ 100% design control via Canva UI

## Implementation Summary

### New Files Created

```
shania/
├── src/
│   ├── services/
│   │   └── canvaService.ts              ← Canva API client
│   ├── config/
│   │   └── canva.ts                     ← Brand-to-template mappings
│   ├── utils/
│   │   └── canvaSecrets.ts              ← Load credentials from GCP
│   └── jobs/
│       └── testCanvaIntegration.ts      ← Integration test script
├── CANVA_SETUP.md                       ← Setup documentation
└── setup-canva-secrets.sh               ← GCP secret creation script
```

### Modified Files

```
shania/
├── src/
│   ├── ai/
│   │   └── postGenerator.ts             ✏️ Use Canva instead of HTML rendering
│   └── index.ts                         ✏️ Initialize Canva on startup
└── package.json                          ✏️ Add @google-cloud/secret-manager
```

### Deprecated (No Longer Used)

```
shania/src/templates/                    ← 20+ HTML template files
├── stat-card/
├── research-card/
├── hook-square/
├── photo-overlay/
├── quote-card/
├── cta-card/
└── ... (all others)
```

These can be deleted or archived after migration is confirmed to be working.

## Configuration Checklist

### Phase 1: Canva Developer Setup
- [ ] Create Canva developer account
- [ ] Create design app in Canva Developer Portal
- [ ] Get Canva API credentials (API token)
- [ ] Create 7 design templates in Canva (one per brand)

### Phase 2: GCP Secrets Setup
- [ ] Create `canva-api-token` secret in GCP Secret Manager
- [ ] Create `canva-brand-templates` secret in GCP Secret Manager
- [ ] Grant service account access to both secrets
- [ ] Verify secrets are readable

### Phase 3: Environment Configuration
- [ ] Set `CANVA_API_TOKEN` environment variable (or load from GCP)
- [ ] Set `CANVA_TEMPLATE_*` for each brand (or load from GCP)
- [ ] Ensure `GCP_PROJECT` is set for production

### Phase 4: Testing
- [ ] Run `npm run build`
- [ ] Run `node dist/jobs/testCanvaIntegration.js`
- [ ] Verify designs are created successfully
- [ ] Verify designs are exported correctly

### Phase 5: Deployment
- [ ] Deploy updated Shania service to Cloud Run
- [ ] Monitor logs for Canva initialization
- [ ] Test post generation through ALEX/LABAT
- [ ] Verify social media posts use new designs

### Phase 6: Cleanup (Optional)
- [ ] Remove deprecated HTML template files from `src/templates/`
- [ ] Remove Puppeteer dependency if not used elsewhere
- [ ] Archive old template documentation

## Brand Template Configuration

Each brand needs a Canva design template with these capabilities:

### WIHY
- **Template Name**: WIHY Stats/Research Card
- **Size**: 1200x1200px (Instagram feed)
- **Colors**: Orange (#fa5f06) + Blue (#0c1d2e)
- **Editable Fields**: headline, subtext, statNumber, statLabel, dataPoints
- **Assets**: WIHY logo, accent shapes

### Community Groceries
- **Template Name**: CG Lifestyle/Recipe Card  
- **Size**: 1200x1200px
- **Colors**: Green + warm orange
- **Editable Fields**: headline, subtext, tip, tipLabel, items
- **Assets**: CG logo, app screenshots

### Vowels
- **Template Name**: Vowels Education Card
- **Size**: 1200x1200px
- **Colors**: Purple/Blue academic tones
- **Editable Fields**: headline, subtext, dataPoints, source, quote
- **Assets**: Vowels logo, book imagery

### Snacking Well
- **Template Name**: Snacking Well Product Card
- **Size**: 1200x1200px
- **Colors**: Gold accents, product-focused
- **Editable Fields**: productName, productImage, statNumber, badge
- **Assets**: Snacking Well logo

### Children's Nutrition
- **Template Name**: Vowels Children's Education (same as Vowels)
- **Size**: 1200x1200px
- **Colors**: Purple/Blue, family-friendly
- **Editable Fields**: headline, subtext, dataPoints, quote
- **Assets**: Children's Nutrition branding

### Parenting with Christ
- **Template Name**: Faith-Focused Family Card
- **Size**: 1200x1200px
- **Colors**: Warm, inviting tones
- **Editable Fields**: headline, subtext, quote, attribution
- **Assets**: Logo, faith symbols

### Otaku Lounge
- **Template Name**: Anime/Pop Culture Design
- **Size**: 1200x1200px
- **Colors**: Purple, hot pink, vibrant
- **Editable Fields**: headline, subtext, badge, cta
- **Assets**: Otaku Lounge logo, anime-inspired graphics

## Environment Variables

### For Local Development

```bash
export CANVA_API_TOKEN="your_canva_api_token_here"
export CANVA_TEMPLATE_WIHY="template_id_wihy"
export CANVA_TEMPLATE_CG="template_id_cg"
export CANVA_TEMPLATE_VOWELS="template_id_vowels"
export CANVA_TEMPLATE_SNACKINGWELL="template_id_snackingwell"
export CANVA_TEMPLATE_CHILDRENNUTRITION="template_id_cn"
export CANVA_TEMPLATE_PARENTINGWITHCHRIST="template_id_pwc"
export CANVA_TEMPLATE_OTAKULOUNGE="template_id_otaku"
```

### For Production (GCP)

```bash
GCP_PROJECT=wihy-ai
# Secrets loaded automatically from GCP Secret Manager
```

## GCP Secrets Structure

### canva-api-token
```
Secret: canva-api-token
Value: cnv_1234567890abcdef...
Access: shania-runner@wihy-ai.iam.gserviceaccount.com
```

### canva-brand-templates
```json
{
  "wihy": "design_123abc_wihy",
  "communitygroceries": "design_456def_cg",
  "vowels": "design_789ghi_vowels",
  "snackingwell": "design_012jkl_sw",
  "childrennutrition": "design_345mno_cn",
  "parentingwithchrist": "design_678pqr_pwc",
  "otakulounge": "design_901stu_otaku"
}
```

## Quick Start

### 1. Install Dependencies
```bash
cd shania
npm install
```

### 2. Create GCP Secrets
```bash
./setup-canva-secrets.sh "your_canva_api_token" wihy-ai
```

### 3. Test Integration
```bash
npm run build
CANVA_API_TOKEN="..." node dist/jobs/testCanvaIntegration.js
```

### 4. Deploy
```bash
gcloud run deploy wihy-shania \
  --source . \
  --set-env-vars="CANVA_API_TOKEN=$(gcloud secrets versions access latest --secret='canva-api-token')" \
  --allow-unauthenticated
```

## Rollback Plan

If Canva integration has issues, you can temporarily rollback to HTML templates:

1. Keep the old HTML template files (don't delete `src/templates/`)
2. Revert `postGenerator.ts` to use `renderTemplateForBrand()`
3. Re-add `puppeteer` and rendering code
4. Deploy the reverted version

**Timeline**: 30 minutes to rollback

## Monitoring

### Key Metrics
- Canva API success rate
- Design creation latency
- Export success rate
- Error rates by brand

### Logs to Watch
```bash
# Monitor Canva initialization
gcloud run logs read wihy-shania --limit=100 | grep -i canva

# Monitor design creation
gcloud run logs read wihy-shania --limit=100 | grep "Canva design"

# Monitor errors
gcloud run logs read wihy-shania --limit=100 | grep "error"
```

## Troubleshooting

### Canva API Token Invalid
```bash
# Verify token is set
echo $CANVA_API_TOKEN

# Check GCP secret
gcloud secrets versions access latest --secret='canva-api-token' --project=wihy-ai
```

### Template IDs Not Found
```bash
# Check template mapping
gcloud secrets versions access latest --secret='canva-brand-templates' --project=wihy-ai

# Verify template IDs are actual Canva design IDs
# (format: typically starts with 'dJAy1' or similar)
```

### Design Export Fails
- Ensure Canva API token has `designs:export` scope
- Verify brand template exists in Canva
- Check Canva API rate limits

### Images Not Showing in Design
- Ensure photo URLs are publicly accessible
- Check Canva API timeout settings (default: 30s)
- Verify image formats are supported (PNG, JPG, WebP)

## Success Criteria

✅ All items completed:
- [ ] Canva client initializes on startup
- [ ] Design creation works for all 7 brands
- [ ] Exported images are correct size (1200x1200px)
- [ ] Post generation completes in < 5 seconds
- [ ] Social media posts use new Canva designs
- [ ] No regressions in post quality
- [ ] Monitoring shows < 0.1% error rate

## Next Steps

1. **Setup Canva Developer Account**
   - Go to https://www.canva.com/developers
   - Create developer account
   - Get API credentials

2. **Create Design Templates**
   - One template per brand
   - Configure with dynamic text fields
   - Test with sample data

3. **Set Up GCP Secrets**
   - Run `./setup-canva-secrets.sh`
   - Update with real template IDs
   - Verify access controls

4. **Deploy & Test**
   - Run integration tests
   - Deploy to staging
   - Run full end-to-end tests
   - Deploy to production

## Support & Resources

- **Canva API Docs**: https://www.canva.com/developers/docs
- **GCP Secret Manager**: https://cloud.google.com/secret-manager
- **Shania Internal Docs**: See other `.md` files in this directory

---

**Status**: Ready for Phase 1 setup  
**Owner**: Shania Team  
**Last Updated**: April 20, 2026
