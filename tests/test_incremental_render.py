# -*- coding: utf-8 -*-
"""
增量渲染性能测试
验证增量渲染优化的效果
"""

import pytest
from core.virtual_screen import VirtualScreen


class TestIncrementalRendering:
    """增量渲染性能测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.screen = VirtualScreen(rows=24, cols=80)
    
    def test_modified_rows_tracking(self):
        """P0: 验证修改行跟踪功能"""
        # 初始状态应该没有修改的行
        assert len(self.screen.modified_rows) == 0
        
        # 写入一些字符
        self.screen.write_char('A')
        self.screen.write_char('B')
        self.screen.write_char('C')
        
        # 应该只有第0行被修改
        assert 0 in self.screen.modified_rows
        assert len(self.screen.modified_rows) == 1
    
    def test_modified_cols_tracking(self):
        """P0: 验证修改列范围跟踪功能"""
        # 写入字符到不同位置
        self.screen.write_char('A')  # (0, 0)
        self.screen.write_char('B')  # (0, 1)
        self.screen.move_cursor(0, 10)
        self.screen.write_char('C')  # (0, 10)
        
        # 验证列范围
        assert 0 in self.screen.modified_cols
        col_range = self.screen.modified_cols[0]
        assert col_range[0] == 0  # 最小列
        assert col_range[1] == 10  # 最大列
    
    def test_multiple_rows_modification(self):
        """P0: 验证多行修改跟踪"""
        # 写入多行
        for row in range(5):
            self.screen.move_cursor(row, 0)
            self.screen.write_char(f'R{row}')
        
        # 应该有5行被修改
        assert len(self.screen.modified_rows) == 5
        for row in range(5):
            assert row in self.screen.modified_rows
    
    def test_clear_screen_mode_2_tracking(self):
        """P0: 验证清屏模式2的修改跟踪"""
        # 先写入一些内容
        self.screen.write_char('A')
        self.screen.modified_rows.clear()
        self.screen.modified_cols.clear()
        
        # 清屏
        self.screen.clear_screen(mode=2)
        
        # 应该所有行都被标记为修改
        assert len(self.screen.modified_rows) == 24
        assert len(self.screen.modified_cols) == 24
        
        # 每行的列范围应该是完整的
        for row in range(24):
            assert row in self.screen.modified_cols
            assert self.screen.modified_cols[row] == [0, 79]
    
    def test_clear_line_tracking(self):
        """P0: 验证清行的修改跟踪"""
        # 写入一些内容
        self.screen.write_text("Hello World")
        self.screen.modified_rows.clear()
        self.screen.modified_cols.clear()
        
        # 移动光标到中间并清行
        self.screen.move_cursor(0, 5)
        self.screen.clear_line(mode=0)
        
        # 验证修改跟踪
        assert 0 in self.screen.modified_rows
        assert 0 in self.screen.modified_cols
        col_range = self.screen.modified_cols[0]
        assert col_range[0] == 5  # 从光标位置开始
        assert col_range[1] == 79  # 到行尾
    
    def test_get_modified_rows_data(self):
        """P0: 验证获取修改行数据功能"""
        # 写入一些内容
        self.screen.write_char('A')
        self.screen.write_char('B')
        
        # 获取修改的行数据
        modified_data = self.screen.get_modified_rows_data()
        
        # 应该返回修改的行
        assert len(modified_data) == 1
        row_idx, cells, col_range = modified_data[0]
        assert row_idx == 0
        assert col_range is not None
        assert col_range[0] == 0
        assert col_range[1] == 1
        
        # 获取后应该清空修改标记
        assert len(self.screen.modified_rows) == 0
        assert len(self.screen.modified_cols) == 0
    
    def test_incremental_render_simulation(self):
        """P1: 模拟增量渲染场景"""
        # 初始化屏幕
        self.screen = VirtualScreen(rows=24, cols=80)
        
        # 模拟完整渲染
        full_render_rows = set(range(24))
        full_render_cell_count = len(full_render_rows) * 80
        
        # 模拟增量渲染：只修改了3行，每行修改10个字符
        self.screen.modified_rows = {5, 10, 15}
        self.screen.modified_cols = {
            5: [0, 9],
            10: [0, 9],
            15: [0, 9]
        }
        
        incremental_render_rows = self.screen.modified_rows
        incremental_cell_count = sum(
            (cols[1] - cols[0] + 1) for cols in self.screen.modified_cols.values()
        )
        
        # 验证增量渲染减少了渲染量
        assert incremental_cell_count < full_render_cell_count
        assert len(incremental_render_rows) < len(full_render_rows)
        
        # 计算优化比例
        reduction = 1 - (incremental_cell_count / full_render_cell_count)
        assert reduction > 0.9  # 应该减少90%以上的渲染量
    
    def test_resize_clears_tracking(self):
        """P1: 验证调整大小时清空修改跟踪"""
        # 写入一些内容
        self.screen.write_char('A')
        
        # 调整大小
        self.screen.resize(30, 100)
        
        # 应该所有新行都被标记为修改
        assert len(self.screen.modified_rows) == 30
        assert len(self.screen.modified_cols) == 30
    
    def test_clear_screen_mode_0_tracking(self):
        """P0: 验证清屏模式0的修改跟踪"""
        # 移动光标到中间
        self.screen.move_cursor(10, 40)
        self.screen.modified_rows.clear()
        self.screen.modified_cols.clear()
        
        # 清屏模式0
        self.screen.clear_screen(mode=0)
        
        # 应该修改从光标行到屏幕底部的所有行
        assert 10 in self.screen.modified_rows
        assert 23 in self.screen.modified_rows
        assert len(self.screen.modified_rows) == 14  # 10到23共14行
        
        # 光标行的列范围应该是从光标位置到行尾
        assert 10 in self.screen.modified_cols
        assert self.screen.modified_cols[10][0] == 40
        assert self.screen.modified_cols[10][1] == 79
        
        # 下面的行应该是完整列范围
        assert self.screen.modified_cols[11] == [0, 79]
    
    def test_clear_screen_mode_1_tracking(self):
        """P0: 验证清屏模式1的修改跟踪"""
        # 移动光标到中间
        self.screen.move_cursor(10, 40)
        self.screen.modified_rows.clear()
        self.screen.modified_cols.clear()
        
        # 清屏模式1
        self.screen.clear_screen(mode=1)
        
        # 应该修改从屏幕顶部到光标行的所有行
        assert 0 in self.screen.modified_rows
        assert 10 in self.screen.modified_rows
        assert len(self.screen.modified_rows) == 11  # 0到10共11行
        
        # 光标行的列范围应该是从行首到光标位置
        assert 10 in self.screen.modified_cols
        assert self.screen.modified_cols[10][0] == 0
        assert self.screen.modified_cols[10][1] == 40
        
        # 上面的行应该是完整列范围
        assert self.screen.modified_cols[0] == [0, 79]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
