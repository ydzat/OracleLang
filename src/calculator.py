import random
import logging
from typing import Dict, List, Any, Optional

from .data_constants import HEXAGRAM_MAP


class HexagramCalculator:
    """
    六爻卦象计算器 - 使用传统三钱法起卦

    三钱法：每爻投掷3枚硬币，根据正反面组合决定爻的性质
    - 3正(老阳/9) → 阳爻 + 动爻
    - 2正1反(少阳/7) → 阳爻
    - 1正2反(少阴/8) → 阴爻
    - 3反(老阴/6) → 阴爻 + 动爻
    """

    HEXAGRAM_MAP = HEXAGRAM_MAP

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def calculate(self, user_id: str) -> Dict[str, Any]:
        """
        使用三钱法计算卦象（模拟6次投掷，每次3枚硬币）

        参数:
            user_id: 用户ID

        返回:
            包含原卦、变卦、动爻和卦象编号的字典
        """
        try:
            self.logger.info(f"Calculating hexagram for user: {user_id}")

            # 使用三钱法起卦
            result = await self._coin_toss_hexagram()

            original = result["original"]
            moving = result["moving"]
            coin_records = result["coin_records"]

            # 计算变卦
            changed = self._calculate_changed_hexagram(original, moving)

            # 计算卦象编号（1-64）
            hexagram_original = self._get_hexagram_number(original)
            hexagram_changed = self._get_hexagram_number(changed) if sum(moving) > 0 else hexagram_original

            self.logger.debug(
                f"Hexagram calculated - Original: {original}, Moving: {moving}, Changed: {changed}"
            )

            return {
                "original": original,
                "changed": changed,
                "moving": moving,
                "coin_records": coin_records,
                "hexagram_original": hexagram_original,
                "hexagram_changed": hexagram_changed
            }

        except Exception as e:
            self.logger.error(f"Error in hexagram calculation: {str(e)}", exc_info=True)
            raise RuntimeError(f"卦象计算失败: {str(e)}") from e
        
    async def _coin_toss_hexagram(self) -> Dict[str, Any]:
        """
        三钱法起卦：模拟传统六爻占卜的掷币方式

        每爻投掷3枚硬币，根据正面(1)反面(0)的数量决定爻的性质：
        - 3正 (sum=3) → 老阳(9) → 阳爻，动爻
        - 2正1反 (sum=2) → 少阳(7) → 阳爻，静爻
        - 1正2反 (sum=1) → 少阴(8) → 阴爻，静爻
        - 3反 (sum=0) → 老阴(6) → 阴爻，动爻

        返回:
            original: 原卦六爻 [初爻, 二爻, ..., 上爻]
            moving: 动爻标记 [0/1, ...]
            coin_records: 每爻的投掷记录，用于展示
        """
        original = []
        moving = []
        coin_records = []

        # 爻位名称（从下到上）
        yao_names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]

        for i in range(6):
            # 模拟投掷3枚硬币
            coins = [random.randint(0, 1) for _ in range(3)]
            coin_sum = sum(coins)

            # 记录投掷结果
            coin_display = "".join(["●" if c == 1 else "○" for c in coins])

            if coin_sum == 3:  # 老阳(9)：阳爻，动爻
                original.append(1)
                moving.append(1)
                yao_type = "老阳(9)"
            elif coin_sum == 2:  # 少阳(7)：阳爻，静爻
                original.append(1)
                moving.append(0)
                yao_type = "少阳(7)"
            elif coin_sum == 1:  # 少阴(8)：阴爻，静爻
                original.append(0)
                moving.append(0)
                yao_type = "少阴(8)"
            else:  # 老阴(6)：阴爻，动爻
                original.append(0)
                moving.append(1)
                yao_type = "老阴(6)"

            coin_records.append({
                "yao": yao_names[i],
                "coins": coin_display,
                "type": yao_type,
                "is_moving": moving[i] == 1
            })

        self.logger.debug(f"Coin toss hexagram: original={original}, moving={moving}")

        return {
            "original": original,
            "moving": moving,
            "coin_records": coin_records
        }
        
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
