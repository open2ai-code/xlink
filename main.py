"""
XLink - SSH客户端
主入口程序

轻量、稳定、高颜值的SSH远程连接工具
技术栈: Python 3.10+ | PyQt6 | paramiko
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
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
    # 注意: PyQt6中这些属性已经默认启用,不需要手动设置
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    # QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
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
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
