@echo off
chcp 65001 >nul
echo ====================================
echo XLink SSH Client - Build Script
echo ====================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [2/4] Generating application icon...
python resources\generate_icon.py
if errorlevel 1 (
    echo [WARNING] Failed to generate icon, using default
)

echo [3/4] Building executable with PyInstaller...
pyinstaller --clean build.spec
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Build completed successfully!
echo ====================================
echo Output: dist\XLink.exe
echo ====================================
echo.
pause
