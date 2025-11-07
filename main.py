"""
OracleLang Plugin - I Ching Divination Plugin for LangBot
Version: 2.0.2
Author: ydzat
"""
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

    async def initialize(self):
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
                "enabled": config_data.get("llm_enabled", False),
                "api_type": config_data.get("llm_api_type", "openai"),
                "api_key": config_data.get("llm_api_key", ""),
                "api_base": config_data.get("llm_api_base", ""),
                "api_secret": config_data.get("llm_api_secret", ""),
                "model": config_data.get("llm_model", "gpt-3.5-turbo")
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
        self.interpreter = HexagramInterpreter(self.plugin_config, plugin_dir, logger=logger)
        self.renderer = HexagramRenderer(logger=logger)
        self.history = HistoryManager(os.path.join(plugin_dir, "data/history"), logger=logger)
        self.limit = UsageLimit(self.plugin_config, os.path.join(plugin_dir, "data/limits"), logger=logger)

        # Load hexagram data
        logger.info("Loading hexagram data...")
        await self.interpreter.load_data()
        logger.info("Hexagram data loaded successfully")

        logger.info("OracleLang plugin initialized successfully")

    async def process_divination_message(self, msg: str, sender_id: str) -> str:
        """
        Process divination message and return response

        Args:
            msg: The message text
            sender_id: The sender's user ID

        Returns:
            Response message string, or None if not a divination command
        """
        import re

        # Clean text, remove @ mentions
        cleaned_text = re.sub(r'@\S+\s*', '', msg).strip()

        # Check if it's a divination command
        CMD_PREFIX = "算卦"
        if not cleaned_text.startswith(CMD_PREFIX):
            return None

        # Extract command arguments
        cmd_args = cleaned_text[len(CMD_PREFIX):].strip()

        # Handle help command
        if cmd_args.strip() == "帮助":
            return self._get_help_text()

        # Handle user ID query command
        if cmd_args.strip() == "我的ID":
            return f"您的用户ID是: {sender_id}"

        # Handle admin commands (admin only)
        if self._is_admin(sender_id) and (cmd_args.startswith("设置") or cmd_args.startswith("重置") or cmd_args.startswith("统计")):
            return await self._handle_admin_commands(sender_id, cmd_args)

        # Check user daily usage limit
        if not self.limit.check_user_limit(sender_id):
            remaining_time = self.limit.get_reset_time()
            return f"您今日的算卦次数已达上限（{self.plugin_config['limit']['daily_max']}次/天），请等待重置。\n下次重置时间: {remaining_time}"

        # Parse command arguments
        method, params, question = self._parse_command(cmd_args)

        # Handle history query
        if method == "历史":
            return self._get_history_text(sender_id)

        # Generate hexagram
        try:
            logger.info(f"User {sender_id} using method {method} for divination, params: {params}, question: {question}")

            hexagram_data = await self.calculator.calculate(
                method=method,
                input_text=params or question,
                user_id=sender_id
            )

            # Generate hexagram visual
            style = self.plugin_config["display"]["style"]
            visual = self.renderer.render_hexagram(
                hexagram_data["original"],
                hexagram_data["changed"],
                hexagram_data["moving"],
                style=style
            )

            # Get hexagram interpretation
            interpretation = await self.interpreter.interpret(
                hexagram_original=hexagram_data["hexagram_original"],
                hexagram_changed=hexagram_data["hexagram_changed"],
                moving=hexagram_data["moving"],
                question=question,
                use_llm=self.plugin_config["llm"]["enabled"]
            )

            # Build response message
            result_msg = self._format_response(question, hexagram_data, interpretation, visual)

            # Save to history
            self.history.save_record(
                user_id=sender_id,
                question=question,
                hexagram_data=hexagram_data,
                interpretation=interpretation
            )

            # Update user usage count
            self.limit.update_usage(sender_id)
            remaining = self.limit.get_remaining(sender_id)

            # Add usage count hint
            result_msg += f"\n\n今日剩余算卦次数: {remaining}/{self.plugin_config['limit']['daily_max']}"

            return result_msg

        except Exception as e:
            logger.error(f"Divination error: {str(e)}", exc_info=True)
            return f"算卦过程出现错误: {str(e)}\n请稍后再试或联系管理员。"

    def _parse_command(self, cmd_args: str) -> tuple:
        """
        Parse command arguments

        Returns:
            (method, params, question) tuple
        """
        # Supported divination methods
        methods = ["数字", "时间", "历史"]

        method = "text"  # Default to text divination
        params = None
        question = cmd_args

        # Check if a specific method is specified
        parts = cmd_args.split(maxsplit=2)
        if parts and parts[0] in methods:
            method = parts[0]
            if len(parts) >= 2:
                params = parts[1]
                question = parts[2] if len(parts) >= 3 else ""

        return method, params, question
    
    def _format_response(self, question: str, hexagram_data: Dict, interpretation: Dict, visual: str) -> str:
        """Format response message"""
        original_name = interpretation["original"]["name"]
        changed_name = interpretation["changed"]["name"]

        response = [
            f"📝 问题: {question}" if question else "🔮 随缘一卦",
            f"\n{visual}",
            f"\n📌 卦象: {original_name} {'→' if hexagram_data['moving'].count(1) > 0 else ''} {changed_name if hexagram_data['moving'].count(1) > 0 else ''}",
            f"\n✨ 卦辞: {interpretation['original']['gua_ci']}",
        ]

        # Moving lines interpretation
        if hexagram_data['moving'].count(1) > 0:
            response.append("\n🔄 动爻:")
            for i, line in enumerate(interpretation["moving_lines_meaning"]):
                if line:
                    response.append(f"  {line}")

        # Overall interpretation
        response.append(f"\n📜 解释: {interpretation['overall_meaning']}")

        # Advice
        if "advice" in interpretation:
            response.append(f"\n💡 建议: {interpretation['advice']}")

        return "\n".join(response)
        
    def _get_history_text(self, user_id: str) -> str:
        """Get user history records as text"""
        records = self.history.get_recent_records(user_id, limit=5)

        if not records:
            return "您还没有算卦记录。"

        result = ["您的近期算卦记录：\n"]
        for i, record in enumerate(records, 1):
            timestamp = record.get("timestamp", "未知时间")
            question = record.get("question", "无问题")
            result.append(f"{i}. [{timestamp}] {question}")

            # Add brief summary
            summary = record.get("result_summary", "")
            if summary:
                result.append(f"   {summary}")

        return "\n".join(result)
        
    async def _handle_admin_commands(self, sender_id: str, cmd: str) -> str:
        """Handle admin commands"""
        parts = cmd.split()

        if parts[0] == "设置" and len(parts) >= 3 and parts[1] == "次数":
            try:
                new_limit = int(parts[2])
                if new_limit > 0:
                    # Note: In v4, config changes should be done through WebUI
                    # This is kept for backward compatibility but won't persist
                    self.plugin_config["limit"]["daily_max"] = new_limit
                    return f"每日算卦次数上限已临时设置为 {new_limit} 次\n注意：此设置在插件重启后会恢复为配置文件中的值，请在WebUI中修改配置以永久保存。"
                else:
                    return "次数必须为正整数"
            except ValueError:
                return "格式错误，请使用数字设置次数"

        elif parts[0] == "重置" and len(parts) >= 2:
            target_user = parts[1]
            self.limit.reset_user(target_user)
            return f"已重置用户 {target_user} 的算卦次数"

        elif parts[0] == "统计":
            stats = self.limit.get_usage_statistics()
            total_users = stats.get("total_users", 0)
            total_usage = stats.get("total_usage", 0)
            return f"算卦统计:\n总用户数: {total_users}\n总使用次数: {total_usage}"

        else:
            return "无效的管理命令，支持的命令：\n算卦 设置 次数 [数字]\n算卦 重置 [用户ID]\n算卦 统计"
    
    def _is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        admin_list = self.plugin_config.get("admin_users", [])
        # Convert to string for comparison
        return str(user_id) in [str(admin) for admin in admin_list]

    def _get_help_text(self) -> str:
        """Get help text"""
        help_text = [
            "📚 OracleLang 算卦插件使用指南 📚",
            "\n基本用法：",
            "算卦 [问题]  - 使用文本起卦方式进行算卦",
            "例如：算卦 我今天的工作运势如何？",
            "      算卦 近期是否适合投资股票？",
            "      算卦  (不提供问题将随缘生成一卦)",
            "注：只有提供问题，才会有AI分析卦象",
            "\n高级用法：",
            "算卦 数字 [数字] [问题]  - 使用指定数字起卦",
            "例如：算卦 数字 1234 我的事业前景如何",
            "",
            "算卦 时间 [时间] [问题]  - 使用当前时间起卦",
            "例如：算卦 时间 明天 财运",
            "",
            "算卦 历史  - 查看您的最近算卦记录",
            "算卦 我的ID  - 查询您的用户ID",
            "\n管理员命令：",
            "算卦 设置 次数 [数字]  - 设置每日算卦次数限制",
            "算卦 重置 [用户ID]  - 重置特定用户的算卦次数",
            "算卦 统计  - 查看使用统计信息",
            f"\n默认每人每日可算卦 {self.plugin_config['limit']['daily_max']} 次"
        ]

        return "\n".join(help_text)
