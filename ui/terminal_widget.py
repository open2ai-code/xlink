# -*- coding: utf-8 -*-
"""
终端控件模块
兼容层: 默认使用自绘控件(NativeTerminalWidget)
旧的QPlainTextEdit实现已备份到 terminal_widget_legacy.py
"""

# 导入新的自绘控件
from ui.native_terminal_widget import NativeTerminalWidget

# 兼容层: TerminalWidget现在指向NativeTerminalWidget
# 这样不需要修改其他文件(tab_manager.py等)
TerminalWidget = NativeTerminalWidget

# 如果需要回退到旧实现,可以修改为:
# from ui.terminal_widget_legacy import TerminalWidgetLegacy as TerminalWidget
