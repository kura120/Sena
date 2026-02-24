@echo off
setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════╗
echo ║       SENA BUILD ^& SETUP WIZARD        ║
echo ║   Self-Evolving AI Assistant           ║
echo ╚════════════════════════════════════════╝
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    timeout /t 1 /nobreak
    
    if exist "%temp%\sena_elevation.tmp" (
        del "%temp%\sena_elevation.tmp"
    ) else (
        echo. > "%temp%\sena_elevation.tmp"
        powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs" >nul 2>&1
        exit /b 0
    )
)
del "%temp%\sena_elevation.tmp" 2>nul

echo [1/5] Validating environment...

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.10+ from https://www.python.org
    pause
    exit /b 1
)
echo ✓ Python found

node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)
echo ✓ Node.js found

echo [2/5] Setting up Python environment...
if not exist .venv (
    python -m venv .venv >nul 2>&1
)
call .venv\Scripts\activate.bat >nul 2>&1
pip install -q -r requirements.txt
echo ✓ Python dependencies installed

echo [3/5] Installing Node dependencies...
cd /d src\ui\behind-the-sena
call npm install --quiet
if %errorLevel% neq 0 (
    echo ERROR: Failed to install Node dependencies
    cd /d ..\..\..\
    pause
    exit /b 1
)
echo ✓ Node dependencies installed

echo [4/5] Building React UI...
call npm run build
if %errorLevel% neq 0 (
    echo ERROR: Failed to build React UI
    cd /d ..\..\..\
    pause
    exit /b 1
)
echo ✓ React UI built successfully

cd /d ..\..\..\

echo [5/5] Creating desktop launcher...

setlocal enabledelayedexpansion
set DESKTOP=%USERPROFILE%\Desktop
set LAUNCHER=%cd%\launcher.js
set ICON=%cd%\assets\sena-logo.png

REM Create VBS launcher
set LAUNCHER_VBS=%TEMP%\sena-launcher.vbs
(
    echo Set objShell = CreateObject("WScript.Shell"^)
    echo objShell.Run "node ""%LAUNCHER%""", 1, False
) > "!LAUNCHER_VBS!"

REM Create shortcut
set SHORTCUT=!DESKTOP!\Sena Debug Dashboard.lnk
powershell -Command "[Windows.ApplicationModel.DesktopAppXActivator,Windows.ApplicationModel.DesktopAppXActivator,ContentType=WindowsRuntime] > $null; $TargetFile='!LAUNCHER_VBS!'; $ShortcutFile='!SHORTCUT!'; $WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut($ShortcutFile); $Shortcut.TargetPath = $TargetFile; $Shortcut.IconLocation = '!ICON!'; $Shortcut.Save()" >nul 2>&1

if exist "!SHORTCUT!" (
    echo ✓ Desktop shortcut created
) else (
    echo ! Shortcut creation skipped (non-critical)
)

echo.
echo ╔════════════════════════════════════════╗
echo ║          BUILD COMPLETE!               ║
echo ║                                        ║
echo ║  📌 Desktop shortcut created          ║
echo ║  🚀 Launch: Click desktop icon or     ║
echo ║     run: node launcher.js             ║
echo ║  💻 Dev mode: run start-dev.bat       ║
echo ╚════════════════════════════════════════╝
echo.

pause
exit /b 0
