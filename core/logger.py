# -*- coding: utf-8 -*-
"""
日志系统模块
提供统一的日志记录功能,支持控制台和文件输出
"""

import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


class Logger:
    """日志管理器"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_logger(cls, name='XLink', log_level=logging.INFO):
        """
        获取日志记录器
        
        Args:
            name: 日志记录器名称
            log_level: 日志级别
            
        Returns:
            logging.Logger实例
        """
        if cls._logger is None:
            cls._init_logger(name, log_level)
        return cls._logger
    
    @classmethod
    def _init_logger(cls, name='XLink', log_level=logging.INFO):
        """
        初始化日志系统
        
        Args:
            name: 日志记录器名称
            log_level: 日志级别
        """
        cls._logger = logging.getLogger(name)
        cls._logger.setLevel(log_level)
        
        # 日志格式: [时间] [级别] [模块] 消息
        log_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 1. 控制台输出 (DEBUG及以上)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(log_format)
        cls._logger.addHandler(console_handler)
        
        # 2. 文件输出 (所有级别,自动轮转)
        try:
            # 创建logs目录
            base_dir = Path(__file__).parent.parent
            log_dir = base_dir / 'logs'
            log_dir.mkdir(exist_ok=True)
            
            log_file = log_dir / 'xlink.log'
            
            # 使用RotatingFileHandler,单文件最大10MB,保留5个备份
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(log_format)
            cls._logger.addHandler(file_handler)
            
            cls._logger.info("日志系统初始化完成")
        except Exception as e:
            print(f"初始化文件日志失败: {e}")
    
    @classmethod
    def setup_exception_hook(cls):
        """
        设置全局异常钩子
        捕获所有未处理的异常并记录到日志
        """
        def exception_handler(exctype, value, traceback):
            """异常处理函数"""
            if cls._logger is None:
                cls.get_logger()
            
            cls._logger.critical(
                "未捕获的异常",
                exc_info=(exctype, value, traceback)
            )
            
            # 显示错误对话框 (如果在GUI环境中)
            try:
                from PySide6.QtWidgets import QApplication, QMessageBox
                from PySide6.QtCore import Qt
                
                app = QApplication.instance()
                if app:
                    error_msg = f"{exctype.__name__}: {value}"
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Critical)
                    msg_box.setWindowTitle("XLink - 发生错误")
                    msg_box.setText("程序遇到了一个未处理的错误")
                    msg_box.setInformativeText(error_msg)
                    msg_box.setDetailedText(
                        f"异常类型: {exctype.__name__}\n"
                        f"异常信息: {value}\n\n"
                        f"详细日志已保存到 logs/xlink.log\n"
                        f"请将日志文件发送给开发者以帮助解决问题。"
                    )
                    msg_box.setStandardButtons(
                        QMessageBox.StandardButton.Ok | 
                        QMessageBox.StandardButton.Close
                    )
                    msg_box.setDefaultButton(QMessageBox.StandardButton.Close)
                    msg_box.exec()
            except Exception:
                pass
            
            # 调用原始异常处理
            sys.__excepthook__(exctype, value, traceback)
        
        # 设置异常钩子
        sys.excepthook = exception_handler
        
        # 同时设置线程异常钩子
        import threading
        old_init = threading.Thread.__init__
        
        def new_init(self, *args, **kwargs):
            old_init(self, *args, **kwargs)
            old_run = self.run
            
            def run_with_except_hook(*args, **kwargs):
                try:
                    old_run(*args, **kwargs)
                except Exception:
                    exception_handler(*sys.exc_info())
            
            self.run = run_with_except_hook
        
        threading.Thread.__init__ = new_init


def get_logger(name=None):
    """
    便捷函数: 获取日志记录器
    
    Args:
        name: 模块名称
        
    Returns:
        logging.Logger实例
    """
    logger = Logger.get_logger()
    if name:
        return logging.getLogger(f"XLink.{name}")
    return logger
