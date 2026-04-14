# -*- coding: utf-8 -*-
"""
对话框模块
包含会话创建/编辑对话框等
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QCheckBox, QMessageBox,
    QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt
import uuid


class SessionDialog(QDialog):
    """会话创建/编辑对话框"""
    
    def __init__(self, parent=None, session_data=None):
        super().__init__(parent)
        self.session_data = session_data
        self.init_ui()
        
        if session_data:
            self.load_session_data(session_data)
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("新建会话" if not self.session_data else "编辑会话")
        self.setFixedSize(450, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        # 会话名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入会话名称")
        form_layout.addRow("会话名称:", self.name_edit)
        
        # 主机地址
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("例如: 192.168.1.100")
        form_layout.addRow("主机地址:", self.host_edit)
        
        # 端口
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        form_layout.addRow("端口:", self.port_spin)
        
        # 用户名
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("输入用户名")
        form_layout.addRow("用户名:", self.username_edit)
        
        # 密码
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("输入密码")
        form_layout.addRow("密码:", self.password_edit)
        
        # 认证方式
        self.auth_combo = QComboBox()
        self.auth_combo.addItems(["密码认证", "密钥认证"])
        self.auth_combo.currentTextChanged.connect(self.on_auth_changed)
        form_layout.addRow("认证方式:", self.auth_combo)
        
        # 密钥文件路径(默认隐藏)
        self.key_path_edit = QLineEdit()
        self.key_path_edit.setPlaceholderText("选择私钥文件")
        self.key_path_edit.setVisible(False)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setVisible(False)
        self.browse_btn.clicked.connect(self.browse_key_file)
        
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.key_path_edit)
        key_layout.addWidget(self.browse_btn)
        form_layout.addRow("密钥文件:", key_layout)
        
        # 记住密码
        self.remember_check = QCheckBox("记住密码")
        form_layout.addRow("", self.remember_check)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_auth_changed(self, auth_method):
        """认证方式改变"""
        is_key = auth_method == "密钥认证"
        self.password_edit.setVisible(not is_key)
        self.key_path_edit.setVisible(is_key)
        self.browse_btn.setVisible(is_key)
    
    def browse_key_file(self):
        """浏览密钥文件"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择私钥文件",
            "",
            "All Files (*.*)"
        )
        if file_path:
            self.key_path_edit.setText(file_path)
    
    def load_session_data(self, data):
        """加载会话数据"""
        self.name_edit.setText(data.get('name', ''))
        self.host_edit.setText(data.get('host', ''))
        self.port_spin.setValue(data.get('port', 22))
        self.username_edit.setText(data.get('username', ''))
        self.password_edit.setText(data.get('password', ''))
        self.remember_check.setChecked(data.get('remember', False))
        
        auth_method = data.get('auth_method', 'password')
        if auth_method == 'key':
            self.auth_combo.setCurrentText("密钥认证")
            self.key_path_edit.setText(data.get('key_path', ''))
    
    def get_session_data(self):
        """获取会话数据"""
        auth_method = 'key' if self.auth_combo.currentText() == "密钥认证" else 'password'
        
        return {
            'id': self.session_data.get('id', str(uuid.uuid4())),
            'name': self.name_edit.text().strip(),
            'host': self.host_edit.text().strip(),
            'port': self.port_spin.value(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text(),
            'auth_method': auth_method,
            'key_path': self.key_path_edit.text().strip(),
            'remember': self.remember_check.isChecked()
        }
    
    def accept(self):
        """确认按钮"""
        # 验证必填字段
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入会话名称")
            self.name_edit.setFocus()
            return
        
        if not self.host_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入主机地址")
            self.host_edit.setFocus()
            return
        
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入用户名")
            self.username_edit.setFocus()
            return
        
        super().accept()
