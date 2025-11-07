"""
OracleLang Divination Command Component
Handles the '!算卦' command for I Ching divination
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command, Subcommand
from langbot_plugin.api.entities.builtin.command.context import ExecuteContext, CommandReturn

logger = logging.getLogger(__name__)


class SuanguaCommand(Command):
    """I Ching divination command handler"""

    async def initialize(self):
        """Initialize command handler and register subcommands"""
        await super().initialize()
        
        # Main divination command (root command)
        @self.subcommand(
            name="",  # Empty string means root command: !算卦
            help="易经算卦 - I Ching Divination",
            usage="算卦 [问题/参数]",
            aliases=[],
        )
        async def divination(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """
            Handle divination command
            
            Examples:
                !算卦 我今天的工作运势如何？
                !算卦 时间 我今天的工作运势如何？
                !算卦 数字 123 456 我今天的工作运势如何？
                !算卦 帮助
                !算卦 历史
            """
            try:
                # Get sender ID
                sender_id = str(context.session.launcher_id)
                
                # Get command arguments (everything after !算卦)
                # context.crt_params contains the parameters as a list
                args_text = " ".join(context.crt_params) if context.crt_params else ""
                
                # Construct the message in the format expected by process_divination_message
                # The method expects "算卦 <args>"
                msg_text = f"算卦 {args_text}".strip()
                
                # Process the divination message through the plugin
                response = await self.plugin.process_divination_message(msg_text, sender_id)
                
                # If we got a response, send it back
                if response:
                    yield CommandReturn(text=response)
                else:
                    # No response means it wasn't recognized as a divination command
                    yield CommandReturn(
                        text="未识别的命令。使用 !算卦 帮助 查看使用说明。"
                    )
                    
            except Exception as e:
                logger.error(f"Error handling divination command: {e}", exc_info=True)
                yield CommandReturn(
                    error=f"算卦过程出现错误: {str(e)}\n请稍后再试或联系管理员。"
                )
        
        # Help subcommand
        @self.subcommand(
            name="帮助",
            help="显示算卦命令的帮助信息",
            usage="算卦 帮助",
            aliases=["help"],
        )
        async def help_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show help information"""
            try:
                sender_id = str(context.session.launcher_id)
                msg_text = "算卦 帮助"
                response = await self.plugin.process_divination_message(msg_text, sender_id)
                
                if response:
                    yield CommandReturn(text=response)
                else:
                    yield CommandReturn(text="无法获取帮助信息")
                    
            except Exception as e:
                logger.error(f"Error showing help: {e}", exc_info=True)
                yield CommandReturn(error=f"获取帮助信息时出错: {str(e)}")
        
        # History subcommand
        @self.subcommand(
            name="历史",
            help="查看您的算卦历史记录",
            usage="算卦 历史",
            aliases=["history"],
        )
        async def history_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show divination history"""
            try:
                sender_id = str(context.session.launcher_id)
                msg_text = "算卦 历史"
                response = await self.plugin.process_divination_message(msg_text, sender_id)
                
                if response:
                    yield CommandReturn(text=response)
                else:
                    yield CommandReturn(text="无法获取历史记录")
                    
            except Exception as e:
                logger.error(f"Error showing history: {e}", exc_info=True)
                yield CommandReturn(error=f"获取历史记录时出错: {str(e)}")
        
        # My ID subcommand
        @self.subcommand(
            name="我的ID",
            help="查看您的用户ID",
            usage="算卦 我的ID",
            aliases=["myid", "id"],
        )
        async def myid_cmd(self, context: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
            """Show user ID"""
            try:
                sender_id = str(context.session.launcher_id)
                msg_text = "算卦 我的ID"
                response = await self.plugin.process_divination_message(msg_text, sender_id)
                
                if response:
                    yield CommandReturn(text=response)
                else:
                    yield CommandReturn(text=f"您的用户ID是: {sender_id}")
                    
            except Exception as e:
                logger.error(f"Error showing user ID: {e}", exc_info=True)
                yield CommandReturn(error=f"获取用户ID时出错: {str(e)}")

