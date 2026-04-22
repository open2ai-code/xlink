# -*- coding: utf-8 -*-
"""
全局异步事件循环管理器
提供共享的asyncio事件循环,避免SSH和SFTP各自创建独立线程
"""

import asyncio
import threading
from typing import Optional, Callable, Any
from core.logger import get_logger


logger = get_logger("AsyncEventLoopManager")


class AsyncEventLoopManager:
    """
    全局异步事件循环管理器(单例模式)
    
    特性:
    - 单例模式,全局共享
    - 后台线程运行asyncio事件循环
    - 线程安全的协程调度
    - 统一的生命周期管理
    """
    
    _instance: Optional['AsyncEventLoopManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._initialized = True
        
        logger.debug("AsyncEventLoopManager实例已创建")
    
    def start(self):
        """启动异步事件循环"""
        if self._loop and self._loop.is_running():
            logger.warning("事件循环已在运行中")
            return
        
        logger.info("正在启动异步事件循环...")
        
        def run_loop():
            """在后台线程中运行事件循环"""
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._ready_event.set()
            
            logger.info("异步事件循环已启动")
            
            # 运行事件循环直到收到关闭信号
            self._loop.run_forever()
            
            # 清理
            self._loop.close()
            self._loop = None
            logger.info("异步事件循环已关闭")
        
        self._thread = threading.Thread(
            target=run_loop,
            daemon=True,
            name="Global-AsyncIO"
        )
        self._thread.start()
        
        # 等待事件循环就绪
        self._ready_event.wait(timeout=5.0)
        
        if not self._ready_event.is_set():
            raise RuntimeError("异步事件循环启动超时")
        
        logger.info("异步事件循环启动完成")
    
    def stop(self):
        """停止异步事件循环"""
        if not self._loop or not self._loop.is_running():
            logger.warning("事件循环未运行")
            return
        
        logger.info("正在停止异步事件循环...")
        
        # 在事件循环中调用stop
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._shutdown_event.set()
        
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        
        logger.info("异步事件循环已停止")
    
    def run_coroutine(self, coro, timeout: float = 30.0) -> Any:
        """
        在异步线程中运行协程(同步等待结果)
        
        Args:
            coro: 协程对象
            timeout: 超时时间(秒)
            
        Returns:
            协程的返回值
            
        Raises:
            RuntimeError: 事件循环未启动
            asyncio.TimeoutError: 执行超时
        """
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("异步事件循环未启动")
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        
        try:
            result = future.result(timeout=timeout)
            return result
        except asyncio.TimeoutError:
            future.cancel()
            logger.error(f"协程执行超时: {timeout}秒")
            raise
        except Exception as e:
            logger.error(f"协程执行失败: {e}")
            raise
    
    def submit_coroutine(self, coro) -> asyncio.Future:
        """
        提交协程异步执行(不等待结果)
        
        Args:
            coro: 协程对象
            
        Returns:
            Future对象
        """
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("异步事件循环未启动")
        
        return asyncio.run_coroutine_threadsafe(coro, self._loop)
    
    def call_soon(self, callback: Callable, *args) -> asyncio.Handle:
        """
        在事件循环中尽快调用回调函数
        
        Args:
            callback: 回调函数
            *args: 回调函数参数
            
        Returns:
            Handle对象
        """
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("异步事件循环未启动")
        
        return self._loop.call_soon_threadsafe(callback, *args)
    
    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """获取事件循环对象"""
        return self._loop
    
    @property
    def is_running(self) -> bool:
        """检查事件循环是否在运行"""
        return self._loop is not None and self._loop.is_running()


# 全局单例
asyncio_manager = AsyncEventLoopManager()
