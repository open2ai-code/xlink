# -*- coding: utf-8 -*-
"""
SFTP文件管理模块
封装paramiko的SFTPClient,提供文件传输和目录操作功能
"""

import os
import stat
from pathlib import Path
from typing import List, Dict, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
import paramiko
from core.logger import get_logger


logger = get_logger("SFTPManager")


class SFTPManager(QObject):
    """SFTP连接和文件操作管理器"""
    
    # 信号定义
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int)  # current, total (bytes)
    operation_completed = pyqtSignal(str)  # operation name
    
    def __init__(self):
        super().__init__()
        self.ssh_client = None
        self.sftp_client = None
        self.is_connected = False
        self.current_path = "/"
    
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
        try:
            logger.info(f"正在连接SFTP服务器: {hostname}:{port}")
            
            # 创建SSH客户端
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(
                paramiko.AutoAddPolicy()
            )
            
            # 连接参数
            connect_kwargs = {
                'hostname': hostname,
                'port': port,
                'username': username,
                'timeout': 10
            }
            
            if password:
                connect_kwargs['password'] = password
            elif key_file:
                connect_kwargs['key_filename'] = key_file
            
            # 建立连接
            self.ssh_client.connect(**connect_kwargs)
            
            # 打开SFTP会话
            self.sftp_client = self.ssh_client.open_sftp()
            self.is_connected = True
            
            logger.info("SFTP连接成功")
            self.connected.emit()
            return True
            
        except Exception as e:
            error_msg = f"SFTP连接失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.is_connected = False
            return False
    
    def disconnect(self):
        """断开SFTP连接"""
        try:
            if self.sftp_client:
                self.sftp_client.close()
                self.sftp_client = None
            
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
            
            self.is_connected = False
            logger.info("SFTP连接已断开")
            self.disconnected.emit()
            
        except Exception as e:
            logger.error(f"断开SFTP连接失败: {e}")
    
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
            items = []
            
            for attr in self.sftp_client.listdir_attr(target_path):
                item = {
                    'name': attr.filename,
                    'size': attr.st_size,
                    'mtime': attr.st_mtime,
                    'is_dir': stat.S_ISDIR(attr.st_mode),
                    'permissions': stat.filemode(attr.st_mode)
                }
                items.append(item)
            
            # 按名称排序,文件夹在前
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            self.current_path = target_path
            logger.debug(f"列出目录 {target_path}: {len(items)} 个项目")
            return items
            
        except Exception as e:
            error_msg = f"列出目录失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
    
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
            self.sftp_client.put(local_path, remote_path, callback=callback)
            
            logger.info(f"文件上传成功: {remote_path}")
            self.operation_completed.emit("upload")
            return True
            
        except Exception as e:
            error_msg = f"上传文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
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
            file_size = self.sftp_client.stat(remote_path).st_size
            
            # 定义进度回调
            def callback(transferred, total):
                self.progress_updated.emit(transferred, file_size)
                if progress_callback:
                    progress_callback(transferred, file_size)
            
            # 下载文件
            self.sftp_client.get(remote_path, local_path, callback=callback)
            
            logger.info(f"文件下载成功: {local_path}")
            self.operation_completed.emit("download")
            return True
            
        except Exception as e:
            error_msg = f"下载文件失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
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
            if is_dir:
                # 递归删除文件夹
                self._remove_dir_recursive(path)
                logger.info(f"删除文件夹成功: {path}")
            else:
                self.sftp_client.remove(path)
                logger.info(f"删除文件成功: {path}")
            
            self.operation_completed.emit("delete")
            return True
            
        except Exception as e:
            error_msg = f"删除失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    def _remove_dir_recursive(self, path: str):
        """递归删除文件夹"""
        for item in self.sftp_client.listdir_attr(path):
            item_path = path + '/' + item.filename
            if stat.S_ISDIR(item.st_mode):
                self._remove_dir_recursive(item_path)
            else:
                self.sftp_client.remove(item_path)
        self.sftp_client.rmdir(path)
    
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
            self.sftp_client.mkdir(path)
            logger.info(f"创建文件夹成功: {path}")
            self.operation_completed.emit("mkdir")
            return True
            
        except Exception as e:
            error_msg = f"创建文件夹失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
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
            self.sftp_client.rename(old_path, new_path)
            logger.info(f"重命名成功: {old_path} -> {new_path}")
            self.operation_completed.emit("rename")
            return True
            
        except Exception as e:
            error_msg = f"重命名失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
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
            self.sftp_client.stat(path)
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
            tree = []
            self._build_directory_tree(start_path, tree)
            return tree
        except Exception as e:
            logger.error(f"获取目录树失败: {e}")
            return []
    
    def _build_directory_tree(self, path: str, tree_list: List[Dict]):
        """
        递归构建目录树
        
        Args:
            path: 当前路径
            tree_list: 树列表(输出)
        """
        try:
            for attr in self.sftp_client.listdir_attr(path):
                if stat.S_ISDIR(attr.st_mode):
                    dir_name = attr.filename
                    dir_path = path.rstrip('/') + '/' + dir_name
                    
                    node = {
                        'name': dir_name,
                        'path': dir_path,
                        'children': []
                    }
                    tree_list.append(node)
                    
                    # 递归获取子目录
                    self._build_directory_tree(dir_path, node['children'])
        except Exception as e:
            logger.debug(f"读取目录 {path} 失败: {e}")
