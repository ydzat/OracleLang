"""
OracleLang Plugin - Liu Yao Divination Plugin for LangBot 4.0
Uses traditional San Qian Fa (coin toss method) for divination
Version: 3.1.0
Author: ydzat
"""
from __future__ import annotations

import os
import pathlib
import logging
from typing import Dict, Any

from langbot_plugin.api.definition.plugin import BasePlugin

# Import core modules
from src.calculator import HexagramCalculator
from src.interpreter import HexagramInterpreter
from src.glyphs import HexagramRenderer
from src.history import HistoryManager
from src.limit import UsageLimit
from src.config_validator import validate_config

# Setup logger
logger = logging.getLogger(__name__)


class OracleLangPlugin(BasePlugin):
    """OracleLang Plugin Main Class"""

    # Core modules
    calculator: HexagramCalculator
    interpreter: HexagramInterpreter
    renderer: HexagramRenderer
    history: HistoryManager
    limit: UsageLimit

    # Plugin configuration
    plugin_config: Dict[str, Any]

    async def initialize(self) -> None:
        """Initialize the plugin"""
        logger.info("OracleLang plugin initializing...")

        # Get plugin directory
        plugin_dir = pathlib.Path(__file__).parent.absolute()

        # Ensure data directories exist
        os.makedirs(os.path.join(plugin_dir, "data/history"), exist_ok=True)
        os.makedirs(os.path.join(plugin_dir, "data/static"), exist_ok=True)
        os.makedirs(os.path.join(plugin_dir, "data/limits"), exist_ok=True)

        # Get plugin configuration from manifest
        config_data = self.get_config()

        # Build config dict compatible with existing modules
        self.plugin_config = {
            "limit": {
                "daily_max": config_data.get("daily_max", 3),
                "reset_hour": config_data.get("reset_hour", 0)
            },
            "llm": {
                "enabled": config_data.get("llm_enabled", True)  # 默认启用 LLM
            },
            "display": {
                "style": config_data.get("display_style", "detailed"),
                "language": "zh"
            },
            "admin_users": config_data.get("admin_users", []),
            "debug": config_data.get("debug", False),
            "timezone": config_data.get("timezone", "Asia/Shanghai")
        }

        # Validate configuration
        logger.info("Validating plugin configuration...")
        is_valid, errors, warnings = validate_config(self.plugin_config, logger)

        if not is_valid:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        if warnings:
            logger.warning(f"Configuration has {len(warnings)} warning(s)")

        logger.info("Configuration validation passed")

        # Initialize core modules with logger
        self.calculator = HexagramCalculator(logger=logger)
        self.interpreter = HexagramInterpreter(self.plugin_config, plugin_dir, plugin=self, logger=logger)
        self.renderer = HexagramRenderer(logger=logger)
        self.history = HistoryManager(os.path.join(plugin_dir, "data/history"), logger=logger)
        self.limit = UsageLimit(self.plugin_config, os.path.join(plugin_dir, "data/limits"), logger=logger)

        # Load hexagram data
        logger.info("Loading hexagram data...")
        await self.interpreter.load_data()
        logger.info("Hexagram data loaded successfully")

        logger.info("OracleLang plugin initialized successfully")

    def __del__(self) -> None:
        """Cleanup when plugin is terminating"""
        logger.info("OracleLang plugin terminating...")

    def _is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        return str(user_id) in [str(uid) for uid in self.plugin_config.get("admin_users", [])]

    def _get_help_text(self) -> str:
        """Get help text"""
        return """六爻算卦使用说明：

基础用法：
  !suangua <问题>  - 使用三钱法起卦占卜

起卦原理（三钱法）：
  模拟投掷3枚硬币，共6次（对应六爻）
  ● 正面  ○ 反面
  3正(●●●) → 老阳(9) → 阳爻，动爻
  2正1反(●●○) → 少阳(7) → 阳爻
  1正2反(●○○) → 少阴(8) → 阴爻
  3反(○○○) → 老阴(6) → 阴爻，动爻

查询命令：
  !suangua help  - 显示此帮助信息
  !suangua history  - 查看您的算卦历史记录
  !suangua myid  - 查看您的用户ID

管理命令（仅管理员）：
  !suangua reset <用户ID>  - 重置用户今日使用次数
  !suangua stats  - 查看系统使用统计

示例：
  !suangua 我今天的工作运势如何？
  !suangua 这次项目能否成功？
"""

    def _parse_question(self, cmd_args: str) -> str:
        """Parse and return the question from command arguments"""
        return cmd_args.strip()

    def _get_history_text(self, sender_id: str) -> str:
        """Get user's divination history"""
        records = self.history.get_recent_records(sender_id, limit=10)

        if not records:
            return "您还没有算卦记录"

        result = "您的算卦历史记录（最近10条）：\n\n"
        for i, record in enumerate(records, 1):
            timestamp = record.get('timestamp', '未知时间')
            question = record.get('question', '无问题')
            # Get hexagram name from interpretation
            interpretation = record.get('interpretation', {})
            original = interpretation.get('original', {})
            hexagram_name = original.get('name', '未知卦象')

            result += f"{i}. {timestamp}\n"
            result += f"   问题：{question}\n"
            result += f"   卦象：{hexagram_name}\n\n"

        return result

    def _format_response(self, question: str, hexagram_data: dict, interpretation: dict, visual: str) -> str:
        """Format response message"""
        original_name = interpretation["original"]["name"]
        changed_name = interpretation["changed"]["name"]
        has_moving = hexagram_data['moving'].count(1) > 0

        response = [
            f"📝 问题: {question}" if question else "🔮 随缘一卦",
        ]

        # 显示投掷记录
        if "coin_records" in hexagram_data:
            response.append("\n🎲 起卦过程:")
            for record in hexagram_data["coin_records"]:
                moving_mark = " ⚡" if record["is_moving"] else ""
                response.append(f"  {record['yao']}: {record['coins']} → {record['type']}{moving_mark}")

        response.extend([
            f"\n{visual}",
            f"\n📌 卦象: {original_name} {'→ ' + changed_name if has_moving else ''}",
            f"\n✨ 卦辞: {interpretation['original']['gua_ci']}",
        ])

        # Moving lines interpretation
        if has_moving:
            response.append("\n🔄 动爻:")
            for line in interpretation["moving_lines_meaning"]:
                if line:
                    response.append(f"  {line}")

        # Overall interpretation
        response.append(f"\n📜 解释: {interpretation['overall_meaning']}")

        # Advice
        if "advice" in interpretation:
            response.append(f"\n💡 建议: {interpretation['advice']}")

        return "\n".join(response)

    async def process_divination(self, question: str, sender_id: str) -> str:
        """
        Process divination request using coin toss method

        Args:
            question: The question to divine
            sender_id: User ID

        Returns:
            Divination result text
        """
        # Calculate hexagram using coin toss method
        hexagram_data = await self.calculator.calculate(user_id=sender_id)

        # Generate hexagram visual
        style = self.plugin_config.get("display", {}).get("style", "detailed")
        visual = self.renderer.render_hexagram(
            hexagram_data["original"],
            hexagram_data["changed"],
            hexagram_data["moving"],
            style=style
        )

        # Get LLM config
        llm_config = self.plugin_config.get("llm", {})
        use_llm = llm_config.get("enabled", False)

        # Get interpretation
        interpretation = await self.interpreter.interpret(
            hexagram_original=hexagram_data["hexagram_original"],
            hexagram_changed=hexagram_data["hexagram_changed"],
            moving=hexagram_data["moving"],
            question=question,
            use_llm=use_llm
        )

        # Build response message
        result_text = self._format_response(question, hexagram_data, interpretation, visual)

        # Save to history
        self.history.save_record(
            user_id=sender_id,
            question=question,
            hexagram_data=hexagram_data,
            interpretation=interpretation
        )

        # Update usage
        self.limit.update_usage(sender_id)
        remaining = self.limit.get_remaining(sender_id)

        # Add usage count hint
        result_text += f"\n\n今日剩余算卦次数: {remaining}/{self.plugin_config['limit']['daily_max']}"

        return result_text