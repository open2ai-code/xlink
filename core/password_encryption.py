"""
密码加密模块
使用cryptography库对密码进行加密存储
"""

import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from core.logger import get_logger


logger = get_logger("PasswordEncryption")


class PasswordEncryption:
    """密码加密解密工具类"""
    
    _instance = None
    _fernet = None
    _key_file = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化加密器"""
        if self._fernet is None:
            self._init_encryption()
    
    def _init_encryption(self):
        """初始化加密密钥"""
        try:
            # 获取密钥文件路径
            base_dir = Path(__file__).parent.parent
            self._key_file = base_dir / "config" / "encryption.key"
            
            # 确保配置目录存在
            self._key_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 加载或生成密钥
            if self._key_file.exists():
                self._load_key()
            else:
                self._generate_key()
            
            logger.info("密码加密系统初始化完成")
            
        except Exception as e:
            logger.error(f"初始化密码加密失败: {e}")
            self._fernet = None
    
    def _generate_key(self):
        """生成新的加密密钥"""
        try:
            # 生成随机密钥
            key = Fernet.generate_key()
            
            # 保存到文件
            with open(self._key_file, 'wb') as f:
                f.write(key)
            
            self._fernet = Fernet(key)
            logger.info("生成新的加密密钥")
            
        except Exception as e:
            logger.error(f"生成加密密钥失败: {e}")
    
    def _load_key(self):
        """从文件加载加密密钥"""
        try:
            with open(self._key_file, 'rb') as f:
                key = f.read()
            
            self._fernet = Fernet(key)
            logger.info("加载加密密钥成功")
            
        except Exception as e:
            logger.error(f"加载加密密钥失败: {e}")
            # 如果加载失败,生成新密钥
            self._generate_key()
    
    def encrypt_password(self, password: str) -> str:
        """
        加密密码
        
        Args:
            password: 明文密码
            
        Returns:
            加密后的密码(base64编码)
        """
        if not self._fernet:
            logger.warning("加密器未初始化,返回明文密码")
            return password
        
        if not password:
            return ""
        
        try:
            # 加密
            encrypted = self._fernet.encrypt(password.encode('utf-8'))
            
            # 转换为base64字符串
            encrypted_str = base64.b64encode(encrypted).decode('utf-8')
            
            return encrypted_str
            
        except Exception as e:
            logger.error(f"加密密码失败: {e}")
            # 加密失败时返回明文(兼容旧数据)
            return password
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        解密密码
        
        Args:
            encrypted_password: 加密后的密码(base64编码)
            
        Returns:
            明文密码
        """
        if not self._fernet:
            logger.warning("加密器未初始化,返回原始密码")
            return encrypted_password
        
        if not encrypted_password:
            return ""
        
        try:
            # 从base64解码
            encrypted_bytes = base64.b64decode(encrypted_password.encode('utf-8'))
            
            # 解密
            decrypted = self._fernet.decrypt(encrypted_bytes)
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            # 解密失败可能是旧数据(明文),直接返回
            logger.debug(f"解密失败(可能是明文密码): {e}")
            return encrypted_password
    
    def is_encrypted(self, password: str) -> bool:
        """
        检查密码是否已加密
        
        Args:
            password: 密码字符串
            
        Returns:
            True表示已加密,False表示明文
        """
        if not password:
            return False
        
        # 加密后的密码格式: base64编码的fernet token
        # 通常以特定字符开头,且长度较长
        try:
            # 尝试base64解码
            decoded = base64.b64decode(password.encode('utf-8'))
            
            # Fernet token有特定格式,长度至少45字节
            if len(decoded) >= 45:
                return True
            
            return False
            
        except Exception:
            # base64解码失败,说明是明文
            return False


# 全局实例
_password_encryption = None


def get_password_encryption() -> PasswordEncryption:
    """获取密码加密实例"""
    global _password_encryption
    if _password_encryption is None:
        _password_encryption = PasswordEncryption()
    return _password_encryption


def encrypt_password(password: str) -> str:
    """便捷函数: 加密密码"""
    return get_password_encryption().encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """便捷函数: 解密密码"""
    return get_password_encryption().decrypt_password(encrypted_password)
