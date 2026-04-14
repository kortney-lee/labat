$BASE  = "https://wihy-shania-graphics-12913076533.us-central1.run.app"
$TOKEN = "wihy-admin-token-2026"

$brands = @(
    @{ id="wihy";                prompt="The hidden truth about ultra-processed food ingredients the industry doesn't want you to know" }
    @{ id="communitygroceries";  prompt="Simple weekly meal prep ideas that bring families together around the dinner table" }
    @{ id="vowels";              prompt="Shocking statistics about childhood obesity rates and what the data reveals" }
    @{ id="snackingwell";        prompt="Healthy snack swaps that taste just as good as your favorite junk food" }
    @{ id="childrennutrition";   prompt="How to teach kids to read food labels and make smarter snack choices" }
    @{ id="parentingwithchrist"; prompt="Biblical wisdom for raising children with purpose and faith in today's world" }
    # otakulounge excluded — do not post from test scripts
)

$results = @()

foreach ($b in $brands) {
    $brand  = $b.id
    $prompt = $b.prompt

    Write-Host "`n== $brand ==" -ForegroundColor Cyan
    Write-Host "   prompt: $($prompt.Substring(0, [Math]::Min(60, $prompt.Length)))..."

    # Write body to a temp file to avoid shell-escaping issues
    $tmpFile = [System.IO.Path]::Combine($env:TEMP, "shania_req_$brand.json")
    $json = [PSCustomObject]@{ brand=$brand; platforms=@("facebook"); prompt=$prompt } | ConvertTo-Json
    [System.IO.File]::WriteAllText($tmpFile, $json, [System.Text.Encoding]::UTF8)

    $response = curl.exe -s -X POST "$BASE/orchestrate-post" `
        -H "Authorization: Bearer $TOKEN" `
        -H "Content-Type: application/json" `
        --data-binary "@$tmpFile" `
        -w "`nHTTP_STATUS:%{http_code}" `
        --max-time 180

    # Split HTTP status from body (join first in case curl output is an array)
    $responseStr = $response -join "`n"
    $parts       = $responseStr -split "`nHTTP_STATUS:"
    $bodyText    = $parts[0].Trim()
    $httpStatus  = if ($parts.Count -gt 1) { $parts[1].Trim() } else { "???" }

    if ($httpStatus -eq "200") {
        try {
            $json    = $bodyText | ConvertFrom-Json
            $fbNode  = $json.pipeline.delivery.facebook
            $fbSt    = if ($fbNode) { $fbNode.status } else { "no-delivery-node" }
            $postId  = if ($fbNode.result.id) { $fbNode.result.id } else { "-" }
            $imgUrl  = if ($json.imageUrl) { $json.imageUrl.Substring(0, [Math]::Min(80,$json.imageUrl.Length)) } else { "-" }
            Write-Host "   status=$($json.status)  fb=$fbSt  postId=$postId" -ForegroundColor Green
            Write-Host "   img: $imgUrl"
            $results += [PSCustomObject]@{ brand=$brand; http=$httpStatus; status=$json.status; fbStatus=$fbSt; postId=$postId }
        } catch {
            Write-Host "   JSON parse error: $_" -ForegroundColor Red
            $results += [PSCustomObject]@{ brand=$brand; http=$httpStatus; status="parse-error"; fbStatus="-"; postId="-" }
        }
    } else {
        Write-Host "   HTTP $httpStatus  body: $($bodyText.Substring(0,[Math]::Min(200,$bodyText.Length)))" -ForegroundColor Red
        $results += [PSCustomObject]@{ brand=$brand; http=$httpStatus; status="error"; fbStatus="error"; postId="-" }
    }
}

Write-Host "`n`n=== FINAL SUMMARY ===" -ForegroundColor Yellow
$results | Format-Table brand, http, status, fbStatus, postId -AutoSize
