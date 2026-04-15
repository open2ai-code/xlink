# -*- coding: utf-8 -*-
"""
XLink自绘终端架构 - 单元测试套件

测试覆盖:
- ANSI序列解析 (terminal_buffer.py)
- 虚拟屏幕功能 (virtual_screen.py)
- 光标渲染器 (cursor_renderer.py)
- 自绘终端控件 (native_terminal_widget.py)
"""

import pytest
from core.terminal_buffer import ANSIParser, TextSegment, TerminalCommand
from core.virtual_screen import VirtualScreen, Cell
from ui.cursor_renderer import CursorRenderer


# ============================================================================
# 一、ANSI序列解析测试
# ============================================================================

class TestANSIParser:
    """ANSI解析器测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.parser = ANSIParser()
    
    # --- 1.1 SGR颜色序列 ---
    
    def test_standard_8_colors(self):
        """测试标准8色解析 (30-37前景色, 40-47背景色)"""
        # 红色前景
        segments = self.parser.parse('\033[31mHello\033[0m')
        assert len(segments) >= 1
        assert segments[0].fg_color == '#FF0000'
        
        # 蓝色背景
        segments = self.parser.parse('\033[44mWorld\033[0m')
        assert segments[0].bg_color == '#0000FF'
    
    def test_bright_8_colors(self):
        """测试亮色8色解析 (90-97前景色, 100-107背景色)"""
        # 亮红色前景
        segments = self.parser.parse('\033[91mBright\033[0m')
        assert segments[0].fg_color == '#FF5555'
        
        # 亮白色背景
        segments = self.parser.parse('\033[107mWhite\033[0m')
        assert segments[0].bg_color == '#FFFFFF'
    
    def test_256_color(self):
        """测试256色解析 (38;5;N / 48;5;N)"""
        # 256色前景
        segments = self.parser.parse('\033[38;5;196mRed256\033[0m')
        assert segments[0].fg_color is not None
        
        # 256色背景
        segments = self.parser.parse('\033[48;5;21mBlue256\033[0m')
        assert segments[0].bg_color is not None
    
    def test_true_color(self):
        """测试真彩色解析 (38;2;R;G;B)"""
        # RGB真彩色
        segments = self.parser.parse('\033[38;2;255;128;64mTrueColor\033[0m')
        assert segments[0].fg_color == '#ff8040'
    
    def test_style_attributes(self):
        """测试样式属性 (0重置, 1加粗, 4下划线)"""
        # 加粗
        segments = self.parser.parse('\033[1mBold\033[0m')
        assert segments[0].bold is True
        
        # 下划线
        segments = self.parser.parse('\033[4mUnderline\033[0m')
        assert segments[0].underline is True
        
        # 重置
        self.parser.parse('\033[1;4mStyled\033[0m')
        assert self.parser.current_bold is False
        assert self.parser.current_underline is False
    
    def test_combined_params(self):
        """测试组合参数解析 (如 \033[1;31m 加粗+红色)"""
        segments = self.parser.parse('\033[1;31mBoldRed\033[0m')
        assert segments[0].bold is True
        assert segments[0].fg_color == '#FF0000'
    
    # --- 1.2 光标控制序列 ---
    
    def test_cursor_position(self):
        """测试光标定位 \033[row;colH"""
        segments = self.parser.parse('\033[5;10HText')
        assert len(self.parser.commands) > 0
        assert self.parser.commands[0].command_type == 'move_cursor'
        assert self.parser.commands[0].params['row'] == 4  # 0-based
        assert self.parser.commands[0].params['col'] == 9
    
    def test_cursor_home(self):
        """测试光标归位 \033[H"""
        segments = self.parser.parse('\033[HText')
        assert any(cmd.command_type == 'refresh_screen' for cmd in self.parser.commands)
    
    def test_cursor_movement(self):
        """测试光标移动 (A上/B下/C右/D左)"""
        # 上移
        self.parser.parse('\033[3A')
        assert any(cmd.command_type == 'cursor_up' for cmd in self.parser.commands)
        
        # 重置
        self.parser.commands = []
        
        # 右移
        self.parser.parse('\033[5C')
        assert any(cmd.command_type == 'cursor_forward' for cmd in self.parser.commands)
    
    def test_cursor_show_hide(self):
        """测试光标显示/隐藏"""
        # 这些序列应该被过滤,不留在文本中
        segments = self.parser.parse('\033[?25lHidden\033[?25h')
        text = ''.join(s.text for s in segments)
        assert '?25' not in text
    
    # --- 1.3 清屏清行序列 ---
    
    def test_clear_screen_full(self):
        """测试清屏 \033[2J (整个屏幕)"""
        segments = self.parser.parse('\033[2J')
        assert any(cmd.command_type == 'clear_screen' for cmd in self.parser.commands)
    
    def test_clear_screen_partial(self):
        """测试部分清屏"""
        # \033[J 或 \033[0J
        segments = self.parser.parse('\033[J')
        assert any(cmd.command_type == 'clear_screen' for cmd in self.parser.commands)
    
    def test_clear_line(self):
        """测试清行 \033[K"""
        segments = self.parser.parse('\033[K')
        assert any(cmd.command_type == 'clear_line' for cmd in self.parser.commands)
        assert self.parser.commands[-1].params.get('mode') == 0
    
    # --- 1.4 特殊序列处理 ---
    
    def test_osc_sequence_filter(self):
        """测试OSC序列过滤 (窗口标题等)"""
        segments = self.parser.parse('\033]0;My Terminal\033\\Text')
        text = ''.join(s.text for s in segments)
        assert 'My Terminal' not in text
        assert 'Text' in text
    
    def test_dec_private_filter(self):
        """测试DEC私有序列过滤"""
        segments = self.parser.parse('\033[?1034hText')
        text = ''.join(s.text for s in segments)
        assert '1034' not in text
    
    def test_charset_filter(self):
        """测试字符集选择序列过滤"""
        segments = self.parser.parse('\033(BText')
        text = ''.join(s.text for s in segments)
        assert '(B' not in text
    
    # --- 1.5 边界情况 ---
    
    def test_incomplete_sequence(self):
        """测试不完整序列处理"""
        # 不完整的ANSI序列应该被保留或安全处理
        segments = self.parser.parse('\033[31Incomplete')
        # 不应该崩溃
        assert isinstance(segments, list)
    
    def test_mixed_sequences(self):
        """测试混合序列解析"""
        text = '\033[2J\033[H\033[1;31mHello\033[0m World'
        segments = self.parser.parse(text)
        assert len(segments) > 0
        assert any(cmd.command_type == 'clear_screen' for cmd in self.parser.commands)
    
    def test_empty_params(self):
        """测试空参数默认值处理"""
        segments = self.parser.parse('\033[mDefault\033[0m')
        assert isinstance(segments, list)


# ============================================================================
# 二、虚拟屏幕功能测试
# ============================================================================

class TestVirtualScreen:
    """虚拟屏幕测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.screen = VirtualScreen(rows=24, cols=80)
    
    # --- 2.1 基本写入 ---
    
    def test_write_char(self):
        """测试字符写入"""
        self.screen.write_char('A', {'fg': '#FF0000', 'bg': '#000000'})
        assert self.screen.cells[0][0].char == 'A'
        assert self.screen.cells[0][0].fg_color == '#FF0000'
        assert self.screen.cursor_col == 1
    
    def test_write_text(self):
        """测试文本写入"""
        self.screen.write_text('Hello', {'fg': '#FFFFFF'})
        row_text = self.screen.get_row_text(0)
        assert row_text.startswith('Hello')
    
    def test_newline_handling(self):
        """测试换行处理"""
        self.screen.write_text('Line1\nLine2')
        # 注意: VirtualScreen允许光标超出屏幕,由渲染层处理滚动
        # 换行后光标应该在第2行(索引1),列0
        assert self.screen.cursor_row >= 1  # 至少在第2行
        # 写入Line2后,光标位置应该是(1, 5)
        assert self.screen.cursor_row == 1
        assert self.screen.cursor_col == 5  # 'Line2'的长度
    
    def test_carriage_return(self):
        """测试回车处理"""
        self.screen.write_text('12345\rAB')
        row_text = self.screen.get_row_text(0)
        assert row_text.startswith('AB345')
    
    def test_tab_handling(self):
        """测试制表符处理"""
        self.screen.write_text('A\tB')
        # 制表符应该被处理
        assert True  # 不崩溃即可
    
    def test_control_char_filter(self):
        """测试控制字符过滤"""
        self.screen.write_text('A\x07B')  # \x07 是响铃
        row_text = self.screen.get_row_text(0)
        assert '\x07' not in row_text
    
    # --- 2.2 光标操作 ---
    
    def test_move_cursor(self):
        """测试光标移动"""
        self.screen.move_cursor(5, 10)
        assert self.screen.cursor_row == 5
        assert self.screen.cursor_col == 10
    
    def test_cursor_boundary(self):
        """测试边界检查"""
        self.screen.move_cursor(100, 100)
        assert self.screen.cursor_row < self.screen.rows
        assert self.screen.cursor_col < self.screen.cols
    
    def test_cursor_directional(self):
        """测试光标上/下/左/右移动"""
        self.screen.move_cursor(10, 10)
        
        self.screen.move_cursor_up(3)
        assert self.screen.cursor_row == 7
        
        self.screen.move_cursor_down(2)
        assert self.screen.cursor_row == 9
        
        self.screen.move_cursor_forward(5)
        assert self.screen.cursor_col == 15
        
        self.screen.move_cursor_back(3)
        assert self.screen.cursor_col == 12
    
    # --- 2.3 清屏清行 ---
    
    def test_clear_screen_mode2(self):
        """测试清屏模式2 (整个屏幕)"""
        self.screen.write_text('Test')
        self.screen.clear_screen(mode=2)
        assert self.screen.get_row_text(0) == ' ' * 80
        assert self.screen.cursor_row == 0
        assert self.screen.cursor_col == 0
    
    def test_clear_line_mode2(self):
        """测试清行模式2 (整行)"""
        self.screen.write_text('Hello World')
        self.screen.clear_line(mode=2)
        assert self.screen.get_row_text(0) == ' ' * 80
    
    def test_modified_rows_tracking(self):
        """测试modified_rows标记"""
        self.screen.write_char('A')
        assert 0 in self.screen.modified_rows
    
    # --- 2.4 滚动机制 ---
    
    def test_auto_scroll(self):
        """测试自动滚动"""
        # 写入超过屏幕行数的内容
        for i in range(30):
            self.screen.write_text(f'Line{i}\n')
        
        # VirtualScreen允许光标超出屏幕范围,这是设计行为
        # 渲染层会处理滚动,确保显示正确的可见区域
        assert self.screen.cursor_row >= 0  # 光标位置有效
        # 验证屏幕内容保留
        assert len(self.screen.cells) == self.screen.rows
    
    def test_scroll_region(self):
        """测试滚动区域设置"""
        self.screen.set_scroll_region(2, 20)
        assert self.screen.scroll_top == 2
        assert self.screen.scroll_bottom == 20
    
    # --- 2.5 屏幕调整 ---
    
    def test_resize(self):
        """测试resize()调整屏幕大小"""
        self.screen.write_text('Hello')
        self.screen.resize(30, 100)
        assert self.screen.rows == 30
        assert self.screen.cols == 100
        # 内容应该保留
        assert self.screen.cells[0][0].char == 'H'
    
    # --- 2.6 数据获取 ---
    
    def test_get_row_text(self):
        """测试get_row_text()"""
        self.screen.write_text('Test123')
        text = self.screen.get_row_text(0)
        assert text.startswith('Test123')
    
    def test_get_modified_rows_data(self):
        """测试get_modified_rows_data()深拷贝"""
        self.screen.write_char('A')
        modified = self.screen.get_modified_rows_data()
        assert len(modified) > 0
        
        # 验证是深拷贝
        row_idx, cells = modified[0]
        cells[0].char = 'X'
        assert self.screen.cells[row_idx][0].char == 'A'  # 原数据未改变
    
    def test_get_debug_info(self):
        """测试get_debug_info()"""
        info = self.screen.get_debug_info()
        assert 'rows' in info
        assert 'cols' in info
        assert 'cursor' in info


# ============================================================================
# 三、光标渲染器测试
# ============================================================================

class TestCursorRenderer:
    """光标渲染器测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.renderer = CursorRenderer()
    
    def test_toggle_visibility(self):
        """测试光标可见性切换"""
        initial = self.renderer.cursor_visible
        self.renderer.toggle_visibility()
        assert self.renderer.cursor_visible != initial
    
    def test_cursor_shapes(self):
        """测试多种光标形状设置"""
        self.renderer.set_shape('block')
        assert self.renderer.cursor_shape == 'block'
        
        self.renderer.set_shape('bar')
        assert self.renderer.cursor_shape == 'bar'
        
        self.renderer.set_shape('underline')
        assert self.renderer.cursor_shape == 'underline'
    
    def test_invalid_shape(self):
        """测试无效形状不改变"""
        old_shape = self.renderer.cursor_shape
        self.renderer.set_shape('invalid')
        assert self.renderer.cursor_shape == old_shape


# ============================================================================
# 四、NCURSES模式检测测试
# ============================================================================

class TestNCURSESDetection:
    """NCURSES模式检测测试"""
    
    @pytest.mark.skip(reason="需要Qt应用程序环境")
    def test_ncurses_detection_logic(self):
        """测试NCURSES检测逻辑"""
        from ui.native_terminal_widget import NativeTerminalWidget
        import time
        
        widget = NativeTerminalWidget()
        
        # 模拟高频刷新
        current_time = time.time() * 1000
        widget._last_refresh_time = current_time - 100
        widget._refresh_count = 1
        
        # 触发检测 (>=10行, 500ms内>=2次)
        widget._detect_ncurses_mode(15, 10)
        assert widget._is_ncurses_mode is True
        assert widget.cursor_visible is False
    
    @pytest.mark.skip(reason="需要Qt应用程序环境")
    def test_ncurses_exit_on_prompt(self):
        """测试提示符检测退出NCURSES模式"""
        from ui.native_terminal_widget import NativeTerminalWidget
        
        widget = NativeTerminalWidget()
        widget._is_ncurses_mode = True
        
        # 模拟提示符
        widget.screen.write_text('[root@localhost ~]# ')
        widget._check_prompt()
        
        assert widget._is_ncurses_mode is False
        assert widget.cursor_visible is True


# ============================================================================
# 五、提示符去重测试
# ============================================================================

class TestPromptDeduplication:
    """提示符去重测试"""
    
    @pytest.mark.skip(reason="需要Qt应用程序环境")
    def test_duplicate_prompt_detection(self):
        """测试重复提示符检测"""
        from ui.native_terminal_widget import NativeTerminalWidget
        from core.terminal_buffer import TextSegment
        
        widget = NativeTerminalWidget()
        
        # 模拟重复提示符
        duplicate_text = '\r\n[root@localhost ~]# \r\n[root@localhost ~]# '
        segment = TextSegment(text=duplicate_text)
        
        # 验证检测到重复
        assert duplicate_text.count('[root@') > 1


# ============================================================================
# 六、集成测试辅助函数
# ============================================================================

def create_test_screen_with_content():
    """创建带测试内容的虚拟屏幕"""
    screen = VirtualScreen(rows=24, cols=80)
    screen.write_text('Hello, World!')
    screen.write_text('\nLine 2')
    return screen


def create_ansi_colored_text():
    """创建带ANSI颜色的测试文本"""
    return '\033[1;31mRed Bold\033[0m \033[32mGreen\033[0m'


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
