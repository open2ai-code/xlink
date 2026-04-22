# -*- coding: utf-8 -*-
"""
测试AsyncSSH数据接收
"""

import asyncio
import asyncssh
import sys

async def test_ssh():
    """测试SSH连接"""
    print("正在连接SSH服务器...")
    
    try:
        # 连接到SSH服务器
        conn = await asyncssh.connect(
            host='192.168.0.100',  # 替换为你的服务器
            port=22,
            username='root',  # 替换为你的用户名
            password='your_password',  # 替换为你的密码
            known_hosts=None,
        )
        
        print("SSH连接成功!")
        
        # 创建交互式shell
        class TestSession(asyncssh.SSHClientSession):
            def connection_made(self, chan):
                print("Session连接已建立")
                self._chan = chan
            
            def data_received(self, data, datatype):
                print(f"收到数据: {len(data)} 字符")
                print(f"数据内容: {repr(data[:200])}")
                print("---")
            
            def connection_lost(self, exc):
                print(f"连接丢失: {exc}")
        
        print("正在创建交互式shell...")
        chan, process = await conn.create_session(
            lambda: TestSession(),
            command=None,
            term_type='xterm-256color',
            term_size=(120, 40),
            encoding='utf-8'
        )
        
        print("Shell创建成功!")
        print("等待数据...")
        
        # 等待10秒接收数据
        await asyncio.sleep(10)
        
        # 关闭连接
        conn.close()
        await conn.wait_closed()
        
    except Exception as e:
        print(f"连接失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_ssh())
