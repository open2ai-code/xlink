"""
终端缓冲区模块
ANSI转义序列解析器,将ANSI颜色代码转换为Qt格式
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class TextSegment:
    """文本片段"""
    text: str
    fg_color: Optional[str] = None  # 前景色
    bg_color: Optional[str] = None  # 背景色
    bold: bool = False
    underline: bool = False


@dataclass
class TerminalCommand:
    """终端控制命令"""
    command_type: str  # 'clear', 'move_cursor', etc.
    params: dict = None  # 命令参数


class ANSIParser:
    """ANSI转义序列解析器"""
    
    # ANSI颜色映射表
    ANSI_COLORS = {
        30: "#000000",  # 黑色
        31: "#FF0000",  # 红色
        32: "#00FF00",  # 绿色
        33: "#FFFF00",  # 黄色
        34: "#0000FF",  # 蓝色
        35: "#FF00FF",  # 洋红
        36: "#00FFFF",  # 青色
        37: "#FFFFFF",  # 白色
        90: "#808080",  # 亮黑色(灰色)
        91: "#FF5555",  # 亮红色
        92: "#55FF55",  # 亮绿色
        93: "#FFFF55",  # 亮黄色
        94: "#5555FF",  # 亮蓝色
        95: "#FF55FF",  # 亮洋红
        96: "#55FFFF",  # 亮青色
        97: "#FFFFFF",  # 亮白色
    }
    
    # 背景色映射
    BG_COLORS = {
        40: "#000000",
        41: "#FF0000",
        42: "#00FF00",
        43: "#FFFF00",
        44: "#0000FF",
        45: "#FF00FF",
        46: "#00FFFF",
        47: "#FFFFFF",
        100: "#808080",
        101: "#FF5555",
        102: "#55FF55",
        103: "#FFFF55",
        104: "#5555FF",
        105: "#FF55FF",
        106: "#55FFFF",
        107: "#FFFFFF",
    }
    
    def __init__(self):
        # ANSI转义序列正则表达式
        # 匹配 \033[<params>m 格式
        self.ansi_pattern = re.compile(r'\033\[([0-9;]*)m')
        # 匹配光标移动等其他序列(简化处理,直接移除)
        self.cursor_pattern = re.compile(r'\033\[[0-9;]*[A-Hf]')
        # 匹配删除序列 \033[K (删除到行尾) \033[1K (删除到行首) \033[2K (删除整行)
        self.erase_pattern = re.compile(r'\033\[([0-2])?K')
        # 匹配所有清屏序列 \033[<n>J
        self.clear_pattern = re.compile(r'\033\[([0-2])?J')
        self.hide_cursor = re.compile(r'\033\[\?25[hl]')
        
        # 当前样式状态
        self.reset_state()
        
        # 控制命令列表
        self.commands = []
    
    def reset_state(self):
        """重置样式状态"""
        self.current_fg = None
        self.current_bg = None
        self.current_bold = False
        self.current_underline = False
        self.commands = []  # 重置命令列表
    
    def parse(self, text: str) -> List[TextSegment]:
        """
        解析包含ANSI转义序列的文本
        
        Args:
            text: 包含ANSI转义序列的原始文本
            
        Returns:
            文本片段列表
        """
        segments = []
        
        # 重置命令列表
        self.commands = []
        
        print(f"[ANSI] ===== 开始解析 =====")
        print(f"[ANSI] 输入文本: {repr(text)}")
        print(f"[ANSI] 十六进制: {text.encode('utf-8').hex()}")
        
        # 检测清屏命令 - 支持所有格式
        # \033[J, \033[0J, \033[1J, \033[2J, \033[3J
        # 注意: 必须先检测组合序列(如 \033[H\033[2J),再检测单个序列
        clear_patterns = [
            r'\033\[H\033\[2J',  # 光标归位+清屏(最常见)
            r'\033\[H\033\[J',   # 光标归位+清屏(无参数)
            r'\033\[2J',         # 清屏
            r'\033\[J',          # 清屏(无参数)
            r'\033\[0J',         # 清屏
            r'\033\[3J',         # 清屏+清除滚动缓冲区
        ]
        
        clear_found = False
        for i, pattern in enumerate(clear_patterns):
            match = re.search(pattern, text)
            if match:
                print(f"[ANSI] 检测到清屏命令: {pattern}")
                print(f"[ANSI] 匹配位置: {match.start()}-{match.end()}")
                self.commands.append(TerminalCommand('clear_screen'))
                text = re.sub(pattern, '', text)
                print(f"[ANSI] 删除后文本: {repr(text)}")
                clear_found = True
                break
        
        if not clear_found:
            print(f"[ANSI] 未检测到清屏命令")
        
        # 移除不需要的控制序列
        text = self.cursor_pattern.sub('', text)
        text = self.erase_pattern.sub('', text)  # 移除删除序列
        text = self.hide_cursor.sub('', text)
        
        # 分割ANSI序列
        parts = self.ansi_pattern.split(text)
        
        # parts交替包含: 文本, 参数, 文本, 参数...
        current_text = ""
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # 这是普通文本
                if part:
                    current_text += part
            else:
                # 这是ANSI参数
                # 先保存之前的文本
                if current_text:
                    segments.append(TextSegment(
                        text=current_text,
                        fg_color=self.current_fg,
                        bg_color=self.current_bg,
                        bold=self.current_bold,
                        underline=self.current_underline
                    ))
                    current_text = ""
                
                # 更新样式状态
                self._update_style(part)
        
        # 添加最后的文本
        if current_text:
            segments.append(TextSegment(
                text=current_text,
                fg_color=self.current_fg,
                bg_color=self.current_bg,
                bold=self.current_bold,
                underline=self.current_underline
            ))
        
        return segments
    
    def _update_style(self, params_str: str):
        """
        根据ANSI参数更新样式状态
        
        Args:
            params_str: 分号分隔的参数列表
        """
        if not params_str:
            self.reset_state()
            return
        
        params = [int(p) for p in params_str.split(';') if p.isdigit()]
        
        for param in params:
            if param == 0:
                # 重置所有样式
                self.reset_state()
            elif param == 1:
                # 加粗
                self.current_bold = True
            elif param == 4:
                # 下划线
                self.current_underline = True
            elif param in self.ANSI_COLORS:
                # 前景色
                self.current_fg = self.ANSI_COLORS[param]
            elif param in self.BG_COLORS:
                # 背景色
                self.current_bg = self.BG_COLORS[param]
    
    @staticmethod
    def strip_ansi(text: str) -> str:
        """
        移除所有ANSI转义序列,返回纯文本
        
        Args:
            text: 包含ANSI序列的文本
            
        Returns:
            纯文本
        """
        ansi_escape = re.compile(r'\033\[[0-9;?]*[A-Za-z]')
        return ansi_escape.sub('', text)
