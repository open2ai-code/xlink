# XLink自绘终端架构 - 测试框架

## 📋 概述

本测试框架为XLink自绘终端架构提供全面的测试覆盖，包括：
- **自动化单元测试** (pytest)
- **手动测试检查清单**
- **测试覆盖率报告**
- **性能测试工具**

## 🗂️ 文件结构

```
tests/
├── __init__.py                      # 测试包初始化
├── conftest.py                      # pytest配置
├── test_native_terminal.py          # 自动化单元测试
├── test_checklist.py                # 手动测试检查清单
└── README.md                        # 本文档

根目录:
├── pytest.ini                       # pytest配置文件
├── run_tests.bat                    # Windows测试运行脚本
└── run_tests.sh                     # Linux/Mac测试运行脚本
```

## 🚀 快速开始

### Windows用户

```bash
# 双击运行测试脚本
run_tests.bat

# 或使用命令行
python -m pytest tests/ -v
```

### Linux/Mac用户

```bash
# 添加执行权限
chmod +x run_tests.sh

# 运行测试脚本
./run_tests.sh

# 或使用命令行
python3 -m pytest tests/ -v
```

## 📝 测试分类

### P0 - 核心功能 (必须通过)
- ANSI序列解析准确性
- 虚拟屏幕写入正确性
- 基础键盘输入
- SSH数据接收与显示
- 清屏命令功能

**运行P0测试:**
```bash
pytest tests/test_native_terminal.py -v -k "test_standard_8_colors or test_write_char"
```

### P1 - 重要功能
- NCURSES模式检测
- 提示符去重
- 光标闪烁与同步
- 256色支持
- 命令历史

**运行P1测试:**
```bash
pytest tests/test_native_terminal.py::TestNCURSESDetection -v
```

### P2 - 增强体验
- 多种光标样式
- Ctrl组合键
- F1-F12功能键
- 右键菜单
- 字体缩放

### P3 - 边界情况
- 极端大文本处理
- 网络异常恢复
- 长时间运行稳定性
- 性能优化验证

## 🧪 运行测试

### 运行所有单元测试

```bash
pytest tests/test_native_terminal.py -v
```

### 运行特定测试类

```bash
# ANSI解析器测试
pytest tests/test_native_terminal.py::TestANSIParser -v

# 虚拟屏幕测试
pytest tests/test_native_terminal.py::TestVirtualScreen -v

# 光标渲染器测试
pytest tests/test_native_terminal.py::TestCursorRenderer -v
```

### 运行特定测试方法

```bash
pytest tests/test_native_terminal.py::TestANSIParser::test_standard_8_colors -v
```

### 生成测试覆盖率报告

```bash
# 安装覆盖率插件
pip install pytest-cov

# 生成HTML报告
pytest tests/test_native_terminal.py --cov=core --cov=ui --cov-report=html

# 查看报告
# Windows: start htmlcov\index.html
# Linux: xdg-open htmlcov/index.html
# Mac: open htmlcov/index.html
```

### 手动测试检查清单

```bash
# 查看检查清单
python tests/test_checklist.py

# 输出到文件
python tests/test_checklist.py > MANUAL_TEST_REPORT.md
```

## 📊 测试覆盖模块

### 1. ANSI解析器 (core/terminal_buffer.py)
- ✅ 标准8色解析
- ✅ 256色解析
- ✅ 真彩色解析
- ✅ 样式属性 (加粗/下划线)
- ✅ 光标控制序列
- ✅ 清屏清行序列
- ✅ 特殊序列过滤 (OSC/DEC/字符集)
- ✅ 边界情况处理

### 2. 虚拟屏幕 (core/virtual_screen.py)
- ✅ 字符/文本写入
- ✅ 换行/回车/制表符
- ✅ 光标操作
- ✅ 清屏清行
- ✅ 滚动机制
- ✅ 屏幕调整
- ✅ 数据获取 (深拷贝)

### 3. 光标渲染器 (ui/cursor_renderer.py)
- ✅ 可见性切换
- ✅ 多种光标样式
- ✅ 无效输入处理

