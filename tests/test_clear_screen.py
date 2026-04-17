# -*- coding: utf-8 -*-
"""
清屏功能测试
验证清屏逻辑的完整性和本地/服务器端状态同步
"""

import pytest
from core.terminal_buffer import ANSIParser, TerminalCommand
from core.virtual_screen import VirtualScreen


class TestClearScreenFunctionality:
    """清屏功能测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.parser = ANSIParser()
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_clear_screen_mode_0(self):
        """P0: 清屏模式0 - 从光标到屏幕底部"""
        # 写入一些内容
        self.screen.write_text("Line 1\nLine 2\nLine 3")
        self.screen.move_cursor(1, 0)  # 移动到第2行
        
        # 清屏模式0
        self.screen.clear_screen(mode=0)
        
        # 验证光标位置及以下的行被清空
        assert self.screen.get_row_text(1) == ' ' * 80
        assert self.screen.get_row_text(2) == ' ' * 80
        # 第1行应该保留
        assert 'Line 1' in self.screen.get_row_text(0)
    
    def test_clear_screen_mode_1(self):
        """P0: 清屏模式1 - 从屏幕顶部到光标"""
        # 写入一些内容
        self.screen.write_text("Line 1\nLine 2\nLine 3")
        self.screen.move_cursor(1, 10)  # 移动到第2行第10列
        
        # 清屏模式1
        self.screen.clear_screen(mode=1)
        
        # 验证光标位置以上的行被清空
        assert self.screen.get_row_text(0) == ' ' * 80
        # 光标所在行只清空到光标位置（包括光标列）
        row_1 = self.screen.get_row_text(1)
        assert row_1[:11] == ' ' * 11  # 前11个字符（0-10列）被清空
    
    def test_clear_screen_mode_2(self):
        """P0: 清屏模式2 - 整个屏幕"""
        # 写入一些内容
        self.screen.write_text("Line 1\nLine 2\nLine 3")
        
        # 清屏模式2
        self.screen.clear_screen(mode=2)
        
        # 验证整个屏幕被清空
        for row in range(24):
            assert self.screen.get_row_text(row) == ' ' * 80
        
        # 验证光标归位
        assert self.screen.cursor_row == 0
        assert self.screen.cursor_col == 0
    
    def test_clear_screen_ansi_sequence_mode_0(self):
        """P0: ANSI清屏序列 \033[J (模式0)"""
        text = "Some text\033[J"
        commands = self.parser.parse(text)
        
        # 验证清屏命令被正确解析
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
        assert clear_commands[0].params.get('mode') == 0
    
    def test_clear_screen_ansi_sequence_mode_2(self):
        """P0: ANSI清屏序列 \033[2J (模式2)"""
        text = "Some text\033[2J"
        commands = self.parser.parse(text)
        
        # 验证清屏命令被正确解析
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
        assert clear_commands[0].params.get('mode') == 2
    
    def test_clear_screen_ansi_sequence_mode_3(self):
        """P0: ANSI清屏序列 \033[3J (模式3 - 清除滚动缓冲区)"""
        text = "Some text\033[3J"
        commands = self.parser.parse(text)
        
        # 验证清屏命令被正确解析
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
        assert clear_commands[0].params.get('mode') == 3
    
    def test_cursor_home_and_clear_sequence(self):
        """P0: 光标归位+清屏组合序列 \033[H\033[2J"""
        text = "\033[H\033[2J"
        commands = self.parser.parse(text)
        
        # 验证清屏和光标归位命令都被解析
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        refresh_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'refresh_screen']
        
        assert len(clear_commands) > 0
        assert len(refresh_commands) > 0
    
    def test_clear_line_mode_0(self):
        """P0: 清行模式0 - 从光标到行尾"""
        self.screen.write_text("Hello World")
        self.screen.move_cursor(0, 5)  # 移动到"World"前
        
        # 清行模式0
        self.screen.clear_line(mode=0)
        
        # 验证光标后的内容被清空
        row_text = self.screen.get_row_text(0)
        assert row_text.startswith("Hello")
        assert "World" not in row_text
    
    def test_clear_line_mode_1(self):
        """P0: 清行模式1 - 从行首到光标"""
        self.screen.write_text("Hello World")
        self.screen.move_cursor(0, 5)  # 移动到"World"前
        
        # 清行模式1
        self.screen.clear_line(mode=1)
        
        # 验证光标前的内容被清空
        row_text = self.screen.get_row_text(0)
        assert "Hello" not in row_text
    
    def test_clear_line_mode_2(self):
        """P0: 清行模式2 - 整行"""
        self.screen.write_text("Hello World")
        self.screen.move_cursor(0, 5)
        
        # 清行模式2
        self.screen.clear_line(mode=2)
        
        # 验证整行被清空
        assert self.screen.get_row_text(0) == ' ' * 80
    
    def test_clear_screen_state_sync(self):
        """P0: 清屏状态同步验证"""
        # 模拟清屏操作
        self.screen.clear_screen(mode=2)
        
        # 验证状态
        assert self.screen.cursor_row == 0
        assert self.screen.cursor_col == 0
        assert len(self.screen.modified_rows) == 24  # 所有行都被标记为修改
    
    def test_multiple_clear_sequences(self):
        """P1: 多个清屏序列处理"""
        text = "\033[H\033[2J\033[3J"
        commands = self.parser.parse(text)
        
        # 验证清屏命令被正确解析
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
    
    def test_clear_screen_with_text(self):
        """P1: 清屏后写入文本"""
        # 清屏
        self.screen.clear_screen(mode=2)
        
        # 写入新文本
        self.screen.write_text("New content")
        
        # 验证新文本正确显示
        assert "New content" in self.screen.get_row_text(0)
    
    def test_clear_screen_ansi_sequence_mode_1(self):
        """P0: ANSI清屏序列 \033[1J (模式1)"""
        text = "Some text\033[1J"
        commands = self.parser.parse(text)
        
        # 验证清屏命令被正确解析
        clear_commands = [cmd for cmd in self.parser.commands if cmd.command_type == 'clear_screen']
        assert len(clear_commands) > 0
        assert clear_commands[0].params.get('mode') == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
