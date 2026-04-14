"""
标签页管理模块
管理多终端标签页
"""

from PyQt6.QtWidgets import QTabWidget, QMenu, QSplitter, QFrame, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from ui.terminal_widget import TerminalWidget
from ui.sftp_panel import SftpPanel
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
        print(f"[TAB DEBUG] 创建新标签页: {session_data.get('name')}")
        
        # 创建容器框架
        container = QFrame()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 创建水平分割器(终端 + SFTP)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 创建终端控件
        terminal = TerminalWidget(self.font_size)
        terminal.setMinimumWidth(400)
        
        # 创建SFTP面板
        sftp_panel = SftpPanel()
        sftp_panel.setMinimumWidth(300)
        print(f"[TAB DEBUG] SFTP面板已创建: {sftp_panel}")
        
        # 添加到分割器
        splitter.addWidget(terminal)
        splitter.addWidget(sftp_panel)
        
        # 设置初始比例 (2:1)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        container_layout.addWidget(splitter)
        
        # 创建SSH连接
        connection = SSHConnection()
        
        # 连接信号 - 添加调试
        def on_status(status):
            print(f"[TAB DEBUG] 连接状态: {status}")
            print(f"[TAB DEBUG] terminal: {terminal}")
            print(f"[TAB DEBUG] sftp_panel: {sftp_panel}")
            self._on_connection_status(status, terminal, sftp_panel)
        
        connection.connection_status.connect(on_status)
        connection.error_occurred.connect(
            lambda error: self._on_error(error, terminal)
        )
        
        # 保存连接引用
        self.connections[terminal] = connection
        self.connections[sftp_panel] = connection  # SFTP也需要连接引用
        
        # 添加标签页
        tab_name = session_data.get("name", "未命名")
        tab_index = self.addTab(container, f"🖥️ {tab_name}")
        self.setCurrentIndex(tab_index)
        
        # 设置终端的SSH连接
        terminal.set_ssh_connection(connection)
        
        # 设置SFTP面板的连接(稍后连接成功后设置)
        sftp_panel.ssh_connection = connection
        print(f"[TAB DEBUG] sftp_panel.ssh_connection 已设置: {sftp_panel.ssh_connection}")
        
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
    
    def _on_connection_status(self, status: str, terminal: TerminalWidget, sftp_panel: SftpPanel = None):
        """
        连接状态变化
            
        Args:
            status: 状态字符串 (connected/disconnected/error)
            terminal: 对应的终端控件
            sftp_panel: 对应的SFTP面板
        """
        print(f"[SFTP STATUS DEBUG] _on_connection_status 被调用")
        print(f"[SFTP STATUS DEBUG] status: {status}")
        print(f"[SFTP STATUS DEBUG] sftp_panel: {sftp_panel}")
        print(f"[SFTP STATUS DEBUG] sftp_panel is None: {sftp_panel is None}")
        
        if sftp_panel:
            print(f"[SFTP STATUS DEBUG] hasattr(sftp_panel, 'ssh_connection'): {hasattr(sftp_panel, 'ssh_connection')}")
            if hasattr(sftp_panel, 'ssh_connection'):
                print(f"[SFTP STATUS DEBUG] sftp_panel.ssh_connection: {sftp_panel.ssh_connection}")
        
        # 找到容器 - 修复: terminal.parent() 是 splitter, 需要再找一层
        container = terminal.parent()  # 这是 splitter
        if container:
            container = container.parent()  # 这才是 container (QFrame)
        
        print(f"[SFTP STATUS DEBUG] terminal.parent(): {terminal.parent()}")
        print(f"[SFTP STATUS DEBUG] container: {container}")
        
        tab_index = self.indexOf(container)
        print(f"[SFTP STATUS DEBUG] tab_index: {tab_index}")
        
        if tab_index == -1:
            print(f"[SFTP STATUS DEBUG] tab_index == -1, 返回")
            return
            
        if status == "connected":
            self.setTabText(tab_index, self.tabText(tab_index).replace("⏳", "✅"))
            self.status_message.emit("连接成功")
            
            # 连接成功后,初始化SFTP面板
            if sftp_panel and hasattr(sftp_panel, 'ssh_connection'):
                try:
                    print(f"[SFTP DEBUG] 开始初始化SFTP面板")
                    print(f"[SFTP DEBUG] sftp_panel: {sftp_panel}")
                    print(f"[SFTP DEBUG] ssh_connection: {sftp_panel.ssh_connection}")
                    print(f"[SFTP DEBUG] ssh_connection.is_connected: {sftp_panel.ssh_connection.is_connected if sftp_panel.ssh_connection else 'None'}")
                    
                    result = sftp_panel.connect_session(sftp_panel.ssh_connection)
                    print(f"[SFTP DEBUG] connect_session 返回结果: {result}")
                    
                    if result:
                        self.status_message.emit("SFTP已就绪")
                    else:
                        self.status_message.emit("SFTP初始化失败")
                except Exception as e:
                    print(f"[SFTP DEBUG] SFTP初始化异常: {e}")
                    import traceback
                    traceback.print_exc()
                    self.status_message.emit(f"SFTP初始化失败: {str(e)}")
        elif status == "disconnected":
            self.setTabText(tab_index, self.tabText(tab_index).replace("⏳", "❌"))
            self.status_message.emit("连接已断开")
        elif status == "error":
            self.setTabText(tab_index, self.tabText(tab_index).replace("⏳", "️"))
    
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
        container = self.widget(index)
        
        # 清理SSH连接
        # 遍历所有连接,找到属于这个容器的
        widgets_to_remove = []
        for widget, connection in list(self.connections.items()):
            # 检查widget是否在这个容器中
            if widget.parent() == container or widget.parent().parent() == container:
                connection.disconnect()
                widgets_to_remove.append(widget)
        
        for widget in widgets_to_remove:
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
        container = self.currentWidget()
        if container:
            # 查找容器中的TerminalWidget
            for child in container.findChildren(TerminalWidget):
                return child
        return None
    
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
