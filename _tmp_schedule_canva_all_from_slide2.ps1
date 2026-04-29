$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$project = 'wihy-ai'
$location = 'us-central1'
$graphicsService = 'https://wihy-shania-graphics-12913076533.us-central1.run.app'
$queue = 'cg-cora-story-cadence'
$brand = 'communitygroceries'
$designId = 'DAHILiPNmNU'

function Ensure-Queue {
  & gcloud tasks queues describe $queue --project $project --location $location 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    & gcloud tasks queues create $queue --project $project --location $location --max-dispatches-per-second 1 --max-concurrent-dispatches 1 | Out-Null
  }
}

function Normalize-Hashtags {
  param([string[]]$InputTags)

  $required = @('CommunityGroceries', 'MealPlanning')
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

  $all = $all | Select-Object -First 10
  return @($all | ForEach-Object { '#'+$_ })
}

# 1) Clean queue so we only keep the new schedule.
Ensure-Queue
$existingTasks = @(gcloud tasks list --project $project --location $location --queue $queue --format='value(name)')
foreach ($taskName in $existingTasks) {
  $taskId = ($taskName -split '/')[-1]
  $prevErr = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & gcloud tasks delete $taskId --project $project --location $location --queue $queue --quiet 2>$null | Out-Null
  $ErrorActionPreference = $prevErr
}

# 2) Remove legacy non-Canva and stale campaign assets.
$legacyVideoObjects = @(
  'gs://cg-web-assets/videos/cora/CGHeader_fb.mp4',
  'gs://cg-web-assets/videos/cora/CGHeader_mobile.mp4'
)

$removedLegacyVideos = @()
foreach ($obj in $legacyVideoObjects) {
  $prevErr = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & gcloud storage rm $obj 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $removedLegacyVideos += $obj }
  $ErrorActionPreference = $prevErr
}

$libraryObjects = @(gcloud storage ls 'gs://wihy-shania-graphics/asset-library/communitygroceries/**' 2>$null)
$legacyLibraryObjects = @(
  $libraryObjects | Where-Object { $_ -match 'cg_cora|cora-story|cora-launch|cg-teaser|teaser' }
)

$removedLegacyLibrary = @()
foreach ($obj in $legacyLibraryObjects) {
  $prevErr = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & gcloud storage rm $obj 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { $removedLegacyLibrary += $obj }
  $ErrorActionPreference = $prevErr
}

# 3) Refresh Canva token and persist rotated refresh token.
$clientId = (gcloud secrets versions access latest --secret canva-client-id --project $project).Trim()
$clientSecret = (gcloud secrets versions access latest --secret canva-client-secret --project $project).Trim()
$refresh = (gcloud secrets versions access latest --secret canva-refresh-token --project $project).Trim()
$tokenBody = "grant_type=refresh_token&refresh_token=$([uri]::EscapeDataString($refresh))&client_id=$([uri]::EscapeDataString($clientId))&client_secret=$([uri]::EscapeDataString($clientSecret))"
$token = Invoke-RestMethod -Uri 'https://api.canva.com/rest/v1/oauth/token' -Method POST -ContentType 'application/x-www-form-urlencoded' -Body $tokenBody -TimeoutSec 90
$access = $token.access_token

$newRefresh = [string]$token.refresh_token
if ($newRefresh) {
  $tmpRefresh = Join-Path $env:TEMP ("canva-refresh-" + [Guid]::NewGuid().ToString('N') + ".txt")
  Set-Content -Path $tmpRefresh -Value $newRefresh -NoNewline
  & gcloud secrets versions add canva-refresh-token --project $project --data-file=$tmpRefresh | Out-Null
  Remove-Item $tmpRefresh -Force
}

# 4) Export full design pages from Canva as PNG URLs.
$createExportBody = @{ design_id = $designId; format = @{ type = 'png' } } | ConvertTo-Json -Depth 8
$createExport = Invoke-RestMethod -Uri 'https://api.canva.com/rest/v1/exports' -Method POST -Headers @{ Authorization = "Bearer $access"; 'Content-Type' = 'application/json' } -Body $createExportBody -TimeoutSec 90
$jobId = [string]$createExport.job.id
$status = [string]$createExport.job.status
$job = $createExport.job

for ($i = 0; $i -lt 600 -and $status -eq 'in_progress'; $i++) {
  $poll = Invoke-RestMethod -Uri ("https://api.canva.com/rest/v1/exports/{0}" -f $jobId) -Method GET -Headers @{ Authorization = "Bearer $access" } -TimeoutSec 90
  $status = [string]$poll.job.status
  $job = $poll.job
}

