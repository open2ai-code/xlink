# -*- coding: utf-8 -*-
"""
清屏功能测试
验证清屏逻辑的完整性和本地/服务器端状态同步
"""

import pytest
from core.terminal_buffer import ANSIParser
from core.virtual_screen import VirtualScreen


class TestClearScreenFunctionality:
    """清屏功能关键测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.parser = ANSIParser()
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_clear_screen_mode_0(self):
        """P0: 清屏模式0 - 从光标到屏幕底部"""
        self.screen.write_text("Line 1\nLine 2\nLine 3")
        self.screen.move_cursor(1, 0)
        
        self.screen.clear_screen(mode=0)
        
        assert self.screen.get_row_text(1) == ' ' * 80
        assert self.screen.get_row_text(2) == ' ' * 80
        assert 'Line 1' in self.screen.get_row_text(0)
    
    def test_clear_screen_mode_1(self):
        """P0: 清屏模式1 - 从屏幕顶部到光标"""
        self.screen.write_text("Line 1\nLine 2\nLine 3")
        self.screen.move_cursor(1, 10)
        
        self.screen.clear_screen(mode=1)
        
        assert self.screen.get_row_text(0) == ' ' * 80
        row_1 = self.screen.get_row_text(1)
        assert row_1[:11] == ' ' * 11
    
    def test_clear_screen_mode_2(self):
        """P0: 清屏模式2 - 整个屏幕"""
        self.screen.write_text("Line 1\nLine 2\nLine 3")
        self.screen.clear_screen(mode=2)
        
        for row in range(24):
            assert self.screen.get_row_text(row) == ' ' * 80
        
        assert self.screen.cursor_row == 0
        assert self.screen.cursor_col == 0
    
    def test_clear_screen_ansi_sequence_mode_0(self):
        """P0: ANSI清屏序列 \033[J (模式0)"""
        text = "Some text\033[J"
        self.parser.parse(text)
        
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
        assert clear_commands[0].params.get('mode') == 0
    
    def test_clear_screen_ansi_sequence_mode_2(self):
        """P0: ANSI清屏序列 \033[2J (模式2)"""
        text = "Some text\033[2J"
        self.parser.parse(text)
        
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
        assert clear_commands[0].params.get('mode') == 2
    
    def test_clear_screen_ansi_sequence_mode_3(self):
        """P0: ANSI清屏序列 \033[3J (模式3)"""
        text = "Some text\033[3J"
        self.parser.parse(text)
        
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
        assert clear_commands[0].params.get('mode') == 3
    
    def test_clear_line_mode_0(self):
        """P0: 清行模式0 - 从光标到行尾"""
        self.screen.write_text("Hello World")
        self.screen.move_cursor(0, 5)
        self.screen.clear_line(mode=0)
        
        row_text = self.screen.get_row_text(0)
        assert row_text.startswith("Hello")
        assert "World" not in row_text
    
    def test_clear_line_mode_2(self):
        """P0: 清行模式2 - 整行"""
        self.screen.write_text("Hello World")
        self.screen.move_cursor(0, 5)
        self.screen.clear_line(mode=2)
        
        assert self.screen.get_row_text(0) == ' ' * 80
    
    def test_clear_screen_state_sync(self):
        """P0: 清屏状态同步验证"""
        self.screen.clear_screen(mode=2)
        
        assert self.screen.cursor_row == 0
        assert self.screen.cursor_col == 0
        assert len(self.screen.modified_rows) == 24


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
