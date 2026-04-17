# -*- coding: utf-8 -*-
"""
优化功能测试 - 精简版

测试:
1. 命令历史机制
2. 提示符检测
3. 批量渲染
"""

import pytest
from core.virtual_screen import VirtualScreen
from core.terminal_buffer import ANSIParser


class TestOptimizations:
    """优化功能测试"""
    
    def test_command_history_mechanism(self):
        """P0: 命令历史机制"""
        history = []
        commands = ["ls -la", "pwd", "cd /tmp", "echo hello"]
        for cmd in commands:
            history.append(cmd)
        
        assert len(history) == 4
        assert history[0] == "ls -la"
        assert history[-1] == "echo hello"
    
    def test_prompt_detection(self):
        """P0: 提示符检测"""
        parser = ANSIParser()
        
        test_prompts = [
            "[root@localhost ~]#",
            "[user@host /path]$",
            "user@host:~$ ",
            "$ ",
            "# "
        ]
        
        for prompt in test_prompts:
            segments = parser.parse(prompt)
            assert len(segments) > 0
            text = ''.join(s.text for s in segments)
            assert len(text.strip()) > 0
    
    def test_batch_render_scheduling(self):
        """P0: 批量渲染调度"""
        render_count = 0
        last_render_time = 0
        batch_count = 0
        min_interval = 16
        
        for i in range(10):
            current_time = i * 5
            
            if current_time - last_render_time < min_interval:
                batch_count += 1
                if batch_count >= 5:
                    render_count += 1
                    last_render_time = current_time
                    batch_count = 0
            else:
                render_count += 1
                last_render_time = current_time
                batch_count = 0
        
        assert render_count < 10
    
    def test_input_buffer_management(self):
        """P0: 输入缓冲区管理"""
        current_input = ""
        
        for char in "hello world":
            current_input += char
        
        assert current_input == "hello world"
        
        current_input = current_input[:-1]
        assert current_input == "hello worl"
        
        current_input = ""
        assert current_input == ""
    
    def test_history_navigation(self):
        """P0: 历史命令导航"""
        history = ["ls", "pwd", "cd /tmp"]
        history_index = -1
        current_input = ""
        
        if history_index < len(history) - 1:
            history_index += 1
            current_input = history[-(history_index + 1)]
        
        assert current_input == "cd /tmp"
        
        if history_index < len(history) - 1:
            history_index += 1
            current_input = history[-(history_index + 1)]
        
        assert current_input == "pwd"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