if ($status -ne 'success') {
  throw "Canva export did not finish: job=$jobId status=$status"
}

$allUrls = @($job.urls)
$totalSlides = $allUrls.Count
if ($totalSlides -lt 2) {
  throw "Expected at least 2 slides from Canva export, got $totalSlides"
}

# Start with slide 2 in 5 hours, then one step every 5 hours.
$startUtc = [DateTime]::UtcNow.AddHours(5)
$scheduled = @()

for ($slide = 2; $slide -le $totalSlides; $slide++) {
  $slideUrl = [string]$allUrls[$slide - 1]

  $prompt = @"
Write a warm social caption for Community Groceries slide $slide of $totalSlides.
Focus: family meal planning, budget shopping, reducing waste, practical next step.
Requirements:
- under 120 words
- 1 practical takeaway
- end with a simple question or CTA
- include hashtags relevant to family meals and meal planning
"@

  $planBody = @{ brand = $brand; prompt = $prompt } | ConvertTo-Json -Depth 6
  $captionBase = ''
  $tags = @('#CommunityGroceries', '#MealPlanning', '#FamilyMeals', '#BudgetMeals', '#FoodAccess')

  try {
    $planResp = Invoke-RestMethod -Uri "$graphicsService/plan-post" -Method POST -ContentType 'application/json' -Body $planBody -TimeoutSec 120
    $captionBase = ([string]$planResp.caption).Trim()
    $tags = Normalize-Hashtags -InputTags @($planResp.hashtags)
  } catch {
    $captionBase = "Slide $slide is part of our full Community Groceries story. We are helping families plan meals, shop smarter, and waste less every week." 
  }

  $caption = @(
    $captionBase,
    '',
    'Download the app:',
    'iOS: https://apps.apple.com/us/app/community-groceries/id6760566970',
    'Android: https://play.google.com/store/apps/details?id=app.communitygroceries.mobile',
    '',
    'Website: https://communitygroceries.com',
    '',
    ($tags -join ' ')
  ) -join "`n"

  $tmp = Join-Path $env:TEMP ("canva_slide_{0}_{1}.png" -f $slide, ([Guid]::NewGuid().ToString('N').Substring(0, 8)))
  Invoke-WebRequest -Uri $slideUrl -OutFile $tmp -UseBasicParsing -TimeoutSec 240
  $bytes = [System.IO.File]::ReadAllBytes($tmp)
  Remove-Item $tmp -Force
  $b64 = [Convert]::ToBase64String($bytes)

  $uploadBody = @{
    fileName = ("canva_slide_{0}.png" -f $slide)
    contentType = 'image/png'
    dataBase64 = $b64
    brand = $brand
    folder = 'approved'
    caption = $caption
    topic = ("canva-slide-{0}" -f $slide)
    metadata = @{
      source = 'canva-direct-design'
      designId = $designId
      slide = ("{0}" -f $slide)
      campaign = 'cg-cora-canva-all'
    }
  } | ConvertTo-Json -Depth 12

  $upload = Invoke-RestMethod -Uri "$graphicsService/asset-library/upload" -Method POST -ContentType 'application/json' -Body $uploadBody -TimeoutSec 240
  $assetUrl = [string]$upload.publicUrl

  $runAt = $startUtc.AddHours(5 * ($slide - 2))
  $runAtIso = $runAt.ToString('yyyy-MM-ddTHH:mm:ssZ')

  foreach ($platform in @('facebook', 'instagram')) {
    $payload = @{ assetUrl = $assetUrl; platform = $platform; caption = $caption; brand = $brand } | ConvertTo-Json -Depth 8 -Compress
    $taskId = "cora-slide$slide-$platform-" + (Get-Date -Format 'yyyyMMddHHmmssfff')

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
      slide = $slide
      platform = $platform
      scheduleTimeUtc = $runAtIso
      taskId = $taskId
      assetUrl = $assetUrl
    }
  }
}

[pscustomobject]@{
  status = 'ok'
  designId = $designId
  totalSlides = $totalSlides
  scheduledSlidesFrom = 2
  scheduledSlidesTo = $totalSlides
  cadenceHours = 5
  startUtc = $startUtc.ToString('yyyy-MM-ddTHH:mm:ssZ')
  tasksCreated = $scheduled.Count
  queue = $queue
  removedLegacyVideos = $removedLegacyVideos
  removedLegacyLibraryCount = $removedLegacyLibrary.Count
  exportJobId = $jobId
  sampleSchedule = @($scheduled | Select-Object -First 8)
} | ConvertTo-Json -Depth 10
