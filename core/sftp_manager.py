# -*- coding: utf-8 -*-
"""
SFTP文件管理模块 - AsyncSSH版本
封装asyncssh的SFTP功能,提供文件传输和目录操作功能
"""

import os
import asyncio
import threading
import stat
from pathlib import Path
from typing import List, Dict, Optional, Callable
from PySide6.QtCore import QObject, Signal as pyqtSignal
import asyncssh
from core.logger import get_logger


logger = get_logger("SFTPManager")


class SFTPManager(QObject):
    """SFTP连接和文件操作管理器(AsyncSSH版本)"""
    
    # 信号定义
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)  # current, total (bytes)
    operation_completed = pyqtSignal(str)  # operation name
    
    def __init__(self):
        super().__init__()
        self.conn = None
        self.sftp = None
        
        # 异步事件循环和线程
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        
        self.is_connected = False
        self.current_path = "/"
    
    def _start_asyncio_loop(self):
        """启动异步事件循环线程"""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._ready_event.set()
            self._loop.run_forever()
        
        self._thread = threading.Thread(target=run_loop, daemon=True, name="SFTP-AsyncIO")
        self._thread.start()
        self._ready_event.wait()
    
    def _stop_asyncio_loop(self):
        """停止异步事件循环"""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
    
    def _run_coroutine(self, coro):
        """在异步线程中运行协程"""
        if not self._loop:
            raise RuntimeError("异步事件循环未启动")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)
    
    def connect(self, hostname: str, port: int, username: str, 
                password: str = None, key_file: str = None) -> bool:
        """
        连接SFTP服务器
        
        Args:
            hostname: 主机地址
            port: 端口号
            username: 用户名
            password: 密码
            key_file: 私钥文件路径
            
        Returns:
            连接是否成功
        """
        # 启动异步事件循环
        if not self._loop:
            self._start_asyncio_loop()
        
        try:
            logger.info(f"正在连接SFTP服务器: {hostname}:{port}")
            
            # 连接参数
            connect_kwargs = {
                'host': hostname,
                'port': port,
                'username': username,
                'known_hosts': None,
                'connect_timeout': 10
            }
            
            if password:
                connect_kwargs['password'] = password
            elif key_file:
                connect_kwargs['client_keys'] = [key_file]
            
            # 建立连接并打开SFTP
            result = self._run_coroutine(self._do_connect(**connect_kwargs))
            
            if result:
                self.is_connected = True
                logger.info("SFTP连接成功")
                self.connected.emit()
                return True
            else:
                self.is_connected = False
                return False
            
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_connected = False
            return False
    
    async def _do_connect(self, **kwargs):
        """异步执行连接"""
        try:
            self.conn = await asyncssh.connect(**kwargs)
            self.sftp = await self.conn.start_sftp_client()
            return True
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def disconnect(self):
        """断开SFTP连接"""
        try:
            if self._loop and self._loop.is_running():
                self._run_coroutine(self._do_disconnect())
            
            self.is_connected = False
            logger.info("SFTP连接已断开")
            self.disconnected.emit()
            
        except Exception as e:
            logger.error(f"断开SFTP连接失败: {e}")
    
    async def _do_disconnect(self):
        """异步断开连接"""
        if self.sftp:
            await self.sftp.close()
            self.sftp = None
        
        if self.conn:
            self.conn.close()
            await self.conn.wait_closed()
            self.conn = None
    
    def list_directory(self, path: str = None) -> List[Dict]:
        """
        列出目录内容
        
        Args:
            path: 目录路径,默认为当前路径
            
        Returns:
            文件列表,每个元素包含: name, size, mtime, is_dir, permissions
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            return []
        
        try:
            target_path = path if path else self.current_path
            items = self._run_coroutine(self._do_list_directory(target_path))
            
            self.current_path = target_path
            logger.debug(f"列出目录 {target_path}: {len(items)} 个项目")
            return items
            
        except Exception as e:
            error_msg = f"列出目录失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
    
    async def _do_list_directory(self, path: str) -> List[Dict]:
        """异步列出目录"""
        items = []
        
        for attr in await self.sftp.readdir(path):
            item = {
                'name': attr.filename,
                'size': attr.size,
                'mtime': attr.mtime,
                'is_dir': stat.S_ISDIR(attr.permissions),
                'permissions': stat.filemode(attr.permissions)
            }
            items.append(item)
        
        # 按名称排序,文件夹在前
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        return items
    
    def upload_file(self, local_path: str, remote_path: str, 
                    progress_callback: Callable = None) -> bool:
        """
        上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数 callback(current, total)
            
        Returns:
            是否成功
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            return False
        
        try:
            logger.info(f"上传文件: {local_path} -> {remote_path}")
            
            # 获取文件大小
            file_size = os.path.getsize(local_path)
            
            # 定义进度回调
            def callback(transferred, total):
                self.progress_updated.emit(transferred, file_size)
                if progress_callback:
                    progress_callback(transferred, file_size)
            
            # 上传文件
            result = self._run_coroutine(
                self._do_upload(local_path, remote_path, callback)
            )
            
            if result:
                logger.info(f"文件上传成功: {remote_path}")
                self.operation_completed.emit("upload")
                return True
            else:
                return False
            
        except Exception as e:
            error_msg = f"上传文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def _do_upload(self, local_path, remote_path, callback):
        """异步上传文件"""
        try:
            await self.sftp.put(local_path, remote_path)
            return True
        except Exception as e:
            logger.error(f"上传失败: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str,
                      progress_callback: Callable = None) -> bool:
        """
        下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径
            progress_callback: 进度回调函数 callback(current, total)
            
        Returns:
            是否成功
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            return False
        
        try:
            logger.info(f"下载文件: {remote_path} -> {local_path}")
            
            # 获取文件大小
            file_attr = self._run_coroutine(self.sftp.stat(remote_path))
            file_size = file_attr.size
            
            # 定义进度回调
            def callback(transferred, total):
                self.progress_updated.emit(transferred, file_size)
                if progress_callback:
                    progress_callback(transferred, file_size)
            
            # 下载文件
            result = self._run_coroutine(
                self._do_download(remote_path, local_path, callback)
            )
            
            if result:
                logger.info(f"文件下载成功: {local_path}")
                self.operation_completed.emit("download")
                return True
            else:
                return False
            
        except Exception as e:
            error_msg = f"下载文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def _do_download(self, remote_path, local_path, callback):
        """异步下载文件"""
        try:
            await self.sftp.get(remote_path, local_path)
            return True
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False
    
    def delete(self, path: str, is_dir: bool = False) -> bool:
        """
        删除文件或文件夹
        
        Args:
            path: 文件/文件夹路径
            is_dir: 是否为文件夹
            
        Returns:
            是否成功
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            return False
        
        try:
            result = self._run_coroutine(self._do_delete(path, is_dir))
            
            if result:
                if is_dir:
                    logger.info(f"删除文件夹成功: {path}")
                else:
                    logger.info(f"删除文件成功: {path}")
                
                self.operation_completed.emit("delete")
                return True
            else:
                return False
            
        except Exception as e:
            error_msg = f"删除失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def _do_delete(self, path: str, is_dir: bool):
        """异步删除文件或文件夹"""
        try:
            if is_dir:
                await self._remove_dir_recursive(path)
            else:
                await self.sftp.remove(path)
            return True
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False
    
    async def _remove_dir_recursive(self, path: str):
        """递归删除文件夹"""
        for attr in await self.sftp.readdir(path):
            item_path = path.rstrip('/') + '/' + attr.filename
            if stat.S_ISDIR(attr.permissions):
                await self._remove_dir_recursive(item_path)
            else:
                await self.sftp.remove(item_path)
        await self.sftp.rmdir(path)
    
    def mkdir(self, path: str) -> bool:
        """
        创建文件夹
        
        Args:
            path: 文件夹路径
            
        Returns:
            是否成功
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            return False
        
        try:
            result = self._run_coroutine(self._do_mkdir(path))
            
            if result:
                logger.info(f"创建文件夹成功: {path}")
                self.operation_completed.emit("mkdir")
                return True
            else:
                return False
            
        except Exception as e:
            error_msg = f"创建文件夹失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def _do_mkdir(self, path: str):
        """异步创建文件夹"""
        try:
            await self.sftp.mkdir(path)
            return True
        except Exception as e:
            logger.error(f"创建文件夹失败: {e}")
            return False
    
    def rename(self, old_path: str, new_path: str) -> bool:
        """
        重命名文件或文件夹
        
        Args:
            old_path: 原路径
            new_path: 新路径
            
        Returns:
            是否成功
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            return False
        
        try:
            result = self._run_coroutine(self._do_rename(old_path, new_path))
            
            if result:
                logger.info(f"重命名成功: {old_path} -> {new_path}")
                self.operation_completed.emit("rename")
                return True
            else:
                return False
            
        except Exception as e:
            error_msg = f"重命名失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def _do_rename(self, old_path: str, new_path: str):
        """异步重命名"""
        try:
            await self.sftp.rename(old_path, new_path)
            return True
        except Exception as e:
            logger.error(f"重命名失败: {e}")
            return False
    
    def get_current_path(self) -> str:
        """获取当前路径"""
        return self.current_path
    
    def change_directory(self, path: str) -> bool:
        """
        切换目录
        
        Args:
            path: 目标目录路径
            
        Returns:
            是否成功
        """
        if not self.is_connected:
            return False
        
        try:
            # 检查目录是否存在
            result = self._run_coroutine(self._do_change_directory(path))
            return result
        except Exception as e:
            logger.error(f"切换目录失败: {e}")
            return False
    
    async def _do_change_directory(self, path: str):
        """异步切换目录"""
        try:
            await self.sftp.stat(path)
            self.current_path = path
            logger.debug(f"切换目录到: {path}")
            return True
        except Exception as e:
            logger.error(f"切换目录失败: {e}")
            return False
    
    def get_directory_tree(self, start_path: str = "/") -> List[Dict]:
        """
        获取目录树结构(递归获取所有子目录)
        
        Args:
            start_path: 起始路径
            
        Returns:
            目录树列表,每个元素包含: name, path, children
        """
        if not self.is_connected:
            return []
        
        try:
            tree = self._run_coroutine(self._do_get_directory_tree(start_path))
            return tree
        except Exception as e:
            logger.error(f"获取目录树失败: {e}")
            return []
    
    async def _do_get_directory_tree(self, start_path: str) -> List[Dict]:
        """异步获取目录树"""
        tree = []
        await self._build_directory_tree(start_path, tree)
        return tree
    
    async def _build_directory_tree(self, path: str, tree_list: List[Dict]):
        """异步递归构建目录树"""
        try:
            for attr in await self.sftp.readdir(path):
                if stat.S_ISDIR(attr.permissions):
                    dir_name = attr.filename
                    dir_path = path.rstrip('/') + '/' + dir_name
                    
                    node = {
                        'name': dir_name,
                        'path': dir_path,
                        'children': []
                    }
                    tree_list.append(node)
                    
                    # 递归获取子目录
                    await self._build_directory_tree(dir_path, node['children'])
        except Exception as e:
            logger.debug(f"读取目录 {path} 失败: {e}")
