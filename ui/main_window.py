"""
主窗口模块
整合所有UI组件,提供主界面布局
"""

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QStatusBar, QMenuBar,
    QToolBar, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QFont
from ui.theme import ThemeManager
from ui.session_panel import SessionPanel
from ui.tab_manager import TabManager
from core.session_manager import SessionManager


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 会话管理器
        self.session_manager = SessionManager()
        
        # 初始化UI
        self._init_ui()
        self._create_menu()
        self._create_toolbar()
        self._create_statusbar()
        
        # 恢复窗口设置
        self._restore_settings()
        
        # 应用主题
        self._apply_theme()
    
    def _init_ui(self):
        """初始化UI布局"""
        self.setWindowTitle("XLink - SSH客户端")
        self.setMinimumSize(900, 600)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧会话面板
        self.session_panel = SessionPanel(self.session_manager, self)
        self.session_panel.setMinimumWidth(200)
        self.session_panel.setMaximumWidth(400)
        
        # 右侧标签管理器
        self.tab_manager = TabManager(
            font_size=self.session_manager.get_font_size()
        )
        
        # 添加到分割器
        splitter.addWidget(self.session_panel)
        splitter.addWidget(self.tab_manager)
        
        # 设置初始分割比例 (1:3)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        # 设置中央控件
        self.setCentralWidget(splitter)
        
        # 连接信号
        self.session_panel.session_connect.connect(self._connect_session)
        self.tab_manager.status_message.connect(self._show_status_message)
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        new_session_action = QAction("新建会话(&N)", self)
        new_session_action.setShortcut("Ctrl+N")
        new_session_action.triggered.connect(self._new_session)
        file_menu.addAction(new_session_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        
        refresh_action = QAction("刷新会话列表(&R)", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.session_panel.refresh)
        edit_menu.addAction(refresh_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        zoom_in_action = QAction("放大字体(&+)", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self._zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小字体(&-)", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self._zoom_out)
        view_menu.addAction(zoom_out_action)
        
        view_menu.addSeparator()
        
        # 主题切换
        theme_menu = view_menu.addMenu("主题")
        
        light_theme_action = QAction("浅色主题", self)
        light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction("深色主题", self)
        dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 新建会话
        new_action = QAction("📝 新建", self)
        new_action.setToolTip("新建会话")
        new_action.triggered.connect(self._new_session)
        toolbar.addAction(new_action)
        
        toolbar.addSeparator()
        
        # 刷新
        refresh_action = QAction("🔄 刷新", self)
        refresh_action.setToolTip("刷新会话列表")
        refresh_action.triggered.connect(self.session_panel.refresh)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # 放大字体
        zoom_in_action = QAction("🔍+ 放大", self)
        zoom_in_action.setToolTip("放大字体")
        zoom_in_action.triggered.connect(self._zoom_in)
        toolbar.addAction(zoom_in_action)
        
        # 缩小字体
        zoom_out_action = QAction("🔍- 缩小", self)
        zoom_out_action.setToolTip("缩小字体")
        zoom_out_action.triggered.connect(self._zoom_out)
        toolbar.addAction(zoom_out_action)
        
        toolbar.addSeparator()
        
        # 主题切换
        theme_action = QAction("🎨 切换主题", self)
        theme_action.setToolTip("切换深浅主题")
        theme_action.triggered.connect(self._toggle_theme)
        toolbar.addAction(theme_action)
    
    def _create_statusbar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
    
    def _restore_settings(self):
        """恢复窗口设置"""
        width, height = self.session_manager.get_window_size()
        self.resize(width, height)
    
    def _save_settings(self):
        """保存窗口设置"""
        self.session_manager.set_window_size(
            self.width(),
            self.height()
        )
    
    def _apply_theme(self):
        """应用主题"""
        theme = self.session_manager.get_theme()
        qss = ThemeManager.get_theme(theme)
        self.setStyleSheet(qss)
    
    def _set_theme(self, theme: str):
        """
        设置主题
        
        Args:
            theme: 主题名称 (light/dark)
        """
        self.session_manager.set_theme(theme)
        self._apply_theme()
        self._show_status_message(f"已切换到{theme}主题")
    
    def _toggle_theme(self):
        """切换主题"""
        current_theme = self.session_manager.get_theme()
        new_theme = "dark" if current_theme == "light" else "light"
        self._set_theme(new_theme)
    
    def _connect_session(self, session_data):
        """
        连接会话
        
        Args:
            session_data: 会话数据
        """
        self.tab_manager.create_new_tab(session_data)
    
    def _new_session(self):
        """新建会话(通过会话面板处理)"""
        self.session_panel._new_session()
    
    def _zoom_in(self):
        """放大字体"""
        current_size = self.session_manager.get_font_size()
        new_size = min(current_size + 1, 24)
        self.session_manager.set_font_size(new_size)
        self.tab_manager.set_font_size(new_size)
        self._show_status_message(f"字体大小: {new_size}")
    
    def _zoom_out(self):
        """缩小字体"""
        current_size = self.session_manager.get_font_size()
        new_size = max(current_size - 1, 8)
        self.session_manager.set_font_size(new_size)
        self.tab_manager.set_font_size(new_size)
        self._show_status_message(f"字体大小: {new_size}")
    
    def _show_status_message(self, message: str):
        """
        显示状态栏消息
        
        Args:
            message: 消息文本
        """
        self.status_label.setText(message)
        self.status_bar.showMessage(message, 3000)  # 3秒后自动清除
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 XLink",
            "<h2>XLink SSH客户端</h2>"
            "<p>版本: 1.0.0</p>"
            "<p>轻量、稳定、高颜值的SSH远程连接工具</p>"
            "<p>技术栈: Python 3.10+ | PyQt6 | paramiko</p>"
            "<p>&copy; 2026 XLink Team</p>"
        )
    
    def closeEvent(self, event):
        """
        窗口关闭事件
        
        Args:
            event: 关闭事件
        """
        # 保存设置
        self._save_settings()
        
        # 关闭所有SSH连接
        self.tab_manager.close_all_connections()
        
        # 确认退出
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出XLink吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
