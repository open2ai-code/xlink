# -*- coding: utf-8 -*-
"""
XLink - SSH客户端
主入口程序

轻量、稳定、高颜值的SSH远程连接工具
技术栈: Python 3.10+ | PySide6 | AsyncSSH
"""

import sys
import os
import asyncio

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from qasync import QEventLoop
from ui.main_window import MainWindow
from core.logger import Logger, get_logger

logger = get_logger("Main")


def main():
    """主函数"""
    # 初始化日志系统
    Logger.get_logger()
    Logger.setup_exception_hook()
    
    logger.info("XLink SSH Client starting...")
    
    # 性能优化: 启用高DPI缩放和共享OpenGL上下文
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 创建qasync事件循环 - 将asyncio集成到Qt事件循环中
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 设置应用信息
    app.setApplicationName("XLink")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("XLink Team")
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    logger.info("Creating main window...")
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    logger.info("XLink SSH Client started successfully")
    
    # 使用qasync事件循环运行应用
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
