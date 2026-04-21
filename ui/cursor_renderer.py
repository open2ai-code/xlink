# -*- coding: utf-8 -*-
"""
光标渲染器模块
支持多种光标样式: 块状、竖线、下划线
"""

from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt


class CursorRenderer:
    """光标渲染器 - 支持多种光标样式"""
    
    def __init__(self):
        self.cursor_shape = 'block'  # 'block' | 'bar' | 'underline'
        self.blink_interval = 500  # 闪烁间隔(ms)
        self.cursor_visible = True  # 光标是否可见(用于闪烁)
        
    def draw(self, painter: QPainter, row: int, col: int, 
             char_width: int, char_height: int, cell_char: str = ' ',
             cell_fg: str = '#D4D4D4', cell_bg: str = '#1E1E1E'):
        """
        绘制光标
        
        Args:
            painter: QPainter对象
            row: 光标行号
            col: 光标列号
            char_width: 字符宽度(像素)
            char_height: 字符高度(像素)
            cell_char: 光标位置的字符
            cell_fg: 字符前景色
            cell_bg: 字符背景色
        """
        if not self.cursor_visible:
            return
        
        x = col * char_width
        y = row * char_height
        
        if self.cursor_shape == 'block':
            # 块状光标: 反色显示当前字符
            self._draw_block_cursor(painter, x, y, char_width, char_height, 
                                   cell_char, cell_fg, cell_bg)
            
        elif self.cursor_shape == 'bar':
            # 竖线光标: 在字符左侧画一条竖线
            self._draw_bar_cursor(painter, x, y, char_height)
            
        elif self.cursor_shape == 'underline':
            # 下划线光标: 在字符底部画下划线
            self._draw_underline_cursor(painter, x, y, char_width, char_height)
    
    def _draw_block_cursor(self, painter, x, y, width, height, 
                          cell_char, cell_fg, cell_bg):
        """绘制块状光标 - 使用高亮背景"""
        # 保存当前状态
        painter.save()
        
        # 绘制高亮背景(光标色块)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.fillRect(x, y, width, height, QColor('#D4D4D4'))
        
        painter.restore()
        
        # 在光标背景上绘制字符(使用反色)
        painter.save()
        # 使用深色绘制字符,确保在高亮背景上可见
        painter.setPen(QColor('#1E1E1E'))
        painter.drawText(x, y, width, height, 
                        Qt.AlignmentFlag.AlignCenter, cell_char)
        painter.restore()
    
    def _draw_bar_cursor(self, painter, x, y, height):
        """绘制竖线光标"""
        painter.save()
        painter.setPen(QColor('#D4D4D4'))
        painter.setBrush(QColor('#D4D4D4'))
        # 在字符左侧画2像素宽的竖线
        painter.drawRect(x, y, 2, height)
        painter.restore()
    
    def _draw_underline_cursor(self, painter, x, y, width, height):
        """绘制下划线光标"""
        painter.save()
        painter.setPen(QColor('#D4D4D4'))
        painter.setBrush(QColor('#D4D4D4'))
        # 在字符底部画2像素高的下划线
        painter.drawRect(x, y + height - 2, width, 2)
        painter.restore()
    
    def toggle_visibility(self):
        """切换光标可见性(用于闪烁)"""
        self.cursor_visible = not self.cursor_visible
    
    def set_shape(self, shape: str):
        """
        设置光标形状
        
        Args:
            shape: 'block' | 'bar' | 'underline'
        """
        if shape in ('block', 'bar', 'underline'):
            self.cursor_shape = shape
