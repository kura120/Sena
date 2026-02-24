@echo off
REM Sena Development Launcher
REM Starts both API and UI for development

echo.
echo ╔════════════════════════════════════════╗
echo ║       SENA DEVELOPMENT LAUNCHER        ║
echo ╚════════════════════════════════════════╝
echo.

REM Activate Python venv
call .venv\Scripts\activate.bat

REM Build React first
echo [1/3] Building React UI...
cd src\ui\behind-the-sena
call npm run build
cd ..\..\..\

REM Start API server
echo [2/3] Starting Python API server...
start /B python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload

REM Wait a moment for server to start
timeout /t 2 /nobreak

REM Open browser
echo [3/3] Opening browser...
start http://127.0.0.1:8000

echo.
echo ✨ Sena is running! Press any key to stop all services.
pause

REM Kill all Python processes spawned by this script
taskkill /F /IM python.exe /T >nul 2>&1

echo Shutting down Sena...
exit /b 0
