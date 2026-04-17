# -*- coding: utf-8 -*-
"""
自绘终端控件模块
完全自主渲染的终端控件,不依赖QPlainTextEdit
提供专业级的终端仿真体验
"""

import time
import logging
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics, QAction
from core.virtual_screen import VirtualScreen
from core.terminal_buffer import ANSIParser
from core.ssh_manager import SSHConnection
from ui.cursor_renderer import CursorRenderer

logger = logging.getLogger(__name__)


class NativeTerminalWidget(QWidget):
    """自绘终端控件 - 完全自主渲染"""
    
    # 信号
    connection_status = pyqtSignal(str)  # connected/disconnected/error
    error_occurred = pyqtSignal(str)
    
    def __init__(self, font_size: int = 13):
        super().__init__()
        
        # 设置控件属性
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        
        # 虚拟屏幕(复用已有的VirtualScreen)
        self.screen = VirtualScreen(rows=24, cols=80)
        
        # ANSI解析器
        self.ansi_parser = ANSIParser()
        
        # 光标渲染器
        self.cursor_renderer = CursorRenderer()
        
        # 字体和度量
        self.font_size = font_size
        self.font = QFont("Consolas", font_size)
        self.char_width = 0
        self.char_height = 0
        self._update_font_metrics()
        
        # SSH连接
        self.ssh_connection = None
        
        # 数据缓冲区
        self.receive_buffer = ""
        
        # 光标状态
        self.cursor_visible = True
        self.cursor_blink_timer = QTimer(self)
        self.cursor_blink_timer.timeout.connect(self._toggle_cursor)
        self.cursor_blink_timer.start(500)  # 500ms闪烁一次
        
        # NCURSES模式检测
        self._is_ncurses_mode = False
        self._refresh_count = 0
        self._last_refresh_time = 0
        
        # 滚动控制
        self._scroll_position = 0  # 滚动偏移(行)
        self._just_cleared_screen = False
        
        # 命令历史管理（本地历史）
        self.command_history = []  # 本地执行的命令历史
        self.history_index = -1
        self.current_input_buffer = ""  # 当前输入缓冲区（用于历史导航）
        
        # 提示符检测
        self.prompt_pattern = None  # 动态检测到的提示符模式
        self.last_prompt = ""  # 最后一次检测到的提示符
        self.prompt_detection_enabled = True
        
        # 颜色配置标志
        self._color_config_sent = False
        
        # 清屏状态跟踪
        self._clear_screen_pending = False  # 清屏操作是否正在进行
        self._clear_screen_mode = 2  # 默认清屏模式（整个屏幕）
        
        # 增量渲染优化
        self._needs_full_render = True  # 是否需要完整渲染
        self._render_region = None  # 渲染区域 (min_row, max_row)
        self._last_rendered_rows = set()  # 上次渲染的行
        
        # 渲染优化
        self._is_rendering = False
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._delayed_render)
        self._pending_render = False
        self._last_render_time = 0
        self._min_render_interval = 16  # 最小渲染间隔（60fps）
        self._batch_update_count = 0
        self._max_batch_updates = 5  # 最大批量更新次数
        
        # 窗口大小调整防抖
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._apply_resize)
        self._pending_resize = None  # 待处理的大小调整
        self._last_resize_time = 0
        self._resize_debounce_interval = 100  # 防抖间隔（毫秒）
        
        # 提示: 自动更新控件大小
        self.setMinimumSize(800, 600)
    
    def _update_font_metrics(self):
        """更新字体度量"""
        metrics = QFontMetrics(self.font)
        self.char_width = metrics.horizontalAdvance('M')  # 使用'M'作为平均宽度
        self.char_height = metrics.height()
    
    def focusInEvent(self, event):
        """获得焦点"""
        super().focusInEvent(event)
    
    def focusOutEvent(self, event):
        """失去焦点"""
        super().focusOutEvent(event)
    
    def event(self, event):
        """
        重写event方法,拦截Tab键的默认焦点切换行为
        确保Tab键传递给keyPressEvent处理
        """
        from PyQt6.QtCore import QEvent
        
        # 拦截KeyPress事件中的Tab键
        if event.type() == QEvent.Type.KeyPress:
            from PyQt6.QtGui import QKeyEvent
            if isinstance(event, QKeyEvent):
                if event.key() == Qt.Key.Key_Tab:
                    # 直接处理Tab键,阻止Qt的默认焦点切换
                    self.keyPressEvent(event)
                    return True  # 事件已处理
        
        return super().event(event)
    
    def set_font_size(self, size: int):
        """设置字体大小"""
        self.font_size = size
        self.font = QFont("Consolas", size)
        self._update_font_metrics()
        self.update()
    
    def connect_ssh(self, connection: SSHConnection):
        """连接SSH服务器"""
        self.ssh_connection = connection
        self.ssh_connection.data_received.connect(self._on_ssh_data)
        self.ssh_connection.connection_status.connect(self._on_connection_status)
        self.ssh_connection.error_occurred.connect(self._on_error)
    
    def set_ssh_connection(self, connection: SSHConnection):
        """
        设置SSH连接(兼容旧接口)
        
        Args:
            connection: SSHConnection对象
        """
        self.connect_ssh(connection)
        # 自动获得焦点,方便用户直接输入
        self.setFocus()
        # 延迟再次尝试获取焦点
        QTimer.singleShot(100, lambda: self.setFocus())
    
    def _on_connection_status(self, status: str):
        """连接状态变化"""
        self.connection_status.emit(status)
    
    def _on_error(self, error: str):
        """错误处理"""
        self.error_occurred.emit(error)
    
    def _on_ssh_data(self, data: str):
        """接收SSH数据"""
        self.receive_buffer += data
        
        # 解析ANSI序列
        segments = self.ansi_parser.parse(self.receive_buffer)
        
        if not segments and not self.ansi_parser.commands:
            # 没有完整的数据,等待更多
            return
        
        # 清空缓冲区
        self.receive_buffer = ""
        
        # 先处理控制命令(如清屏),再写入文本
        for cmd in self.ansi_parser.commands:
            if cmd.command_type == 'clear_screen':
                # 获取清屏模式
                mode = cmd.params.get('mode', 2)
                self._handle_clear_screen(mode)
            elif cmd.command_type == 'refresh_screen':
                # 刷新屏幕(光标归位),不清除内容
                self.screen.move_cursor(0, 0)
            elif cmd.command_type == 'cursor_move':
                self.screen.move_cursor(cmd.row, cmd.col)
            elif cmd.command_type == 'clear_line':
                # 处理清行命令(退格删除时会用到)
                mode = cmd.params.get('mode', 0)
                self.screen.clear_line(mode)
            elif cmd.command_type == 'cursor_up':
                n = cmd.params.get('n', 1)
                self.screen.move_cursor_up(n)
            elif cmd.command_type == 'cursor_down':
                n = cmd.params.get('n', 1)
                self.screen.move_cursor_down(n)
            elif cmd.command_type == 'cursor_forward':
                n = cmd.params.get('n', 1)
                self.screen.move_cursor_forward(n)
            elif cmd.command_type == 'cursor_back':
                n = cmd.params.get('n', 1)
                self.screen.move_cursor_back(n)
        
        # 写入文本数据
        for segment in segments:
            if segment.text:
                # 检测并记录提示符
                self._detect_and_record_prompt(segment.text)
                
                # 正常写入文本
                self.screen.write_text(segment.text, {
                    'fg': segment.fg_color or '#D4D4D4',
                    'bg': segment.bg_color or '#1E1E1E',
                    'bold': segment.bold,
                    'underline': segment.underline
                })
        
        # NCURSES模式检测
        if len(self.screen.modified_rows) > 0:
            self._detect_ncurses_mode(len(self.screen.modified_rows), 
                                     self.screen.cursor_row)
            
            # 提示符检测
            self._check_prompt()
            
            # 触发批量渲染
            self._schedule_render()
        
        # 重置ANSI解析器状态
        self.ansi_parser.reset_state()
    
    def _detect_ncurses_mode(self, modified_rows_count: int, cursor_row: int):
        """
        NCURSES模式检测 - 基于刷新频率
        
        原理:
        - NCURSES程序: 持续高频刷新(>2次/秒,每次>=10行)
        - 普通命令: 一次性输出,然后停止
        """
        current_time = time.time() * 1000  # ms
        
        if modified_rows_count >= 10:
            # 大屏刷新,检查刷新频率
            if current_time - self._last_refresh_time < 500:
                self._refresh_count += 1
            else:
                self._refresh_count = 1
            
            self._last_refresh_time = current_time
            
            # 500ms内>=2次大屏刷新 → NCURSES模式
            if self._refresh_count >= 2:
                if not self._is_ncurses_mode:
                    self._is_ncurses_mode = True
                    self.cursor_visible = False
        else:
            # 小屏刷新,重置计数
            self._refresh_count = 0
    
    def _check_prompt(self):
        """检测提示符"""
        last_line = self.screen.get_row_text(self.screen.cursor_row)
        stripped = last_line.rstrip()
        
        # 检测bash/zsh提示符(以#或$结尾)
        if stripped and (stripped.endswith('#') or stripped.endswith('$') or '#' in stripped):
            # 检测到提示符,退出NCURSES模式
            if self._is_ncurses_mode:
                self._is_ncurses_mode = False
                self.cursor_visible = True
                self._refresh_count = 0
    
    def _detect_and_record_prompt(self, text: str):
        """
        检测并记录提示符
        
        Args:
            text: 接收到的文本数据
        """
        if not self.prompt_detection_enabled:
            return
            
        import re
        
        # 常见的提示符模式
        prompt_patterns = [
            r'\[.*?@.*?\].*?[#$]',  # [user@host path]# 或 $
            r'.*?[#$]\s*$',          # 以#或$结尾的提示符
            r'[a-zA-Z0-9_]+@[a-zA-Z0-9_]+.*?[#$]',  # user@host# 格式
            r'[a-zA-Z0-9_]+%.*?$',   # zsh默认提示符
        ]
        
        # 按行检查
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 尝试匹配提示符模式
            for pattern in prompt_patterns:
                match = re.search(pattern, line)
                if match:
                    prompt = match.group(0).strip()
                    # 验证是否为有效的提示符
                    if len(prompt) < 100 and ('#' in prompt or '$' in prompt or '%' in prompt):
                        self.last_prompt = prompt
                        # 更新提示符模式
                        if not self.prompt_pattern or prompt != self.last_prompt:
                            self.prompt_pattern = pattern
                        return
    
    def _schedule_render(self):
        """调度渲染 - 实现批量更新和延迟渲染"""
        current_time = time.time() * 1000  # ms
        time_since_last_render = current_time - self._last_render_time
        
        # 如果距离上次渲染时间很短，累积更新
        if time_since_last_render < self._min_render_interval:
            self._batch_update_count += 1
            
            # 如果达到最大批量更新次数，立即渲染
            if self._batch_update_count >= self._max_batch_updates:
                self._perform_render()
                return
        
        # 否则延迟渲染
        self._pending_render = True
        self._render_timer.start(self._min_render_interval)
    
    def _delayed_render(self):
        """延迟渲染处理"""
        if self._pending_render:
            self._perform_render()
    
    def _perform_render(self):
        """执行实际的渲染"""
        current_time = time.time() * 1000
        
        # 检查是否满足最小渲染间隔
        if current_time - self._last_render_time >= self._min_render_interval:
            self.update()
            self._last_render_time = current_time
            self._batch_update_count = 0
            self._pending_render = False
    
    def _handle_clear_screen(self, mode: int = 2):
        """
        处理清屏命令 - 确保本地和服务器端状态同步
        
        Args:
            mode: 清屏模式
                0: 从光标到屏幕底部
                1: 从屏幕顶部到光标
                2: 整个屏幕(默认)
                3: 整个屏幕+清除滚动缓冲区
        """
        # 标记清屏操作正在进行
        self._clear_screen_pending = True
        self._clear_screen_mode = mode
        
        # 执行本地清屏
        self.screen.clear_screen(mode)
        
        # 重置相关状态
        self._just_cleared_screen = True
        self._is_ncurses_mode = False
        self._refresh_count = 0
        
        # 重置滚动位置
        if mode == 2 or mode == 3:
            self._scroll_position = 0
        
        # 标记清屏完成
        self._clear_screen_pending = False
        
        # 标记需要完整渲染
        self._needs_full_render = True
    
    def clear(self, mode: int = 2):
        """
        清屏 - 主动触发清屏（用户操作）
        
        Args:
            mode: 清屏模式，默认2（整个屏幕）
        """
        # 清除本地虚拟屏幕
        self.screen.clear_screen(mode)
        
        # 重置滚动位置
        if mode == 2 or mode == 3:
            self._scroll_position = 0
        
        # 向服务器发送清屏命令，确保服务器端状态同步
        if self.ssh_connection and self.ssh_connection.is_connected:
            # 根据模式发送不同的ANSI清屏序列
            if mode == 0:
                # 从光标到屏幕底部
                self.ssh_connection.send_data('\033[J')
            elif mode == 1:
                # 从屏幕顶部到光标
                self.ssh_connection.send_data('\033[1J')
            elif mode == 2:
                # 整个屏幕 + 光标归位
                self.ssh_connection.send_data('\033[2J\033[H')
            elif mode == 3:
                # 整个屏幕 + 清除滚动缓冲区 + 光标归位
                self.ssh_connection.send_data('\033[3J\033[2J\033[H')
        
        # 重置相关状态
        self._just_cleared_screen = True
        self._is_ncurses_mode = False
        self._refresh_count = 0
        
        # 标记需要完整渲染
        self._needs_full_render = True
        
        # 触发重绘
        self.update()
    
    def _toggle_cursor(self):
        """切换光标可见性(闪烁)"""
        if not self._is_ncurses_mode:
            self.cursor_renderer.toggle_visibility()
            self.update()
    
    def paintEvent(self, event):
        """自绘核心 - 直接绘制到QWidget（增量渲染优化版）"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # 计算可见区域
        visible_rows = self.height() // self.char_height
        start_row = self._scroll_position
        end_row = min(start_row + visible_rows, self.screen.rows)
        
        # 确定需要渲染的行
        is_full_render = self._needs_full_render  # 保存原始值
        if self._needs_full_render:
            # 完整渲染：渲染所有可见行
            rows_to_render = set(range(start_row, end_row))
            self._needs_full_render = False
            cols_to_render = None  # None表示渲染整行
        else:
            # 增量渲染：只渲染修改过的行和列
            modified_rows = self.screen.modified_rows.copy()
            # 只渲染可见区域内的修改行
            rows_to_render = {row for row in modified_rows if start_row <= row < end_row}
            
            # 如果没有修改的行，跳过渲染
            if not rows_to_render:
                painter.end()
                return
            
            # 获取修改的列范围
            cols_to_render = {row: self.screen.modified_cols.get(row) for row in rows_to_render}
        
        # 1. 绘制背景（仅完整渲染或修改行数较多时）
        if is_full_render or len(rows_to_render) > visible_rows // 2:
            painter.fillRect(self.rect(), QColor("#1E1E1E"))
        
        # 2. 绘制虚拟屏幕内容（增量渲染）
        painter.setFont(self.font)
        for row in sorted(rows_to_render):
            # 计算屏幕行在控件中的位置
            y = (row - start_row) * self.char_height
            
            # 如果是增量渲染，只清除需要重绘的区域
            if cols_to_render is not None:
                col_range = cols_to_render.get(row)
                if col_range:
                    # 只清除修改的列范围
                    min_col, max_col = col_range
                    x_start = min_col * self.char_width
                    width = (max_col - min_col + 1) * self.char_width
                    painter.fillRect(x_start, y, width, self.char_height, QColor("#1E1E1E"))
                else:
                    # 清除整行
                    painter.fillRect(0, y, self.width(), self.char_height, QColor("#1E1E1E"))
            
            # 确定要渲染的列范围
            if cols_to_render is not None:
                col_range = cols_to_render.get(row)
                if col_range:
                    start_col, end_col = col_range
                else:
                    start_col, end_col = 0, self.screen.cols - 1
            else:
                start_col, end_col = 0, self.screen.cols - 1
            
            for col in range(start_col, end_col + 1):
                cell = self.screen.cells[row][col]
                x = col * self.char_width
                
                # 绘制背景色
                if cell.bg_color != '#1E1E1E':
                    painter.fillRect(x, y, self.char_width, self.char_height, 
                                   QColor(cell.bg_color))
                
                # 绘制字符
                if cell.char != ' ':
                    painter.setPen(QColor(cell.fg_color))
                    if cell.bold:
                        font = QFont(self.font)
                        font.setBold(True)
                        painter.setFont(font)
                    else:
                        painter.setFont(self.font)
                    
                    painter.drawText(x, y, self.char_width, self.char_height,
                                   Qt.AlignmentFlag.AlignCenter, cell.char)
        
        # 3. 绘制光标(普通模式显示,NCURSES模式隐藏)
        if not self._is_ncurses_mode and self.cursor_renderer.cursor_visible:
            cursor_row = self.screen.cursor_row - start_row
            if 0 <= cursor_row < visible_rows:
                # 检查光标所在行是否需要渲染
                if self.screen.cursor_row in rows_to_render:
                    cell = self.screen.cells[self.screen.cursor_row][self.screen.cursor_col]
                    self.cursor_renderer.draw(
                        painter, 
                        cursor_row, 
                        self.screen.cursor_col,
                        self.char_width,
                        self.char_height,
                        cell.char,
                        cell.fg_color,
                        cell.bg_color
                    )
        
        # 记录渲染状态
        self._last_rendered_rows = rows_to_render.copy()
        painter.end()
    
    def keyPressEvent(self, event):
        """处理键盘输入"""
        if not self.ssh_connection or not self.ssh_connection.is_connected:
            return
        
        key = event.key()
        modifiers = event.modifiers()
        text = event.text()
        
        # Enter键 - 记录命令历史
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.ssh_connection.send_data('\r\n')
            # 记录当前输入到本地历史
            if self.current_input_buffer.strip():
                self.command_history.append(self.current_input_buffer.strip())
                # 限制历史记录数量
                if len(self.command_history) > 1000:
                    self.command_history = self.command_history[-500:]
                self.current_input_buffer = ""
                self.history_index = -1
            return
        
        # Backspace键
        if key == Qt.Key.Key_Backspace:
            self.ssh_connection.send_data('\x08 \x08')
            # 更新本地输入缓冲区
            if self.current_input_buffer:
                self.current_input_buffer = self.current_input_buffer[:-1]
            return
        
        # Delete键
        if key == Qt.Key.Key_Delete:
            self.ssh_connection.send_data('\x1b[3~')
            return
        
        # 方向键 - 始终发送到服务器
        if key == Qt.Key.Key_Left:
            self.ssh_connection.send_data('\x1b[D')
            return
        if key == Qt.Key.Key_Right:
            self.ssh_connection.send_data('\x1b[C')
            return
        if key == Qt.Key.Key_Up:
            # 发送上方向键序列到服务器，由服务器处理历史记录
            self.ssh_connection.send_data('\x1b[A')
            return
        if key == Qt.Key.Key_Down:
            # 发送下方向键序列到服务器，由服务器处理历史记录
            self.ssh_connection.send_data('\x1b[B')
            return
        
        # Home/End键
        if key == Qt.Key.Key_Home:
            self.ssh_connection.send_data('\x1b[H')
            return
        if key == Qt.Key.Key_End:
            self.ssh_connection.send_data('\x1b[F')
            return
        
        # Tab键
        if key == Qt.Key.Key_Tab:
            self.ssh_connection.send_data('\t')
            return
        
        # Ctrl+C
        if key == Qt.Key.Key_C and modifiers & Qt.KeyboardModifier.ControlModifier:
            cursor = self.cursor_renderer
            # 如果没有自定义渲染逻辑,直接发送
            self.ssh_connection.send_data('\x03')
            # 清空当前输入缓冲区
            self.current_input_buffer = ""
            return
        
        # Ctrl+D
        if key == Qt.Key.Key_D and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x04')
            return
        
        # Ctrl+L - 清屏
        if key == Qt.Key.Key_L and modifiers & Qt.KeyboardModifier.ControlModifier:
            # 发送清屏命令到服务器，服务器会返回清屏序列
            self.ssh_connection.send_data('\x0c')
            # 同时执行本地清屏，确保状态同步
            self.clear(mode=2)
            return
        
        # Ctrl+U - 删除整行
        if key == Qt.Key.Key_U and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x15')
            # 清空本地输入缓冲区
            self.current_input_buffer = ""
            return
        
        # Ctrl+K - 删除光标到行尾
        if key == Qt.Key.Key_K and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x0b')
            return
        
        # Ctrl+A - 行首
        if key == Qt.Key.Key_A and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x01')
            return
        
        # Ctrl+E - 行尾
        if key == Qt.Key.Key_E and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x05')
            return
        
        # Ctrl+V - 粘贴
        if key == Qt.Key.Key_V and modifiers & Qt.KeyboardModifier.ControlModifier:
            self._paste_from_clipboard()
            return
        
        # F1-F12功能键
        function_keys = {
            Qt.Key.Key_F1: '\x1bOP',
            Qt.Key.Key_F2: '\x1bOQ',
            Qt.Key.Key_F3: '\x1bOR',
            Qt.Key.Key_F4: '\x1bOS',
            Qt.Key.Key_F5: '\x1b[15~',
            Qt.Key.Key_F6: '\x1b[17~',
            Qt.Key.Key_F7: '\x1b[18~',
            Qt.Key.Key_F8: '\x1b[19~',
            Qt.Key.Key_F9: '\x1b[20~',
            Qt.Key.Key_F10: '\x1b[21~',
            Qt.Key.Key_F11: '\x1b[23~',
            Qt.Key.Key_F12: '\x1b[24~',
        }
        if key in function_keys:
            self.ssh_connection.send_data(function_keys[key])
            return
        
        # 可打印字符 - 更新输入缓冲区
        if text and text.isprintable():
            self.ssh_connection.send_data(text)
            # 更新本地输入缓冲区（用于历史导航）
            self.current_input_buffer += text
            return
    
    def _history_previous(self):
        """上一条历史命令"""
        if not self.command_history:
            return
        
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            cmd = self.command_history[-(self.history_index + 1)]
            # 清行并显示历史命令
            self._clear_current_line()
            self._display_text_on_screen(cmd)
            # 更新输入缓冲区
            self.current_input_buffer = cmd
    
    def _history_next(self):
        """下一条历史命令"""
        if self.history_index > 0:
            self.history_index -= 1
            cmd = self.command_history[-(self.history_index + 1)]
            self._clear_current_line()
            self._display_text_on_screen(cmd)
            # 更新输入缓冲区
            self.current_input_buffer = cmd
        elif self.history_index == 0:
            self.history_index = -1
            self._clear_current_line()
            # 恢复到当前输入
            if self.current_input_buffer:
                self._display_text_on_screen(self.current_input_buffer)
    
    def get_command_history(self) -> list:
        """
        获取命令历史列表
        
        Returns:
            命令历史列表
        """
        return self.command_history.copy()
    
    def clear_command_history(self):
        """清空命令历史"""
        self.command_history = []
        self.history_index = -1
        self.current_input_buffer = ""
    
    def _clear_current_line(self):
        """清空当前行内容"""
        # 清除当前行的内容
        for col in range(self.screen.cols):
            self.screen.cells[self.screen.cursor_row][col].reset()
        self.screen.modified_rows.add(self.screen.cursor_row)
        self.screen.cursor_col = 0
        self._render_timer.start(16)  # 触发重绘
    
    def _display_text_on_screen(self, text: str):
        """在屏幕上显示文本（不发送到服务器）"""
        # 将文本写入屏幕缓冲区
        attrs = {
            'fg': '#D4D4D4',  # 默认前景色
            'bg': '#1E1E1E',  # 默认背景色
            'bold': False,
            'underline': False
        }
        self.screen.write_text(text, attrs)
        self._render_timer.start(16)  # 触发重绘
    
    def _paste_from_clipboard(self):
        """从剪贴板粘贴"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text and self.ssh_connection:
            self.ssh_connection.send_data(text)
    
    def append_data(self, data: str):
        """
        追加数据到终端显示(兼容旧接口)
        
        Args:
            data: 要显示的文本数据
        """
        # 直接写入虚拟屏幕，使用默认属性
        attrs = {
            'fg': '#D4D4D4',  # 默认前景色
            'bg': '#1E1E1E',  # 默认背景色
            'bold': False,
            'underline': False
        }
        self.screen.write_text(data, attrs)
        self._render_timer.start(16)  # 触发重绘
    
    def resizeEvent(self, event):
        """窗口大小改变 - 使用防抖机制避免频繁调整"""
        super().resizeEvent(event)
        
        # 获取新的窗口大小
        new_width = self.width()
        new_height = self.height()
        
        # 计算新的行列数
        new_cols = new_width // self.char_width
        new_rows = new_height // self.char_height
        
        # 确保至少有最小行列
        new_cols = max(40, new_cols)
        new_rows = max(10, new_rows)
        
        # 如果大小没有变化，不处理
        if (self._pending_resize and 
            self._pending_resize['cols'] == new_cols and 
            self._pending_resize['rows'] == new_rows):
            return
        
        # 保存待处理的大小调整
        self._pending_resize = {'cols': new_cols, 'rows': new_rows}
        
        # 启动防抖定时器
        self._resize_timer.start(self._resize_debounce_interval)
    
    def _apply_resize(self):
        """应用窗口大小调整 - 实际执行终端大小调整"""
        if not self._pending_resize:
            return
        
        new_cols = self._pending_resize['cols']
        new_rows = self._pending_resize['rows']
        self._pending_resize = None
        
        # 如果大小没有变化，不处理
        if new_cols == self.screen.cols and new_rows == self.screen.rows:
            return
        
        # 更新字体度量（确保准确性）
        self._update_font_metrics()
        
        # 重新计算行列数
        new_cols = self.width() // self.char_width
        new_rows = self.height() // self.char_height
        new_cols = max(40, new_cols)
        new_rows = max(10, new_rows)
        
        # 调整虚拟屏幕大小
        old_rows = self.screen.rows
        old_cols = self.screen.cols
        self.screen.resize(new_rows, new_cols)
        
        # 通知SSH服务器新的终端大小
        if self.ssh_connection and self.ssh_connection.is_connected:
            self.ssh_connection.resize_terminal(new_cols, new_rows)
            logger.debug(f"终端大小已调整: {old_cols}x{old_rows} -> {new_cols}x{new_rows}")
        
        # 重置滚动位置（避免越界）
        if self._scroll_position >= new_rows:
            self._scroll_position = max(0, new_rows - 1)
        
        # 标记需要完整渲染
        self._needs_full_render = True
        
        # 触发重绘
        self.update()
    
    def contextMenuEvent(self, event):
        """右键菜单"""
        menu = QMenu(self)
        
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)
        
        paste_action = QAction("粘贴", self)
        paste_action.triggered.connect(self._paste_from_clipboard)
        menu.addAction(paste_action)
        
        menu.addSeparator()
        
        clear_action = QAction("清屏", self)
        clear_action.triggered.connect(lambda: self.clear(mode=2))
        menu.addAction(clear_action)
        
        menu.exec(event.globalPos())
    
    def copy(self):
        """复制选中的文本(暂未实现选择功能)"""
        from PyQt6.QtWidgets import QApplication
        # TODO: 实现文本选择功能
        pass
