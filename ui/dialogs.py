"""
对话框模块
提供会话编辑等对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QGroupBox, QFileDialog, QMessageBox,
    QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox
)
from PyQt6.QtCore import Qt
import os


class SessionDialog(QDialog):
    """会话编辑对话框"""
    
    def __init__(self, parent=None, session_data=None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            session_data: 现有会话数据(编辑模式),None表示新建模式
        """
        super().__init__(parent)
        self.session_data = session_data
        
        self.setWindowTitle("编辑会话" if session_data else "新建会话")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        self._init_ui()
        
        # 如果是编辑模式,填充数据
        if session_data:
            self._load_data(session_data)
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout()
        
        # 会话名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: 生产服务器")
        basic_layout.addRow("会话名称:", self.name_edit)
        
        # 分组
        self.group_edit = QLineEdit()
        self.group_edit.setPlaceholderText("例如: 生产环境")
        basic_layout.addRow("分组:", self.group_edit)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 连接信息组
        conn_group = QGroupBox("连接信息")
        conn_layout = QFormLayout()
        
        # 主机地址
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("例如: 192.168.1.100 或 example.com")
        conn_layout.addRow("主机地址:", self.host_edit)
        
        # 端口
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        conn_layout.addRow("端口:", self.port_spin)
        
        # 用户名
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("例如: root")
        conn_layout.addRow("用户名:", self.username_edit)
        
        # 超时时间
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        conn_layout.addRow("超时时间:", self.timeout_spin)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # 认证信息组
        auth_group = QGroupBox("认证方式")
        auth_layout = QVBoxLayout()
        
        # 认证类型选择
        auth_type_layout = QHBoxLayout()
        auth_type_layout.addWidget(QLabel("认证类型:"))
        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems(["密码认证", "私钥认证"])
        self.auth_type_combo.currentIndexChanged.connect(self._on_auth_type_changed)
        auth_type_layout.addWidget(self.auth_type_combo)
        auth_layout.addLayout(auth_type_layout)
        
        # 密码输入
        self.password_label = QLabel("密码:")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("输入SSH密码")
        auth_layout.addWidget(self.password_label)
        auth_layout.addWidget(self.password_edit)
        
        # 私钥文件选择
        self.key_file_layout = QHBoxLayout()
        self.key_file_label = QLabel("私钥文件:")
        self.key_file_edit = QLineEdit()
        self.key_file_edit.setPlaceholderText("选择私钥文件路径")
        self.key_file_edit.setReadOnly(True)
        self.key_file_button = QPushButton("浏览...")
        self.key_file_button.clicked.connect(self._select_key_file)
        self.key_file_button.setMaximumWidth(80)
        
        self.key_file_layout.addWidget(self.key_file_label)
        self.key_file_layout.addWidget(self.key_file_edit)
        self.key_file_layout.addWidget(self.key_file_button)
        
        auth_layout.addLayout(self.key_file_layout)
        
        # 默认隐藏私钥文件相关控件
        self.key_file_label.setVisible(False)
        self.key_file_edit.setVisible(False)
        self.key_file_button.setVisible(False)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("保存")
        self.save_button.setMinimumWidth(100)
        self.save_button.clicked.connect(self._save)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _on_auth_type_changed(self, index):
        """
        认证类型切换事件
        
        Args:
            index: 选中的索引(0=密码, 1=私钥)
        """
        if index == 0:  # 密码认证
            self.password_label.setVisible(True)
            self.password_edit.setVisible(True)
            self.key_file_label.setVisible(False)
            self.key_file_edit.setVisible(False)
            self.key_file_button.setVisible(False)
        else:  # 私钥认证
            self.password_label.setVisible(False)
            self.password_edit.setVisible(False)
            self.key_file_label.setVisible(True)
            self.key_file_edit.setVisible(True)
            self.key_file_button.setVisible(True)
    
    def _select_key_file(self):
        """选择私钥文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择私钥文件",
            os.path.expanduser("~/.ssh"),
            "All Files (*);;Private Keys (*_rsa;*_ed25519;*.pem;*.key)"
        )
        if file_path:
            self.key_file_edit.setText(file_path)
    
    def _load_data(self, data):
        """
        加载会话数据到表单
        
        Args:
            data: 会话数据字典
        """
        self.name_edit.setText(data.get("name", ""))
        self.group_edit.setText(data.get("group", ""))
        self.host_edit.setText(data.get("host", ""))
        self.port_spin.setValue(data.get("port", 22))
        self.username_edit.setText(data.get("username", ""))
        self.timeout_spin.setValue(data.get("timeout", 30))
        
        # 认证方式
        auth_type = data.get("auth_type", "password")
        if auth_type == "key":
            self.auth_type_combo.setCurrentIndex(1)
            self.key_file_edit.setText(data.get("key_file", ""))
        else:
            self.auth_type_combo.setCurrentIndex(0)
            self.password_edit.setText(data.get("password", ""))
    
    def _save(self):
        """验证并保存数据"""
        # 验证必填字段
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入会话名称")
            return
        
        if not self.host_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入主机地址")
            return
        
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入用户名")
            return
        
        # 根据认证类型验证
        auth_type = "password" if self.auth_type_combo.currentIndex() == 0 else "key"
        
        if auth_type == "password":
            if not self.password_edit.text().strip():
                QMessageBox.warning(self, "警告", "请输入密码")
                return
        else:
            if not self.key_file_edit.text().strip():
                QMessageBox.warning(self, "警告", "请选择私钥文件")
                return
            if not os.path.exists(self.key_file_edit.text()):
                QMessageBox.warning(self, "警告", "私钥文件不存在")
                return
        
        # 接受对话框
        self.accept()
    
    def get_data(self) -> dict:
        """
        获取表单数据
        
        Returns:
            会话数据字典
        """
        auth_type = "password" if self.auth_type_combo.currentIndex() == 0 else "key"
        
        data = {
            "name": self.name_edit.text().strip(),
            "group": self.group_edit.text().strip() or "默认分组",
            "host": self.host_edit.text().strip(),
            "port": self.port_spin.value(),
            "username": self.username_edit.text().strip(),
            "timeout": self.timeout_spin.value(),
            "auth_type": auth_type
        }
        
        if auth_type == "password":
            data["password"] = self.password_edit.text()
            data["key_file"] = ""
        else:
            data["password"] = ""
            data["key_file"] = self.key_file_edit.text().strip()
        
        return data


class ImportExportDialog(QDialog):
    """导入导出会话配置对话框"""
    
    def __init__(self, parent=None, mode='export', session_manager=None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            mode: 'export' 或 'import'
            session_manager: SessionManager实例
        """
        super().__init__(parent)
        self.mode = mode
        self.session_manager = session_manager
        
        self.setWindowTitle("导出会话" if mode == 'export' else "导入会话")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        if self.mode == 'export':
            self._init_export_ui(layout)
        else:
            self._init_import_ui(layout)
    
    def _init_export_ui(self, layout):
        """初始化导出UI"""
        # 导出格式选择
        format_group = QGroupBox("导出格式")
        format_layout = QHBoxLayout()
        
        self.format_group = QButtonGroup()
        self.json_radio = QRadioButton("JSON (完整信息)")
        self.json_radio.setChecked(True)
        self.csv_radio = QRadioButton("CSV (Excel可编辑)")
        
        self.format_group.addButton(self.json_radio, 0)
        self.format_group.addButton(self.csv_radio, 1)
        
        format_layout.addWidget(self.json_radio)
        format_layout.addWidget(self.csv_radio)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # 文件路径
        file_group = QGroupBox("保存位置")
        file_layout = QHBoxLayout()
        
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("选择保存路径...")
        file_layout.addWidget(self.file_edit)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_export_file)
        file_layout.addWidget(browse_btn)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._do_export)
        button_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _init_import_ui(self, layout):
        """初始化导入UI"""
        # 文件选择
        file_group = QGroupBox("选择文件")
        file_layout = QHBoxLayout()
        
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("选择导入文件...")
        file_layout.addWidget(self.file_edit)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_import_file)
        file_layout.addWidget(browse_btn)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 导入模式
        mode_group = QGroupBox("导入模式")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        self.merge_radio = QRadioButton("合并 (保留现有,新会话自动重命名)")
        self.merge_radio.setChecked(True)
        self.replace_radio = QRadioButton("替换 (清空现有,全部导入)")
        
        self.mode_group.addButton(self.merge_radio, 0)
        self.mode_group.addButton(self.replace_radio, 1)
        
        mode_layout.addWidget(self.merge_radio)
        mode_layout.addWidget(self.replace_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._do_import)
        button_layout.addWidget(import_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _browse_export_file(self):
        """浏览导出文件路径"""
        if self.json_radio.isChecked():
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存文件", "", "JSON Files (*.json)"
            )
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存文件", "", "CSV Files (*.csv)"
            )
        
        if file_path:
            self.file_edit.setText(file_path)
    
    def _browse_import_file(self):
        """浏览导入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "JSON/CSV Files (*.json *.csv)"
        )
        
        if file_path:
            self.file_edit.setText(file_path)
    
    def _do_export(self):
        """执行导出"""
        file_path = self.file_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "提示", "请选择保存路径")
            return
        
        format_type = 'json' if self.json_radio.isChecked() else 'csv'
        
        if self.session_manager.export_sessions(file_path, format_type):
            QMessageBox.information(self, "成功", "会话导出成功")
            self.accept()
        else:
            QMessageBox.critical(self, "失败", "会话导出失败")
    
    def _do_import(self):
        """执行导入"""
        file_path = self.file_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "提示", "请选择导入文件")
            return
        
        mode = 'merge' if self.merge_radio.isChecked() else 'replace'
        
        success, fail, errors = self.session_manager.import_sessions(file_path, mode)
        
        if success > 0:
            msg = f"导入成功: {success} 个会话"
            if fail > 0:
                msg += f"\n失败: {fail} 个"
            if errors:
                msg += "\n\n错误信息:\n" + "\n".join(errors)
            QMessageBox.information(self, "完成", msg)
            self.accept()
        else:
            error_msg = "导入失败\n\n" + "\n".join(errors) if errors else "导入失败"
            QMessageBox.critical(self, "错误", error_msg)
