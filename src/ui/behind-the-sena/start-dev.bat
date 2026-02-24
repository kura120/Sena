@echo off
cd /d "%~dp0"

REM Create a wrapper script to run both services
set "wrapper=%temp%\sena-dev-wrapper.bat"
(
    echo @echo off
    echo cd /d "%~dp0\..\..\.."
    echo call .venv\Scripts\activate.bat
    echo echo Starting API server...
    echo start /B python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 --reload
    echo timeout /t 2 /nobreak
    echo echo Starting Vite dev server...
    echo cd src\ui\behind-the-sena
    echo npm run dev
) > "%wrapper%"

REM Start the wrapper in a single window
start "Sena Dev Environment" cmd /k "%wrapper%"

REM Wait for Vite to be ready
timeout /t 5 /nobreak >nul
:wait_vite
netstat -an | findstr ":5173" | findstr "LISTENING" >nul
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_vite
)

REM Open browser
start http://localhost:5173

REM Clean up and exit this launcher window
del "%wrapper%" 2>nul
exit


