"""
OracleLang Plugin - Liu Yao Divination Plugin for LangBot 4.0
Uses traditional San Qian Fa (coin toss method) for divination
Version: 4.0.0
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
                "enabled": config_data.get("llm_enabled", True),  # 默认启用 LLM
                "model": config_data.get("llm_model", "")
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
        errors: list[str] = []
        warnings: list[str] = []

        # Validate limit.daily_max
        daily_max = self.plugin_config.get("limit", {}).get("daily_max", 3)
        if not isinstance(daily_max, int):
            errors.append(f"limit.daily_max 必须是整数，当前类型: {type(daily_max).__name__}")
        elif daily_max <= 0:
            errors.append(f"limit.daily_max 必须大于 0，当前值: {daily_max}")
        elif daily_max > 100:
            warnings.append(f"limit.daily_max 设置过高 ({daily_max})，建议设置在 1-100 之间")

        # Validate limit.reset_hour
        reset_hour = self.plugin_config.get("limit", {}).get("reset_hour", 0)
        if not isinstance(reset_hour, int):
            errors.append(f"limit.reset_hour 必须是整数，当前类型: {type(reset_hour).__name__}")
        elif reset_hour < 0 or reset_hour > 23:
            errors.append(f"limit.reset_hour 必须在 0-23 之间，当前值: {reset_hour}")

        # Validate llm.enabled
        llm_enabled = self.plugin_config.get("llm", {}).get("enabled", True)
        if not isinstance(llm_enabled, bool):
            errors.append(f"llm.enabled 必须是布尔值，当前类型: {type(llm_enabled).__name__}")

        # Validate display.style
        style = self.plugin_config.get("display", {}).get("style", "detailed")
        valid_styles = ["simple", "traditional", "detailed"]
        if not isinstance(style, str):
            errors.append(f"display.style 必须是字符串，当前类型: {type(style).__name__}")
        elif style not in valid_styles:
            errors.append(f"display.style 必须是以下之一: {', '.join(valid_styles)}，当前值: {style}")

        # Validate display.language
        language = self.plugin_config.get("display", {}).get("language", "zh")
        valid_languages = ["zh", "en"]
        if not isinstance(language, str):
            errors.append(f"display.language 必须是字符串，当前类型: {type(language).__name__}")
        elif language not in valid_languages:
            warnings.append(f"display.language 建议使用: {', '.join(valid_languages)}，当前值: {language}")

        # Validate admin_users
        admin_users = self.plugin_config.get("admin_users", [])
        if not isinstance(admin_users, list):
            errors.append(f"admin_users 必须是列表，当前类型: {type(admin_users).__name__}")
        else:
            for i, user_id in enumerate(admin_users):
                if not isinstance(user_id, str):
                    errors.append(f"admin_users[{i}] 必须是字符串，当前类型: {type(user_id).__name__}")
                elif not user_id.strip():
                    warnings.append(f"admin_users[{i}] 是空字符串，将被忽略")

        # Validate debug
        debug = self.plugin_config.get("debug", False)
        if not isinstance(debug, bool):
            errors.append(f"debug 必须是布尔值，当前类型: {type(debug).__name__}")

        if errors:
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
        return """## 六爻算卦使用说明

### 基础用法
- **算卦 <问题>** — 使用三钱法起卦占卜

### 起卦原理（三钱法）
模拟投掷3枚硬币，共6次（对应六爻）
- ● 正面  ○ 反面
- 3正(●●●) → 老阳(9) → 阳爻，动爻 ⚡
- 2正1反(●●○) → 少阳(7) → 阳爻
- 1正2反(●○○) → 少阴(8) → 阴爻
- 3反(○○○) → 老阴(6) → 阴爻，动爻 ⚡

### 查询命令
- **算卦 help** — 显示此帮助信息
- **算卦 history** — 查看您的算卦历史记录
- **算卦 myid** — 查看您的用户ID

### 管理命令（仅管理员）
- **算卦 reset <用户ID>** — 重置用户今日使用次数
- **算卦 stats** — 查看系统使用统计

### 示例
- 算卦 我今天的工作运势如何？
- 算卦 这次项目能否成功？

> 提示：私聊和群聊的算卦次数独立计算。
"""

    def _parse_question(self, cmd_args: str) -> str:
        """Parse and return the question from command arguments"""
        return cmd_args.strip()

    def _get_history_text(self, launcher_type: str, sender_id: str) -> str:
        """Get user's divination history"""
        records = self.history.get_recent_records(launcher_type, sender_id, limit=10)

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

    def _format_response(self, question: str, hexagram_data: dict, interpretation: dict, visual: str, remaining: int = 0) -> str:
        """Format response as Markdown using the MarkdownFormatter."""
        from src.formatter import MarkdownFormatter
        formatter = MarkdownFormatter(logger=logger)
        return formatter.format_divination_result(
            result=interpretation,
            question=question,
            style=self.plugin_config.get("display", {}).get("style", "detailed"),
            hexagram_data={
                "original": hexagram_data["original"],
                "changed": hexagram_data["changed"],
                "moving": hexagram_data["moving"],
            },
            remaining=remaining,
            daily_max=self.plugin_config.get("limit", {}).get("daily_max", 3),
        )

    async def process_divination(self, question: str, launcher_type: str, sender_id: str) -> str:
        """
        Process divination request using coin toss method

        Args:
            question: The question to divine
            launcher_type: The launcher type (e.g. 'group', 'private')
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

        # Update usage
        self.limit.update_usage(launcher_type, sender_id)
        remaining = self.limit.get_remaining(launcher_type, sender_id)

        # Build response using MarkdownFormatter
        result_text = self._format_response(
            question, hexagram_data, interpretation, visual, remaining=remaining
        )

        # Save to history
        self.history.save_record(
            launcher_type=launcher_type,
            user_id=sender_id,
            question=question,
            hexagram_data=hexagram_data,
            interpretation=interpretation
        )

        return result_text