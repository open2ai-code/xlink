# -*- coding: utf-8 -*-
"""
终端控件模块
使用完全自主渲染的NativeTerminalWidget，不依赖QPlainTextEdit
"""

# 导入自绘终端控件
from ui.native_terminal_widget import NativeTerminalWidget

# TerminalWidget指向NativeTerminalWidget
# 这样不需要修改其他文件(tab_manager.py等)
TerminalWidget = NativeTerminalWidget
