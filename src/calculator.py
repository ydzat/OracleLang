import random
import hashlib
import time
import logging
from typing import Dict, List, Any, Optional
import asyncio

from .data_constants import HEXAGRAM_MAP


class HexagramCalculator:
    """
    卦象计算器类，用于根据不同方法生成六爻卦象
    """

    # 从常量模块导入映射表
    HEXAGRAM_MAP = HEXAGRAM_MAP

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize calculator

        Args:
            logger: Logger instance for logging messages
        """
        self.logger = logger or logging.getLogger(__name__)
    
    async def calculate(self, method: str, input_text: str, user_id: str) -> Dict[str, Any]:
        """
        根据提供的方法计算卦象

        参数:
            method: 起卦方式，可选 'random', 'text', '数字', '时间' 等
            input_text: 用户输入文本或参数
            user_id: 用户ID

        返回:
            包含原卦、变卦和动爻信息的字典

        Raises:
            ValueError: 当输入参数无效时
            RuntimeError: 当计算过程出现错误时
        """
        try:
            # 默认使用文本起卦
            if not method or method not in ["random", "text", "数字", "时间"]:
                self.logger.debug(f"Unknown method '{method}', defaulting to 'text'")
                method = "text"

            self.logger.info(f"Calculating hexagram: method={method}, user_id={user_id}")

            # 根据方法调用对应的计算函数
            if method == "random" or not input_text:
                result = await self._random_hexagram()
            elif method == "数字":
                result = await self._number_hexagram(input_text)
            elif method == "时间":
                result = await self._time_hexagram()
            else:  # 文本起卦
                result = await self._text_hexagram(input_text)

            # 确保结果格式正确
            if "original" not in result or "moving" not in result:
                raise ValueError("计算结果格式不正确：缺少必要字段")

            # 计算变卦
            original = result["original"]
            moving = result["moving"]

            # 检查爻的数量
            if len(original) != 6 or len(moving) != 6:
                raise ValueError(f"爻的数量必须为6，实际为 original={len(original)}, moving={len(moving)}")

            changed = self._calculate_changed_hexagram(original, moving)

            # 计算卦象编号（1-64）
            hexagram_original = self._get_hexagram_number(original)
            hexagram_changed = self._get_hexagram_number(changed) if sum(moving) > 0 else hexagram_original

            # 日志输出
            self.logger.debug(
                f"Hexagram calculated - Original: {original}, Moving: {moving}, Changed: {changed}"
            )
            self.logger.debug(
                f"Hexagram numbers - Original: {hexagram_original}, Changed: {hexagram_changed}"
            )

            return {
                "original": original,
                "changed": changed,
                "moving": moving,
                "hexagram_original": hexagram_original,
                "hexagram_changed": hexagram_changed
            }

        except ValueError as e:
            # 参数验证错误，直接抛出
            self.logger.error(f"Validation error in hexagram calculation: {str(e)}")
            raise

        except Exception as e:
            # 其他未预期的错误
            self.logger.error(
                f"Unexpected error in hexagram calculation: {str(e)}",
                exc_info=True
            )
            raise RuntimeError(f"卦象计算失败: {str(e)}") from e
        
    async def _random_hexagram(self) -> Dict[str, List[int]]:
        """
        随机起卦法：模拟传统的掷币方式

        每爻通过三次"掷币"决定，三个硬币正面(1)反面(0)的组合决定爻的性质：
        - 三阳爻 (阳爻老爻) [1,1,1] -> 9 -> 动爻，记为1
        - 二阳一阴 (阳爻少爻) [1,1,0] -> 7 -> 不动爻，记为1
        - 二阴一阳 (阴爻少爻) [0,0,1] -> 8 -> 不动爻，记为0
        - 三阴爻 (阴爻老爻) [0,0,0] -> 6 -> 动爻，记为0
        """
        try:
            original = []
            moving = []

            for _ in range(6):
                # 模拟掷三次硬币
                coins = [random.randint(0, 1) for _ in range(3)]
                coin_sum = sum(coins)

                if coin_sum == 3:  # 三阳爻，动爻，记为1
                    original.append(1)
                    moving.append(1)
                elif coin_sum == 2:  # 二阳一阴，不动爻，记为1
                    original.append(1)
                    moving.append(0)
                elif coin_sum == 1:  # 二阴一阳，不动爻，记为0
                    original.append(0)
                    moving.append(0)
                else:  # 三阴爻，动爻，记为0
                    original.append(0)
                    moving.append(1)

            self.logger.debug(f"Random hexagram generated: original={original}, moving={moving}")
            return {
                "original": original,
                "moving": moving
            }
        except Exception as e:
            self.logger.error(f"Error generating random hexagram: {str(e)}")
            raise
        
    async def _text_hexagram(self, text: str) -> Dict[str, List[int]]:
        """
        文本起卦法：根据文本内容生成唯一的卦象

        实现方法:
        1. 计算文本的哈希值
        2. 将哈希值转换为6位二进制数作为卦象
        3. 根据哈希值的某些位确定动爻
        """
        try:
            if not text:
                self.logger.warning("Empty text provided for text hexagram, using random method")
                return await self._random_hexagram()

            self.logger.debug(f"Generating text hexagram from: {text[:50]}...")

            # 计算文本的SHA256哈希值
            h = hashlib.sha256(text.encode('utf-8')).hexdigest()

            # 使用哈希值的前6个字符确定原卦
            original = []
            for i in range(6):
                # 取哈希值的第i个字符的二进制最低位
                char_val = int(h[i], 16)
                original.append(char_val & 1)  # 取最低位的值(0或1)

            # 使用哈希值的后6个字符确定动爻
            moving = []
            for i in range(6):
                # 取哈希的后部分，确定动爻
                char_val = int(h[-(i+1)], 16)
                # 概率约1/3的爻为动爻
                moving.append(1 if char_val < 5 else 0)

            self.logger.debug(f"Text hexagram generated: original={original}, moving={moving}")
            return {
                "original": original,
                "moving": moving
            }
        except Exception as e:
            self.logger.error(f"Error generating text hexagram: {str(e)}")
            raise
        
    async def _number_hexagram(self, number_str: str) -> Dict[str, List[int]]:
        """
        数字起卦法：根据用户输入的数字序列生成卦象

        实现方法:
        1. 将输入数字转换为数字序列
        2. 根据数字序列各位的值或总和生成卦象
        """
        try:
            # 尝试转换为整数
            number = int(number_str.replace(" ", ""))
            self.logger.debug(f"Generating number hexagram from: {number}")

            # 生成6个爻的值
            original = []
            moving = []

            # 取出各位数字
            num_str = str(number)
            for i in range(6):
                if i < len(num_str):
                    # 从右到左取数字
                    digit = int(num_str[-(i+1)])
                    original.append(digit % 2)  # 奇数为阳(1)，偶数为阴(0)
                    moving.append(1 if digit in [6, 9] else 0)  # 6和9为动爻
                else:
                    # 不足6位则剩余位使用随机值
                    digit = random.randint(0, 1)
                    original.append(digit)
                    moving.append(0)  # 默认不是动爻

            self.logger.debug(f"Number hexagram generated: original={original}, moving={moving}")
            return {
                "original": original,
                "moving": moving
            }

        except ValueError as e:
            # 转换失败，使用文本起卦
            self.logger.warning(f"Failed to parse number '{number_str}', falling back to text method: {str(e)}")
            return await self._text_hexagram(number_str)
            
    async def _time_hexagram(self) -> Dict[str, List[int]]:
        """
        时间起卦法：根据当前时间生成卦象
        """
        try:
            current_time = time.localtime()
            year, month, day = current_time.tm_year, current_time.tm_mon, current_time.tm_mday
            hour, minute, second = current_time.tm_hour, current_time.tm_min, current_time.tm_sec

            self.logger.debug(
                f"Generating time hexagram from: {year}-{month:02d}-{day:02d} "
                f"{hour:02d}:{minute:02d}:{second:02d}"
            )

            # 生成原卦
            original = [
                month % 2,  # 月份奇偶
                day % 2,    # 日期奇偶
                (day // 10) % 2,  # 日期十位奇偶
                hour % 2,   # 小时奇偶
                minute % 2, # 分钟奇偶
                second % 2  # 秒数奇偶
            ]

            # 生成动爻
            moving = [
                1 if month in [1, 6, 8] else 0,  # 选定几个月份作为动爻
                1 if day in [1, 6, 9, 15, 18, 24, 27, 30] else 0,  # 选定日期
                1 if hour in [0, 6, 12, 18] else 0,  # 选定时辰
                1 if minute < 10 else 0,  # 开始10分钟作为动爻
                0,  # 静爻
                0   # 静爻
            ]

            self.logger.debug(f"Time hexagram generated: original={original}, moving={moving}")
            return {
                "original": original,
                "moving": moving
            }
        except Exception as e:
            self.logger.error(f"Error generating time hexagram: {str(e)}")
            raise
        
    def _calculate_changed_hexagram(self, original: List[int], moving: List[int]) -> List[int]:
        """计算变卦，动爻所在的爻位会变化（阴变阳，阳变阴）"""
        changed = original.copy()
        
        for i in range(len(original)):
            if moving[i] == 1:
                # 阴变阳，阳变阴
                changed[i] = 1 - original[i]
                
        return changed
        
    def _get_hexagram_number(self, hexagram: List[int]) -> int:
        """
        计算卦象对应的序号（1-64）

        实现原理：
        - 将六爻看作6位二进制数（从下到上）
        - 转换为十进制后，查找映射表得到正确的易经卦序
        """
        # 将爻转换为二进制数（下爻为第0位）
        binary = 0
        for i, val in enumerate(hexagram):
            binary |= (val << i)

        # 使用标准易经卦序映射表查找对应的卦序
        if binary in self.HEXAGRAM_MAP:
            return self.HEXAGRAM_MAP[binary]
        else:
            # 如果找不到映射（理论上不应该发生），记录错误
            self.logger.error(
                f"Hexagram mapping not found for binary value: {bin(binary)} ({binary}), "
                f"hexagram: {hexagram}"
            )
            # 返回一个默认值，避免程序崩溃
            return (binary % 64) + 1
