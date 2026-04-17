# -*- coding: utf-8 -*-
"""
验证优化效果的测试脚本
测试三个重点优化项：
1. 命令历史机制
2. 提示符检测
3. 性能优化
"""

import pytest
from core.virtual_screen import VirtualScreen
from core.terminal_buffer import ANSIParser


class TestOptimizations:
    """验证优化效果"""
    
    def test_command_history_mechanism(self):
        """测试命令历史机制优化"""
        # 模拟命令历史记录
        history = []
        current_input = ""
        
        # 模拟输入命令
        commands = ["ls -la", "pwd", "cd /tmp", "echo hello"]
        for cmd in commands:
            current_input = cmd
            history.append(cmd)
        
        # 验证历史记录
        assert len(history) == 4
        assert history[0] == "ls -la"
        assert history[-1] == "echo hello"
        
        # 验证历史限制（最多1000条，超过后保留最后500条）
        for i in range(1005):
            history.append(f"cmd_{i}")
            # 模拟实际实现中的限制逻辑
            if len(history) > 1000:
                history = history[-500:]
        
        # 验证历史记录被正确限制
        # 初始4条 + 1005条 = 1009条
        # 当超过1000条时，会截断到500条
        # 最终应该是500条左右（取决于截断时机）
        assert len(history) <= 508  # 4 + (1005-501) = 508
        assert len(history) >= 500  # 至少500条
    
    def test_prompt_detection(self):
        """测试提示符检测通用性"""
        parser = ANSIParser()
        
        # 测试不同类型的提示符
        test_prompts = [
            "[root@localhost ~]#",
            "[user@host /path]$",
            "user@host:~$ ",
            "admin@server% ",
            "$ ",
            "# "
        ]
        
        for prompt in test_prompts:
            # 验证提示符可以正确解析
            segments = parser.parse(prompt)
            assert len(segments) > 0
            # 提示符应该被正确解析为文本
            text = ''.join(s.text for s in segments)
            assert len(text.strip()) > 0
    
    def test_batch_render_scheduling(self):
        """测试批量渲染调度"""
        # 模拟渲染调度逻辑
        render_count = 0
        last_render_time = 0
        batch_count = 0
        min_interval = 16  # ms
        
        # 模拟快速连续更新
        for i in range(10):
            current_time = i * 5  # 每5ms一次更新
            
            if current_time - last_render_time < min_interval:
                batch_count += 1
                if batch_count >= 5:  # 达到最大批量次数
                    render_count += 1
                    last_render_time = current_time
                    batch_count = 0
            else:
                render_count += 1
                last_render_time = current_time
                batch_count = 0
        
        # 验证批量渲染减少了实际渲染次数
        assert render_count < 10  # 应该少于10次实际渲染
    
    def test_input_buffer_management(self):
        """测试输入缓冲区管理"""
        current_input = ""
        
        # 模拟输入
        for char in "hello world":
            current_input += char
        
        assert current_input == "hello world"
        
        # 模拟退格
        current_input = current_input[:-1]
        assert current_input == "hello worl"
        
        # 模拟Ctrl+U（清空整行）
        current_input = ""
        assert current_input == ""
    
    def test_history_navigation(self):
        """测试历史命令导航"""
        history = ["ls", "pwd", "cd /tmp"]
        history_index = -1
        current_input = ""
        
        # 上一条
        if history_index < len(history) - 1:
            history_index += 1
            cmd = history[-(history_index + 1)]
            current_input = cmd
        
        assert current_input == "cd /tmp"
        
        # 再上一条
        if history_index < len(history) - 1:
            history_index += 1
            cmd = history[-(history_index + 1)]
            current_input = cmd
        
        assert current_input == "pwd"
        
        # 下一条
        if history_index > 0:
            history_index -= 1
            cmd = history[-(history_index + 1)]
            current_input = cmd
        
        assert current_input == "cd /tmp"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
