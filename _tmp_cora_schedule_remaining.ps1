$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$project = 'wihy-ai'
$location = 'us-central1'
$graphicsService = 'https://wihy-shania-graphics-12913076533.us-central1.run.app'
$cgService = 'https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app'
$queue = 'cg-cora-story-cadence'
$brand = 'communitygroceries'
$designId = 'DAHILiPNmNU'

function Normalize-Hashtags {
  param([string[]]$InputTags)
  $required = @('CommunityGroceries', 'KansasCity')
  $all = @()

  foreach ($t in $InputTags) {
    if (-not $t) { continue }
    $clean = ($t -replace '^#+', '').Trim()
    if (-not $clean) { continue }
    if (-not ($all | Where-Object { $_.ToLower() -eq $clean.ToLower() })) {
      $all += $clean
    }
  }

  foreach ($r in $required) {
    if (-not ($all | Where-Object { $_.ToLower() -eq $r.ToLower() })) {
      if ($r -eq 'CommunityGroceries') {
        $all = @($r) + $all
      } else {
        $all += $r
      }
    }
  }

  $all = $all | Select-Object -First 9
  return @($all | ForEach-Object { '#'+$_ })
}

$admin = (gcloud secrets versions access latest --secret internal-admin-token --project $project).Trim()

# Find the just-published launch post and anchor schedule times from it.
$feed = Invoke-RestMethod -Uri "$cgService/api/labat/page/feed?limit=30" -Headers @{ 'X-Admin-Token' = $admin } -Method GET
$launchPost = @($feed.data | Where-Object { ($_.message -as [string]) -match 'meet cora|launch video|new best friend for family meal planning' } | Sort-Object {[DateTime]$_.created_time} -Descending | Select-Object -First 1)
if (-not $launchPost) {
  throw 'Could not find launch post to anchor cadence schedule.'
}
$baseUtc = [DateTime]::Parse($launchPost.created_time).ToUniversalTime()

# Canva export for first 9 pages.
$clientId = (gcloud secrets versions access latest --secret canva-client-id --project $project).Trim()
$clientSecret = (gcloud secrets versions access latest --secret canva-client-secret --project $project).Trim()
$refresh = (gcloud secrets versions access latest --secret canva-refresh-token --project $project).Trim()
$tokenBody = "grant_type=refresh_token&refresh_token=$([uri]::EscapeDataString($refresh))&client_id=$([uri]::EscapeDataString($clientId))&client_secret=$([uri]::EscapeDataString($clientSecret))"
$token = Invoke-RestMethod -Uri 'https://api.canva.com/rest/v1/oauth/token' -Method POST -ContentType 'application/x-www-form-urlencoded' -Body $tokenBody -TimeoutSec 60
$access = $token.access_token

# Persist the rotated refresh token so future calls do not fail with revoked lineage.
$newRefresh = [string]$token.refresh_token
if ($newRefresh) {
  $tmpRefresh = Join-Path $env:TEMP ("canva-refresh-" + [Guid]::NewGuid().ToString('N') + ".txt")
  Set-Content -Path $tmpRefresh -Value $newRefresh -NoNewline
  & gcloud secrets versions add canva-refresh-token --project $project --data-file=$tmpRefresh | Out-Null
  Remove-Item $tmpRefresh -Force
}

$createExportBody = @{ design_id = $designId; format = @{ type = 'png' } } | ConvertTo-Json -Depth 8
$createExport = Invoke-RestMethod -Uri 'https://api.canva.com/rest/v1/exports' -Method POST -Headers @{ Authorization = "Bearer $access"; 'Content-Type' = 'application/json' } -Body $createExportBody -TimeoutSec 60
$jobId = [string]$createExport.job.id
$status = [string]$createExport.job.status
$job = $createExport.job
for ($i = 0; $i -lt 400 -and $status -eq 'in_progress'; $i++) {
  $poll = Invoke-RestMethod -Uri ("https://api.canva.com/rest/v1/exports/{0}" -f $jobId) -Method GET -Headers @{ Authorization = "Bearer $access" } -TimeoutSec 60
  $status = [string]$poll.job.status
  $job = $poll.job
}
if ($status -ne 'success') {
  throw "Canva export did not finish: job=$jobId status=$status"
}
$allUrls = @($job.urls)
if ($allUrls.Count -lt 9) {
  throw "Expected at least 9 pages from Canva export, got $($allUrls.Count)"
}

$storySteps = @(
  @{ step = 2; header = 'Meet Cora'; sub = 'A simpler way to plan, shop, and waste less.'; detail = 'Introduce Cora and explain how she helps families stay organized.' },
  @{ step = 3; header = 'Plan Before You Shop'; sub = 'Know what you need before you buy.'; detail = 'Focus on planning first so shopping is less stressful.' },
  @{ step = 4; header = 'Turn Meals Into Lists'; sub = 'Build grocery lists from the meals you want.'; detail = 'Show how chosen meals become a practical shopping list.' },
  @{ step = 5; header = 'Shop With Purpose'; sub = 'Everything you need, nothing you don’t.'; detail = 'Highlight intentional shopping and budget control.' },
  @{ step = 6; header = 'Use What You Buy'; sub = 'Track ingredients and reduce waste.'; detail = 'Emphasize using ingredients fully and reducing waste.' },
  @{ step = 7; header = 'Plan For Real Life'; sub = 'Meals that fit your family, budget, and routine.'; detail = 'Show flexibility for busy family schedules and real budgets.' },
  @{ step = 8; header = 'Cook With Confidence'; sub = 'Step-by-step guidance for every meal.'; detail = 'Confidence through simple, guided cooking steps.' },
  @{ step = 9; header = 'Waste Less. Save More.'; sub = 'Bring intention back to grocery shopping.'; detail = 'Final benefit: less waste, lower cost, more peace at home.' }
)