### 4. NCURSES检测 (native_terminal_widget.py)
- ✅ 高频刷新检测
- ✅ 模式切换
- ✅ 提示符退出

### 5. 提示符去重 (native_terminal_widget.py)
- ✅ 重复提示符检测
- ✅ 截断位置计算

## 🔧 测试工具建议

### 自动化测试
```bash
# 使用pytest运行测试
pytest tests/ -v --tb=short

# 使用标记过滤
pytest tests/ -v -m p0  # 仅P0测试
pytest tests/ -v -m "not slow"  # 排除慢速测试
```

### 手动测试
连接真实Linux服务器验证以下场景：

```bash
# 基础命令
ls -la
echo -e '\033[31mRed\033[0m'
clear

# 颜色测试
dircolors
ls --color=always

# NCURSES程序
top
htop
vim /etc/hosts
nano /etc/hosts

# 交互测试
python3
mysql -u root -p

# 压力测试
cat /var/log/syslog
yes | head -n 10000

# 提示符测试
export PS1='[\u@\h \W]\$ '
su -
```

### 性能测试
```bash
# 监控内存占用
# Linux: ps aux | grep xlink
# Windows: 任务管理器

# 监控CPU占用
# Linux: top -p $(pgrep -f xlink)
# Windows: 任务管理器

# 长时间运行测试
# 连续运行24小时，观察稳定性
```

## 📈 测试报告模板

测试完成后，使用以下模板生成报告：

```markdown
# XLink自绘终端测试报告

## 基本信息
- 测试日期: YYYY-MM-DD
- 测试人员: XXX
- 测试版本: 2.0.0

## 测试结果汇总
- P0核心功能: X/Y (Z%)
- P1重要功能: X/Y (Z%)
- P2增强体验: X/Y (Z%)
- P3边界情况: X/Y (Z%)
- 回归测试: X/Y (Z%)

## 通过率
- 总体通过率: X/Y (Z%)

## 发现的问题
1. [问题描述]
   - 严重程度: P0/P1/P2/P3
   - 复现步骤: ...
   - 预期结果: ...
   - 实际结果: ...

## 测试结论
- [ ] 通过,可以发布
- [ ] 有条件通过,需修复以下P0/P1问题
- [ ] 不通过,存在严重问题

## 备注
...
```

## 🐛 已知问题回归测试

以下历史问题需要重点验证：

| 问题 | 状态 | 验证方法 |
|------|------|----------|
| 提示符重复显示 | ✅ 已修复 | 多次回车检查提示符 |
| DEC私有序列过滤 | ✅ 已修复 | 运行top命令 |
| 清屏命令失效 | ✅ 已修复 | 执行clear命令 |
| 坐标映射错误 | ✅ 已修复 | vim编辑检查光标位置 |
| Cell深拷贝问题 | ✅ 已修复 | 渲染后修改检查原数据 |
| PyQt6兼容性 | ✅ 已修复 | 运行所有UI测试 |

## 📚 相关文档

- [XLink项目README](../README.md)
- [自绘终端架构文档](../ARCHITECTURE.md)
- [ANSI序列规范](https://en.wikipedia.org/wiki/ANSI_escape_code)
- [PyQt6文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [pytest文档](https://docs.pytest.org/)

## 🤝 贡献指南

### 添加新测试

1. 在 `test_native_terminal.py` 中添加测试类或方法
2. 使用描述性的测试函数名 (以 `test_` 开头)
3. 添加适当的标记 (`@pytest.mark.p0` 等)
4. 确保测试独立,不依赖其他测试

### 示例

```python
@pytest.mark.p0
def test_new_feature(self):
    """测试新功能"""
    # Arrange
    parser = ANSIParser()
    
    # Act
    segments = parser.parse('\033[31mTest\033[0m')
    
    # Assert
    assert len(segments) == 1
    assert segments[0].fg_color == '#FF0000'
```

## 📞 支持

如有问题，请：
1. 查看本文档
2. 检查pytest输出日志
3. 查看项目issues
4. 联系开发团队

---

**最后更新**: 2026-04-15
**维护者**: XLink Team
