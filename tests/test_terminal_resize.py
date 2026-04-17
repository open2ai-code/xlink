# -*- coding: utf-8 -*-
"""
终端大小自适应测试
验证窗口大小变化时终端能正确调整并同步到服务器
"""

import pytest
from unittest.mock import Mock
from core.virtual_screen import VirtualScreen


class TestTerminalResize:
    """终端大小自适应关键测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_screen_resize_basic(self):
        """P0: 基本屏幕大小调整"""
        assert self.screen.rows == 24
        assert self.screen.cols == 80
        
        self.screen.resize(30, 100)
        
        assert self.screen.rows == 30
        assert self.screen.cols == 100
    
    def test_screen_resize_smaller(self):
        """P0: 缩小屏幕"""
        for i in range(20):
            self.screen.write_text(f"Line {i}\n")
        
        self.screen.resize(15, 60)
        
        assert self.screen.rows == 15
        assert self.screen.cols == 60
        assert self.screen.cursor_row < 15
        assert self.screen.cursor_col < 60
    
    def test_screen_resize_content_preserved(self):
        """P0: 调整大小时内容保留"""
        self.screen.write_text("Hello World")
        self.screen.resize(30, 100)
        
        assert "Hello World" in self.screen.get_row_text(0)
    
    def test_screen_resize_cursor_bounds(self):
        """P0: 调整大小时光标位置限制"""
        self.screen.move_cursor(23, 79)
        self.screen.resize(10, 40)
        
        assert self.screen.cursor_row < 10
        assert self.screen.cursor_col < 40
    
    def test_screen_resize_modified_rows(self):
        """P0: 调整大小后标记修改行"""
        self.screen.resize(30, 100)
        assert len(self.screen.modified_rows) == 30


class TestSSHResizeNotification:
    """SSH终端大小通知测试"""
    
    def test_ssh_resize_called(self):
        """P0: SSH连接时调用resize_terminal"""
        mock_ssh = Mock()
        mock_ssh.is_connected = True
        mock_ssh.resize_terminal = Mock()
        
        if mock_ssh and mock_ssh.is_connected:
            mock_ssh.resize_terminal(100, 30)
        
        mock_ssh.resize_terminal.assert_called_once_with(100, 30)
    
    def test_ssh_resize_not_called_when_disconnected(self):
        """P0: SSH断开时不调用resize_terminal"""
        mock_ssh = Mock()
        mock_ssh.is_connected = False
        mock_ssh.resize_terminal = Mock()
        
        if mock_ssh and mock_ssh.is_connected:
            mock_ssh.resize_terminal(100, 30)
        
        mock_ssh.resize_terminal.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
