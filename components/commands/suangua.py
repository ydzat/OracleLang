"""
OracleLang Divination Command Component
Handles the '!算卦' command for I Ching divination
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command
from langbot_plugin.api.entities.builtin.command.context import ExecuteContext, CommandReturn

logger = logging.getLogger(__name__)


class SuanguaCommand(Command):
    """I Ching divination command handler"""

    async def initialize(self):
        """Initialize command handler and register subcommands"""
        await super().initialize()

        # Default handler for divination (catch-all subcommand)
        @self.subcommand(
            name="*",  # Catch-all for any unmatched subcommand (treated as question)
            help="六爻算卦 - 三钱法起卦",
            usage="算卦 <问题>",
            aliases=[],
        )
        async def divination_default(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """
            Handle divination command with question as parameters

            Examples:
                !算卦 今日运势
                !算卦 我今天的工作运势如何？
            """
            try:
                # Get sender ID and launcher type
                sender_id = str(context.session.launcher_id)
                launcher_type = str(context.session.launcher_type.value) if hasattr(context.session.launcher_type, 'value') else str(context.session.launcher_type)

                # All parameters are the question
                question = " ".join(context.crt_params) if context.crt_params else ""

                if not question.strip():
                    yield CommandReturn(
                        text="请输入您的问题。使用算卦 help 查看使用说明。"
                    )
                    return

                # Check user daily usage limit
                if not self.plugin.limit.check_user_limit(launcher_type, sender_id):
                    remaining_time = self.plugin.limit.get_reset_time()
                    yield CommandReturn(
                        text=f"您今日的算卦次数已达上限（{self.plugin.plugin_config['limit']['daily_max']}次/天），请等待重置。\n下次重置时间: {remaining_time}"
                    )
                    return

                # Process divination using coin toss method
                result = await self.plugin.process_divination(
                    question=question.strip(),
                    launcher_type=launcher_type,
                    sender_id=sender_id,
                )

                yield CommandReturn(text=result)

            except Exception as e:
                logger.error(f"Error handling divination command: {e}", exc_info=True)
                yield CommandReturn(
                    text=f"**错误**: 算卦过程出现错误: {str(e)}\n请稍后再试或联系管理员。"
                )
        
        # Help subcommand
        @self.subcommand(
            name="help",
            help="显示算卦命令的帮助信息",
            usage="算卦 help",
            aliases=["帮助"],
        )
        async def help_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show help information"""
            try:
                help_text = self.plugin._get_help_text()
                yield CommandReturn(text=help_text)
                    
            except Exception as e:
                logger.error(f"Error showing help: {e}", exc_info=True)
                yield CommandReturn(text=f"**错误**: 获取帮助信息时出错: {str(e)}")
        
        # History subcommand
        @self.subcommand(
            name="history",
            help="查看您的算卦历史记录",
            usage="算卦 history",
            aliases=["历史"],
        )
        async def history_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show divination history"""
            try:
                sender_id = str(context.session.launcher_id)
                launcher_type = str(context.session.launcher_type.value) if hasattr(context.session.launcher_type, 'value') else str(context.session.launcher_type)
                history_text = self.plugin._get_history_text(launcher_type, sender_id)
                yield CommandReturn(text=history_text)
                    
            except Exception as e:
                logger.error(f"Error showing history: {e}", exc_info=True)
                yield CommandReturn(text=f"**错误**: 获取历史记录时出错: {str(e)}")
        
        # My ID subcommand
        @self.subcommand(
            name="myid",
            help="查看您的用户ID",
            usage="算卦 myid",
            aliases=["我的ID", "id"],
        )
        async def myid_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show user ID"""
            try:
                sender_id = str(context.session.launcher_id)
                yield CommandReturn(text=f"**您的用户ID是**: {sender_id}")
                    
            except Exception as e:
                logger.error(f"Error showing user ID: {e}", exc_info=True)
                yield CommandReturn(text=f"**错误**: 获取用户ID时出错: {str(e)}")
        
        # Admin: Reset user usage
        @self.subcommand(
            name="reset",
            help="重置用户今日使用次数（仅管理员）",
            usage="算卦 reset <用户ID>",
            aliases=["重置"],
        )
        async def reset_usage_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Reset user usage (admin only)"""
            try:
                sender_id = str(context.session.launcher_id)
                launcher_type = str(context.session.launcher_type.value) if hasattr(context.session.launcher_type, 'value') else str(context.session.launcher_type)
                
                # Check admin permission
                if not self.plugin._is_admin(sender_id):
                    yield CommandReturn(text="**错误**: 此命令仅限管理员使用")
                    return

                # Parse parameters
                if len(context.crt_params) < 1:
                    yield CommandReturn(text="**错误**: 用法：算卦 reset <用户ID>")
                    return

                target_user = context.crt_params[0]
                self.plugin.limit.reset_user(launcher_type, target_user)
                yield CommandReturn(text=f"✅ **已重置**用户 {target_user} 的今日使用次数")

            except Exception as e:
                logger.error(f"Error resetting user usage: {e}", exc_info=True)
                yield CommandReturn(text=f"**错误**: 重置使用次数时出错: {str(e)}")
        
        # Admin: Statistics
        @self.subcommand(
            name="stats",
            help="查看系统使用统计（仅管理员）",
            usage="算卦 stats",
            aliases=["统计"],
        )
        async def stats_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show statistics (admin only)"""
            try:
                sender_id = str(context.session.launcher_id)
                
                # Check admin permission
                if not self.plugin._is_admin(sender_id):
                    yield CommandReturn(text="**错误**: 此命令仅限管理员使用")
                    return

                stats = self.plugin.limit.get_usage_statistics()
                stats_text = f"""## 📊 系统使用统计
- **总用户数**: {stats['total_users']}
- **总使用次数**: {stats['total_usage']}
- **上次重置**: {stats['last_reset']}
"""
                yield CommandReturn(text=stats_text)

            except Exception as e:
                logger.error(f"Error showing statistics: {e}", exc_info=True)
                yield CommandReturn(text=f"**错误**: 获取统计信息时出错: {str(e)}")
