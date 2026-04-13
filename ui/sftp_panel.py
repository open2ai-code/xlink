"""
SFTP文件管理面板
提供可视化文件浏览、上传、下载、删除等功能
"""

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QToolBar, QToolButton, QFileDialog, QMessageBox, QProgressBar,
    QLabel, QHeaderView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem
from datetime import datetime
import os
from core.sftp_manager import SFTPManager
from core.logger import get_logger


logger = get_logger("SFTPPanel")


class SftpPanel(QFrame):
    """SFTP文件管理面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.sftp_manager = SFTPManager()
        self.current_session = None
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """初始化UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        self._create_toolbar(layout)
        
        # 路径导航
        self._create_path_bar(layout)
        
        # 文件列表
        self._create_file_list(layout)
        
        # 进度条
        self._create_progress_bar(layout)
    
    def _create_toolbar(self, layout):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # 刷新按钮
        self.refresh_action = QAction("刷新", self)
        self.refresh_action.setToolTip("刷新当前目录")
        toolbar.addAction(self.refresh_action)
        
        toolbar.addSeparator()
        
        # 上传按钮
        self.upload_action = QAction("上传", self)
        self.upload_action.setToolTip("上传文件到服务器")
        toolbar.addAction(self.upload_action)
        
        # 下载按钮
        self.download_action = QAction("下载", self)
        self.download_action.setToolTip("下载文件到本地")
        toolbar.addAction(self.download_action)
        
        toolbar.addSeparator()
        
        # 新建文件夹按钮
        self.mkdir_action = QAction("新建文件夹", self)
        self.mkdir_action.setToolTip("创建新文件夹")
        toolbar.addAction(self.mkdir_action)
        
        # 删除按钮
        self.delete_action = QAction("删除", self)
        self.delete_action.setToolTip("删除选中的文件/文件夹")
        toolbar.addAction(self.delete_action)
        
        toolbar.addSeparator()
        
        # 向上一级按钮
        self.up_action = QAction("向上一级", self)
        self.up_action.setToolTip("返回上级目录")
        toolbar.addAction(self.up_action)
        
        layout.addWidget(toolbar)
    
    def _create_path_bar(self, layout):
        """创建路径导航栏"""
        path_layout = QHBoxLayout()
        
        path_label = QLabel("路径:")
        path_layout.addWidget(path_label)
        
        self.path_edit = QLabel("/")
        self.path_edit.setStyleSheet("QLabel { background-color: #1e1e1e; padding: 5px; border: 1px solid #3e3e3e; }")
        path_layout.addWidget(self.path_edit)
        
        layout.addLayout(path_layout)
    
    def _create_file_list(self, layout):
        """创建文件列表"""
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["名称", "大小", "修改时间", "权限"])
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
        # 双击进入文件夹
        self.file_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # 右键菜单
        self.file_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.file_tree)
    
    def _create_progress_bar(self, layout):
        """创建进度条"""
        progress_layout = QHBoxLayout()
        
        self.progress_label = QLabel("")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addLayout(progress_layout)
    
    def _connect_signals(self):
        """连接信号"""
        # 工具栏按钮
        self.refresh_action.triggered.connect(self.refresh)
        self.upload_action.triggered.connect(self.upload_file)
        self.download_action.triggered.connect(self.download_file)
        self.mkdir_action.triggered.connect(self.create_directory)
        self.delete_action.triggered.connect(self.delete_selected)
        self.up_action.triggered.connect(self.go_up)
        
        # SFTP管理器信号
        self.sftp_manager.connected.connect(self._on_connected)
        self.sftp_manager.disconnected.connect(self._on_disconnected)
        self.sftp_manager.error_occurred.connect(self._on_error)
        self.sftp_manager.progress_updated.connect(self._on_progress)
        self.sftp_manager.operation_completed.connect(self.refresh)
    
    def connect_session(self, ssh_connection):
        """
        连接到会话的SFTP
        
        Args:
            ssh_connection: SSHConnection对象
        """
        if not ssh_connection or not ssh_connection.is_connected:
            logger.error("SSH未连接,无法建立SFTP连接")
            return False
        
        self.current_session = ssh_connection
        
        # 使用SSH连接创建SFTP
        try:
            # 复用SSH连接
            self.sftp_manager.ssh_client = ssh_connection.client
            self.sftp_manager.sftp_client = ssh_connection.client.open_sftp()
            self.sftp_manager.is_connected = True
            
            logger.info("SFTP连接已建立")
            self._on_connected()
            return True
            
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            return False
    
    def disconnect(self):
        """断开SFTP连接"""
        if self.sftp_manager.is_connected:
            try:
                if self.sftp_manager.sftp_client:
                    self.sftp_manager.sftp_client.close()
                    self.sftp_manager.sftp_client = None
                self.sftp_manager.is_connected = False
                self.file_tree.clear()
                self.path_edit.setText("/")
                logger.info("SFTP已断开")
            except Exception as e:
                logger.error(f"断开SFTP失败: {e}")
    
    def refresh(self):
        """刷新当前目录"""
        if not self.sftp_manager.is_connected:
            return
        
        items = self.sftp_manager.list_directory()
        self._update_file_list(items)
        self.path_edit.setText(self.sftp_manager.get_current_path())
    
    def _update_file_list(self, items):
        """更新文件列表"""
        self.file_tree.clear()
        
        for item in items:
            tree_item = QTreeWidgetItem(self.file_tree)
            
            # 名称
            name = item['name']
            if item['is_dir']:
                name = "📁 " + name
            else:
                name = "📄 " + name
            tree_item.setText(0, name)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item)
            
            # 大小
            if item['is_dir']:
                size_str = "-"
            else:
                size = item['size']
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
            tree_item.setText(1, size_str)
            
            # 修改时间
            mtime = datetime.fromtimestamp(item['mtime'])
            tree_item.setText(2, mtime.strftime("%Y-%m-%d %H:%M"))
            
            # 权限
            tree_item.setText(3, item['permissions'])
    
    def _on_item_double_clicked(self, item, column):
        """双击项目"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data['is_dir']:
            # 进入文件夹
            dir_name = data['name']
            current_path = self.sftp_manager.get_current_path()
            if current_path == "/":
                new_path = "/" + dir_name
            else:
                new_path = current_path + "/" + dir_name
            
            if self.sftp_manager.change_directory(new_path):
                self.refresh()
    
    def go_up(self):
        """向上一级"""
        current_path = self.sftp_manager.get_current_path()
        if current_path == "/":
            return
        
        parent_path = os.path.dirname(current_path)
        if not parent_path:
            parent_path = "/"
        
        if self.sftp_manager.change_directory(parent_path):
            self.refresh()
    
    def upload_file(self):
        """上传文件"""
        if not self.sftp_manager.is_connected:
            QMessageBox.warning(self, "提示", "SFTP未连接")
            return
        
        # 选择本地文件
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要上传的文件"
        )
        
        if not file_path:
            return
        
        # 远程路径
        file_name = os.path.basename(file_path)
        current_path = self.sftp_manager.get_current_path()
        remote_path = current_path + "/" + file_name
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"正在上传: {file_name}")
        
        # 上传
        success = self.sftp_manager.upload_file(file_path, remote_path)
        
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        if success:
            QMessageBox.information(self, "成功", f"文件上传成功: {file_name}")
        else:
            QMessageBox.critical(self, "失败", "文件上传失败")
    
    def download_file(self):
        """下载文件"""
        if not self.sftp_manager.is_connected:
            QMessageBox.warning(self, "提示", "SFTP未连接")
            return
        
        # 获取选中的文件
        selected = self.file_tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要下载的文件")
            return
        
        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data['is_dir']:
            QMessageBox.warning(self, "提示", "暂不支持下载文件夹")
            return
        
        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", data['name']
        )
        
        if not save_path:
            return
        
        # 远程路径
        current_path = self.sftp_manager.get_current_path()
        remote_path = current_path + "/" + data['name']
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"正在下载: {data['name']}")
        
        # 下载
        success = self.sftp_manager.download_file(remote_path, save_path)
        
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        if success:
            QMessageBox.information(self, "成功", f"文件下载成功")
        else:
            QMessageBox.critical(self, "失败", "文件下载失败")
    
    def create_directory(self):
        """创建文件夹"""
        if not self.sftp_manager.is_connected:
            QMessageBox.warning(self, "提示", "SFTP未连接")
            return
        
        # 输入文件夹名称
        dir_name, ok = QFileDialog.getExistingDirectory(
            self, "选择父目录"
        )
        
        from PyQt6.QtWidgets import QInputDialog
        dir_name, ok = QInputDialog.getText(
            self, "新建文件夹", "请输入文件夹名称:"
        )
        
        if not ok or not dir_name.strip():
            return
        
        # 创建
        current_path = self.sftp_manager.get_current_path()
        new_path = current_path + "/" + dir_name.strip()
        
        if self.sftp_manager.mkdir(new_path):
            QMessageBox.information(self, "成功", "文件夹创建成功")
        else:
            QMessageBox.critical(self, "失败", "文件夹创建失败")
    
    def delete_selected(self):
        """删除选中的文件/文件夹"""
        if not self.sftp_manager.is_connected:
            QMessageBox.warning(self, "提示", "SFTP未连接")
            return
        
        selected = self.file_tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要删除的项目")
            return
        
        # 确认删除
        names = [item.data(0, Qt.ItemDataRole.UserRole)['name'] for item in selected]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除以下 {len(names)} 个项目吗?\n" + "\n".join(names),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 删除
        current_path = self.sftp_manager.get_current_path()
        for item in selected:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            path = current_path + "/" + data['name']
            self.sftp_manager.delete(path, data['is_dir'])
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        
        menu.addAction(self.upload_action)
        menu.addAction(self.download_action)
        menu.addSeparator()
        menu.addAction(self.mkdir_action)
        menu.addAction(self.delete_action)
        menu.addSeparator()
        menu.addAction(self.refresh_action)
        
        menu.exec(self.file_tree.viewport().mapToGlobal(pos))
    
    def _on_connected(self):
        """连接成功"""
        self.refresh()
    
    def _on_disconnected(self):
        """连接断开"""
        self.file_tree.clear()
        self.path_edit.setText("/")
    
    def _on_error(self, error_msg):
        """错误处理"""
        QMessageBox.critical(self, "错误", error_msg)
    
    def _on_progress(self, current, total):
        """进度更新"""
        if total > 0:
            percent = int(current / total * 100)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"传输中: {percent}%")
