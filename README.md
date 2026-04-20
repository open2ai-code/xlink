# XLink - SSH客户端

轻量、稳定、高颜值的SSH远程连接工具,对标Xshell,面向运维/开发者。

## 技术栈

- Python 3.10+
- PyQt6 (GUI框架)
- paramiko (SSH连接)
- JSON配置持久化
- 支持PyInstaller打包

## 功能特性

### 1. 会话管理
- ✅ 新增/编辑/删除SSH配置
- ✅ 分组管理会话
- ✅ 支持密码认证和RSA私钥认证
- ✅ JSON配置自动保存

### 2. 终端交互
- ✅ ANSI颜色显示
- ✅ UTF-8编码支持
- ✅ 文本选择与复制（鼠标拖拽选择，双击选择单词）
- ✅ 复制粘贴 (Ctrl+C/V)
- ✅ 清屏功能 (Ctrl+L)
- ✅ 命令历史记录 (上下箭头)

### 3. 连接能力
- ✅ 密码认证
- ✅ RSA私钥认证
- ✅ 超时处理
- ✅ 断线检测
- ✅ 实时状态提示

### 4. 界面布局
- ✅ 左侧会话列表(树形结构)
- ✅ 右侧多标签终端
- ✅ 底部状态栏

### 5. 基础体验
- ✅ 记住窗口大小
- ✅ 字体大小切换 (Ctrl+±)
- ✅ 深浅主题切换
- ✅ Unicode图标

### 6. 异常处理
- ✅ 连接失败友好提示
- ✅ 认证错误提示
- ✅ 网络中断提示
- ✅ 全局异常捕获,不崩溃

## 项目结构

```
XLink/
├── main.py                 # 主入口程序
├── requirements.txt        # 依赖清单
├── README.md              # 项目说明
├── config/
│   └── sessions.json      # 会话配置存储(自动生成)
├── core/
│   ├── __init__.py
│   ├── session_manager.py # 会话配置管理
│   ├── ssh_manager.py     # SSH连接管理
│   └── terminal_buffer.py # ANSI解析器
├── ui/
│   ├── __init__.py
│   ├── main_window.py     # 主窗口
│   ├── session_panel.py   # 会话列表面板
│   ├── terminal_widget.py # 终端控件
│   ├── tab_manager.py     # 标签页管理
│   ├── dialogs.py         # 对话框
│   └── theme.py           # 主题管理
└── resources/
    └── icons/             # 图标资源
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行程序

```bash
python main.py
```

### 3. 使用流程

1. **新建会话**: 点击左侧空白处右键 → 新建会话
2. **填写配置**: 输入主机地址、端口、用户名、密码/私钥
3. **连接服务器**: 双击会话节点或右键 → 连接
4. **多标签管理**: 可以打开多个会话,每个会话独立标签页
5. **切换主题**: 视图 → 主题 → 浅色/深色

## 快捷键

- `Ctrl+N` - 新建会话
- `Ctrl+Q` - 退出程序
- `Ctrl++` - 放大字体
- `Ctrl+-` - 缩小字体
- `Ctrl+C` - 复制(选中文本) / 发送中断信号(无选中)
- `Ctrl+V` - 粘贴
- `Ctrl+L` - 清屏
- `↑/↓` - 命令历史
- `F5` - 刷新会话列表

## 打包发布

使用PyInstaller打包为独立的exe文件:

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包程序
pyinstaller --name XLink --windowed --onefile main.py

# 生成的exe在 dist/XLink.exe
```

## 配置说明

会话配置保存在 `config/sessions.json`,格式如下:

```json
{
  "sessions": [
    {
      "id": "unique-uuid",
      "name": "会话名称",
      "group": "分组名称",
      "host": "主机地址",
      "port": 22,
      "username": "用户名",
      "auth_type": "password|key",
      "password": "密码",
      "key_file": "私钥路径",
      "timeout": 30
    }
  ],
  "settings": {
    "window_size": [1200, 800],
    "font_size": 12,
    "theme": "light"
  }
}
```

## 注意事项

1. **私钥格式**: 支持RSA/DSA/ECDSA/Ed25519格式的私钥文件
2. **编码**: 终端使用UTF-8编码,确保服务器locale设置为UTF-8
3. **防火墙**: 确保目标服务器22端口可访问
4. **权限**: 私钥文件需要有正确的读取权限

## 常见问题

### Q: 连接失败怎么办?
A: 检查以下几点:
- 主机地址和端口是否正确
- 网络是否可达(ping测试)
- 防火墙是否开放22端口
- 用户名和密码/私钥是否正确

### Q: 中文显示乱码?
A: 确保服务器locale设置为UTF-8:
```bash
# 查看当前locale
locale

# 如果没有设置UTF-8,执行:
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

### Q: 如何备份会话配置?
A: 复制 `config/sessions.json` 文件即可。

## 开发计划

- [ ] SFTP文件传输
- [ ] 端口转发
- [ ] 会话导入/导出
- [ ] 批量操作
- [ ] 日志记录
- [ ] 自动补全

## 许可证

MIT License

## 联系方式

如有问题或建议,欢迎反馈。

---

**XLink Team** © 2026
