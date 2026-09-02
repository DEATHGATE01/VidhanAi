# ═══════════════════════════════════════════════════════════════
# VidhanAI — Dev launcher (PowerShell)
#
# Usage (from the project root, one-time setup if needed):
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\start.ps1
#
# Backend  → http://localhost:5000  (Flask / app.py)
# Frontend → http://localhost:5173  (Vite dev server)
#   /api/* requests are proxied by Vite → Flask automatically.
# ═══════════════════════════════════════════════════════════════

param (
    [switch]$NoBrowser   # pass -NoBrowser to skip auto-opening the browser
)

$ErrorActionPreference = "Stop"
$Root     = $PSScriptRoot
$Backend  = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend_new"

# ── Colour helpers ──────────────────────────────────────────────
function Print-Header {
    Write-Host ""
    Write-Host "  ================================================" -ForegroundColor DarkGray
    Write-Host "   ⚖️  VidhanAI  |  Dev Server Launcher" -ForegroundColor Cyan
    Write-Host "  ================================================" -ForegroundColor DarkGray
    Write-Host ""
}

function Print-Ok($msg)   { Write-Host "  ✅ $msg" -ForegroundColor Green  }
function Print-Info($msg) { Write-Host "  ℹ  $msg" -ForegroundColor Cyan   }
function Print-Warn($msg) { Write-Host "  ⚠  $msg" -ForegroundColor Yellow }
function Print-Err($msg)  { Write-Host "  ❌ $msg" -ForegroundColor Red    }

# ── Preflight checks ────────────────────────────────────────────
function Assert-Command($cmd, $installHint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Print-Err "$cmd not found in PATH.  $installHint"
        exit 1
    }
}

Print-Header
Print-Info "Checking prerequisites..."

Assert-Command "python" "Install Python 3.10+ from https://python.org and add to PATH."
Assert-Command "node"   "Install Node.js 18+ from https://nodejs.org"
Assert-Command "npm"    "npm should come with Node.js — reinstall Node."

$pyVer  = (python --version 2>&1) -replace "Python ", ""
$nodeVer = (node   --version 2>&1)
Print-Ok "Python $pyVer"
Print-Ok "Node   $nodeVer"

# ── Auto-install frontend dependencies ──────────────────────────
$nodeModules = Join-Path $Frontend "node_modules"
if (-not (Test-Path $nodeModules)) {
    Print-Warn "node_modules not found — running npm install..."
    Push-Location $Frontend
    npm install
    Pop-Location
}

# ── Port availability check ─────────────────────────────────────
function Test-Port($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    return $null -ne $conn
}

if (Test-Port 5000) {
    Print-Warn "Port 5000 is already in use. Flask may already be running, or another process is on :5000."
}
if (Test-Port 5173) {
    Print-Warn "Port 5173 is already in use. Vite may already be running."
}

# ── Launch Flask backend ─────────────────────────────────────────
# Runs on the locally fine-tuned Llama-3.2-3B via Ollama
# (VIDHANAI_USE_OLLAMA=1). Groq stays in the chain as a fallback when Ollama
# isn't running; to force fine-tuned-only, unset GROQ_API_KEY too.
Print-Info "Starting Flask backend on http://localhost:5000 (Ollama fine-tuned model)..."

$env:VIDHANAI_USE_OLLAMA = "1"
$backendJob = Start-Process `
    -FilePath "python" `
    -ArgumentList "app.py" `
    -WorkingDirectory $Backend `
    -PassThru `
    -WindowStyle Normal
Remove-Item Env:VIDHANAI_USE_OLLAMA -ErrorAction SilentlyContinue

Print-Ok "Flask started  (PID $($backendJob.Id))"

# Give Flask a moment to bind before Vite starts proxying
Start-Sleep -Seconds 2

# ── Launch Vite frontend ─────────────────────────────────────────
Print-Info "Starting Vite frontend on http://localhost:5173..."

$frontendJob = Start-Process `
    -FilePath "npm" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $Frontend `
    -PassThru `
    -WindowStyle Normal `

Print-Ok "Vite started   (PID $($frontendJob.Id))"

# ── Open browser ────────────────────────────────────────────────
if (-not $NoBrowser) {
    Start-Sleep -Seconds 3   # wait for Vite to be ready
    Print-Info "Opening http://localhost:5173 in browser..."
    Start-Process "http://localhost:5173"
}

# ── Summary ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ================================================" -ForegroundColor DarkGray
Write-Host "   Backend  : http://localhost:5000" -ForegroundColor White
Write-Host "   Frontend : http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "   Press Ctrl+C to stop this script." -ForegroundColor DarkGray
Write-Host "   (The two server windows will stay open; close them manually.)" -ForegroundColor DarkGray
Write-Host "  ================================================" -ForegroundColor DarkGray
Write-Host ""

# ── Keep script alive so Ctrl+C can be caught ───────────────────
try {
    while ($true) {
        # Check if either process has died unexpectedly
        if ($backendJob.HasExited) {
            Print-Warn "Flask backend exited (code $($backendJob.ExitCode))."
        }
        if ($frontendJob.HasExited) {
            Print-Warn "Vite frontend exited (code $($frontendJob.ExitCode))."
        }
        Start-Sleep -Seconds 10
    }
} finally {
    # On Ctrl+C: attempt to kill child processes
    Write-Host ""
    Print-Info "Shutting down servers..."
    if (-not $backendJob.HasExited)  { Stop-Process -Id $backendJob.Id  -Force -ErrorAction SilentlyContinue }
    if (-not $frontendJob.HasExited) { Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue }
    Print-Ok "Servers stopped. Goodbye."
}
