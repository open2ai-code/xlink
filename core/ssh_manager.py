"""
SSH连接管理模块
封装paramiko,提供异步SSH连接和数据传输功能
"""

import paramiko
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional


class SSHConnection(QObject):
    """SSH连接管理类"""
    
    # 信号定义
    data_received = pyqtSignal(str)  # 接收到数据
    connection_status = pyqtSignal(str)  # 连接状态变化: connected/disconnected/error
    error_occurred = pyqtSignal(str)  # 错误信息
    
    def __init__(self):
        super().__init__()
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.channel = None
        self.is_connected = False
        self.is_running = False
        self.read_thread = None
        self.session_info = {}
    
    def connect(self, host: str, port: int, username: str, 
                password: Optional[str] = None, 
                key_file: Optional[str] = None,
                timeout: int = 30):
        """
        建立SSH连接
        
        Args:
            host: 主机地址
            port: 端口号
            username: 用户名
            password: 密码(可选)
            key_file: 私钥文件路径(可选)
            timeout: 连接超时时间(秒)
        """
        self.session_info = {
            "host": host,
            "port": port,
            "username": username
        }
        
        try:
            # 在新线程中执行连接,避免阻塞GUI
            connect_thread = threading.Thread(
                target=self._do_connect,
                args=(host, port, username, password, key_file, timeout),
                daemon=True
            )
            connect_thread.start()
            
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {str(e)}")
            self.connection_status.emit("error")
    
    def _do_connect(self, host: str, port: int, username: str,
                    password: Optional[str], key_file: Optional[str],
                    timeout: int):
        """实际执行连接的内部方法(在线程中运行)"""
        try:
            # 连接服务器
            if key_file and key_file.strip():
                # 使用私钥认证
                pkey = self._load_private_key(key_file)
                self.client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    pkey=pkey,
                    timeout=timeout,
                    allow_agent=False,
                    look_for_keys=False
                )
            else:
                # 使用密码认证
                self.client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=timeout
                )
            
            # 创建交互式channel
            self.channel = self.client.invoke_shell()
            self.channel.setblocking(0)  # 非阻塞模式
            self.is_connected = True
            self.is_running = True
            
            # 发送连接成功信号
            self.connection_status.emit("connected")
            
            # 启动后台读取线程
            self.read_thread = threading.Thread(
                target=self._read_output,
                daemon=True
            )
            self.read_thread.start()
            
        except paramiko.AuthenticationException:
            self.error_occurred.emit("认证失败: 用户名、密码或私钥错误")
            self.connection_status.emit("error")
        except paramiko.SSHException as e:
            self.error_occurred.emit(f"SSH错误: {str(e)}")
            self.connection_status.emit("error")
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {str(e)}")
            self.connection_status.emit("error")
    
    def _load_private_key(self, key_file: str):
        """
        加载私钥文件(支持RSA/DSA/ECDSA/Ed25519)
        
        Args:
            key_file: 私钥文件路径
            
        Returns:
            PKey对象
        """
        # 尝试不同的私钥格式
        key_classes = [
            paramiko.RSAKey,
            paramiko.DSSKey,
            paramiko.ECDSAKey,
            paramiko.Ed25519Key
        ]
        
        for key_class in key_classes:
            try:
                return key_class.from_private_key_file(key_file)
            except paramiko.SSHException:
                continue
        
        raise paramiko.SSHException("无法识别的私钥格式")
    
    def _read_output(self):
        """后台线程: 持续读取SSH输出"""
        while self.is_running and self.is_connected:
            try:
                if self.channel.recv_ready():
                    # 读取数据
                    data = self.channel.recv(4096)
                    if data:
                        # 解码为字符串(使用replace避免编码错误)
                        text = data.decode('utf-8', errors='replace')
                        self.data_received.emit(text)
                    else:
                        # 连接已关闭
                        break
                else:
                    # 短暂休眠,避免CPU占用过高
                    time.sleep(0.01)
            except Exception as e:
                if self.is_running:
                    self.error_occurred.emit(f"读取数据错误: {str(e)}")
                break
        
        # 循环结束,连接断开
        if self.is_connected:
            self.is_connected = False
            self.connection_status.emit("disconnected")
    
    def send_data(self, data: str):
        """
        发送数据到SSH服务器
        
        Args:
            data: 要发送的字符串
        """
        if self.is_connected and self.channel:
            try:
                self.channel.send(data)
            except Exception as e:
                self.error_occurred.emit(f"发送数据失败: {str(e)}")
    
    def disconnect(self):
        """断开SSH连接"""
        self.is_running = False
        self.is_connected = False
        
        # 等待读取线程结束
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)
        
        # 关闭channel和client
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
            self.channel = None
        
        if self.client:
            try:
                self.client.close()
            except:
                pass
        
        self.connection_status.emit("disconnected")
    
    def get_session_info(self) -> dict:
        """获取会话信息"""
        return self.session_info.copy()
    
    def __del__(self):
        """析构函数: 确保连接被清理"""
        self.disconnect()
