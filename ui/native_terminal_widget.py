# -*- coding: utf-8 -*-
"""
自绘终端控件模块
完全自主渲染的终端控件,不依赖QPlainTextEdit
提供专业级的终端仿真体验
"""

import time
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics, QAction
from core.virtual_screen import VirtualScreen
from core.terminal_buffer import ANSIParser
from core.ssh_manager import SSHConnection
from ui.cursor_renderer import CursorRenderer


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
        
        # 命令历史
        self.command_history = []
        self.history_index = -1
        
        # 颜色配置标志
        self._color_config_sent = False
        
        # 渲染优化
        self._is_rendering = False
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self.update)
        
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
        # 调试:打印接收到的原始数据
        print(f"[SSH Data] 接收到 {len(data)} 字节, repr: {repr(data[:200])}")
        
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
                self.screen.clear_screen()
                self._just_cleared_screen = True
                self._is_ncurses_mode = False
                self._refresh_count = 0
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
        
        # 去重:检测重复的提示符 - 智能版本
        for segment in segments:
            if segment.text:
                # 检查是否是纯提示符(可能带\r\n前缀)
                stripped = segment.text.strip()
                if stripped.count('[root@') > 1 and len(stripped) < 100:
                    # 这是重复的提示符,只保留第一个
                    first_prompt = segment.text.find('[root@')
                    second_prompt = segment.text.find('[root@', first_prompt + 1)
                    
                    # 找到第二个提示符之前的换行符
                    first_prompt_end = second_prompt
                    for i in range(second_prompt - 1, first_prompt, -1):
                        if segment.text[i] == '\n':
                            end_pos = i
                            if i > 0 and segment.text[i-1] == '\r':
                                end_pos = i - 1
                            first_prompt_end = end_pos
                            break
                    
                    text_to_write = segment.text[:first_prompt_end]
                    self.screen.write_text(text_to_write, {
                        'fg': segment.fg_color or '#D4D4D4',
                        'bg': segment.bg_color or '#1E1E1E',
                        'bold': segment.bold,
                        'underline': segment.underline
                    })
                    continue
                
                # 正常写入
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
            
            # 触发重绘
            self._render_timer.start(16)  # 60fps
        
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
    
    def _toggle_cursor(self):
        """切换光标可见性(闪烁)"""
        if not self._is_ncurses_mode:
            self.cursor_renderer.toggle_visibility()
            self.update()
    
    def paintEvent(self, event):
        """自绘核心 - 直接绘制到QWidget"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # 1. 绘制背景
        painter.fillRect(self.rect(), QColor("#1E1E1E"))
        
        # 2. 计算可见区域
        visible_rows = self.height() // self.char_height
        start_row = self._scroll_position
        end_row = min(start_row + visible_rows, self.screen.rows)
        
        # 3. 绘制虚拟屏幕内容
        painter.setFont(self.font)
        for row in range(start_row, end_row):
            # 计算屏幕行在控件中的位置
            screen_row = row  # 直接使用虚拟屏幕的行号
            y = (screen_row - start_row) * self.char_height  # 计算在控件中的Y坐标
            
            for col in range(self.screen.cols):
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
        
        # 4. 绘制光标(普通模式显示,NCURSES模式隐藏)
        if not self._is_ncurses_mode and self.cursor_renderer.cursor_visible:
            cursor_row = self.screen.cursor_row - start_row
            if 0 <= cursor_row < visible_rows:
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
    
    def keyPressEvent(self, event):
        """处理键盘输入"""
        print(f"[KeyPress] key={event.key()}, text={repr(event.text())}")
        
        if not self.ssh_connection or not self.ssh_connection.is_connected:
            print(f"[KeyPress] 跳过: 未连接")
            return
        
        key = event.key()
        modifiers = event.modifiers()
        text = event.text()
        
        # Enter键
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.ssh_connection.send_data('\r\n')
            return
        
        # Backspace键
        if key == Qt.Key.Key_Backspace:
            self.ssh_connection.send_data('\x08 \x08')
            return
        
        # Delete键
        if key == Qt.Key.Key_Delete:
            self.ssh_connection.send_data('\x1b[3~')
            return
        
        # 方向键
        if key == Qt.Key.Key_Left:
            self.ssh_connection.send_data('\x1b[D')
            return
        if key == Qt.Key.Key_Right:
            self.ssh_connection.send_data('\x1b[C')
            return
        if key == Qt.Key.Key_Up:
            # 优先处理命令历史
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self._history_previous()
                return
            self.ssh_connection.send_data('\x1b[A')
            return
        if key == Qt.Key.Key_Down:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self._history_next()
                return
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
            print(f"[KeyPress] 发送Tab键到服务器")
            self.ssh_connection.send_data('\t')
            return
        
        # Ctrl+C
        if key == Qt.Key.Key_C and modifiers & Qt.KeyboardModifier.ControlModifier:
            cursor = self.cursor_renderer
            # 如果没有自定义渲染逻辑,直接发送
            self.ssh_connection.send_data('\x03')
            return
        
        # Ctrl+D
        if key == Qt.Key.Key_D and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x04')
            return
        
        # Ctrl+L - 清屏
        if key == Qt.Key.Key_L and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x0c')
            return
        
        # Ctrl+U - 删除整行
        if key == Qt.Key.Key_U and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.ssh_connection.send_data('\x15')
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
        
        # 可打印字符
        if text and text.isprintable():
            self.ssh_connection.send_data(text)
            return
    
    def _history_previous(self):
        """上一条历史命令"""
        if not self.command_history:
            return
        
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            cmd = self.command_history[-(self.history_index + 1)]
            # TODO: 发送到服务器并显示
            self.ssh_connection.send_data('\x15')  # Ctrl+U 清行
            self.ssh_connection.send_data(cmd)
    
    def _history_next(self):
        """下一条历史命令"""
        if self.history_index > 0:
            self.history_index -= 1
            cmd = self.command_history[-(self.history_index + 1)]
            self.ssh_connection.send_data('\x15')  # Ctrl+U 清行
            self.ssh_connection.send_data(cmd)
        elif self.history_index == 0:
            self.history_index = -1
            self.ssh_connection.send_data('\x15')  # 清空
    
    def _paste_from_clipboard(self):
        """从剪贴板粘贴"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text and self.ssh_connection:
            self.ssh_connection.send_data(text)
    
    def clear(self):
        """清屏"""
        self.screen.clear_screen()
        self._scroll_position = 0
        self.update()
    
    def resizeEvent(self, event):
        """窗口大小改变"""
        super().resizeEvent(event)
        # 重新计算可见区域
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
        clear_action.triggered.connect(self.clear)
        menu.addAction(clear_action)
        
        menu.exec(event.globalPos())
    
    def copy(self):
        """复制选中的文本(暂未实现选择功能)"""
        from PyQt6.QtWidgets import QApplication
        # TODO: 实现文本选择功能
        pass
