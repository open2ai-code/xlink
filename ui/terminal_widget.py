"""
终端控件模块
基于QPlainTextEdit实现的自定义SSH终端
"""

import re
from PyQt6.QtWidgets import QPlainTextEdit, QMenu, QToolBar, QToolButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QTextCharFormat, QFont, QAction, QKeySequence
from core.terminal_buffer import ANSIParser
from core.ssh_manager import SSHConnection


class TerminalWidget(QPlainTextEdit):
    """自定义SSH终端控件"""
    
    def __init__(self, font_size: int = 13):
        super().__init__()
        
        # 安装事件过滤器,在事件到达之前就拦截
        self.installEventFilter(self)
        
        # 设置终端属性
        # 注意: 不能使用 setReadOnly(True),因为这会隐藏光标
        # 我们通过事件过滤器来阻止所有输入,同时保持光标可见
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Cascadia Code", font_size))
        
        # 设置光标可见
        self.setCursorWidth(8)  # 设置光标宽度(块状光标)
        
        # 完全禁用文本输入相关的功能
        self.setUndoRedoEnabled(False)  # 禁用撤销重做
        # 注意: 不使用 NoTextInteraction,否则会隐藏光标
        # 通过事件过滤器来阻止输入
        
        # 性能优化: 限制最大行数,防止内存溢出
        self.setMaximumBlockCount(10000)  # 最多保留10000行
        
        # 命令历史记录
        self.command_history = []
        self.history_index = -1
        self.current_input = ""
        
        # ANSI解析器
        self.ansi_parser = ANSIParser()
        
        # 数据缓冲区(用于处理被分割的ANSI序列)
        self.receive_buffer = ""
        
        # 是否忽略服务器回显(因为我们已经在本地显示了)
        self.ignore_echo = False
        
        # SSH连接
        self.ssh_connection = None
        
        # 输入位置标记(用户只能在此位置之后输入)
        self.input_position = 0
        
        # 标志: 是否需要设置 input_position
        self.need_set_input_position = True
        
        # 批量渲染优化
        self._pending_segments = []  # 待渲染的文本片段
        self._render_batch_size = 50  # 批量渲染阈值
        self._is_rendering = False  # 是否正在渲染
        self._render_timer = QTimer(self)  # 渲染定时器
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._flush_pending_segments)
        
        # 光标闪烁
        self._cursor_visible = True  # 光标可见性状态
        self._cursor_timer = QTimer(self)  # 光标闪烁定时器
        self._cursor_timer.timeout.connect(self._toggle_cursor)
        self._cursor_timer.start(1000)  # 1000ms (1秒) 闪烁一次
        
        # 设置右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # 创建快捷工具栏
        self._create_toolbar()
        
        # 连接数据接收信号
        # 注意: 这个会在外部连接具体的SSHConnection对象
    
    def _toggle_cursor(self):
        """切换光标可见性(闪烁效果)"""
        self._cursor_visible = not self._cursor_visible
        
        # 更新光标位置
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)
        
        # 注意: QPlainTextEdit的光标闪烁是自动的，这里主要是确保光标在正确位置
    
    def _process_backspace(self, text: str) -> str:
        """
        处理退格字符 - 简化版本,只处理\x08和空格
        真正的删除由ANSI解析器处理\x1b[K序列
        
        Args:
            text: 包含退格字符的文本
            
        Returns:
            处理后的文本
        """
        result = []
        i = 0
        while i < len(text):
            if text[i] == '\x08':  # 退格字符
                # 删除前一个字符(普通字符)
                if result and result[-1] not in '\033':
                    result.pop()
                # 跳过退格后的空格
                if i + 1 < len(text) and text[i + 1] == ' ':
                    i += 1
            else:
                result.append(text[i])
            i += 1
        return ''.join(result)
    
    def set_ssh_connection(self, connection: SSHConnection):
        """
        设置SSH连接
        
        Args:
            connection: SSHConnection对象
        """
        self.ssh_connection = connection
        self.ssh_connection.data_received.connect(self.append_data)
        
        # 设置标志,表示需要重新设置 input_position
        self.need_set_input_position = True
        
        # 自动获得焦点,方便用户直接输入
        self.setFocus()
    
    def _create_toolbar(self):
        """创建快捷工具栏"""
        # 注意: 工具栏作为终端控件的一部分,显示在顶部
        # 由于QPlainTextEdit不直接支持toolbar,我们使用父窗口的toolbar
        # 这里只定义actions,由父窗口添加到toolbar
        
        # 清屏动作
        self.clear_action = QAction("清屏", self)
        self.clear_action.setToolTip("清除终端输出 (Ctrl+L)")
        self.clear_action.setShortcut(QKeySequence("Ctrl+L"))
        self.clear_action.triggered.connect(self.clear_screen)
        
        # 重启连接动作
        self.restart_action = QAction("重启连接", self)
        self.restart_action.setToolTip("断开并重新连接SSH")
        self.restart_action.triggered.connect(self.restart_connection)
        
        # 复制全部动作
        self.copy_all_action = QAction("复制全部", self)
        self.copy_all_action.setToolTip("复制终端所有输出到剪贴板")
        self.copy_all_action.triggered.connect(self.copy_all_text)
        
        # 复制选中动作
        self.copy_selection_action = QAction("复制选中", self)
        self.copy_selection_action.setToolTip("复制选中的文本 (Ctrl+C)")
        self.copy_selection_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_selection_action.triggered.connect(self.copy)
    
    def _flush_pending_segments(self):
        """
        批量渲染待处理的文本片段
        禁用信号以避免频繁刷新,提升性能
        """
        print(f"[RENDER DEBUG] _flush_pending_segments 被调用, 片段数: {len(self._pending_segments)}")
        if not self._pending_segments or self._is_rendering:
            print(f"[RENDER DEBUG] 退出渲染: pending={len(self._pending_segments)}, is_rendering={self._is_rendering}")
            return
        
        self._is_rendering = True
        
        try:
            # 禁用文档信号,避免每次插入都触发重绘
            self.document().blockSignals(True)
            
            # 移动到文档末尾
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            print(f"[RENDER DEBUG] 渲染前文档字符数: {self.document().characterCount()}")
            
            # 批量插入所有片段
            for i, segment in enumerate(self._pending_segments):
                format = QTextCharFormat()
                
                # 设置前景色
                if segment.fg_color:
                    format.setForeground(QColor(segment.fg_color))
                else:
                    format.setForeground(QColor("#d4d4d4"))
                
                # 设置背景色
                if segment.bg_color:
                    format.setBackground(QColor(segment.bg_color))
                else:
                    format.setBackground(QColor("#1e1e1e"))
                
                # 设置字体粗细
                if segment.bold:
                    format.setFontWeight(QFont.Weight.Bold)
                else:
                    format.setFontWeight(QFont.Weight.Normal)
                
                # 设置下划线
                format.setFontUnderline(segment.underline)
                
                # 插入文本
                print(f"[RENDER DEBUG] 插入片段{i}: {repr(segment.text)}")
                cursor.insertText(segment.text, format)
            
            # 恢复文档信号
            self.document().blockSignals(False)
            print(f"[RENDER DEBUG] 渲染后文档字符数: {self.document().characterCount()}")
            
            # 检查是否是提示符
            if self._pending_segments:
                last_text = self._pending_segments[-1].text
                if '#' in last_text or '$' in last_text:
                    # 这是提示符,更新 input_position
                    self.input_position = self.document().characterCount() - 1
                    self.need_set_input_position = False
                    print(f"[RENDER DEBUG] 检测到提示符,更新 input_position 为: {self.input_position}")
            
            # 清空待渲染队列
            self._pending_segments.clear()
            
            # 手动触发一次重绘
            self.viewport().update()
            
            # 滚动到底部
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().maximum()
            )
            
            # 确保光标在文档末尾
            cursor = self.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
            
        finally:
            self._is_rendering = False
    
    def clear_screen(self):
        """清屏"""
        self.clear()
        self.input_position = 0
        self.need_set_input_position = True
    
    def restart_connection(self):
        """重启连接"""
        if self.ssh_connection:
            # 由父窗口处理重启逻辑
            self.restart_requested.emit()
    
    def copy_all_text(self):
        """复制所有文本"""
        all_text = self.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(all_text)
    
    # 信号: 请求重启连接
    restart_requested = pyqtSignal()
    
    def append_data(self, data: str):
        """
        追加SSH服务器返回的数据
        
        Args:
            data: 从服务器接收的文本数据
        """
        # 调试: 打印接收到的原始数据
        print(f"[APPEND DEBUG] ===== 接收到数据 =====")
        print(f"[APPEND DEBUG] 原始数据: {repr(data)}")
        print(f"[APPEND DEBUG] 接收前文档字符数: {self.document().characterCount()}")
        
        # 将新数据添加到缓冲区
        self.receive_buffer += data
        print(f"[DEBUG] 合并后缓冲区: {repr(self.receive_buffer)}")
        
        # 先移除所有ANSI删除序列 (\x1b[K, \x1b[0K, \x1b[1K, \x1b[2K 等)
        # 注意: 只删除 \x1b[...K (行删除),不删除 \x1b[...J (清屏)
        # 使用更宽松的正则,匹配所有 \x1b[...K 格式
        before_erase = self.receive_buffer
        self.receive_buffer = re.sub(r'\x1b\[[0-9;]*K', '', self.receive_buffer)
        if before_erase != self.receive_buffer:
            print(f"[DEBUG] 删除了行删除序列: {repr(before_erase)} -> {repr(self.receive_buffer)}")
        
        # 重要: 在过滤控制字符之前,先处理OSC序列(因为OSC序列以\x07结尾)
        # OSC序列格式: \x1b]<num>;<text>\x07 或 \x1b]<num>;<text>\x1b\
        osc_pattern = re.compile(r'\x1b\].*?(?:\x1b\\|\x07)')
        before_osc = self.receive_buffer
        
        # 调试: 检查OSC匹配
        osc_matches = osc_pattern.findall(before_osc)
        if osc_matches:
            print(f"[DEBUG] OSC匹配结果: {osc_matches}")
        
        self.receive_buffer = osc_pattern.sub('', self.receive_buffer)
        if before_osc != self.receive_buffer:
            print(f"[DEBUG] 删除了OSC序列: {repr(before_osc)}")
            print(f"[DEBUG] 删除后: {repr(self.receive_buffer)}")
        
        # 移除控制字符(\x07 响铃等),但保留:
        # - \x08 退格(单独处理)
        # - \x0a 换行(LF)
        # - \x0d 回车(CR)
        # - \x1b ESC(ANSI转义序列起始符)
        # 过滤范围: \x00-\x06, \x07, \x09, \x0b-\x0c, \x0e-\x1a, \x1c-\x1f
        # 注意: \x1b (ESC=27) 必须保留!
        self.receive_buffer = re.sub(r'[\x00-\x06\x07\x09\x0b\x0c\x0e-\x1a\x1c-\x1f]', '', self.receive_buffer)
        
        # 然后处理退格字符 \x08
        if '\x08' in self.receive_buffer:
            print(f"[DEBUG] 检测到退格字符,处理前: {repr(self.receive_buffer)}")
            
            # 计算有效退格次数
            # 注意: \x08 \x08 (退格+空格+退格) 是删除一个字符的完整操作
            # 整个 \x08 \x08 序列只算1次退格
            temp_buffer = self.receive_buffer
            backspace_count = 0
            i = 0
            print(f"[DEBUG] 开始计算退格次数, 缓冲区: {repr(temp_buffer)}")
            while i < len(temp_buffer):
                if temp_buffer[i] == '\x08':
                    backspace_count += 1
                    print(f"[DEBUG] 在位置 {i} 发现退格, 当前计数: {backspace_count}")
                    # 跳过 \x08 \x08 整个序列 (退格+空格+退格)
                    # 即跳过3个字符: \x08 + ' ' + \x08
                    if i + 2 < len(temp_buffer) and temp_buffer[i+1] == ' ' and temp_buffer[i+2] == '\x08':
                        print(f"[DEBUG] 跳过整个 \\x08 \\x08 序列 (位置 {i} 到 {i+2})")
                        i += 3
                        continue
                    # 如果只是 \x08 + ' ', 跳过2个字符
                    elif i + 1 < len(temp_buffer) and temp_buffer[i + 1] == ' ':
                        print(f"[DEBUG] 跳过位置 {i+1} 的空格")
                        i += 2
                        continue
                i += 1
            
            print(f"[DEBUG] 最终退格次数: {backspace_count}")
            
            # 在终端上删除相应数量的字符
            if backspace_count > 0:
                print(f"[DEBUG] 执行删除 {backspace_count} 个字符")
                print(f"[DEBUG] 删除前 input_position: {self.input_position}")
                print(f"[DEBUG] 删除前 need_set_input_position: {self.need_set_input_position}")
                
                cursor = self.textCursor()
                print(f"[DEBUG] 删除前光标位置: {cursor.position()}, input_position: {self.input_position}")
                cursor.movePosition(cursor.MoveOperation.End)
                print(f"[DEBUG] 移动到末尾后光标位置: {cursor.position()}")
                
                # 删除最后一个字符(重复backspace_count次)
                # 但不能删除到 input_position 之前
                deleted = 0
                for _ in range(backspace_count):
                    print(f"[DEBUG] 循环检查: cursor.position()={cursor.position()}, input_position={self.input_position}")
                    if cursor.position() > self.input_position:
                        cursor.deletePreviousChar()
                        deleted += 1
                        print(f"[DEBUG] 删除了1个字符, 已删除: {deleted}")
                    else:
                        print(f"[DEBUG] 到达input_position,停止删除")
                        break
                
                print(f"[DEBUG] 总共删除: {deleted} 个字符")
                print(f"[DEBUG] 删除后 input_position: {self.input_position} (不变)")
                self.setTextCursor(cursor)
            
            self.receive_buffer = self._process_backspace(self.receive_buffer)
            print(f"[DEBUG] 处理后: {repr(self.receive_buffer)}")
        
        # 检查缓冲区是否包含完整的ANSI序列
        # 如果缓冲区以ESC开头但没有完整的序列,等待更多数据
        if '\033' in self.receive_buffer:
            # 检查是否有未完成的ANSI序列
            esc_pos = self.receive_buffer.rfind('\033')
            after_esc = self.receive_buffer[esc_pos:]
            
            print(f"[DEBUG] 检查ANSI序列完整性: {repr(after_esc)}")
            
            # 如果ESC后面没有完整的序列(以字母结尾),则等待
            # 支持两种格式:
            # 1. \033[<params><letter> - 标准CSI序列
            # 2. \033[?<params><letter> - DEC私有序列
            has_complete_sequence = re.search(r'\033\[\?[0-9;]*[A-Za-z]', after_esc) or \
                                   re.search(r'\033\[[0-9;]*[A-Za-z]', after_esc)
            
            if not has_complete_sequence:
                print(f"[DEBUG] 检测到不完整的ANSI序列,等待更多数据")
                # 可能还有更多数据,暂时不处理
                # 但为了避免卡住,设置一个最大等待时间
                if len(self.receive_buffer) > 1000:
                    print(f"[DEBUG] 缓冲区过大,强制处理")
                    pass  # 缓冲区太大,强制处理
                else:
                    # 如果缓冲区包含普通文本(不仅仅是ESC序列),先处理
                    if len(self.receive_buffer) > len(after_esc):
                        print(f"[DEBUG] 缓冲区有普通文本,继续处理")
                        pass  # 有普通文本,继续处理
                    else:
                        print(f"[DEBUG] 缓冲区只有ESC序列,返回等待")
                        return
        
        # 处理缓冲区中的数据
        text_to_process = self.receive_buffer
        self.receive_buffer = ""
        
        print(f"[DEBUG] text_to_process: {repr(text_to_process)}, 长度: {len(text_to_process)}")
        print(f"[DEBUG] text_to_process的十六进制: {text_to_process.encode('utf-8').hex()}")
        
        # 解析ANSI序列
        segments = self.ansi_parser.parse(text_to_process)
        print(f"[DEBUG] ANSI解析完成,生成 {len(segments)} 个片段")
        for i, seg in enumerate(segments):
            print(f"[DEBUG] 片段{i}: {repr(seg.text)}, fg={seg.fg_color}, bg={seg.bg_color}, bold={seg.bold}")
        
        # 处理控制命令
        for cmd in self.ansi_parser.commands:
            if cmd.command_type == 'clear_screen':
                # 执行清屏
                print(f"[DEBUG] 执行清屏命令")
                self.clear()
                # 清屏后需要重新设置 input_position
                self.input_position = 0
                self.need_set_input_position = True
                # 不要return,继续处理剩余的文本(如提示符)
        
        # 如果有文本内容要显示(包括空格)
        if segments:
            print(f"[DEBUG] 准备渲染 {len(segments)} 个片段")
            # 批量渲染优化: 将片段加入队列
            self._pending_segments.extend(segments)
            
            # 如果累积了足够的片段或数据量大,立即渲染
            if len(self._pending_segments) >= self._render_batch_size or \
               sum(len(seg.text) for seg in self._pending_segments) > 1000:
                print(f"[DEBUG] 触发立即渲染")
                self._flush_pending_segments()
            else:
                # 否则延迟渲染,等待更多数据
                print(f"[DEBUG] 延迟渲染,启动定时器")
                self._render_timer.start(16)  # 16ms ≈ 60fps
            
            # 检查是否是提示符,如果是则更新 input_position
            # 注意: 每次收到提示符都要更新,因为位置会变化
            stripped = text_to_process.rstrip()
            if len(text_to_process) > 0 and (stripped.endswith('#') or stripped.endswith('$') or '#' in text_to_process):
                # 这是提示符,更新 input_position
                # 注意: 这里不能立即获取 characterCount，因为渲染可能是异步的
                # 需要在 _flush_pending_segments 中更新
                self.need_set_input_position = False
                print(f"[DEBUG] 检测到提示符,将在渲染后更新 input_position")
            elif self.need_set_input_position:
                # 需要设置但还没收到提示符
                print(f"[DEBUG] 跳过非提示符消息,不设置 input_position")
        
        # 滚动到底部
        self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        )
    
    def keyPressEvent(self, event):
        """
        处理键盘事件
        
        Args:
            event: 键盘事件
        """
        # 调试: 记录所有按键事件
        print(f"[KEY DEBUG] 按键: {event.key()}, 文本: {repr(event.text())}, ReadOnly: {self.isReadOnly()}")
        print(f"[KEY DEBUG] 文档当前字符数: {self.document().characterCount()}")
        
        # Enter键 - 发送命令
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._send_command()
            return
        
        # 上下箭头 - 命令历史
        if event.key() == Qt.Key.Key_Up:
            self._history_previous()
            return
        
        if event.key() == Qt.Key.Key_Down:
            self._history_next()
            return
        
        # Backspace键 - 只发送到服务器,让服务器处理删除和回显
        if event.key() == Qt.Key.Key_Backspace:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x08 \x08')  # 退格+空格+退格
            return
        
        # Delete键 - 删除光标后字符
        if event.key() == Qt.Key.Key_Delete:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[3~')  # ANSI Delete
            return
        
        # Ctrl+X - 取消操作(很多编辑器使用)
        if event.key() == Qt.Key.Key_X and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x18')  # Ctrl+X
            return
        
        # Ctrl+Y - 恢复删除的文本(yank)
        if event.key() == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x19')  # Ctrl+Y
            return
        
        # Ctrl+_ 或 Ctrl+/ - 撤销(Undo)
        if event.key() in (Qt.Key.Key_Slash, Qt.Key.Key_Minus) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1f')  # Ctrl+_
            return
        
        # Alt+键处理(Alt通常转换为\x1b+字符)
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            # Alt+F/B - 前进/后退一个单词
            if event.key() == Qt.Key.Key_F:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1bf')  # Alt+F
                return
            if event.key() == Qt.Key.Key_B:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1bb')  # Alt+B
                return
            # Alt+D - 删除光标到单词末尾
            if event.key() == Qt.Key.Key_D:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1bd')  # Alt+D
                return
            # Alt+Backspace - 删除光标前的单词
            if event.key() == Qt.Key.Key_Backspace:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b\x7f')  # Alt+Backspace
                return
            # 其他Alt+字母
            if event.key() >= Qt.Key.Key_A and event.key() <= Qt.Key.Key_Z:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    char = chr(event.key().value() - Qt.Key.Key_A.value() + ord('a'))
                    self.ssh_connection.send_data('\x1b' + char)  # Alt+letter
                return
        
        # Ctrl+方向键 - 按单词移动
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Left:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;5D')  # Ctrl+Left
                return
            if event.key() == Qt.Key.Key_Right:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;5C')  # Ctrl+Right
                return
            if event.key() == Qt.Key.Key_Up:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;5A')  # Ctrl+Up
                return
            if event.key() == Qt.Key.Key_Down:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;5B')  # Ctrl+Down
                return
            if event.key() == Qt.Key.Key_Delete:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[3;5~')  # Ctrl+Delete
                return
            if event.key() == Qt.Key.Key_Home:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;5H')  # Ctrl+Home
                return
            if event.key() == Qt.Key.Key_End:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;5F')  # Ctrl+End
                return
        
        # Ctrl+C - 复制 或 发送中断信号
        if event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            cursor = self.textCursor()
            if cursor.hasSelection():
                # 有选中文本,执行复制
                self.copy()
            else:
                # 无选中,发送Ctrl+C到服务器
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x03')
            return
        
        # Ctrl+V - 粘贴
        if event.key() == Qt.Key.Key_V and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.paste()
            return
        
        # Ctrl+L - 清屏
        if event.key() == Qt.Key.Key_L and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.clear()
            self.input_position = self.document().characterCount() - 1
            self.need_set_input_position = True
            return
        
        # Ctrl+D - 发送EOF(退出shell)
        if event.key() == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x04')  # EOT
            return
        
        # Ctrl+Z - 挂起进程
        if event.key() == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1a')  # SUSP
            return
        
        # Ctrl+U - 删除整行
        if event.key() == Qt.Key.Key_U and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x15')  # Ctrl+U
            return
        
        # Ctrl+K - 删除光标到行尾
        if event.key() == Qt.Key.Key_K and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x0b')  # Ctrl+K
            return
        
        # Ctrl+W - 删除前一个单词
        if event.key() == Qt.Key.Key_W and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x17')  # Ctrl+W
            return
        
        # Ctrl+A - 光标移到行首
        if event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x01')  # Ctrl+A
            return
        
        # Ctrl+E - 光标移到行尾
        if event.key() == Qt.Key.Key_E and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x05')  # Ctrl+E
            return
        
        # Ctrl+R - 搜索历史命令
        if event.key() == Qt.Key.Key_R and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x12')  # Ctrl+R
            return
        
        # Shift+方向键 - 选择模式(终端可能支持)
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if event.key() == Qt.Key.Key_Left:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;2D')  # Shift+Left
                return
            if event.key() == Qt.Key.Key_Right:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;2C')  # Shift+Right
                return
            if event.key() == Qt.Key.Key_Up:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;2A')  # Shift+Up
                return
            if event.key() == Qt.Key.Key_Down:
                if self.ssh_connection and self.ssh_connection.is_connected:
                    self.ssh_connection.send_data('\x1b[1;2B')  # Shift+Down
                return
        
        # Left/Right箭头 - 移动光标
        if event.key() == Qt.Key.Key_Left:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[D')  # ANSI左箭头
            return
        
        if event.key() == Qt.Key.Key_Right:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[C')  # ANSI右箭头
            return
        
        # Up/Down箭头 - 上下移动(如果不是命令历史)
        if event.key() == Qt.Key.Key_Up:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[A')  # ANSI上箭头
            return
        
        if event.key() == Qt.Key.Key_Down:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[B')  # ANSI下箭头
            return
        
        # Home键
        if event.key() == Qt.Key.Key_Home:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[H')  # ANSI Home
            return
        
        # End键
        if event.key() == Qt.Key.Key_End:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[F')  # ANSI End
            return
        
        # Page Up/Down
        if event.key() == Qt.Key.Key_PageUp:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[5~')  # ANSI PageUp
            return
        
        if event.key() == Qt.Key.Key_PageDown:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[6~')  # ANSI PageDown
            return
        
        # Insert键
        if event.key() == Qt.Key.Key_Insert:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[2~')  # ANSI Insert
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
        
        if event.key() in function_keys:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data(function_keys[event.key()])
            return
        
        # F13-F20功能键(一些终端支持)
        extended_function_keys = {
            Qt.Key.Key_F13: '\x1b[25~',
            Qt.Key.Key_F14: '\x1b[26~',
            Qt.Key.Key_F15: '\x1b[28~',
            Qt.Key.Key_F16: '\x1b[29~',
            Qt.Key.Key_F17: '\x1b[31~',
            Qt.Key.Key_F18: '\x1b[32~',
            Qt.Key.Key_F19: '\x1b[33~',
            Qt.Key.Key_F20: '\x1b[34~',
        }
        
        if event.key() in extended_function_keys:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data(extended_function_keys[event.key()])
            return
        
        # Escape键
        if event.key() == Qt.Key.Key_Escape:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b')  # ESC
            return
        
        # Tab键 - 命令补全,发送到服务器
        if event.key() == Qt.Key.Key_Tab:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\t')  # Tab字符
            return
        
        # Shift+Tab - 反向补全
        if event.key() == Qt.Key.Key_Tab and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data('\x1b[Z')  # Shift+Tab
            return
        
        # 空格键 - 特殊处理,因为event.text()可能为空
        if event.key() == Qt.Key.Key_Space:
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data(' ')
            return
        
        # 其他可打印字符 - 只发送到服务器,不本地显示
        if event.text() and event.text().isprintable():
            # 直接发送到服务器,服务器会回显
            if self.ssh_connection and self.ssh_connection.is_connected:
                self.ssh_connection.send_data(event.text())
            return
        
        # 其他按键 - 由于设置了ReadOnly,不会触发默认行为
    
    def eventFilter(self, obj, event):
        """
        事件过滤器 - 在事件到达控件之前就拦截
        
        Args:
            obj: 事件目标对象
            event: 事件对象
            
        Returns:
            bool: True表示事件已处理,不再传递; False表示继续传递
        """
        from PyQt6.QtCore import QEvent
        
        # 拦截所有可能导致文本变化的事件
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.InputMethod):
            # 只处理键盘按下事件
            if event.type() == QEvent.Type.KeyPress:
                print(f"[FILTER DEBUG] 拦截键盘事件: {event.key()}, 文本: {repr(event.text())}")
                print(f"[FILTER DEBUG] 拦截前文档字符数: {self.document().characterCount()}")
                
                # 直接调用 keyPressEvent 处理
                self.keyPressEvent(event)
            
            # 返回 True,阻止事件继续传递到 QPlainTextEdit
            return True
        
        # 其他事件交给父类处理
        return super().eventFilter(obj, event)
    
    def insertPlainText(self, text):
        """重写: 完全阻止插入纯文本"""
        # 完全禁用,任何本地插入都被阻止
        # 只有 append_data 方法才能显示文本
        # print(f"[BLOCK DEBUG] 阻止插入文本: {repr(text)}")
        pass
    
    def insertFromMimeData(self, source):
        """重写: 阻止从剪贴板插入文本"""
        # 完全禁用,不执行任何操作
        pass
    
    def inputMethodEvent(self, event):
        """重写: 阻止输入法输入"""
        # 完全禁用,不执行任何操作
        pass
    
    def focusInEvent(self, event):
        """重写: 焦点进入事件"""
        # 调用父类方法,但确保光标在正确位置
        super().focusInEvent(event)
        # 移动光标到文档末尾
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.setTextCursor(cursor)
    
    def mousePressEvent(self, event):
        """重写: 鼠标点击事件"""
        # 允许鼠标选择文本
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """重写: 鼠标双击事件"""
        # 允许选择单词
        super().mouseDoubleClickEvent(event)
    
    def _send_command(self):
        """发送用户输入的命令到SSH服务器"""
        if not self.ssh_connection or not self.ssh_connection.is_connected:
            return
        
        # 获取当前行输入(用于历史记录)
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.setPosition(self.input_position, cursor.MoveMode.KeepAnchor)
        command = cursor.selectedText()
        
        # 添加到历史记录
        if command.strip():
            self.command_history.append(command)
            # 限制历史记录数量
            if len(self.command_history) > 100:
                self.command_history.pop(0)
            self.history_index = len(self.command_history)
        
        # 发送回车到服务器
        self.ssh_connection.send_data('\n')
        
        # 更新输入位置
        self.input_position = self.document().characterCount() - 1
    
    def _history_previous(self):
        """显示上一条命令历史"""
        if not self.command_history or self.history_index <= 0:
            return
        
        self.history_index -= 1
        self._replace_current_command(self.command_history[self.history_index])
    
    def _history_next(self):
        """显示下一条命令历史"""
        if not self.command_history or self.history_index >= len(self.command_history) - 1:
            # 清空输入
            self._replace_current_command("")
            self.history_index = len(self.command_history)
            return
        
        self.history_index += 1
        self._replace_current_command(self.command_history[self.history_index])
    
    def _replace_current_command(self, text: str):
        """
        替换当前输入的命令
        
        Args:
            text: 新的命令文本
        """
        cursor = self.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.setPosition(self.input_position, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(text)
    
    def _show_context_menu(self, pos):
        """
        显示右键菜单
        
        Args:
            pos: 鼠标位置
        """
        menu = QMenu(self)
        
        # 复制动作
        copy_action = QAction("复制", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)
        
        # 粘贴动作
        paste_action = QAction("粘贴", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)
        
        menu.addSeparator()
        
        # 全选
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.selectAll)
        menu.addAction(select_all_action)
        
        # 清屏
        clear_action = QAction("清屏", self)
        clear_action.setShortcut("Ctrl+L")
        clear_action.triggered.connect(self.clear_terminal)
        menu.addAction(clear_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def clear_terminal(self):
        """清空终端显示"""
        self.clear()
        self.input_position = self.document().characterCount() - 1
    
    def set_font_size(self, size: int):
        """
        设置字体大小
        
        Args:
            size: 字体大小
        """
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
    
    def focusInEvent(self, event):
        """获得焦点事件"""
        super().focusInEvent(event)
        # 确保光标在输入位置
        cursor = self.textCursor()
        if cursor.position() < self.input_position:
            cursor.movePosition(cursor.MoveOperation.End)
            self.setTextCursor(cursor)
