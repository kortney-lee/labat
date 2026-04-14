$BASE = "https://wihy-shania-graphics-12913076533.us-central1.run.app"
$TOKEN = "wihy-admin-token-2026"
$body = '{"brand":"wihy","platforms":["facebook"]}'

try {
    $r = Invoke-RestMethod -Uri "$BASE/orchestrate-post" -Method Post `
         -Headers @{ Authorization="Bearer $TOKEN"; "Content-Type"="application/json" } `
         -Body $body -TimeoutSec 180
    $r | ConvertTo-Json -Depth 6
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    $stream = $_.Exception.Response.GetResponseStream()
    $reader = [System.IO.StreamReader]::new($stream)
    $errorBody = $reader.ReadToEnd()
    Write-Host "Body: $errorBody" -ForegroundColor Red
}
