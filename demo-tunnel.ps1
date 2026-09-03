# VidhanAI - Demo tunnel launcher (cloudflared)
# Runs the whole local stack reachable from the internet while Ollama + n8n
# stay on this laptop. Safe for public exposure: the backend starts with
# debug OFF (the Werkzeug interactive debugger is an RCE if exposed); bill
# summaries still use the local fine-tuned model (VIDHANAI_USE_OLLAMA=1).
# Tunnel = Cloudflare quick tunnel: no account, clean visitor page, random URL.

$ErrorActionPreference = 'Stop'
$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py    = 'C:\Python313\python.exe'
$Back  = Join-Path $Root 'backend'
$Front = Join-Path $Root 'frontend_new'
$Cf    = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
$Log   = Join-Path $env:TEMP 'vidhanai-cloudflared.log'

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}
function Ok-Url($u) {
    try { return (Invoke-WebRequest -UseBasicParsing $u -TimeoutSec 2).StatusCode -eq 200 }
    catch { return $false }
}

Write-Host 'VidhanAI demo tunnel' -ForegroundColor Cyan

# 1. Backend (:5000) - debug OFF for public exposure
if (Test-Port 5000) { Write-Host 'backend already on :5000 - skipping' }
else {
    $env:FLASK_ENV = 'production'          # kills the Werkzeug debugger
    $env:VIDHANAI_USE_OLLAMA = '1'         # summaries from local fine-tuned Llama
    Start-Process -FilePath $Py -ArgumentList 'app.py' -WorkingDirectory $Back -WindowStyle Minimized
    Write-Host 'backend starting (debug off, Ollama on)...'
}

# 2. Frontend (:5173)
if (Test-Port 5173) { Write-Host 'frontend already on :5173 - skipping' }
else {
    Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' -WorkingDirectory $Front -WindowStyle Minimized
    Write-Host 'frontend starting...'
}

# 3. Wait for both services
Write-Host 'waiting for services' -NoNewline
$b = $f = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    $b = Ok-Url 'http://127.0.0.1:5000/api/health'
    $f = Ok-Url 'http://127.0.0.1:5173/'
    if ($b -and $f) { Write-Host ' ready.'; break }
    Write-Host '.' -NoNewline
}
Write-Host " backend=$b frontend=$f"
if (-not ($b -and $f)) { Write-Warning 'Services not ready in time - see the two windows above.' }

# 4. Tunnel: cloudflared quick tunnel -> Vite (Vite proxies /api -> Flask)
if (Test-Path $Log) { Remove-Item $Log -Force -ErrorAction SilentlyContinue }
$p = Start-Process -FilePath $Cf -ArgumentList 'tunnel', '--url', 'http://127.0.0.1:5173', '--no-autoupdate' `
    -WindowStyle Hidden -RedirectStandardOutput $Log -RedirectStandardError "$Log.err" -PassThru
Write-Host "cloudflared pid $($p.Id) - waiting for public URL..."

$url = $null
$logSrc = @($Log, "$Log.err")   # cloudflared writes its log to stderr
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    $m = Select-String -Path $logSrc -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($m) { $url = $m.Matches[0].Value; break }
}

if ($url) {
    Write-Host ''
    Write-Host "PUBLIC URL: $url" -ForegroundColor Green
    Write-Host 'Open it from any device to demo the app.'
} else {
    Write-Warning 'Could not extract tunnel URL - tail of log:'
    Get-Content $logSrc -Tail 15 -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host 'Keep this laptop ON and awake. Ollama (:11434) and n8n must stay running.' -ForegroundColor Yellow
Write-Host 'Stop the tunnel by closing the hidden cloudflared process (cloudflared.exe).'
