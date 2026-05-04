@echo off
echo ==============================================
echo       Starting VidhanAi Application
echo ==============================================

echo [1/2] Starting Backend Server...
start "VidhanAi Backend" cmd /k "cd backend && call ..\venv\Scripts\activate.bat && python app.py"

echo [2/2] Starting Frontend Server...
start "VidhanAi Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ==============================================
echo  Both servers are starting in separate windows!
echo  Backend API: http://localhost:5000
echo  Frontend UI: http://localhost:5173 (usually)
echo ==============================================
