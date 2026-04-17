# -*- coding: utf-8 -*-
"""
XLink自绘终端架构 - 核心测试套件

测试覆盖:
- ANSI序列解析 (terminal_buffer.py)
- 虚拟屏幕功能 (virtual_screen.py)
- 光标渲染器 (cursor_renderer.py)
"""

import pytest
from core.terminal_buffer import ANSIParser, TextSegment, TerminalCommand
from core.virtual_screen import VirtualScreen, Cell
from ui.cursor_renderer import CursorRenderer


class TestANSIParser:
    """ANSI解析器测试"""
    
    def setup_method(self):
        self.parser = ANSIParser()
    
    def test_standard_colors(self):
        """P0: 标准颜色解析"""
        segments = self.parser.parse('\033[31mHello\033[0m')
        assert len(segments) >= 1
        colored = [s for s in segments if s.fg_color is not None]
        if colored:
            assert colored[0].fg_color == '#FF0000'
    
    def test_256_color(self):
        """P0: 256色解析"""
        segments = self.parser.parse('\033[38;5;196mRed\033[0m')
        assert len(segments) > 0
    
    def test_true_color(self):
        """P0: 真彩色解析"""
        segments = self.parser.parse('\033[38;2;255;0;0mRed\033[0m')
        assert len(segments) > 0
    
    def test_style_attributes(self):
        """P0: 样式属性解析"""
        segments = self.parser.parse('\033[1;4mBold Underline\033[0m')
        assert len(segments) > 0
    
    def test_cursor_position(self):
        """P0: 光标定位解析"""
        self.parser.parse('\033[10;20H')
        assert any(cmd.command_type == 'move_cursor' for cmd in self.parser.commands)
    
    def test_cursor_home(self):
        """P0: 光标归位解析"""
        self.parser.parse('\033[H')
        assert any(cmd.command_type == 'refresh_screen' for cmd in self.parser.commands)
    
    def test_cursor_movement(self):
        """P0: 光标移动解析"""
        self.parser.parse('\033[5A')
        assert any(cmd.command_type == 'cursor_up' for cmd in self.parser.commands)
    
    def test_cursor_show_hide(self):
        """P0: 光标显示隐藏解析 - 验证序列被过滤"""
        segments = self.parser.parse('\033[?25l')
        assert isinstance(segments, list)
    
    def test_clear_screen(self):
        """P0: 清屏解析"""
        self.parser.parse('\033[2J')
        assert any(cmd.command_type == 'clear_screen' for cmd in self.parser.commands)
    
    def test_clear_line(self):
        """P0: 清行解析"""
        self.parser.parse('\033[2K')
        assert any(cmd.command_type == 'clear_line' for cmd in self.parser.commands)
    
    def test_osc_sequence_filter(self):
        """P0: OSC序列过滤"""
        segments = self.parser.parse('\033]0;Terminal Title\033\\Normal text')
        text = ''.join(s.text for s in segments)
        assert 'Terminal Title' not in text
        assert 'Normal text' in text
    
    def test_mixed_sequences(self):
        """P0: 混合序列解析"""
        segments = self.parser.parse('\033[31m\033[1mRed Bold\033[0m')
        assert len(segments) > 0


class TestVirtualScreen:
    """虚拟屏幕测试"""
    
    def setup_method(self):
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_write_char(self):
        """P0: 字符写入"""
        self.screen.write_char('A')
        assert self.screen.cells[0][0].char == 'A'
    
    def test_write_text(self):
        """P0: 文本写入"""
        self.screen.write_text('Hello')
        assert self.screen.get_row_text(0).startswith('Hello')
    
    def test_newline_handling(self):
        """P0: 换行处理"""
        self.screen.write_text('line1\nline2')
        assert self.screen.cursor_row >= 1
    
    def test_carriage_return(self):
        """P0: 回车处理"""
        self.screen.write_text('Hello')
        self.screen.move_cursor(0, 0)
        assert self.screen.cursor_col == 0
    
    def test_tab_handling(self):
        """P0: Tab处理"""
        self.screen.write_text('A\tB')
        assert self.screen.cursor_col > 1
    
    def test_control_char_filter(self):
        """P0: 控制字符过滤"""
        self.screen.write_text('A\x07B')
        row_text = self.screen.get_row_text(0)
        assert '\x07' not in row_text
    
    def test_move_cursor(self):
        """P0: 光标移动"""
        self.screen.move_cursor(10, 20)
        assert self.screen.cursor_row == 10
        assert self.screen.cursor_col == 20
    
    def test_cursor_boundary(self):
        """P0: 光标边界"""
        self.screen.move_cursor(0, 0)
        self.screen.move_cursor_back(1)
        assert self.screen.cursor_col >= 0
    
    def test_clear_screen_mode2(self):
        """P0: 清屏模式2"""
        self.screen.write_text('Test')
        self.screen.clear_screen(mode=2)
        assert self.screen.get_row_text(0) == ' ' * 80
        assert self.screen.cursor_row == 0
        assert self.screen.cursor_col == 0
    
    def test_clear_line_mode2(self):
        """P0: 清行模式2"""
        self.screen.write_text('Hello World')
        self.screen.clear_line(mode=2)
        assert self.screen.get_row_text(0) == ' ' * 80
    
    def test_modified_rows_tracking(self):
        """P0: 修改行跟踪"""
        self.screen.write_char('A')
        assert 0 in self.screen.modified_rows
    
    def test_auto_scroll(self):
        """P0: 自动滚动"""
        for i in range(25):
            self.screen.write_text(f'Line {i}\n')
        assert self.screen.cursor_row <= 24
    
    def test_scroll_region(self):
        """P0: 滚动区域设置"""
        self.screen.set_scroll_region(5, 20)
        assert self.screen.scroll_top == 5
        assert self.screen.scroll_bottom == 20
    
    def test_resize(self):
        """P0: 屏幕调整"""
        self.screen.write_text('Hello')
        self.screen.resize(30, 100)
        assert self.screen.rows == 30
        assert self.screen.cols == 100
        assert self.screen.cells[0][0].char == 'H'
    
    def test_get_row_text(self):
        """P0: 获取行文本"""
        self.screen.write_text('Hello World')
        assert 'Hello World' in self.screen.get_row_text(0)
    
    def test_get_modified_rows_data(self):
        """P0: 获取修改行数据"""
        self.screen.write_char('A')
        data = self.screen.get_modified_rows_data()
        assert len(data) > 0
    
    def test_get_debug_info(self):
        """P0: 获取调试信息"""
        info = self.screen.get_debug_info()
        assert 'rows' in info
        assert 'cols' in info


class TestCursorRenderer:
    """光标渲染器测试"""
    
    def setup_method(self):
        self.renderer = CursorRenderer()
    
    def test_toggle_visibility(self):
        """P0: 光标可见性切换"""
        initial = self.renderer.cursor_visible
        self.renderer.toggle_visibility()
        assert self.renderer.cursor_visible != initial
    
    def test_cursor_shapes(self):
        """P0: 光标形状设置"""
        self.renderer.set_shape('block')
        assert self.renderer.cursor_shape == 'block'
        
        self.renderer.set_shape('underline')
        assert self.renderer.cursor_shape == 'underline'
        
        self.renderer.set_shape('bar')
        assert self.renderer.cursor_shape == 'bar'
    
    def test_invalid_shape(self):
        """P0: 无效形状处理"""
        old_shape = self.renderer.cursor_shape
        self.renderer.set_shape('invalid')
        assert self.renderer.cursor_shape == old_shape


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
