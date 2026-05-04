$ErrorActionPreference = "Stop"

Set-Location "C:\Users\Kortn\Repo\labat\vowels"
Write-Host "[1/4] Building Vowels..." -ForegroundColor Cyan
npm run build

Set-Location "C:\Users\Kortn\Repo\labat"
Write-Host "[2/4] Deploying to Firebase Hosting..." -ForegroundColor Cyan
firebase deploy --only hosting:vowels --project wihy-ai --config firebase.vowels.json

Write-Host "[3/4] Smoke checks..." -ForegroundColor Cyan
$home = Invoke-WebRequest -Uri "https://vowels-org.web.app" -UseBasicParsing -TimeoutSec 60
$rss = Invoke-WebRequest -Uri "https://vowels-org.web.app/rss.xml" -UseBasicParsing -TimeoutSec 60
$feed = Invoke-WebRequest -Uri "https://vowels-org.web.app/feed" -UseBasicParsing -TimeoutSec 60

if ($home.StatusCode -ne 200 -or $rss.StatusCode -ne 200 -or $feed.StatusCode -ne 200) {
  throw "Smoke check failed: home=$($home.StatusCode), rss=$($rss.StatusCode), feed=$($feed.StatusCode)"
}

Write-Host "[4/5] Triggering Alex SEO cycles..." -ForegroundColor Cyan
$alexUrl = (gcloud run services describe wihy-alex-vowels --region us-central1 --project wihy-ai --format="value(status.url)").Trim()

if (-not $alexUrl) {
  Write-Host "Could not resolve Alex service URL; skipping trigger." -ForegroundColor Yellow
} else {
  $health = Invoke-WebRequest -Uri "$alexUrl/api/astra/health" -UseBasicParsing -TimeoutSec 60
  if ($health.StatusCode -eq 200) {
    $token = ""
    try {
      $token = (gcloud secrets versions access latest --secret internal-admin-token --project wihy-ai).Trim()
    } catch {
      Write-Host "Could not load internal-admin-token secret; skipping trigger/all." -ForegroundColor Yellow
    }

    if ($token) {
      Invoke-WebRequest -Uri "$alexUrl/api/astra/trigger/all" -Method POST -UseBasicParsing -TimeoutSec 60 -Headers @{ "x-admin-token" = $token } | Out-Null
      Write-Host "Alex SEO trigger/all started." -ForegroundColor Green
    }
  } else {
    Write-Host "Alex health check failed; skipping trigger." -ForegroundColor Yellow
  }
}

Write-Host "[5/5] Deployment successful" -ForegroundColor Green
Write-Host "Live URL: https://vowels-org.web.app" -ForegroundColor Green
Write-Host "RSS: https://vowels-org.web.app/rss.xml" -ForegroundColor Green
Write-Host "JSON Feed: https://vowels-org.web.app/feed" -ForegroundColor Green
