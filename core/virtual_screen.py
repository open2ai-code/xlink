# -*- coding: utf-8 -*-
"""
虚拟屏幕缓冲区模块
实现完整的终端屏幕仿真,支持光标定位、清屏、清行等操作
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set


@dataclass
class Cell:
    """屏幕单元格"""
    char: str = ' '
    fg_color: str = '#D4D4D4'  # 默认前景色
    bg_color: str = '#1E1E1E'  # 默认背景色
    bold: bool = False
    underline: bool = False
    
    def reset(self):
        """重置单元格"""
        self.char = ' '
        self.fg_color = '#D4D4D4'
        self.bg_color = '#1E1E1E'
        self.bold = False
        self.underline = False


class VirtualScreen:
    """
    虚拟屏幕缓冲区
    维护终端的二维屏幕状态,支持NCURSES全屏刷新
    """
    
    def __init__(self, rows: int = 24, cols: int = 80):
        """
        初始化虚拟屏幕
        
        Args:
            rows: 屏幕行数(默认24)
            cols: 屏幕列数(默认80)
        """
        self.rows = rows
        self.cols = cols
        self.cells = [[Cell() for _ in range(cols)] for _ in range(rows)]
        self.cursor_row = 0
        self.cursor_col = 0
        self.modified_rows: Set[int] = set()  # 追踪修改的行,用于增量渲染
        
        # 滚动区域(默认整个屏幕)
        self.scroll_top = 0
        self.scroll_bottom = rows - 1
        
        # 调试计数
        self._write_count = 0
        self._render_count = 0
    
    def move_cursor(self, row: int, col: int):
        """
        移动光标到指定位置
        
        Args:
            row: 目标行号(0-based)
            col: 目标列号(0-based)
        """
        # 边界检查
        self.cursor_row = max(0, min(row, self.rows - 1))
        self.cursor_col = max(0, min(col, self.cols - 1))
    
    def move_cursor_up(self, n: int = 1):
        """光标上移"""
        self.cursor_row = max(0, self.cursor_row - n)
    
    def move_cursor_down(self, n: int = 1):
        """光标下移"""
        self.cursor_row = min(self.rows - 1, self.cursor_row + n)
    
    def move_cursor_forward(self, n: int = 1):
        """光标右移"""
        self.cursor_col = min(self.cols - 1, self.cursor_col + n)
    
    def move_cursor_back(self, n: int = 1):
        """光标左移"""
        self.cursor_col = max(0, self.cursor_col - n)
    
    def write_char(self, char: str, attrs: Optional[dict] = None):
        """
        在当前光标位置写入字符
        
        Args:
            char: 要写入的字符
            attrs: 字符属性 {'fg': '#FF0000', 'bg': '#000000', 'bold': True, 'underline': False}
        """
        if attrs is None:
            attrs = {}
        
        # 边界检查: 如果光标超出屏幕,先滚动
        if self.cursor_row >= self.rows:
            # 滚动屏幕: 移除第一行,所有行上移
            self.cells.pop(0)
            # 添加新的空行
            new_row = [Cell(' ', '#D4D4D4', '#1E1E1E', False, False) for _ in range(self.cols)]
            self.cells.append(new_row)
            # 光标回到最后一行
            self.cursor_row = self.rows - 1
        
        if self.cursor_col >= self.cols:
            return
        
        cell = self.cells[self.cursor_row][self.cursor_col]
        cell.char = char
        cell.fg_color = attrs.get('fg', '#D4D4D4')
        cell.bg_color = attrs.get('bg', '#1E1E1E')
        cell.bold = attrs.get('bold', False)
        cell.underline = attrs.get('underline', False)
        
        # 标记此行已修改
        self.modified_rows.add(self.cursor_row)
        
        # 光标右移
        self.cursor_col += 1
        if self.cursor_col >= self.cols:
            self.cursor_col = 0
            self.cursor_row += 1
            # 如果超出滚动区域底部,滚动屏幕
            if self.cursor_row >= self.rows:
                self.cells.pop(0)
                new_row = [Cell(' ', '#D4D4D4', '#1E1E1E', False, False) for _ in range(self.cols)]
                self.cells.append(new_row)
                self.cursor_row = self.rows - 1
        
        self._write_count += 1
    
    def write_text(self, text: str, attrs: Optional[dict] = None):
        """
        写入文本字符串
        
        Args:
            text: 要写入的文本
            attrs: 字符属性
        """
        for char in text:
            if char == '\n':
                # 换行
                self.cursor_col = 0
                self.cursor_row += 1
                # 允许光标超出屏幕,由渲染层处理滚动
            elif char == '\r':
                # 回车
                self.cursor_col = 0
            elif char == '\x08':  # Backspace退格
                # 光标左移一格,但不删除字符(删除由服务器发送的空格处理)
                self.move_cursor_back(1)
            elif ord(char) < 32 and char not in ('\t',):  # 过滤控制字符,保留制表符
                # 忽略其他控制字符(如\x07响铃等)
                continue
            else:
                self.write_char(char, attrs)
    
    def clear_screen(self, mode: int = 2):
        """
        清屏
        
        Args:
            mode: 清屏模式
                0: 从光标到屏幕底部
                1: 从屏幕顶部到光标
                2: 整个屏幕(默认)
        """
        if mode == 2:
            # 清整个屏幕
            print(f"[VirtualScreen] 清屏前,第0行第1个字符: {repr(self.cells[0][0].char)}")
            for row in range(self.rows):
                for col in range(self.cols):
                    self.cells[row][col].reset()
            print(f"[VirtualScreen] 清屏后,第0行第1个字符: {repr(self.cells[0][0].char)}")
            self.modified_rows = set(range(self.rows))
            self.cursor_row = 0
            self.cursor_col = 0
        elif mode == 0:
            # 从光标到屏幕底部
            # 先清除光标所在行的右侧
            for col in range(self.cursor_col, self.cols):
                self.cells[self.cursor_row][col].reset()
            self.modified_rows.add(self.cursor_row)
            
            # 再清除下面的所有行
            for row in range(self.cursor_row + 1, self.rows):
                for col in range(self.cols):
                    self.cells[row][col].reset()
                self.modified_rows.add(row)
        elif mode == 1:
            # 从屏幕顶部到光标
            # 先清除上面的所有行
            for row in range(0, self.cursor_row):
                for col in range(self.cols):
                    self.cells[row][col].reset()
                self.modified_rows.add(row)
            
            # 再清除光标所在行的左侧
            for col in range(0, self.cursor_col + 1):
                self.cells[self.cursor_row][col].reset()
            self.modified_rows.add(self.cursor_row)
    
    def clear_line(self, mode: int = 0):
        """
        清行
        
        Args:
            mode: 清行模式
                0: 从光标到行尾(默认)
                1: 从行首到光标
                2: 整行
        """
        if mode == 0:
            # 从光标到行尾
            for col in range(self.cursor_col, self.cols):
                self.cells[self.cursor_row][col].reset()
        elif mode == 1:
            # 从行首到光标
            for col in range(0, self.cursor_col + 1):
                self.cells[self.cursor_row][col].reset()
        elif mode == 2:
            # 整行
            for col in range(self.cols):
                self.cells[self.cursor_row][col].reset()
        
        self.modified_rows.add(self.cursor_row)
    
    def insert_line(self, n: int = 1):
        """在光标位置插入n行(下面的行下移)"""
        for _ in range(n):
            # 滚动区域底部的行被删除
            # 所有行下移一行
            for row in range(self.scroll_bottom, self.cursor_row, -1):
                self.cells[row] = self.cells[row - 1][:]
                self.modified_rows.add(row)
            
            # 光标所在行清空
            for col in range(self.cols):
                self.cells[self.cursor_row][col].reset()
            self.modified_rows.add(self.cursor_row)
    
    def delete_line(self, n: int = 1):
        """删除光标位置的n行(下面的行上移)"""
        for _ in range(n):
            # 所有行上移一行
            for row in range(self.cursor_row, self.scroll_bottom):
                self.cells[row] = self.cells[row + 1][:]
                self.modified_rows.add(row)
            
            # 滚动区域底部的新行清空
            for col in range(self.cols):
                self.cells[self.scroll_bottom][col].reset()
            self.modified_rows.add(self.scroll_bottom)
    
    def _scroll_up(self):
        """向上滚动一行(在滚动区域内)"""
        # 滚动区域顶部的一行被删除
        # 所有行上移一行
        for row in range(self.scroll_top, self.scroll_bottom):
            self.cells[row] = self.cells[row + 1][:]
            self.modified_rows.add(row)
        
        # 滚动区域底部的新行清空
        for col in range(self.cols):
            self.cells[self.scroll_bottom][col].reset()
        self.modified_rows.add(self.scroll_bottom)
    
    def set_scroll_region(self, top: int, bottom: int):
        """
        设置滚动区域
        
        Args:
            top: 滚动区域顶部行号(0-based)
            bottom: 滚动区域底部行号(0-based)
        """
        self.scroll_top = max(0, min(top, self.rows - 1))
        self.scroll_bottom = max(self.scroll_top, min(bottom, self.rows - 1))
    
    def get_modified_rows_data(self) -> List[Tuple[int, List[Cell]]]:
        """
        获取修改过的行数据,用于渲染
        
        Returns:
            [(行号, [Cell, Cell, ...]), ...]
            注意: 返回Cell对象的深拷贝,避免后续修改影响渲染
        """
        result = []
        for row_idx in sorted(self.modified_rows):
            # 创建Cell对象的深拷贝
            copied_cells = [Cell(cell.char, cell.fg_color, cell.bg_color, cell.bold, cell.underline) 
                          for cell in self.cells[row_idx]]
            result.append((row_idx, copied_cells))
        
        self.modified_rows.clear()
        self._render_count += 1
        return result
    
    def get_row_text(self, row: int) -> str:
        """获取指定行的纯文本"""
        if 0 <= row < self.rows:
            return ''.join(cell.char for cell in self.cells[row])
        return ''
    
    def resize(self, rows: int, cols: int):
        """
        调整屏幕大小
        
        Args:
            rows: 新行数
            cols: 新列数
        """
        # 保留现有内容
        old_cells = self.cells
        old_rows = self.rows
        old_cols = self.cols
        
        self.rows = rows
        self.cols = cols
        self.cells = [[Cell() for _ in range(cols)] for _ in range(rows)]
        
        # 复制旧数据
        for r in range(min(rows, old_rows)):
            for c in range(min(cols, old_cols)):
                self.cells[r][c] = old_cells[r][c]
        
        # 标记所有行为已修改
        self.modified_rows = set(range(rows))
        
        # 调整光标位置
        self.cursor_row = min(self.cursor_row, rows - 1)
        self.cursor_col = min(self.cursor_col, cols - 1)
        
        # 重置滚动区域
        self.scroll_top = 0
        self.scroll_bottom = rows - 1
    
    def get_debug_info(self) -> dict:
        """获取调试信息"""
        return {
            'rows': self.rows,
            'cols': self.cols,
            'cursor': (self.cursor_row, self.cursor_col),
            'modified_rows_count': len(self.modified_rows),
            'write_count': self._write_count,
            'render_count': self._render_count
        }
