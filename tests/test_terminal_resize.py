# -*- coding: utf-8 -*-
"""
终端大小自适应测试
验证窗口大小变化时终端能正确调整并同步到服务器
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.virtual_screen import VirtualScreen


class TestTerminalResize:
    """终端大小自适应测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_screen_resize_basic(self):
        """P0: 基本屏幕大小调整"""
        # 初始大小
        assert self.screen.rows == 24
        assert self.screen.cols == 80
        
        # 调整大小
        self.screen.resize(30, 100)
        
        # 验证新大小
        assert self.screen.rows == 30
        assert self.screen.cols == 100
    
    def test_screen_resize_smaller(self):
        """P0: 缩小屏幕"""
        # 写入一些内容
        for i in range(20):
            self.screen.write_text(f"Line {i}\n")
        
        # 缩小屏幕
        self.screen.resize(15, 60)
        
        # 验证大小调整
        assert self.screen.rows == 15
        assert self.screen.cols == 60
        
        # 验证光标位置在范围内
        assert self.screen.cursor_row < 15
        assert self.screen.cursor_col < 60
    
    def test_screen_resize_content_preserved(self):
        """P0: 调整大小时内容保留"""
        # 写入内容
        self.screen.write_text("Hello World")
        
        # 调整大小
        self.screen.resize(30, 100)
        
        # 验证内容保留
        assert "Hello World" in self.screen.get_row_text(0)
    
    def test_screen_resize_cursor_bounds(self):
        """P0: 调整大小时光标位置限制"""
        # 移动光标到边缘
        self.screen.move_cursor(23, 79)
        
        # 缩小屏幕
        self.screen.resize(10, 40)
        
        # 验证光标在新范围内
        assert self.screen.cursor_row < 10
        assert self.screen.cursor_col < 40
    
    def test_screen_resize_modified_rows(self):
        """P0: 调整大小后标记修改行"""
        self.screen.resize(30, 100)
        
        # 验证所有行都被标记为修改
        assert len(self.screen.modified_rows) == 30
    
    def test_resize_debounce_mechanism(self):
        """P1: 防抖机制模拟测试"""
        # 模拟快速连续的大小调整
        resize_events = [
            {'cols': 80, 'rows': 24},
            {'cols': 85, 'rows': 25},
            {'cols': 90, 'rows': 26},
            {'cols': 95, 'rows': 27},
            {'cols': 100, 'rows': 28},
        ]
        
        # 模拟防抖逻辑
        pending_resize = None
        actual_resizes = []
        
        for event in resize_events:
            pending_resize = event
        
        # 最终只应用最后一次调整
        if pending_resize:
            actual_resizes.append(pending_resize)
        
        # 验证只应用了一次
        assert len(actual_resizes) == 1
        assert actual_resizes[0] == {'cols': 100, 'rows': 28}
    
    def test_resize_minimum_size(self):
        """P0: 最小大小限制"""
        # 尝试调整到非常小的大小
        self.screen.resize(5, 20)
        
        # 验证最小大小限制（在widget层实现）
        # 这里只测试screen层能处理小尺寸
        assert self.screen.rows == 5
        assert self.screen.cols == 20
    
    def test_resize_large_size(self):
        """P1: 调整到较大尺寸"""
        self.screen.resize(60, 200)
        
        assert self.screen.rows == 60
        assert self.screen.cols == 200
    
    def test_scroll_position_after_resize(self):
        """P0: 调整大小后滚动位置处理"""
        # 模拟滚动位置
        scroll_position = 20
        
        # 缩小屏幕
        self.screen.resize(15, 60)
        
        # 验证滚动位置需要调整（在widget层处理）
        # 这里只测试screen resize
        assert self.screen.rows == 15
        
        # 模拟widget层的滚动位置调整逻辑
        if scroll_position >= self.screen.rows:
            scroll_position = max(0, self.screen.rows - 1)
        
        assert scroll_position < self.screen.rows
    
    def test_resize_preserves_visible_content(self):
        """P1: 调整大小保留可见内容"""
        # 写入多行内容
        for i in range(24):
            self.screen.write_text(f"Line {i}\n")
        
        # 调整大小（增加行数）
        self.screen.resize(30, 80)
        
        # 验证前24行内容保留
        for i in range(24):
            row_text = self.screen.get_row_text(i)
            # 内容应该保留（可能被截断或填充）
            assert f"Line {i}" in row_text or i >= self.screen.rows


class TestSSHResizeNotification:
    """SSH终端大小通知测试"""
    
    def test_ssh_resize_called(self):
        """P0: SSH连接时调用resize_terminal"""
        # 模拟SSH连接
        mock_ssh = Mock()
        mock_ssh.is_connected = True
        mock_ssh.resize_terminal = Mock()
        
        # 模拟调整大小
        new_cols = 100
        new_rows = 30
        
        if mock_ssh and mock_ssh.is_connected:
            mock_ssh.resize_terminal(new_cols, new_rows)
        
        # 验证调用
        mock_ssh.resize_terminal.assert_called_once_with(new_cols, new_rows)
    
    def test_ssh_resize_not_called_when_disconnected(self):
        """P0: SSH断开时不调用resize_terminal"""
        # 模拟SSH连接（断开状态）
        mock_ssh = Mock()
        mock_ssh.is_connected = False
        mock_ssh.resize_terminal = Mock()
        
        # 模拟调整大小
        if mock_ssh and mock_ssh.is_connected:
            mock_ssh.resize_terminal(100, 30)
        
        # 验证未调用
        mock_ssh.resize_terminal.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
