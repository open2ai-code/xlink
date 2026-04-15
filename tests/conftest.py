# -*- coding: utf-8 -*-
"""
pytest配置文件
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "p0: P0核心功能测试标记"
    )
    config.addinivalue_line(
        "markers", "p1: P1重要功能测试标记"
    )
    config.addinivalue_line(
        "markers", "p2: P2增强体验测试标记"
    )
    config.addinivalue_line(
        "markers", "p3: P3边界情况测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记"
    )
