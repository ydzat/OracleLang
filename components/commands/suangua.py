"""
OracleLang Divination Command Component
Handles the '!suangua' or '!算卦' command for I Ching divination
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command
from langbot_plugin.api.entities.builtin.command.context import ExecuteContext, CommandReturn

logger = logging.getLogger(__name__)


class SuanguaCommand(Command):
    """I Ching divination command handler"""

    async def _execute(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
        """
        Override the default _execute to handle custom command routing.
        This allows us to catch all unmatched subcommands as divination questions.
        """
        context.shift()

        # Check if it's a registered subcommand
        if context.crt_command in self.registered_subcommands:
            subcommand = self.registered_subcommands[context.crt_command]
            async for return_value in subcommand.subcommand(self, context):
                yield return_value
        else:
            # Treat as divination question - call the default handler
            if "" in self.registered_subcommands:
                # Shift back to include the "subcommand" as part of the question
                context.crt_params.insert(0, context.crt_command)
                context.crt_command = ""

                subcommand = self.registered_subcommands[""]
                async for return_value in subcommand.subcommand(self, context):
                    yield return_value
            else:
                yield CommandReturn(text=f"❌ 未知命令: {context.crt_command}")

    async def initialize(self):
        """Initialize command handler and register subcommands"""
        await super().initialize()

        # Default handler for divination (root command with question as parameters)
        @self.subcommand(
            name="",  # Empty string means default handler
            help="六爻算卦 - 三钱法起卦",
            usage="suangua <问题>",
            aliases=[],
        )
        async def divination_default(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """
            Handle divination command with question as parameters

            Examples:
                !suangua 今日运势
                !suangua 我今天的工作运势如何？
            """
            try:
                # Get sender ID
                sender_id = str(context.session.launcher_id)

                # All parameters are the question
                question = " ".join(context.crt_params) if context.crt_params else ""

                if not question.strip():
                    yield CommandReturn(
                        text="请输入您的问题。使用 !suangua help 查看使用说明。"
                    )
                    return

                # Check user daily usage limit
                if not self.plugin.limit.check_user_limit(sender_id):
                    remaining_time = self.plugin.limit.get_reset_time()
                    yield CommandReturn(
                        text=f"您今日的算卦次数已达上限（{self.plugin.plugin_config['limit']['daily_max']}次/天），请等待重置。\n下次重置时间: {remaining_time}"
                    )
                    return

                # Process divination using coin toss method
                result = await self.plugin.process_divination(
                    question=question.strip(),
                    sender_id=sender_id
                )

                yield CommandReturn(text=result)

            except Exception as e:
                logger.error(f"Error handling divination command: {e}", exc_info=True)
                yield CommandReturn(
                    text=f"❌ 算卦过程出现错误: {str(e)}\n请稍后再试或联系管理员。"
                )
        
        # Help subcommand
        @self.subcommand(
            name="help",
            help="显示算卦命令的帮助信息",
            usage="suangua help",
            aliases=["帮助"],
        )
        async def help_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show help information"""
            try:
                help_text = self.plugin._get_help_text()
                yield CommandReturn(text=help_text)
                    
            except Exception as e:
                logger.error(f"Error showing help: {e}", exc_info=True)
                yield CommandReturn(text=f"❌ 获取帮助信息时出错: {str(e)}")
        
        # History subcommand
        @self.subcommand(
            name="history",
            help="查看您的算卦历史记录",
            usage="suangua history",
            aliases=["历史"],
        )
        async def history_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show divination history"""
            try:
                sender_id = str(context.session.launcher_id)
                history_text = self.plugin._get_history_text(sender_id)
                yield CommandReturn(text=history_text)
                    
            except Exception as e:
                logger.error(f"Error showing history: {e}", exc_info=True)
                yield CommandReturn(text=f"❌ 获取历史记录时出错: {str(e)}")
        
        # My ID subcommand
        @self.subcommand(
            name="myid",
            help="查看您的用户ID",
            usage="suangua myid",
            aliases=["我的ID", "id"],
        )
        async def myid_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show user ID"""
            try:
                sender_id = str(context.session.launcher_id)
                yield CommandReturn(text=f"您的用户ID是: {sender_id}")
                    
            except Exception as e:
                logger.error(f"Error showing user ID: {e}", exc_info=True)
                yield CommandReturn(text=f"❌ 获取用户ID时出错: {str(e)}")
        
        # Admin: Set user limit
        @self.subcommand(
            name="set",
            help="设置用户每日限额（仅管理员）",
            usage="suangua set <用户ID> <次数>",
            aliases=["设置"],
        )
        async def set_limit_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Set user daily limit (admin only)"""
            try:
                sender_id = str(context.session.launcher_id)
                
                # Check admin permission
                if not self.plugin._is_admin(sender_id):
                    yield CommandReturn(text="❌ 此命令仅限管理员使用")
                    return

                # Parse parameters
                if len(context.crt_params) < 2:
                    yield CommandReturn(text="❌ 用法：!suangua set <用户ID> <次数>")
                    return

                target_user = context.crt_params[0]
                try:
                    new_limit = int(context.crt_params[1])
                    self.plugin.limit.set_user_limit(target_user, new_limit)
                    yield CommandReturn(text=f"✅ 已将用户 {target_user} 的每日限额设置为 {new_limit} 次")
                except ValueError:
                    yield CommandReturn(text="❌ 错误：次数必须是整数")

            except Exception as e:
                logger.error(f"Error setting user limit: {e}", exc_info=True)
                yield CommandReturn(text=f"❌ 设置限额时出错: {str(e)}")
        
        # Admin: Reset user usage
        @self.subcommand(
            name="reset",
            help="重置用户今日使用次数（仅管理员）",
            usage="suangua reset <用户ID>",
            aliases=["重置"],
        )
        async def reset_usage_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Reset user usage (admin only)"""
            try:
                sender_id = str(context.session.launcher_id)
                
                # Check admin permission
                if not self.plugin._is_admin(sender_id):
                    yield CommandReturn(text="❌ 此命令仅限管理员使用")
                    return

                # Parse parameters
                if len(context.crt_params) < 1:
                    yield CommandReturn(text="❌ 用法：!suangua reset <用户ID>")
                    return

                target_user = context.crt_params[0]
                self.plugin.limit.reset_user_usage(target_user)
                yield CommandReturn(text=f"✅ 已重置用户 {target_user} 的今日使用次数")

            except Exception as e:
                logger.error(f"Error resetting user usage: {e}", exc_info=True)
                yield CommandReturn(text=f"❌ 重置使用次数时出错: {str(e)}")
        
        # Admin: Statistics
        @self.subcommand(
            name="stats",
            help="查看系统使用统计（仅管理员）",
            usage="suangua stats",
            aliases=["统计"],
        )
        async def stats_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show statistics (admin only)"""
            try:
                sender_id = str(context.session.launcher_id)
                
                # Check admin permission
                if not self.plugin._is_admin(sender_id):
                    yield CommandReturn(text="❌ 此命令仅限管理员使用")
                    return

                stats = self.plugin.limit.get_statistics()
                stats_text = f"""📊 系统使用统计：
总用户数：{stats['total_users']}
今日活跃用户：{stats['active_today']}
总算卦次数：{stats['total_divinations']}
今日算卦次数：{stats['today_divinations']}
"""
                yield CommandReturn(text=stats_text)

            except Exception as e:
                logger.error(f"Error showing statistics: {e}", exc_info=True)
                yield CommandReturn(text=f"❌ 获取统计信息时出错: {str(e)}")

