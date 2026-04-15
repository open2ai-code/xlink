#!/bin/bash
# XLink自绘终端测试运行脚本
# Linux/Mac版本

echo "========================================"
echo "XLink 自绘终端架构 - 测试运行器"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3,请先安装Python 3.10+"
    exit 1
fi

# 检查pytest是否安装
if ! python3 -m pytest --version &> /dev/null; then
    echo "[提示] 正在安装pytest..."
    pip3 install pytest
fi

echo ""
echo "请选择测试类型:"
echo ""
echo "1. 运行所有单元测试 (快速)"
echo "2. 运行P0核心功能测试"
echo "3. 运行P1重要功能测试"
echo "4. 运行完整测试套件 (包含手动检查清单)"
echo "5. 生成测试覆盖率报告"
echo "6. 查看手动测试检查清单"
echo "7. 运行特定测试文件"
echo ""
read -p "请输入选项 (1-7): " choice

case $choice in
    1)
        echo ""
        echo "========================================"
        echo "运行所有单元测试..."
        echo "========================================"
        python3 -m pytest tests/test_native_terminal.py -v --tb=short
        ;;
    2)
        echo ""
        echo "========================================"
        echo "运行P0核心功能测试..."
        echo "========================================"
        python3 -m pytest tests/test_native_terminal.py -v -k "test_standard_8_colors or test_write_char or test_clear_screen" --tb=short
        ;;
    3)
        echo ""
        echo "========================================"
        echo "运行P1重要功能测试..."
        echo "========================================"
        python3 -m pytest tests/test_native_terminal.py::TestNCURSESDetection -v --tb=short
        ;;
    4)
        echo ""
        echo "========================================"
        echo "运行完整测试套件..."
        echo "========================================"
        python3 -m pytest tests/ -v --tb=short
        echo ""
        echo "手动测试检查清单已生成: tests/MANUAL_TEST_REPORT.md"
        ;;
    5)
        echo ""
        echo "========================================"
        echo "检查并安装pytest-cov..."
        echo "========================================"
        if ! python3 -m pytest --cov --version &> /dev/null; then
            pip3 install pytest-cov
        fi
        
        echo ""
        echo "生成测试覆盖率报告..."
        python3 -m pytest tests/test_native_terminal.py --cov=core --cov=ui --cov-report=html --cov-report=term
        echo ""
        echo "覆盖率报告已生成: htmlcov/index.html"
        
        # 尝试在浏览器中打开
        if command -v xdg-open &> /dev/null; then
            xdg-open htmlcov/index.html
        elif command -v open &> /dev/null; then
            open htmlcov/index.html
        fi
        ;;
    6)
        echo ""
        echo "========================================"
        echo "手动测试检查清单"
        echo "========================================"
        python3 tests/test_checklist.py
        ;;
    7)
        echo ""
        read -p "请输入测试文件路径 (例如: tests/test_native_terminal.py): " testfile
        python3 -m pytest $testfile -v --tb=short
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "测试完成!"
echo "========================================"
