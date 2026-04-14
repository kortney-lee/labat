$BASE = "https://wihy-shania-graphics-12913076533.us-central1.run.app"
$TOKEN = "wihy-admin-token-2026"
$results = @()

$brandPrompts = @{
    wihy                = "The hidden truth about processed food ingredients the industry doesn't want you to know"
    communitygroceries  = "Simple weekly meal prep ideas that bring families together around the dinner table"
    vowels              = "Shocking statistics about childhood obesity rates and what the data reveals"
    snackingwell        = "Healthy snack swaps that taste just as good as your favorite junk food"
    childrennutrition   = "How to teach kids to read food labels and make smarter snack choices"
    parentingwithchrist = "Biblical wisdom for raising children with purpose and faith in today's world"
    otakulounge         = "Top anime series of 2025 that every fan needs to add to their watchlist"
}

$brands = $brandPrompts.Keys

foreach ($brand in $brands) {
    Write-Host "`n== $brand ==" -ForegroundColor Cyan
    try {
        $reqFile = [System.IO.Path]::GetTempFileName()
        @{ brand = $brand; platforms = @("facebook"); prompt = $brandPrompts[$brand] } | ConvertTo-Json | Set-Content $reqFile -Encoding UTF8
        $body = Get-Content $reqFile -Raw
        $r = Invoke-RestMethod -Uri "$BASE/orchestrate-post" -Method Post `
             -Headers @{ Authorization = "Bearer $TOKEN"; "Content-Type" = "application/json" } `
             -Body $body -TimeoutSec 180
        $fb = $r.pipeline.delivery.facebook
        $color = if ($fb.status -eq "delivered") { "Green" } else { "Yellow" }
        Write-Host "  status=$($r.status)  fb=$($fb.status)  postId=$($fb.result.id)" -ForegroundColor $color
        $results += [PSCustomObject]@{ brand=$brand; status=$r.status; fbStatus=$fb.status; postId=$fb.result.id; img=$r.imageUrl }
    } catch {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $results += [PSCustomObject]@{ brand=$brand; status="error"; fbStatus="error"; postId=$null; img=$null }
    }
}

Write-Host ""
Write-Host "=== FINAL SUMMARY ===" -ForegroundColor Yellow
$results | Format-Table brand, status, fbStatus, postId -AutoSize
