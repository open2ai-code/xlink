"""
会话列表面板模块
左侧会话列表树形控件
"""

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from ui.dialogs import SessionDialog


class SessionPanel(QTreeWidget):
    """会话列表面板"""
    
    # 信号定义
    session_connect = pyqtSignal(dict)  # 连接会话信号,发送会话数据
    session_edit = pyqtSignal(dict)  # 编辑会话信号
    session_delete = pyqtSignal(str)  # 删除会话信号,发送会话ID
    
    def __init__(self, session_manager, parent=None):
        """
        初始化会话面板
        
        Args:
            session_manager: SessionManager实例
            parent: 父窗口
        """
        super().__init__(parent)
        self.session_manager = session_manager
        
        # 设置树形控件
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # 加载会话数据
        self._load_sessions()
    
    def _load_sessions(self):
        """加载会话数据到树形控件"""
        self.clear()
        
        # 按分组组织会话
        groups = self.session_manager.get_groups()
        
        for group in groups:
            # 创建分组节点
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, f"{group}")
            group_item.setExpanded(True)
            
            # 设置分组图标(使用Unicode)
            group_item.setText(0, f"📁 {group}")
            
            # 获取该分组下的会话
            sessions = self.session_manager.get_sessions_by_group(group)
            
            for session in sessions:
                # 创建会话节点
                session_item = QTreeWidgetItem(group_item)
                session_item.setText(0, f"🖥️ {session['name']}")
                session_item.setData(0, Qt.ItemDataRole.UserRole, session)
                
                # 设置工具提示
                tooltip = f"{session['host']}:{session['port']}\n{session['username']}"
                session_item.setToolTip(0, tooltip)
    
    def _on_item_double_clicked(self, item, column):
        """
        双击项目事件
        
        Args:
            item: 被双击的项
            column: 列索引
        """
        # 检查是否是会话节点(有数据)
        session_data = item.data(0, Qt.ItemDataRole.UserRole)
        if session_data:
            self.session_connect.emit(session_data)
    
    def _show_context_menu(self, pos):
        """
        显示右键菜单
        
        Args:
            pos: 鼠标位置
        """
        menu = QMenu(self)
        
        # 获取当前项
        item = self.itemAt(pos)
        
        if item is None:
            # 空白区域 - 只显示新建会话
            new_action = QAction("➕ 新建会话", self)
            new_action.triggered.connect(self._new_session)
            menu.addAction(new_action)
        else:
            session_data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if session_data:
                # 会话节点
                connect_action = QAction("🔗 连接", self)
                connect_action.triggered.connect(lambda: self._connect_session(session_data))
                menu.addAction(connect_action)
                
                menu.addSeparator()
                
                edit_action = QAction("✏️ 编辑", self)
                edit_action.triggered.connect(lambda: self._edit_session(session_data))
                menu.addAction(edit_action)
                
                delete_action = QAction("🗑️ 删除", self)
                delete_action.triggered.connect(lambda: self._delete_session(session_data))
                menu.addAction(delete_action)
            else:
                # 分组节点
                new_action = QAction("➕ 新建会话", self)
                new_action.triggered.connect(self._new_session)
                menu.addAction(new_action)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _new_session(self):
        """新建会话"""
        dialog = SessionDialog(self)
        if dialog.exec():
            # 获取数据并保存
            data = dialog.get_data()
            self.session_manager.add_session(data)
            self._load_sessions()
            self.session_edit.emit(data)
    
    def _connect_session(self, session_data):
        """
        连接会话
        
        Args:
            session_data: 会话数据
        """
        self.session_connect.emit(session_data)
    
    def _edit_session(self, session_data):
        """
        编辑会话
        
        Args:
            session_data: 会话数据
        """
        dialog = SessionDialog(self, session_data)
        if dialog.exec():
            # 获取数据并更新
            data = dialog.get_data()
            self.session_manager.update_session(session_data['id'], data)
            self._load_sessions()
            self.session_edit.emit(data)
    
    def _delete_session(self, session_data):
        """
        删除会话
        
        Args:
            session_data: 会话数据
        """
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除会话 '{session_data['name']}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.session_manager.delete_session(session_data['id'])
            self._load_sessions()
    
    def refresh(self):
        """刷新会话列表"""
        self._load_sessions()
