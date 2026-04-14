# Asset Manifest — Brand Organization

Assets are organized by brand. **Do not mix assets across brand folders.**
SnackingWell is a sub-brand of Vowels — its assets go in `Vowels/`.

## Folder Structure

```
shania/assets/
├── ChildrensNutrition/  ← "What Is Healthy?" book brand (whatishealthy.org)
├── CommunityGroceries/  ← CG brand videos & logos
├── OtakuLounge/         ← Otaku Lounge (anime/manga)
├── ParentingWithChrist/ ← Parenting with Christ (faith-based)
├── Vowels/              ← Vowels data storytelling + SnackingWell
└── Wihy/                ← WIHY brand videos & logos
```

---

## ChildrensNutrition/ (What Is Healthy? Book)

**Page:** Childrens.Nutrition.Education (269598952893508)
**Domain:** whatishealthy.org

| File | Used As | Deployed To |
|------|---------|-------------|
| `5-STAR Hi Res 2025.png` | Award badge | `static_whatishealthy/award-5star.png` |
| `BookGreen.jpg` | Hero front cover | `static_whatishealthy/book-green.jpg` |
| `BookGreen.png` | PNG variant | — |
| `BookOrange.jpg` | Hero back stack + gallery | `static_whatishealthy/book-orange.jpg` |
| `BookOrange.png` | PNG variant | — |
| `Book3.jpg` | Chapter preview cover | `static_whatishealthy/book-cover.jpg` |
| `Book6.jpg` | Mid stack + gallery | `static_whatishealthy/book-cg.jpg` |
| `Book1.jpg`, `Book2.jpg`, `Book8.jpg`, `Book9.jpg` | Gallery / alt editions | Various |
| `Untitled (6 x 9 in).jpg` | Spread image | `static_whatishealthy/book-spread.jpg` |
| `Untitled (6 x 9 in) (1).png` | Spread image | `static_whatishealthy/book-spread.png` |
| `WhatisHealthy_eBook.pdf` | Free eBook download | `static_whatishealthy/WhatisHealthy_eBook.pdf` |
| `childrennutrition_logo.png` | Brand logo | **TODO** — create |

## CommunityGroceries/

**Page:** Community Groceries (2051601018287997)
**Domain:** communitygroceries.com

| File | Used As | Deployed To |
|------|---------|-------------|
| `cg_logo.png` | Logo (stat ads) | `shania/assets/CommunityGroceries/cg_logo.png` |
| `CG_logo_app.png` | App logo (high-res) | — |
| `CGHeader_fb.mp4` | Landscape video (YouTube, Facebook feed) | `static_whatishealthy/cg-header.mp4` |
| `CGHeader_mobile.mp4` | Vertical video 9:16 (Reels, Stories, TikTok) | — |

**GCS:** `gs://cg-web-assets/images/Logo_CG.png` (live)

## Wihy/

**Page:** WiHy.ai (937763702752161)
**Domain:** wihy.ai

| File | Used As | Deployed To |
|------|---------|-------------|
| `wihy_logo.png` | Logo (stat ads) | `shania/assets/Wihy/wihy_logo.png` |
| `Favicon-web.png` | Web favicon | — |
| `WIHYVIDEO_web.mp4` | Landscape video (YouTube, Facebook feed) | — |
| `WIHYVIDEO_Mobile.mp4` | Vertical video 9:16 (Reels, Stories, TikTok) | — |

**GCS:** `gs://wihy-web-assets/images/Logo_wihy.png` (live)

## Vowels/ (+ SnackingWell)

**Page:** Vowels.Org (100193518975897)
**Domain:** vowels.org
**Sub-brand:** SnackingWell (snackingwell.com) — publishes to Vowels page

| File | Used As | Deployed To |
|------|---------|-------------|
| `Vowels_logo.png` | Original logo | — |
| `vowels_logo.png` | Standardized logo (stat ads) | `shania/assets/Vowels/vowels_logo.png` |

> Book assets formerly here were moved to `ChildrensNutrition/` (April 2026).

## ParentingWithChrist/

**Page:** Parenting with Christ (329626030226536)

| File | Used As | Status |
|------|---------|--------|
| `parentingwithchrist_logo.png` | Brand logo | **TODO** — create |

No assets yet. Add logo and media as they become available.

## OtakuLounge/

**Page:** Otaku.lounge (244564118751271)

| File | Used As | Status |
|------|---------|--------|
| `otakulounge_logo.png` | Brand logo | **TODO** — create |

No assets yet. Add logo and media as they become available.

---

## Logo Standardization

All brands use `{brand}_logo.png` in their folder. `generate_stat_ads.py` references:
- `shania/assets/Wihy/wihy_logo.png`
- `shania/assets/CommunityGroceries/cg_logo.png`
- `shania/assets/Vowels/vowels_logo.png`

GCS upload target: `gs://wihy-web-assets/images/brands/{brand}_logo.png`

---

## Refresh Command (whatishealthy.org static assets)

```powershell
$cn = "shania\assets\ChildrensNutrition"
$cg = "shania\assets\CommunityGroceries"
$dest = "static_whatishealthy"

Copy-Item "$cn\5-STAR Hi Res 2025.png" "$dest\award-5star.png" -Force
Copy-Item "$cn\BookGreen.jpg" "$dest\book-green.jpg" -Force
Copy-Item "$cn\BookOrange.jpg" "$dest\book-orange.jpg" -Force
Copy-Item "$cn\Book6.jpg" "$dest\book-cg.jpg" -Force
Copy-Item "$cn\Book3.jpg" "$dest\book-cover.jpg" -Force
Copy-Item "$cn\Book9.jpg" "$dest\book-alt.jpg" -Force
Copy-Item "$cn\WhatisHealthy_eBook.pdf" "$dest\WhatisHealthy_eBook.pdf" -Force
Copy-Item "$cn\Untitled (6 x 9 in).jpg" "$dest\book-spread.jpg" -Force
Copy-Item "$cn\Untitled (6 x 9 in) (1).png" "$dest\book-spread.png" -Force
Copy-Item "$cg\CGHeader_fb.mp4" "$dest\cg-header.mp4" -Force
```
