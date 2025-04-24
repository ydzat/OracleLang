from typing import List, Dict, Any, Optional
from .data_constants import TRIGRAMS, UNICODE_SYMBOLS, HEXAGRAM_UNICODE

class HexagramRenderer:
    """
    卦象图形渲染器，用于生成卦象的文字图示
    """
    
    # 从常量模块导入数据
    UNICODE_SYMBOLS = UNICODE_SYMBOLS
    HEXAGRAM_UNICODE = HEXAGRAM_UNICODE
    TRIGRAMS = TRIGRAMS
    
    def render_hexagram(self, original: List[int], changed: List[int], 
                        moving: List[int], style: str = "detailed") -> str:
        """
        渲染卦象图示
        
        参数:
            original: 原卦的六爻数组
            changed: 变卦的六爻数组
            moving: 动爻标记数组
            style: 渲染风格，可选 'simple', 'traditional', 'detailed'
            
        返回:
            渲染后的文本
        """
        if style == "simple":
            return self._render_simple(original, changed, moving)
        elif style == "traditional":
            return self._render_traditional(original, changed, moving)
        else:  # detailed
            return self._render_detailed(original, changed, moving)
    
    def _render_simple(self, original: List[int], changed: List[int], moving: List[int]) -> str:
        """简单模式: 使用Unicode符号表示卦象"""
        has_moving = sum(moving) > 0
        
        # 计算原卦和变卦的二进制值
        original_binary = self._to_binary(original)
        changed_binary = self._to_binary(changed)
        
        # 获取对应的Unicode符号
        original_symbol = self.HEXAGRAM_UNICODE.get(original_binary, "？")
        changed_symbol = self.HEXAGRAM_UNICODE.get(changed_binary, "？")
        
        # 如果没有变化，只返回原卦符号
        if not has_moving:
            return f"{original_symbol}"
        else:
            return f"{original_symbol} {self.UNICODE_SYMBOLS['arrow']} {changed_symbol}"
    
    def _render_traditional(self, original: List[int], changed: List[int], moving: List[int]) -> str:
        """传统模式: 使用卦名表示"""
        has_moving = sum(moving) > 0
        
        # 计算上下卦的三进制值
        original_upper = self._to_binary(original[3:])
        original_lower = self._to_binary(original[:3])
        
        # 获取上下卦的名称
        original_upper_name = self.TRIGRAMS.get(original_upper, ("？", "未知", ""))[1]
        original_lower_name = self.TRIGRAMS.get(original_lower, ("？", "未知", ""))[1]
        
        original_name = f"{original_lower_name}{original_upper_name}"
        
        # 如果没有变化，只返回原卦名称
        if not has_moving:
            return f"{original_name}"
        else:
            # 计算变卦的上下卦
            changed_upper = self._to_binary(changed[3:])
            changed_lower = self._to_binary(changed[:3])
            
            # 获取变卦的名称
            changed_upper_name = self.TRIGRAMS.get(changed_upper, ("？", "未知", ""))[1]
            changed_lower_name = self.TRIGRAMS.get(changed_lower, ("？", "未知", ""))[1]
            
            changed_name = f"{changed_lower_name}{changed_upper_name}"
            
            return f"{original_name} {self.UNICODE_SYMBOLS['arrow']} {changed_name}"
    
    def _render_detailed(self, original: List[int], changed: List[int], moving: List[int]) -> str:
        """详细模式: 显示爻的具体形态"""
        has_moving = sum(moving) > 0
        
        # 找出原卦和变卦对应的卦名
        original_binary = self._to_binary(original)
        original_upper = self._to_binary(original[3:])
        original_lower = self._to_binary(original[:3])
        
        # 获取上下卦的名称和象
        original_upper_info = self.TRIGRAMS.get(original_upper, ("？", "未知", ""))
        original_lower_info = self.TRIGRAMS.get(original_lower, ("？", "未知", ""))
        
        # 确定卦名
        original_name = f"{original_lower_info[1]}为{original_lower_info[2]}{original_upper_info[1]}为{original_upper_info[2]}"
        
        # 准备爻的表示
        lines = []
        
        # 从上往下生成爻的表示（易经卦象是从下往上数的）
        for i in range(5, -1, -1):
            # 原卦的爻
            original_line = self.UNICODE_SYMBOLS["whole_line"] if original[i] == 1 else self.UNICODE_SYMBOLS["broken_line"]
            
            # 如果有动爻，也显示变卦的爻
            if has_moving:
                changed_line = self.UNICODE_SYMBOLS["whole_line"] if changed[i] == 1 else self.UNICODE_SYMBOLS["broken_line"]
                line_text = f"{original_line}  {changed_line}"
                
                # 标记动爻
                if moving[i] == 1:
                    line_text += " *"
            else:
                line_text = original_line
                
            lines.append(line_text)
        
        # 如果有变卦，生成变卦的名称
        if has_moving:
            changed_binary = self._to_binary(changed)
            changed_upper = self._to_binary(changed[3:])
            changed_lower = self._to_binary(changed[:3])
            
            changed_upper_info = self.TRIGRAMS.get(changed_upper, ("？", "未知", ""))
            changed_lower_info = self.TRIGRAMS.get(changed_lower, ("？", "未知", ""))
            
            changed_name = f"{changed_lower_info[1]}为{changed_lower_info[2]}{changed_upper_info[1]}为{changed_upper_info[2]}"
            
            # 在最上面一爻添加原卦名称，在最下面一爻添加变卦名称
            lines[0] += f"  {original_name}（原卦）"
            lines[-1] += f"  {changed_name}（变卦）"
        else:
            # 只在最上面一爻添加卦名
            lines[0] += f"  {original_name}"
        
        # 组合所有爻的表示
        return "\n".join(lines)
    
    def _to_binary(self, yao_list: List[int]) -> int:
        """将爻的列表转换为二进制值"""
        result = 0
        for i, yao in enumerate(yao_list):
            if yao == 1:
                result |= (1 << i)
        return result
