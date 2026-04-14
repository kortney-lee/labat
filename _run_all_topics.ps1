# Run 50 posts for each underrepresented topic (fitness already running separately)
$topics = @(
    "supplements",
    "nutrition",
    "weight-management",
    "mental-health",
    "sugar-and-blood-health",
    "sleep",
    "meal-planning",
    "processed-foods",
    "fasting",
    "gut-health",
    "food-scanning",
    "heart-health",
    "alcohol-and-health",
    "protein-and-muscle",
    "hydration",
    "immune-health",
    "wellness",
    "brain-health",
    "hormones",
    "longevity",
    "health-apps"
)

$limit = 50
$total = $topics.Count
$i = 0
$results = @()

foreach ($topic in $topics) {
    $i++
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "[$ts] [$i/$total] Topic: $topic (limit $limit)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    .\.venv\Scripts\python.exe -m src.content.generate_wihy_posts --topic $topic --limit $limit 2>&1 | ForEach-Object { $_ }
    $sw.Stop()

    $results += [PSCustomObject]@{
        Topic = $topic
        Duration = "$([math]::Round($sw.Elapsed.TotalMinutes, 1))m"
    }

    Write-Host "[$topic] Completed in $([math]::Round($sw.Elapsed.TotalMinutes, 1)) minutes" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "ALL TOPICS COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
$results | Format-Table -AutoSize

# ── Auto-regenerate sitemap with all new posts ──
Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host "Regenerating sitemap.xml..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# Re-download latest index from GCS
gcloud storage cp "gs://wihy-web-assets/blog/posts/index.json" "data/index.json" 2>$null

# Regenerate and upload sitemap
.\.venv\Scripts\python.exe _regen_sitemap.py

# Deploy to Firebase hosting
firebase deploy --only hosting:ml-wihy-ai --project wihy-ai 2>&1 | Select-Object -Last 5

Write-Host "`nSitemap updated and deployed!" -ForegroundColor Green
