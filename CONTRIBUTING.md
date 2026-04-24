# Contributing to XLink

Thank you for your interest in contributing to XLink! This document provides guidelines and instructions for contributing.

感谢您对XLink项目的贡献兴趣！本文档提供了贡献的指南和说明。

## Table of Contents / 目录

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting Pull Requests](#submitting-pull-requests)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

本项目受我们的[行为准则](CODE_OF_CONDUCT.md)约束。参与本项目即表示您期望遵守此准则。

---

## Getting Started / 入门指南

### Prerequisites / 前置要求

- Python 3.10 or higher
- Git
- Basic knowledge of PySide6 (Qt for Python)
- Familiarity with SSH protocol

### Development Setup / 开发环境设置

1. **Fork the repository / Fork仓库**
   
   Click the "Fork" button on GitHub to create your own copy.

2. **Clone your fork / 克隆你的Fork**

   ```bash
   git clone https://github.com/YOUR_USERNAME/XLink.git
   cd XLink
   ```

3. **Create a virtual environment / 创建虚拟环境**

   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

4. **Install dependencies / 安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application / 运行应用程序**

   ```bash
   python main.py
   ```

---

## Making Changes / 进行修改

1. **Create a new branch / 创建新分支**

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes / 进行代码修改**
   
   - Follow the coding standards below
   - Add comments where necessary
   - Test your changes thoroughly

3. **Commit your changes / 提交修改**

   ```bash
   git add .
   git commit -m "type: description"
   ```

---

## Submitting Pull Requests / 提交Pull Request

1. **Push your branch / 推送分支**

   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request / 创建Pull Request**
   
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template with:
     - Clear description of changes
     - Related issue numbers (if any)
     - Screenshots (for UI changes)
     - Testing steps

3. **Wait for review / 等待审核**
   
   - Maintainers will review your code
   - Address any feedback or requested changes
   - Once approved, your PR will be merged

---

## Coding Standards / 编码规范

### Python Style / Python风格

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (compatible with Black formatter)
- Use type hints where possible

### Naming Conventions / 命名规范

- **Classes**: PascalCase (e.g., `SFTPManager`)
- **Functions/Methods**: snake_case (e.g., `connect_to_server`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`)
- **Private members**: Leading underscore (e.g., `_internal_method`)

### Code Organization / 代码组织

```python
# Imports should be grouped and ordered
import standard_library
import third_party_library
import local_module

# Constants at the top
CONSTANT_VALUE = 100

# Class definition
class MyClass:
    """Class docstring."""
    
    def __init__(self):
        """Initialize."""
        pass
    
    def public_method(self):
        """Public method docstring."""
        pass
    
    def _private_method(self):
        """Private method docstring."""
        pass
```

### Comments / 注释

- Use docstrings for classes and methods
- Add inline comments for complex logic
- Write comments in English or Chinese (both acceptable)

```python
def connect_to_server(self, host: str, port: int) -> bool:
    """
    Connect to remote SSH server.
    
    Args:
        host: Server hostname or IP address
        port: Server port number
    
    Returns:
        True if connection successful, False otherwise
    """
    pass
```

---

## Commit Message Guidelines / 提交信息规范

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): description

[optional body]

[optional footer]
```

### Types / 类型

- `feat`: New feature (新功能)
- `fix`: Bug fix (修复Bug)
- `docs`: Documentation changes (文档更新)
- `style`: Code style changes (formatting, etc.) (代码格式调整)
- `refactor`: Code refactoring (代码重构)
- `perf`: Performance improvements (性能优化)
- `test`: Adding or updating tests (测试相关)
- `chore`: Maintenance tasks (维护任务)

### Examples / 示例

```bash
feat(sftp): add breadcrumb navigation to file manager
fix(terminal): resolve ANSI color rendering issue
docs(readme): update installation instructions
refactor(core): simplify async event loop management
perf(sftp): optimize directory listing cache
```

---

## Reporting Bugs / 报告Bug

Before creating bug reports, please check existing issues to avoid duplicates.

创建Bug报告前，请先检查是否已有相关Issue。

### Bug Report Template / Bug报告模板

**Title**: [Bug] Brief description of the issue

**Environment**:
- OS: Windows 11 / Ubuntu 22.04 / macOS 13
- Python version: 3.10.5
- XLink version: v1.0.0

**Steps to Reproduce**:
1. Go to '...'
2. Click on '...'
3. Scroll down to '...'
4. See error

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happens

**Screenshots**: If applicable

**Additional Context**: Log files, error messages, etc.

---

## Suggesting Features / 功能建议

**Title**: [Feature] Brief description of the feature

**Problem Statement**: What problem does this solve?

**Proposed Solution**: How should it work?

**Alternatives Considered**: Other solutions you've thought about

**Additional Context**: Mockups, examples, references

---

## Project Structure / 项目结构

```
XLink/
├── core/           # Core business logic
├── ui/             # User interface components
├── resources/      # Icons and assets
├── config/         # Configuration files (auto-generated)
└── tests/          # Test files
```

---

## Need Help? / 需要帮助?

- Check existing [Issues](https://github.com/YOUR_USERNAME/XLink/issues)
- Read the [README](README.md)
- Contact maintainers

---

Thank you for contributing to XLink! 🎉

感谢您为XLink项目做出贡献！
