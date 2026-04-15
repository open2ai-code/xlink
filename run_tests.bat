@echo off
REM XLink自绘终端测试运行脚本
REM Windows批处理文件

echo ========================================
echo XLink 自绘终端架构 - 测试运行器
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python,请先安装Python 3.10+
    pause
    exit /b 1
)

REM 检查pytest是否安装
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装pytest...
    pip install pytest
)

echo.
echo 请选择测试类型:
echo.
echo 1. 运行所有单元测试 (快速)
echo 2. 运行P0核心功能测试
echo 3. 运行P1重要功能测试
echo 4. 运行完整测试套件 (包含手动检查清单)
echo 5. 生成测试覆盖率报告
echo 6. 查看手动测试检查清单
echo 7. 运行特定测试文件
echo.
set /p choice=请输入选项 (1-7): 

if "%choice%"=="1" goto run_all_unit
if "%choice%"=="2" goto run_p0
if "%choice%"=="3" goto run_p1
if "%choice%"=="4" goto run_full
if "%choice%"=="5" goto run_coverage
if "%choice%"=="6" goto show_checklist
if "%choice%"=="7" goto run_specific
goto end

:run_all_unit
echo.
echo ========================================
echo 运行所有单元测试...
echo ========================================
python -m pytest tests/test_native_terminal.py -v --tb=short
goto end

:run_p0
echo.
echo ========================================
echo 运行P0核心功能测试...
echo ========================================
python -m pytest tests/test_native_terminal.py -v -k "test_standard_8_colors or test_write_char or test_clear_screen" --tb=short
goto end

:run_p1
echo.
echo ========================================
echo 运行P1重要功能测试...
echo ========================================
python -m pytest tests/test_native_terminal.py::TestNCURSESDetection -v --tb=short
goto end

:run_full
echo.
echo ========================================
echo 运行完整测试套件...
echo ========================================
python -m pytest tests/ -v --tb=short
echo.
echo 手动测试检查清单已生成: tests\MANUAL_TEST_REPORT.md
goto end

:run_coverage
echo.
echo ========================================
echo 检查并安装pytest-cov...
echo ========================================
python -m pytest --cov --version >nul 2>&1
if errorlevel 1 (
    pip install pytest-cov
)

echo.
echo 生成测试覆盖率报告...
python -m pytest tests/test_native_terminal.py --cov=core --cov=ui --cov-report=html --cov-report=term
echo.
echo 覆盖率报告已生成: htmlcov\index.html
start htmlcov\index.html
goto end

:show_checklist
echo.
echo ========================================
echo 手动测试检查清单
echo ========================================
python tests/test_checklist.py
goto end

:run_specific
echo.
set /p testfile=请输入测试文件路径 (例如: tests/test_native_terminal.py): 
python -m pytest %testfile% -v --tb=short
goto end

:end
echo.
echo ========================================
echo 测试完成!
echo ========================================
pause
