@echo off
:: ═══════════════════════════════════════════════════════════════
:: VidhanAI — Start both servers (backend + frontend)
::
:: Usage: double-click this file, or run from the project root:
::        start.bat
::
:: Backend  → http://localhost:5000  (Flask)
:: Frontend → http://localhost:3000  (Vite proxies /api to :5000)
:: ═══════════════════════════════════════════════════════════════

title VidhanAI Dev Launcher

echo.
echo  ==============================================
echo   VidhanAI  ^|  Starting dev servers...
echo  ==============================================
echo.

:: ── Resolve paths ──────────────────────────────────────────────
set ROOT=%~dp0
set BACKEND=%ROOT%backend
set FRONTEND=%ROOT%frontend

:: ── Check python ───────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] python not found in PATH.
    echo  Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: ── Check node ─────────────────────────────────────────────────
where node >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] node not found in PATH.
    echo  Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

:: ── Install frontend deps if node_modules is missing ───────────
if not exist "%FRONTEND%\node_modules" (
    echo  [INFO] node_modules missing -- running npm install...
    pushd "%FRONTEND%"
    call npm install
    popd
)

:: ── Launch backend in a new window ─────────────────────────────
echo  [1/2] Starting Flask backend on http://localhost:5000
start "VidhanAI Backend :5000" cmd /k "cd /d "%BACKEND%" && python app.py"

:: Small pause so Flask can bind the port before Vite tries to proxy
timeout /t 3 /nobreak >nul

:: ── Launch frontend in a new window ────────────────────────────
echo  [2/2] Starting Vite frontend on http://localhost:3000
start "VidhanAI Frontend :3000" cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo.
echo  ==============================================
echo   Both servers starting in separate windows.
echo   Backend  : http://localhost:5000
echo   Frontend : http://localhost:3000
echo   Press any key to close this launcher.
echo  ==============================================
echo.
pause >nul
