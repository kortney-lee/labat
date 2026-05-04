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

Write-Host "[4/4] Deployment successful" -ForegroundColor Green
Write-Host "Live URL: https://vowels-org.web.app" -ForegroundColor Green
Write-Host "RSS: https://vowels-org.web.app/rss.xml" -ForegroundColor Green
Write-Host "JSON Feed: https://vowels-org.web.app/feed" -ForegroundColor Green
