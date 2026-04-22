# -*- coding: utf-8 -*-
"""
SFTP文件管理模块
提供可视化文件浏览、上传、下载、删除等功能
包含：
- SftpFileManager: SFTP文件管理核心组件
- SftpFileManagerWindow: SFTP文件管理独立窗口
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QToolBar, QToolButton, QFileDialog, QMessageBox, QProgressBar,
    QLabel, QHeaderView, QMenu, QSplitter, QDockWidget, QDialog
)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QThread
from PySide6.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem
from datetime import datetime
import os
from typing import List, Dict
from core.sftp_manager import SFTPManager
from core.logger import get_logger


logger = get_logger("SFTP")


class SftpFileManager(QFrame):
    """SFTP文件管理核心组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.sftp_manager = SFTPManager()
        self.current_session = None
        self._initial_auto_select_done = False  # 标记是否已完成首次自动定位
        
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
        
        # 主分割器(树形目录 + 文件列表)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧: 树形目录
        self._create_directory_tree(main_splitter)
        
        # 右侧: 文件列表区域
        file_list_container = QFrame()
        file_list_layout = QVBoxLayout(file_list_container)
        file_list_layout.setContentsMargins(0, 0, 0, 0)
        file_list_layout.setSpacing(0)
        
        # 路径导航
        self._create_path_bar(file_list_layout)
        
        # 文件列表
        self._create_file_list(file_list_layout)
        
        # 进度条
        self._create_progress_bar(file_list_layout)
        
        main_splitter.addWidget(file_list_container)
        
        # 设置分割器比例: 树形目录占30%, 文件列表占70%
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        
        layout.addWidget(main_splitter)
    
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
    
    def _create_directory_tree(self, parent):
        """创建树形目录"""
        # 创建目录树容器
        tree_frame = QFrame()
        tree_frame.setFrameShape(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        tree_layout.setContentsMargins(2, 2, 2, 2)
        tree_layout.setSpacing(2)
        
        # 添加标题
        tree_label = QLabel("📂 目录结构")
        tree_label.setStyleSheet("QLabel { font-weight: bold; padding: 5px; background-color: #2d2d30; color: #d4d4d4; }")
        tree_layout.addWidget(tree_label)
        
        # 创建树形控件
        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderLabels(["目录"])
        self.dir_tree.header().setVisible(False)
        self.dir_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        
        # 点击目录切换
        self.dir_tree.itemClicked.connect(self._on_dir_tree_clicked)
        
        # 双击展开/折叠
        self.dir_tree.itemDoubleClicked.connect(self._on_dir_tree_double_clicked)
        
        # 展开节点时加载子目录
        self.dir_tree.itemExpanded.connect(self._on_dir_tree_expanded)
        
        tree_layout.addWidget(self.dir_tree)
        
        # 添加到父容器
        parent.addWidget(tree_frame)
    
    def _load_directory_tree(self):
        """加载目录树(懒加载模式 - 只加载根目录)"""
        if not self.sftp_manager.is_connected:
            return
        
        # 清空树
        self.dir_tree.clear()
        
        # 添加根节点
        root_item = QTreeWidgetItem(self.dir_tree)
        root_item.setText(0, "📁 /")
        root_item.setData(0, Qt.ItemDataRole.UserRole, {"path": "/", "name": "/"})
        root_item.setExpanded(True)
        
        # 异步加载根目录的子文件夹
        import asyncio
        asyncio.ensure_future(self._load_subdirs_async("/", root_item, None))
    
    def _load_children_for_node(self, parent_item: QTreeWidgetItem, path: str):
        """
        为节点加载子目录(懒加载模式)
        
        Args:
            parent_item: 父节点
            path: 父目录路径
        """
        try:
            # 添加"加载中..."占位符
            loading_item = QTreeWidgetItem(parent_item)
            loading_item.setText(0, "加载中...")
            loading_item.setDisabled(True)
            
            # 异步获取该目录的子目录
            import asyncio
            asyncio.ensure_future(self._load_subdirs_async(path, parent_item, loading_item))
        except Exception as e:
            logger.error(f"加载子目录失败: {e}")
    
    async def _load_subdirs_async(self, path: str, parent_item: QTreeWidgetItem, loading_item: QTreeWidgetItem):
        """异步加载子目录"""
        logger.info(f"开始加载子目录: {path}")
        try:
            # 获取目录列表
            items = await self.sftp_manager.sftp.readdir(path)
            logger.info(f"获取到目录列表: {len(items)} 项")
            
            # 移除"加载中..."占位符
            if loading_item:
                parent_item.removeChild(loading_item)
            
            # 只添加文件夹到目录树
            import stat
            dir_count = 0
            for name in items:
                if stat.S_ISDIR(name.attrs.permissions):
                    dir_name = name.filename
                    dir_path = path.rstrip('/') + '/' + dir_name
                    
                    # 添加子节点
                    child_item = QTreeWidgetItem(parent_item)
                    child_item.setText(0, "📁 " + dir_name)
                    child_item.setData(0, Qt.ItemDataRole.UserRole, {"path": dir_path, "name": dir_name})
                    
                    # 添加"加载中..."占位符，用于懒加载
                    placeholder = QTreeWidgetItem(child_item)
                    placeholder.setText(0, "加载中...")
                    placeholder.setDisabled(True)
                    dir_count += 1
            
            logger.info(f"子目录加载完成: {path}, 共 {dir_count} 个子目录")
            
            # 如果是根目录加载完成，且还未进行过首次自动定位，则自动定位到用户目录
            if path == "/" and not self._initial_auto_select_done:
                self._initial_auto_select_done = True  # 标记已完成首次定位
                import asyncio
                asyncio.ensure_future(self._auto_select_user_dir())
        except Exception as e:
            logger.error(f"加载子目录失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            if loading_item:
                loading_item.setText(0, "加载失败")
    
    async def _auto_select_user_dir(self):
        """自动定位并选择用户目录"""
        try:
            # 获取当前用户名
            username = None
            if self.current_session and hasattr(self.current_session, 'session_info'):
                username = self.current_session.session_info.get('username')
            
            if not username:
                logger.warning("无法获取用户名，使用根目录")
                return
            
            logger.info(f"当前用户名: {username}")
            
            # 尝试常见的用户目录路径
            user_dirs = [
                f"/home/{username}",
                f"/Users/{username}",
            ]
            
            if username == "root":
                user_dirs.append("/root")
            
            # 检查哪个用户目录存在
            for user_dir in user_dirs:
                try:
                    await self.sftp_manager.sftp.stat(user_dir)
                    logger.info(f"找到用户目录: {user_dir}")
                    
                    # 等待目录树加载完成
                    import asyncio
                    await asyncio.sleep(0.3)
                    
                    # 确保用户目录节点已加载到目录树中
                    # 如果用户目录是 /home/user，需要确保 /home 节点已展开
                    if user_dir.count('/') > 1:
                        parent_dir = '/'.join(user_dir.split('/')[:-1]) or '/'
                        await self._ensure_dir_tree_node_loaded(parent_dir)
                        await asyncio.sleep(0.2)
                    
                    # 在目录树中查找并选中该节点
                    self._select_tree_node_by_path(user_dir)
                    
                    # 切换右侧显示
                    self.sftp_manager.change_directory(user_dir)
                    self.path_edit.setText(user_dir)
                    logger.info(f"自动定位到用户目录: {user_dir}")
                    return
                except Exception as e:
                    logger.debug(f"目录 {user_dir} 不存在: {e}")
                    continue
            
            # 如果都没找到，使用根目录
            logger.info("未找到用户目录，使用根目录")
        except Exception as e:
            logger.error(f"自动定位用户目录失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _ensure_dir_tree_node_loaded(self, path: str):
        """确保目录树中的节点已加载"""
        try:
            # 查找节点
            item = self._find_tree_node_by_path(path)
            if item and item.childCount() == 1:
                first_child = item.child(0)
                if first_child.text(0) == "加载中...":
                    # 正在加载，等待
                    import asyncio
                    await asyncio.sleep(0.5)
                elif first_child.text(0) == "加载中...":
                    # 需要手动加载
                    item.removeChild(first_child)
                    self._load_children_for_node(item, path)
                    import asyncio
                    await asyncio.sleep(0.3)
        except Exception as e:
            logger.debug(f"确保节点加载失败: {e}")
    
    def _find_tree_node_by_path(self, target_path: str):
        """根据路径查找目录树节点"""
        if target_path == "/":
            return self.dir_tree.topLevelItem(0)
        
        return self._find_node_recursive(self.dir_tree, target_path)
    
    def _find_node_recursive(self, tree_or_item, target_path: str):
        """递归查找节点"""
        if isinstance(tree_or_item, QTreeWidget):
            for i in range(tree_or_item.topLevelItemCount()):
                item = tree_or_item.topLevelItem(i)
                result = self._find_node_recursive(item, target_path)
                if result:
                    return result
        else:
            item = tree_or_item
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('path') == target_path:
                return item
            
            for i in range(item.childCount()):
                child = item.child(i)
                result = self._find_node_recursive(child, target_path)
                if result:
                    return result
        
        return None
    
    def _select_tree_node_by_path(self, target_path: str):
        """根据路径选中目录树节点"""
        item = self._find_tree_node_by_path(target_path)
        if item:
            self.dir_tree.setCurrentItem(item)
            # 不展开节点，只选中
            logger.info(f"已选中目录树节点: {target_path}")
        else:
            logger.warning(f"未找到目录树节点: {target_path}")
    
    def _on_directory_tree_ready(self, tree):
        """目录树准备好后的回调"""
        # 清空并重新填充目录树
        self.dir_tree.clear()
        
        # 添加根节点
        root_item = QTreeWidgetItem(self.dir_tree)
        root_item.setText(0, "📁 /")
        root_item.setData(0, Qt.ItemDataRole.UserRole, {"path": "/", "name": "/"})
        root_item.setExpanded(True)
        
        # 添加子节点
        for node in tree:
            self._add_tree_node(node, root_item)
    
    def _add_tree_node(self, node, parent):
        """添加目录树节点"""
        item = QTreeWidgetItem(parent)
        item.setText(0, "📁 " + node['name'])
        item.setData(0, Qt.ItemDataRole.UserRole, {"path": node['path'], "name": node['name']})
        
        # 添加子节点
        for child in node.get('children', []):
            self._add_tree_node(child, item)
    
    def _on_dir_tree_clicked(self, item, column):
        """点击目录树节点 - 切换目录显示"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and 'path' in data:
            path = data['path']
            # 切换到该目录（change_directory内部会触发目录列表刷新）
            self.sftp_manager.change_directory(path)
            self.path_edit.setText(path)
    
    def _on_dir_tree_expanded(self, item):
        """展开目录树节点时加载子目录"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and 'path' in data:
            path = data['path']
            logger.info(f"展开目录节点: {path}, 当前子节点数: {item.childCount()}")
            
            # 检查是否已经加载过子节点
            if item.childCount() == 1:
                first_child = item.child(0)
                if first_child.text(0) == "加载中...":
                    # 有占位符，需要加载子目录
                    logger.info(f"移除占位符，开始加载子目录: {path}")
                    item.removeChild(first_child)
                    self._load_children_for_node(item, path)
                elif first_child.text(0) == "加载失败":
                    # 移除失败提示，重新加载
                    logger.info(f"重新加载失败的子目录: {path}")
                    item.removeChild(first_child)
                    self._load_children_for_node(item, path)
                # else: 已加载过子节点，无需操作
            elif item.childCount() == 0:
                # 没有子节点，首次加载
                logger.info(f"首次加载子目录: {path}")
                self._load_children_for_node(item, path)
    
    def _on_dir_tree_double_clicked(self, item, column):
        """双击目录树节点(展开/折叠 + 懒加载)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and 'path' in data:
            path = data['path']
            
            # 检查是否已经加载过子节点
            # 如果只有一个子节点且是"加载中..."，说明正在加载或需要加载
            if item.childCount() == 1:
                first_child = item.child(0)
                if first_child.text(0) == "加载中...":
                    # 移除占位符
                    item.removeChild(first_child)
                    # 加载实际的子目录
                    self._load_children_for_node(item, path)
                elif first_child.text(0) == "加载失败":
                    # 移除失败提示，重新加载
                    item.removeChild(first_child)
                    self._load_children_for_node(item, path)
            elif item.childCount() == 0:
                # 没有子节点，首次加载
                self._load_children_for_node(item, path)
        
        # 切换展开/折叠状态（延迟执行，让懒加载先完成）
        import asyncio
        asyncio.ensure_future(self._delayed_toggle_expand(item))
    
    async def _delayed_toggle_expand(self, item):
        """延迟切换展开状态"""
        import asyncio
        await asyncio.sleep(0.1)  # 等待懒加载完成
        item.setExpanded(not item.isExpanded())
    
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
        
        # 新增的异步信号
        self.sftp_manager.directory_listed.connect(self._on_directory_listed)
        self.sftp_manager.file_operation_result.connect(self._on_file_operation_result)
        self.sftp_manager.directory_tree_ready.connect(self._on_directory_tree_ready)
    
    def connect_session(self, ssh_connection):
        """
        连接到会话的SFTP
        
        Args:
            ssh_connection: SSHConnection对象
        """
        logger.info(f"开始连接SFTP会话")
        
        if not ssh_connection:
            logger.error("SSH连接对象为空")
            QMessageBox.critical(self, "错误", "SSH连接对象为空")
            return False
            
        if not ssh_connection.is_connected:
            logger.error("SSH未连接,无法建立SFTP连接")
            QMessageBox.critical(self, "错误", "SSH未连接,无法建立SFTP连接")
            return False
        
        logger.info(f"SSH连接状态: {ssh_connection.is_connected}")
        logger.info(f"SSH连接对象: {ssh_connection.conn}")
        
        self.current_session = ssh_connection
        
        # 使用SSH连接创建SFTP - 使用异步方法
        try:
            # 复用SSH连接
            logger.info("正在打开SFTP通道...")
            self.sftp_manager.conn = ssh_connection.conn
            # 使用异步方式打开SFTP
            import asyncio
            asyncio.ensure_future(self._open_sftp_channel())
            return True
            
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(self, "错误", error_msg)
            return False

    async def _open_sftp_channel(self):
        """异步打开SFTP通道"""
        try:
            self.sftp_manager.sftp = await self.sftp_manager.conn.start_sftp_client()
            self.sftp_manager.is_connected = True
            logger.info("SFTP连接已建立")
            self._on_connected()
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            self.sftp_manager.error_occurred.emit(error_msg)
    
    def disconnect(self):
        """断开SFTP连接"""
        if self.sftp_manager.is_connected:
            try:
                # 使用异步断开连接
                import asyncio
                asyncio.ensure_future(self.sftp_manager._do_disconnect())
                self.file_tree.clear()
                self.dir_tree.clear()
                self.path_edit.setText("/")
                logger.info("SFTP已断开")
            except Exception as e:
                logger.error(f"断开SFTP失败: {e}")
    
    def refresh(self):
        """刷新当前目录"""
        if not self.sftp_manager.is_connected:
            return
        
        # 使用异步版本
        self.sftp_manager.list_directory_async()
        self.path_edit.setText(self.sftp_manager.get_current_path())
        
        # 更新目录树
        self._load_directory_tree()
    
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
        
        # 使用异步上传
        self.sftp_manager.upload_file_async(file_path, remote_path)
    
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
        
        # 使用异步下载
        self.sftp_manager.download_file_async(remote_path, save_path)
    
    def create_directory(self):
        """创建文件夹"""
        if not self.sftp_manager.is_connected:
            QMessageBox.warning(self, "提示", "SFTP未连接")
            return
        
        # 输入文件夹名称
        from PySide6.QtWidgets import QInputDialog
        dir_name, ok = QInputDialog.getText(
            self, "新建文件夹", "请输入文件夹名称:"
        )
        
        if not ok or not dir_name.strip():
            return
        
        # 创建
        current_path = self.sftp_manager.get_current_path()
        new_path = current_path + "/" + dir_name.strip()
        
        # 使用异步创建
        self.sftp_manager.mkdir_async(new_path)
    
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
            # 使用异步删除
            self.sftp_manager.delete_async(path, data['is_dir'])
    
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
        logger.info("SFTP连接成功,开始刷新目录")
        # 加载目录树
        self._load_directory_tree()
        logger.info("目录刷新完成")
    
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
    
    def _on_directory_listed(self, items):
        """目录列表异步返回"""
        self._update_file_list(items)
        
        # 同时更新目录树（如果是根目录加载）
        current_path = self.sftp_manager.get_current_path()
        if current_path == "/":
            self._load_directory_tree()
    
    def _on_file_operation_result(self, success, operation_name):
        """文件操作结果异步返回"""
        if success:
            logger.info(f"文件操作成功: {operation_name}")
            # 操作成功后刷新列表
            self.refresh()
        else:
            logger.error(f"文件操作失败: {operation_name}")
            QMessageBox.critical(self, "错误", f"{operation_name} 操作失败")


class SftpFileManagerWindow(QDialog):
    """SFTP文件管理独立窗口"""
    
    def __init__(self, parent=None, ssh_connection=None):
        super().__init__(parent)
        
        self.ssh_connection = ssh_connection
        
        # 设置窗口属性
        self.setWindowTitle("SFTP 文件管理器")
        self.setMinimumSize(1000, 600)
        self.resize(1200, 700)
        
        # 设置为独立窗口(不跟随父窗口)
        self.setWindowFlags(Qt.WindowType.Window)
        
        # 创建SFTP文件管理器
        self.file_manager = SftpFileManager(self)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.file_manager)
        
        # 如果有SSH连接,立即连接
        if ssh_connection and ssh_connection.is_connected:
            self.file_manager.connect_session(ssh_connection)
    
    def set_ssh_connection(self, ssh_connection):
        """
        设置SSH连接
        
        Args:
            ssh_connection: SSHConnection对象
        """
        self.ssh_connection = ssh_connection
        if ssh_connection and ssh_connection.is_connected:
            self.file_manager.connect_session(ssh_connection)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 断开SFTP连接
        self.file_manager.disconnect()
        event.accept()