$scheduled = @()
foreach ($step in $storySteps) {
  $userPrompt = @"
You are writing post $($step.step) of 9 in a launch storytelling flow for Community Groceries.

Flow context:
launch video -> introduce Cora -> plan -> list -> shop -> reduce waste -> real life -> cook -> final benefit.

Current slide header: $($step.header)
Current slide subheader: $($step.sub)
Post intent: $($step.detail)

Write a REAL social post, not a numbered series label.
Requirements:
- 1-2 short paragraphs, warm and human
- include one vivid real-life moment or mini-story
- include one practical takeaway
- end with a simple engagement question or CTA
- under 140 words
- no mention of "series X/9"
- no generic hype language
- hashtags should be relevant to family meals, meal planning, budget shopping, and reducing waste
"@

  $planBody = @{ brand = $brand; prompt = $userPrompt } | ConvertTo-Json -Depth 6
  $planResp = Invoke-RestMethod -Uri "$graphicsService/plan-post" -Method POST -ContentType 'application/json' -Body $planBody -TimeoutSec 120
  $tags = Normalize-Hashtags -InputTags @($planResp.hashtags)
  $caption = ([string]$planResp.caption).Trim() + "`n`n" + ($tags -join ' ')

  $pageIndex = $step.step - 1
  $assetPageUrl = [string]$allUrls[$pageIndex]
  $tmp = Join-Path $env:TEMP ("cg_cora_story_{0}_{1}.png" -f $step.step, ([Guid]::NewGuid().ToString('N').Substring(0, 8)))
  Invoke-WebRequest -Uri $assetPageUrl -OutFile $tmp -UseBasicParsing -TimeoutSec 180
  $bytes = [System.IO.File]::ReadAllBytes($tmp)
  Remove-Item $tmp -Force
  $b64 = [Convert]::ToBase64String($bytes)

  $uploadBody = @{
    fileName = ("cg_cora_story_{0}.png" -f $step.step)
    contentType = 'image/png'
    dataBase64 = $b64
    brand = $brand
    folder = 'approved'
    caption = $caption
    topic = ("cora-story-step-{0}" -f $step.step)
    metadata = @{
      source = 'canva-static-design'
      designId = $designId
      step = ("{0}" -f $step.step)
      header = $step.header
      campaign = 'cg-cora-story-9'
    }
  } | ConvertTo-Json -Depth 12

  $upload = Invoke-RestMethod -Uri "$graphicsService/asset-library/upload" -Method POST -ContentType 'application/json' -Body $uploadBody -TimeoutSec 180
  $assetUrl = [string]$upload.publicUrl

  $runAt = $baseUtc.AddHours(5 * ($step.step - 1))
  $runAtIso = $runAt.ToString('yyyy-MM-ddTHH:mm:ssZ')

  foreach ($platform in @('facebook', 'instagram')) {
    $payload = @{ assetUrl = $assetUrl; platform = $platform; caption = $caption; brand = $brand } | ConvertTo-Json -Depth 8 -Compress
    $taskId = "cora-s$($step.step)-$platform-" + (Get-Date -Format 'yyyyMMddHHmmssfff')

    $payloadFile = Join-Path $env:TEMP ("cora-task-" + [Guid]::NewGuid().ToString('N') + ".json")
    [System.IO.File]::WriteAllText($payloadFile, $payload, [System.Text.UTF8Encoding]::new($false))

    $cmd = "gcloud tasks create-http-task $taskId --queue=$queue --project=$project --location=$location --url=$graphicsService/deliver --method=POST --header=Content-Type:application/json --body-file=$payloadFile --schedule-time=$runAtIso"
    $prevErr = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $taskOut = & cmd /c $cmd 2>&1
    $exit = $LASTEXITCODE
    $ErrorActionPreference = $prevErr

    Remove-Item $payloadFile -Force

    if ($exit -ne 0) {
      throw "Failed creating task ${taskId}: $($taskOut -join ' ')"
    }

    $scheduled += [pscustomobject]@{
      step = $step.step
      header = $step.header
      platform = $platform
      scheduleTimeUtc = $runAtIso
      taskId = $taskId
      captionPreview = ($caption.Substring(0, [Math]::Min(140, $caption.Length)))
      taskOutput = ($taskOut -join ' ')
    }
  }
}

[pscustomobject]@{
  status = 'ok'
  queue = $queue
  baseLaunchPostId = $launchPost.id
  baseLaunchTimeUtc = $baseUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
  exportJobId = $jobId
  scheduledCount = $scheduled.Count
  scheduled = $scheduled
} | ConvertTo-Json -Depth 10
