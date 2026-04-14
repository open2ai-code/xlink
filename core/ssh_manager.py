"""
SSH连接管理模块 - 商用级重构版
基于paramiko实现高性能、高稳定性的SSH连接管理

核心特性:
- 线程安全的连接管理
- 智能心跳保活机制
- 自动重连与异常恢复
- 低延迟数据传输
- 完善的编码处理(UTF-8/Latin-1 fallback)
- 终端模式优化(vt100/xterm)
"""

import paramiko
import threading
import time
import queue
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from core.logger import get_logger


logger = get_logger("SSHConnection")


class SSHConnection(QObject):
    """
    商用级SSH连接管理类
    
    特性:
    - 线程安全的异步连接
    - 智能心跳检测(可配置间隔)
    - 自动重连机制(指数退避)
    - 双缓冲队列(输入/输出)
    - 低延迟数据读取(自适应轮询)
    - 完善的异常处理
    """
    
    # 信号定义
    data_received = pyqtSignal(str)  # 接收到数据
    connection_status = pyqtSignal(str)  # 连接状态: connected/disconnecting/disconnected/error/reconnecting
    error_occurred = pyqtSignal(str)  # 错误信息
    reconnecting = pyqtSignal(int)  # 正在重连,参数: 尝试次数
    
    # 连接状态常量
    STATE_DISCONNECTED = "disconnected"
    STATE_CONNECTING = "connecting"
    STATE_CONNECTED = "connected"
    STATE_DISCONNECTING = "disconnecting"
    STATE_RECONNECTING = "reconnecting"
    
    def __init__(self):
        super().__init__()
        
        # SSH核心对象
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
        self.transport: Optional[paramiko.Transport] = None
        
        # 连接状态
        self._state = self.STATE_DISCONNECTED
        self._state_lock = threading.Lock()
        
        # 会话信息
        self.session_info: Dict[str, Any] = {}
        self._connect_params: Dict[str, Any] = {}
        
        # 线程管理
        self._read_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 数据队列(线程安全)
        self._send_queue = queue.Queue()
        
        # 心跳配置
        self.heartbeat_interval = 30  # 秒
        self.heartbeat_timeout = 90  # 秒
        self._last_heartbeat_time = 0
        self._last_activity_time = 0
        
        # 重连配置
        self.auto_reconnect = True
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # 初始重连延迟(秒)
        self.max_reconnect_delay = 60  # 最大重连延迟(秒)
        self._reconnect_attempts = 0
        
        # 终端配置
        self.term_width = 120
        self.term_height = 40
        self.term_type = 'xterm-256color'
        
        # 数据读取优化
        self._read_buffer_size = 8192  # 8KB读取缓冲区
        self._read_poll_interval = 0.005  # 5ms轮询间隔(低延迟)
        self._max_idle_poll_interval = 0.1  # 100ms最大空闲轮询间隔
        
        # 日志
        logger.debug("SSHConnection实例已创建")
    
    @property
    def is_connected(self) -> bool:
        """线程安全地检查连接状态"""
        with self._state_lock:
            return self._state == self.STATE_CONNECTED
    
    @property
    def state(self) -> str:
        """获取当前连接状态"""
        with self._state_lock:
            return self._state
    
    def _set_state(self, new_state: str):
        """线程安全地设置连接状态"""
        with self._state_lock:
            old_state = self._state
            self._state = new_state
            logger.debug(f"连接状态变更: {old_state} -> {new_state}")
    
    def connect(self, host: str, port: int, username: str, 
                password: Optional[str] = None, 
                key_file: Optional[str] = None,
                timeout: int = 30,
                auto_reconnect: bool = True):
        """
        建立SSH连接(异步)
        
        Args:
            host: 主机地址
            port: 端口号
            username: 用户名
            password: 密码
            key_file: 私钥文件路径
            timeout: 连接超时时间(秒)
            auto_reconnect: 是否启用自动重连
        """
        # 保存连接参数(用于重连)
        self._connect_params = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'key_file': key_file,
            'timeout': timeout
        }
        
        self.session_info = {
            "host": host,
            "port": port,
            "username": username
        }
        
        self.auto_reconnect = auto_reconnect
        
        # 在新线程中执行连接
        connect_thread = threading.Thread(
            target=self._do_connect,
            args=(host, port, username, password, key_file, timeout),
            daemon=True,
            name=f"SSH-Connect-{host}:{port}"
        )
        connect_thread.start()
    
    def _do_connect(self, host: str, port: int, username: str,
                    password: Optional[str], key_file: Optional[str],
                    timeout: int):
        """实际执行连接(在线程中运行)"""
        try:
            self._set_state(self.STATE_CONNECTING)
            logger.info(f"正在连接SSH服务器: {host}:{port}")
            
            # 创建SSH客户端
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 连接参数优化
            connect_kwargs = {
                'hostname': host,
                'port': port,
                'username': username,
                'timeout': timeout,
                'allow_agent': False,  # 禁用SSH agent,避免干扰
                'look_for_keys': False,  # 不自动查找密钥
                'compress': False,  # 禁用压缩,降低延迟
            }
            
            # 认证方式
            if key_file and key_file.strip():
                # 私钥认证
                pkey = self._load_private_key(key_file)
                connect_kwargs['pkey'] = pkey
                logger.debug("使用私钥认证")
            elif password:
                # 密码认证
                connect_kwargs['password'] = password
                logger.debug("使用密码认证")
            
            # 建立连接
            self.client.connect(**connect_kwargs)
            self.transport = self.client.get_transport()
            
            if not self.transport:
                raise paramiko.SSHException("无法获取transport")
            
            # 保持连接活跃
            self.transport.set_keepalive(self.heartbeat_interval)
            
            # 创建交互式channel(终端模式优化)
            self.channel = self.client.invoke_shell(
                term=self.term_type,
                width=self.term_width,
                height=self.term_height
            )
            
            # 设置为非阻塞模式
            self.channel.setblocking(0)
            
            # 设置channel超时
            self.channel.settimeout(1.0)
            
            # 更新状态
            self._set_state(self.STATE_CONNECTED)
            self._reconnect_attempts = 0
            self._running = True
            self._last_activity_time = time.time()
            
            logger.info(f"SSH连接成功: {host}:{port}")
            
            # 发送连接成功信号
            self.connection_status.emit(self.STATE_CONNECTED)
            
            # 启动后台线程
            self._start_read_thread()
            self._start_heartbeat_thread()
            
        except paramiko.AuthenticationException:
            error_msg = "认证失败: 用户名、密码或私钥错误"
            logger.error(error_msg)
            self._set_state(self.STATE_DISCONNECTED)
            self.error_occurred.emit(error_msg)
            self.connection_status.emit("error")
            
        except paramiko.SSHException as e:
            error_msg = f"SSH协议错误: {str(e)}"
            logger.error(error_msg)
            self._set_state(self.STATE_DISCONNECTED)
            self.error_occurred.emit(error_msg)
            self.connection_status.emit("error")
            
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._set_state(self.STATE_DISCONNECTED)
            self.error_occurred.emit(error_msg)
            self.connection_status.emit("error")
    
    def _load_private_key(self, key_file: str):
        """
        加载私钥文件(支持多种格式)
        
        Args:
            key_file: 私钥文件路径
            
        Returns:
            PKey对象
        """
        key_classes = [
            paramiko.RSAKey,
            paramiko.DSSKey,
            paramiko.ECDSAKey,
            paramiko.Ed25519Key
        ]
        
        last_exception = None
        for key_class in key_classes:
            try:
                return key_class.from_private_key_file(key_file)
            except paramiko.PasswordRequiredException:
                raise paramiko.SSHException("私钥已加密,需要提供密码")
            except paramiko.SSHException as e:
                last_exception = e
                continue
        
        raise paramiko.SSHException(f"无法识别的私钥格式: {last_exception}")
    
    def _start_read_thread(self):
        """启动数据读取线程"""
        self._read_thread = threading.Thread(
            target=self._read_output_loop,
            daemon=True,
            name=f"SSH-Read-{self.session_info.get('host', 'unknown')}"
        )
        self._read_thread.start()
        logger.debug("数据读取线程已启动")
    
    def _read_output_loop(self):
        """
        数据读取主循环(优化版)
        
        特性:
        - 自适应轮询间隔(降低CPU占用)
        - 大数据块读取(减少系统调用)
        - 编码容错处理
        - 活动检测(用于心跳)
        """
        logger.debug("数据读取循环开始")
        
        adaptive_poll_interval = self._read_poll_interval
        consecutive_empty_reads = 0
        
        while self._running and self.is_connected:
            try:
                if not self.channel:
                    logger.warning("Channel为空,退出读取循环")
                    break
                
                # 检查channel是否可用
                if self.channel.closed:
                    logger.warning("Channel已关闭,退出读取循环")
                    break
                
                # 读取数据
                if self.channel.recv_ready():
                    # 有大块数据时,一次性读取更多
                    try:
                        data = self.channel.recv(self._read_buffer_size)
                        
                        if data:
                            # 重置空闲计数
                            consecutive_empty_reads = 0
                            adaptive_poll_interval = self._read_poll_interval
                            
                            # 更新活动时间
                            self._last_activity_time = time.time()
                            
                            # 解码数据(UTF-8优先,Latin-1降级)
                            try:
                                text = data.decode('utf-8')
                            except UnicodeDecodeError:
                                # UTF-8解码失败,尝试Latin-1(不会失败)
                                text = data.decode('latin-1')
                            
                            # 发送数据信号
                            self.data_received.emit(text)
                            
                            # 清空发送队列
                            self._flush_send_queue()
                        else:
                            # 收到空数据,连接可能已断开
                            logger.warning("收到空数据,连接可能已断开")
                            break
                    except Exception as e:
                        logger.error(f"读取数据异常: {e}", exc_info=True)
                        break
                else:
                    # 没有数据可读
                    consecutive_empty_reads += 1
                    
                    # 自适应调整轮询间隔
                    if consecutive_empty_reads > 100:  # 约0.5秒无数据
                        adaptive_poll_interval = min(
                            adaptive_poll_interval * 1.5,
                            self._max_idle_poll_interval
                        )
                    
                    # 短暂休眠
                    time.sleep(adaptive_poll_interval)
                    
            except socket.timeout:
                # 超时是正常的,继续循环
                continue
            except EOFError:
                logger.info("收到EOF,连接已关闭")
                break
            except Exception as e:
                if self._running:
                    logger.error(f"读取循环异常: {e}", exc_info=True)
                    self.error_occurred.emit(f"读取数据错误: {str(e)}")
                break
        
        # 循环结束,处理断开
        logger.info("数据读取循环结束")
        self._on_connection_lost()
    
    def _flush_send_queue(self):
        """刷新发送队列(批量发送)"""
        try:
            while not self._send_queue.empty():
                data = self._send_queue.get_nowait()
                if self.channel and not self.channel.closed:
                    self.channel.send(data)
                self._send_queue.task_done()
        except Exception as e:
            logger.error(f"刷新发送队列失败: {e}")
    
    def _start_heartbeat_thread(self):
        """启动心跳检测线程"""
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"SSH-Heartbeat-{self.session_info.get('host', 'unknown')}"
        )
        self._heartbeat_thread.start()
        logger.debug("心跳检测线程已启动")
    
    def _heartbeat_loop(self):
        """
        心跳检测循环
        
        功能:
        - 定期发送心跳包
        - 检测连接活跃度
        - 触发自动重连
        """
        logger.debug("心跳检测循环开始")
        
        while self._running and self.is_connected:
            try:
                time.sleep(self.heartbeat_interval)
                
                if not self._running or not self.is_connected:
                    break
                
                current_time = time.time()
                time_since_activity = current_time - self._last_activity_time
                
                # 检查是否超时
                if time_since_activity > self.heartbeat_timeout:
                    logger.warning(f"连接超时({time_since_activity:.1f}秒无活动)")
                    
                    if self.auto_reconnect:
                        self._trigger_reconnect()
                    else:
                        self._on_connection_lost()
                    break
                
                # 发送心跳(通过transport)
                if self.transport and self.transport.is_active():
                    try:
                        self.transport.send_ignore()
                        self._last_heartbeat_time = current_time
                        logger.debug("心跳发送成功")
                    except Exception as e:
                        logger.warning(f"心跳发送失败: {e}")
                        # 可能是连接问题,尝试重连
                        if self.auto_reconnect:
                            self._trigger_reconnect()
                        break
                        
            except Exception as e:
                logger.error(f"心跳循环异常: {e}", exc_info=True)
                break
        
        logger.debug("心跳检测循环结束")
    
    def send_data(self, data: str):
        """
        发送数据到SSH服务器(线程安全)
        
        Args:
            data: 要发送的字符串
        """
        if not self.is_connected or not self.channel:
            logger.warning("连接未建立,无法发送数据")
            return
        
        try:
            # 直接发送(低延迟)
            if self.channel and not self.channel.closed:
                self.channel.send(data)
                self._last_activity_time = time.time()
        except Exception as e:
            logger.error(f"发送数据失败: {e}")
            self.error_occurred.emit(f"发送数据失败: {str(e)}")
    
    def disconnect(self):
        """优雅地断开SSH连接"""
        if not self._running:
            return
        
        logger.info("正在断开SSH连接...")
        self._set_state(self.STATE_DISCONNECTING)
        self._running = False
        self.auto_reconnect = False  # 禁用自动重连
        
        # 等待线程结束
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=3)
        
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2)
        
        # 关闭channel
        if self.channel:
            try:
                self.channel.close()
            except Exception as e:
                logger.debug(f"关闭channel异常: {e}")
            finally:
                self.channel = None
        
        # 关闭transport
        if self.transport:
            try:
                self.transport.close()
            except Exception as e:
                logger.debug(f"关闭transport异常: {e}")
            finally:
                self.transport = None
        
        # 关闭client
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.debug(f"关闭client异常: {e}")
            finally:
                self.client = None
        
        # 清空队列
        self._clear_send_queue()
        
        # 更新状态
        self._set_state(self.STATE_DISCONNECTED)
        self.connection_status.emit(self.STATE_DISCONNECTED)
        
        logger.info("SSH连接已断开")
    
    def _clear_send_queue(self):
        """清空发送队列"""
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
                self._send_queue.task_done()
            except:
                break
    
    def _on_connection_lost(self):
        """连接丢失时的处理"""
        if not self._running:
            return
        
        logger.warning("连接已丢失")
        self._set_state(self.STATE_DISCONNECTED)
        self._running = False
        
        # 触发自动重连
        if self.auto_reconnect:
            self._trigger_reconnect()
        else:
            self.connection_status.emit(self.STATE_DISCONNECTED)
    
    def _trigger_reconnect(self):
        """触发重连(指数退避)"""
        if not self._running:
            return
        
        self._reconnect_attempts += 1
        
        if self._reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"重连次数超限({self.max_reconnect_attempts}),停止重连")
            self.error_occurred.emit("重连失败: 超过最大重连次数")
            self.connection_status.emit("error")
            return
        
        # 计算退避延迟
        delay = min(
            self.reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
            self.max_reconnect_delay
        )
        
        logger.info(f"将在 {delay:.1f} 秒后尝试第 {self._reconnect_attempts} 次重连...")
        self.reconnecting.emit(self._reconnect_attempts)
        self._set_state(self.STATE_RECONNECTING)
        
        # 在延迟后重连
        reconnect_thread = threading.Thread(
            target=self._delayed_reconnect,
            args=(delay,),
            daemon=True,
            name=f"SSH-Reconnect-{self.session_info.get('host', 'unknown')}"
        )
        reconnect_thread.start()
    
    def _delayed_reconnect(self, delay: float):
        """延迟后执行重连"""
        time.sleep(delay)
        
        if not self.auto_reconnect:
            return
        
        logger.info("开始重连...")
        
        # 使用保存的参数重连
        params = self._connect_params
        self.connect(
            host=params['host'],
            port=params['port'],
            username=params['username'],
            password=params.get('password'),
            key_file=params.get('key_file'),
            timeout=params['timeout'],
            auto_reconnect=True
        )
    
    def resize_terminal(self, width: int, height: int):
        """
        调整终端大小
        
        Args:
            width: 终端宽度(字符数)
            height: 终端高度(行数)
        """
        if self.is_connected and self.channel:
            try:
                self.channel.resize_pty(width=width, height=height)
                self.term_width = width
                self.term_height = height
                logger.debug(f"终端大小已调整: {width}x{height}")
            except Exception as e:
                logger.error(f"调整终端大小失败: {e}")
    
    def get_session_info(self) -> dict:
        """获取会话信息"""
        return self.session_info.copy()
    
    def __del__(self):
        """析构函数: 确保连接被清理"""
        self.disconnect()


# 导入socket(用于异常处理)
import socket
