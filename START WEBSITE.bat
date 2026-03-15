@echo off
title Polymarket AI Dashboard
echo ============================================
echo   Starting Polymarket AI Dashboard...
echo ============================================
echo.

cd /d "%~dp0frontend"

:: Open browser after a short delay
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:3000"

:: Start the Next.js dev server
npm run dev
