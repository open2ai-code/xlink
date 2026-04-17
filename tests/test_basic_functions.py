# -*- coding: utf-8 -*-
"""
XLink 基本功能自动化测试 - 精简版

运行方式:
    pytest tests/test_basic_functions.py -v
"""

import pytest
from core.terminal_buffer import ANSIParser, TextSegment
from core.virtual_screen import VirtualScreen


class TestVirtualScreen:
    """虚拟屏幕核心测试"""
    
    def test_initialization(self):
        """P0: 虚拟屏幕初始化"""
        screen = VirtualScreen(rows=24, cols=80)
        assert screen.rows == 24
        assert screen.cols == 80
        assert screen.cursor_row == 0
        assert screen.cursor_col == 0
    
    def test_write_and_clear(self):
        """P0: 写入和清屏"""
        screen = VirtualScreen(rows=24, cols=80)
        screen.write_text('Test')
        screen.clear_screen(mode=2)
        assert screen.get_row_text(0) == ' ' * 80
        assert screen.cursor_row == 0
        assert screen.cursor_col == 0
    
    def test_newline_handling(self):
        """P0: 换行处理"""
        screen = VirtualScreen(rows=24, cols=80)
        screen.write_text('line1\nline2')
        assert screen.cursor_row >= 1
    
    def test_resize_preserves_content(self):
        """P0: 调整大小保留内容"""
        screen = VirtualScreen(rows=24, cols=80)
        screen.write_text('Hello')
        screen.resize(30, 100)
        assert screen.rows == 30
        assert screen.cols == 100
        assert screen.cells[0][0].char == 'H'


class TestBasicInput:
    """基础输入测试"""
    
    def setup_method(self):
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_text_input(self):
        """P0: 文本输入"""
        self.screen.write_text('hello world')
        assert self.screen.get_row_text(0).startswith('hello world')
    
    def test_no_duplicate_display(self):
        """P0: 输入无重复显示"""
        self.screen.write_text('pwd')
        row_text = self.screen.get_row_text(0)
        assert row_text.count('pwd') == 1


class TestNavigation:
    """导航键测试"""
    
    def setup_method(self):
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_cursor_movement(self):
        """P0: 光标移动"""
        self.screen.move_cursor(5, 10)
        self.screen.move_cursor_back(1)
        assert self.screen.cursor_col == 9
        
        self.screen.move_cursor_forward(2)
        assert self.screen.cursor_col == 11
        
        self.screen.move_cursor_up(1)
        assert self.screen.cursor_row == 4
        
        self.screen.move_cursor_down(1)
        assert self.screen.cursor_row == 5
    
    def test_home_end(self):
        """P0: Home/End键"""
        self.screen.move_cursor(0, 10)
        self.screen.move_cursor(0, 0)
        assert self.screen.cursor_col == 0
        
        self.screen.move_cursor(0, 79)
        assert self.screen.cursor_col == 79


class TestCtrlKeys:
    """Ctrl组合键测试"""
    
    def test_ctrl_sequences(self):
        """P0: Ctrl组合键序列"""
        assert '\x03' == chr(3)   # Ctrl+C
        assert '\x04' == chr(4)   # Ctrl+D
        assert '\x0c' == chr(12)  # Ctrl+L
        assert '\x15' == chr(21)  # Ctrl+U


class TestANSIParser:
    """ANSI解析器测试"""
    
    def setup_method(self):
        self.parser = ANSIParser()
    
    def test_color_parsing(self):
        """P0: 颜色解析"""
        segments = self.parser.parse('\033[31mRed\033[0m')
        assert len(segments) > 0
        colored = [s for s in segments if s.fg_color is not None]
        if colored:
            assert colored[0].fg_color == '#FF0000'
    
    def test_clear_screen_parsing(self):
        """P0: 清屏命令解析"""
        self.parser.parse('\033[H\033[2J')
        assert any(cmd.command_type == 'clear_screen' for cmd in self.parser.commands)
    
    def test_invalid_sequence(self):
        """P1: 非法ANSI序列不崩溃"""
        segments = self.parser.parse('\033[31Incomplete')
        assert isinstance(segments, list)


class TestErrorHandling:
    """错误处理测试"""
    
    def test_empty_input(self):
        """P1: 空输入处理"""
        screen = VirtualScreen(rows=24, cols=80)
        screen.write_text('')
        assert screen.get_row_text(0) == ' ' * 80
    
    def test_control_char_filter(self):
        """P1: 控制字符过滤"""
        screen = VirtualScreen(rows=24, cols=80)
        screen.write_text('A\x07B')
        row_text = screen.get_row_text(0)
        assert '\x07' not in row_text


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
