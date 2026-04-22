# -*- coding: utf-8 -*-
"""
SFTP文件管理模块 - AsyncSSH版本
封装asyncssh的SFTP功能,提供文件传输和目录操作功能
"""

import os
import asyncio
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
    directory_listed = pyqtSignal(list)  # directory listing result
    file_operation_result = pyqtSignal(bool, str)  # success, operation name for file ops
    directory_tree_ready = pyqtSignal(list)  # directory tree ready signal
    
    def __init__(self):
        super().__init__()
        self.conn = None
        self.sftp = None
        
        self.is_connected = False
        self.current_path = "/"
    
    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """获取当前事件循环"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            # 如果没有运行中的事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    def connect(self, hostname: str, port: int, username: str, 
                password: str = None, key_file: str = None) -> bool:
        """
        连接SFTP服务器（异步）
        
        Args:
            hostname: 主机地址
            port: 端口号
            username: 用户名
            password: 密码
            key_file: 私钥文件路径
            
        Returns:
            连接是否成功
        """
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
            
            # 使用asyncio.ensure_future异步执行连接
            asyncio.ensure_future(self._do_connect_and_open_sftp(**connect_kwargs))
            return True  # 立即返回，连接结果通过信号通知
            
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_connected = False
            return False
    
    async def _do_connect_and_open_sftp(self, **kwargs):
        """异步执行连接并打开SFTP"""
        try:
            self.conn = await asyncssh.connect(**kwargs)
            self.sftp = await self.conn.start_sftp_client()
            self.is_connected = True
            logger.info("SFTP连接成功")
            self.connected.emit()
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_connected = False
    
    def disconnect(self):
        """断开SFTP连接"""
        try:
            # 使用asyncio.ensure_future异步执行断开连接
            asyncio.ensure_future(self._do_disconnect())
            
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
        
        self.is_connected = False
        logger.info("SFTP连接已断开")
        self.disconnected.emit()
    
    def list_directory_async(self, path: str = None):
        """
        异步列出目录内容
        
        Args:
            path: 目录路径,默认为当前路径
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            self.directory_listed.emit([])
            return
        
        try:
            target_path = path if path else self.current_path
            logger.debug(f"开始列出目录 {target_path}")
            
            # 使用asyncio.ensure_future异步执行
            asyncio.ensure_future(self._do_list_directory_async(target_path))
            
        except Exception as e:
            error_msg = f"列出目录失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.directory_listed.emit([])

    def list_directory(self, path: str = None) -> List[Dict]:
        """
        同步列出目录内容 - 已废弃，请使用 list_directory_async
        
        Args:
            path: 目录路径,默认为当前路径
            
        Returns:
            文件列表,每个元素包含: name, size, mtime, is_dir, permissions
        """
        logger.warning("list_directory 已废弃，请使用 list_directory_async")
        if not self.is_connected:
            logger.error("SFTP未连接")
            return []
        
        try:
            target_path = path if path else self.current_path
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                items = loop.run_until_complete(self._do_list_directory(target_path))
                self.current_path = target_path
                logger.debug(f"列出目录 {target_path}: {len(items)} 个项目")
                return items
            finally:
                loop.close()
        except Exception as e:
            error_msg = f"列出目录失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []

    async def _do_list_directory_async(self, path: str):
        """异步列出目录 - 发送信号返回结果"""
        try:
            items = []
            
            for name in await self.sftp.readdir(path):
                # SFTPName对象包含filename和attrs属性
                attrs = name.attrs
                item = {
                    'name': name.filename,
                    'size': attrs.size,
                    'mtime': attrs.mtime,
                    'is_dir': stat.S_ISDIR(attrs.permissions),
                    'permissions': stat.filemode(attrs.permissions)
                }
                items.append(item)
            
            # 按名称排序,文件夹在前
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            self.current_path = path
            logger.debug(f"列出目录 {path}: {len(items)} 个项目")
            self.directory_listed.emit(items)
            
        except Exception as e:
            error_msg = f"列出目录失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.directory_listed.emit([])

    async def _do_list_directory(self, path: str) -> List[Dict]:
        """异步列出目录 - 返回结果"""
        items = []
        
        for name in await self.sftp.readdir(path):
            # SFTPName对象包含filename和attrs属性
            attrs = name.attrs
            item = {
                'name': name.filename,
                'size': attrs.size,
                'mtime': attrs.mtime,
                'is_dir': stat.S_ISDIR(attrs.permissions),
                'permissions': stat.filemode(attrs.permissions)
            }
            items.append(item)
        
        # 按名称排序,文件夹在前
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        return items
    
    def upload_file_async(self, local_path: str, remote_path: str, 
                         progress_callback: Callable = None):
        """
        异步上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数 callback(current, total)
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            self.file_operation_result.emit(False, "upload")
            return
        
        try:
            logger.info(f"上传文件: {local_path} -> {remote_path}")
            
            # 获取文件大小
            file_size = os.path.getsize(local_path)
            
            # 定义进度回调
            def callback(transferred, total):
                self.progress_updated.emit(transferred, file_size)
                if progress_callback:
                    progress_callback(transferred, file_size)
            
            # 使用asyncio.ensure_future异步执行上传
            asyncio.ensure_future(
                self._do_upload_async(local_path, remote_path, callback, file_size)
            )
            
        except Exception as e:
            error_msg = f"上传文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "upload")

    async def _do_upload_async(self, local_path, remote_path, callback, file_size):
        """异步上传文件 - 通过信号返回结果"""
        try:
            await self.sftp.put(local_path, remote_path, progress_handler=callback)
            logger.info(f"文件上传成功: {remote_path}")
            self.operation_completed.emit("upload")
            self.file_operation_result.emit(True, "upload")
        except Exception as e:
            error_msg = f"上传文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "upload")
    
    def download_file_async(self, remote_path: str, local_path: str,
                           progress_callback: Callable = None):
        """
        异步下载文件
        
        Args:
            remote_path: 远程文件路径
            local_path: 本地文件路径
            progress_callback: 进度回调函数 callback(current, total)
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            self.file_operation_result.emit(False, "download")
            return
        
        try:
            logger.info(f"下载文件: {remote_path} -> {local_path}")
            
            # 使用asyncio.ensure_future异步执行下载，同时获取文件大小
            asyncio.ensure_future(
                self._do_download_with_size_check(remote_path, local_path, progress_callback)
            )
            
        except Exception as e:
            error_msg = f"下载文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "download")

    async def _do_download_with_size_check(self, remote_path, local_path, progress_callback):
        """异步下载文件并检查大小 - 通过信号返回结果"""
        try:
            # 先获取文件大小
            file_attr = await self.sftp.stat(remote_path)
            file_size = file_attr.size
            
            # 定义进度回调
            def callback(transferred, total):
                self.progress_updated.emit(transferred, file_size)
                if progress_callback:
                    progress_callback(transferred, file_size)
            
            # 执行下载
            await self.sftp.get(remote_path, local_path, progress_handler=callback)
            logger.info(f"文件下载成功: {local_path}")
            self.operation_completed.emit("download")
            self.file_operation_result.emit(True, "download")
        except Exception as e:
            error_msg = f"下载文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "download")
    
    def delete_async(self, path: str, is_dir: bool = False):
        """
        异步删除文件或文件夹
        
        Args:
            path: 文件/文件夹路径
            is_dir: 是否为文件夹
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            self.file_operation_result.emit(False, "delete")
            return
        
        try:
            # 使用asyncio.ensure_future异步执行删除
            asyncio.ensure_future(self._do_delete_async(path, is_dir))
            
        except Exception as e:
            error_msg = f"删除失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "delete")

    async def _do_delete_async(self, path: str, is_dir: bool):
        """异步删除文件或文件夹 - 通过信号返回结果"""
        try:
            if is_dir:
                await self._remove_dir_recursive(path)
            else:
                await self.sftp.remove(path)
            
            if is_dir:
                logger.info(f"删除文件夹成功: {path}")
            else:
                logger.info(f"删除文件成功: {path}")
            
            self.operation_completed.emit("delete")
            self.file_operation_result.emit(True, "delete")
        except Exception as e:
            error_msg = f"删除失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "delete")
    
    async def _remove_dir_recursive(self, path: str):
        """递归删除文件夹"""
        for name in await self.sftp.readdir(path):
            item_path = path.rstrip('/') + '/' + name.filename
            if stat.S_ISDIR(name.attrs.permissions):
                await self._remove_dir_recursive(item_path)
            else:
                await self.sftp.remove(item_path)
        await self.sftp.rmdir(path)
    
    def mkdir_async(self, path: str):
        """
        异步创建文件夹
        
        Args:
            path: 文件夹路径
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            self.file_operation_result.emit(False, "mkdir")
            return
        
        try:
            # 使用asyncio.ensure_future异步执行创建
            asyncio.ensure_future(self._do_mkdir_async(path))
            
        except Exception as e:
            error_msg = f"创建文件夹失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "mkdir")

    async def _do_mkdir_async(self, path: str):
        """异步创建文件夹 - 通过信号返回结果"""
        try:
            await self.sftp.mkdir(path)
            logger.info(f"创建文件夹成功: {path}")
            self.operation_completed.emit("mkdir")
            self.file_operation_result.emit(True, "mkdir")
        except Exception as e:
            error_msg = f"创建文件夹失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "mkdir")
    
    def rename_async(self, old_path: str, new_path: str):
        """
        异步重命名文件或文件夹
        
        Args:
            old_path: 原路径
            new_path: 新路径
        """
        if not self.is_connected:
            logger.error("SFTP未连接")
            self.file_operation_result.emit(False, "rename")
            return
        
        try:
            # 使用asyncio.ensure_future异步执行重命名
            asyncio.ensure_future(self._do_rename_async(old_path, new_path))
            
        except Exception as e:
            error_msg = f"重命名失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "rename")

    async def _do_rename_async(self, old_path: str, new_path: str):
        """异步重命名 - 通过信号返回结果"""
        try:
            await self.sftp.rename(old_path, new_path)
            logger.info(f"重命名成功: {old_path} -> {new_path}")
            self.operation_completed.emit("rename")
            self.file_operation_result.emit(True, "rename")
        except Exception as e:
            error_msg = f"重命名失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.file_operation_result.emit(False, "rename")
    
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
            # 使用异步方式切换目录
            asyncio.ensure_future(self._do_change_directory_async(path))
            return True
        except Exception as e:
            logger.error(f"切换目录失败: {e}")
            return False
    
    async def _do_change_directory_async(self, path: str):
        """异步切换目录"""
        try:
            await self.sftp.stat(path)
            self.current_path = path
            logger.debug(f"切换目录到: {path}")
            # 触发目录列表刷新
            self.list_directory_async(path)
        except Exception as e:
            logger.error(f"切换目录失败: {e}")
            self.error_occurred.emit(f"切换目录失败: {e}")
    
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
            # 使用异步方式获取目录树
            asyncio.ensure_future(self._do_get_directory_tree_async(start_path))
            return []  # 异步操作，立即返回空列表，结果通过信号返回
        except Exception as e:
            logger.error(f"获取目录树失败: {e}")
            return []
    
    async def _do_get_directory_tree_async(self, start_path: str):
        """异步获取目录树并通过信号返回"""
        try:
            tree = []
            await self._build_directory_tree(start_path, tree)
            self.directory_tree_ready.emit(tree)
        except Exception as e:
            logger.error(f"获取目录树失败: {e}")
            self.error_occurred.emit(f"获取目录树失败: {e}")
    
    async def _build_directory_tree(self, path: str, tree_list: List[Dict]):
        """异步递归构建目录树"""
        try:
            for name in await self.sftp.readdir(path):
                if stat.S_ISDIR(name.attrs.permissions):
                    dir_name = name.filename
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
