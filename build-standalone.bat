@echo off
REM Build script for creating standalone Sena executable
REM Requires: Python 3.10+, Node.js LTS, pyinstaller

echo.
echo ╔════════════════════════════════════════╗
echo ║     SENA STANDALONE BUILDER            ║
echo ║  Creating Distributable Executable     ║
echo ╚════════════════════════════════════════╝
echo.

REM Check for required tools
echo [1/4] Checking dependencies...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python not found
    exit /b 1
)
echo ✓ Python found

node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Node.js not found
    exit /b 1
)
echo ✓ Node.js found

echo [2/4] Installing build dependencies...
pip install -q -r requirements-dist.txt
if %errorLevel% neq 0 (
    echo ERROR: Failed to install build dependencies
    exit /b 1
)
echo ✓ Build dependencies installed

echo [3/4] Building React UI...
cd src\ui\behind-the-sena
call npm install --quiet
call npm run build
if %errorLevel% neq 0 (
    echo ERROR: Failed to build React UI
    cd ..\..\..\
    exit /b 1
)
echo ✓ React UI built
cd ..\..\..\

echo [4/4] Building executable...
pyinstaller --onefile --windowed --icon=assets/sena-logo.png launcher.js
if %errorLevel% neq 0 (
    echo ERROR: PyInstaller failed
    exit /b 1
)
echo ✓ Executable built

echo.
echo ╔════════════════════════════════════════╗
echo ║      BUILD COMPLETE!                   ║
echo ║                                        ║
echo ║  Output: dist\Sena.exe                 ║
echo ║  Size: Ready for distribution          ║
echo ║  Ready: Upload to GitHub Releases      ║
echo ╚════════════════════════════════════════╝
echo.

pause
