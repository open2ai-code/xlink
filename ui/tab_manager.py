"""
标签页管理模块
管理多终端标签页
"""

from PyQt6.QtWidgets import QTabWidget, QMenu
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from ui.terminal_widget import TerminalWidget
from core.ssh_manager import SSHConnection


class TabManager(QTabWidget):
    """多标签页管理器"""
    
    # 信号定义
    status_message = pyqtSignal(str)  # 状态栏消息
    
    def __init__(self, font_size: int = 13):
        super().__init__()
        
        self.font_size = font_size
        
        # 设置标签页属性
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setTabPosition(QTabWidget.TabPosition.North)
        
        # 连接标签关闭信号
        self.tabCloseRequested.connect(self._close_tab)
        
        # 设置右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # 存储每个标签页的SSH连接
        self.connections = {}
    
    def create_new_tab(self, session_data: dict):
        """
        创建新的终端标签页并连接
        
        Args:
            session_data: 会话数据字典
        """
        # 创建终端控件
        terminal = TerminalWidget(self.font_size)
        
        # 创建SSH连接
        connection = SSHConnection()
        
        # 连接信号
        connection.connection_status.connect(
            lambda status: self._on_connection_status(status, terminal)
        )
        connection.error_occurred.connect(
            lambda error: self._on_error(error, terminal)
        )
        
        # 保存连接引用
        self.connections[terminal] = connection
        
        # 添加标签页
        tab_name = session_data.get("name", "未命名")
        tab_index = self.addTab(terminal, f"🖥️ {tab_name}")
        self.setCurrentIndex(tab_index)
        
        # 设置终端的SSH连接
        terminal.set_ssh_connection(connection)
        
        # 发起连接
        connection.connect(
            host=session_data.get("host", ""),
            port=session_data.get("port", 22),
            username=session_data.get("username", ""),
            password=session_data.get("password", ""),
            key_file=session_data.get("key_file", ""),
            timeout=session_data.get("timeout", 30)
        )
        
        self.status_message.emit(f"正在连接到 {session_data.get('host')}...")
    
    def _on_connection_status(self, status: str, terminal: TerminalWidget):
        """
        连接状态变化
        
        Args:
            status: 状态字符串 (connected/disconnected/error)
            terminal: 对应的终端控件
        """
        tab_index = self.indexOf(terminal)
        if tab_index == -1:
            return
        
        if status == "connected":
            self.setTabText(tab_index, self.tabText(tab_index).replace("⏳", "✅"))
            self.status_message.emit("连接成功")
        elif status == "disconnected":
            self.setTabText(tab_index, self.tabText(tab_index).replace("⏳", "❌"))
            self.status_message.emit("连接已断开")
        elif status == "error":
            self.setTabText(tab_index, self.tabText(tab_index).replace("⏳", "⚠️"))
    
    def _on_error(self, error: str, terminal: TerminalWidget):
        """
        错误处理
        
        Args:
            error: 错误信息
            terminal: 对应的终端控件
        """
        self.status_message.emit(error)
        # 在终端中显示错误
        terminal.append_data(f"\n\r[错误] {error}\n\r")
    
    def _close_tab(self, index):
        """
        关闭标签页
        
        Args:
            index: 标签页索引
        """
        widget = self.widget(index)
        
        # 清理SSH连接
        if widget in self.connections:
            connection = self.connections[widget]
            connection.disconnect()
            del self.connections[widget]
        
        # 移除标签页
        self.removeTab(index)
        
        self.status_message.emit(f"已关闭标签页")
    
    def _show_context_menu(self, pos):
        """
        显示标签页右键菜单
        
        Args:
            pos: 鼠标位置
        """
        menu = QMenu(self)
        
        # 当前标签页索引
        tab_index = self.tabBar().tabAt(pos)
        
        if tab_index == -1:
            return
        
        # 关闭当前标签
        close_action = QAction("关闭当前标签", self)
        close_action.triggered.connect(lambda: self._close_tab(tab_index))
        menu.addAction(close_action)
        
        # 关闭其他标签
        close_other_action = QAction("关闭其他标签", self)
        close_other_action.triggered.connect(lambda: self._close_other_tabs(tab_index))
        menu.addAction(close_other_action)
        
        # 关闭所有标签
        close_all_action = QAction("关闭所有标签", self)
        close_all_action.triggered.connect(self._close_all_tabs)
        menu.addAction(close_all_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _close_other_tabs(self, keep_index: int):
        """
        关闭其他标签页
        
        Args:
            keep_index: 保留的标签页索引
        """
        # 从后往前关闭,避免索引变化
        for i in range(self.count() - 1, -1, -1):
            if i != keep_index:
                self._close_tab(i)
    
    def _close_all_tabs(self):
        """关闭所有标签页"""
        while self.count() > 0:
            self._close_tab(0)
    
    def get_current_terminal(self) -> TerminalWidget:
        """获取当前终端控件"""
        return self.currentWidget()
    
    def set_font_size(self, size: int):
        """
        设置所有终端的字体大小
        
        Args:
            size: 字体大小
        """
        self.font_size = size
        for i in range(self.count()):
            terminal = self.widget(i)
            if isinstance(terminal, TerminalWidget):
                terminal.set_font_size(size)
    
    def close_all_connections(self):
        """关闭所有SSH连接"""
        for connection in self.connections.values():
            connection.disconnect()
        self.connections.clear()
