@echo off
chcp 65001 >nul
echo ========================================
echo   XLink SSH客户端 - 启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python,请先安装Python 3.10+
    pause
    exit /b 1
)

echo [检查] 正在检查依赖项...
python -c "import PyQt6, paramiko" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖项...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖项安装失败
        pause
        exit /b 1
    )
)

echo [启动] 正在启动XLink...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [错误] 程序运行出错
    pause
)
