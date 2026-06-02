"""
OracleLang Divination Event Listener Component
Listens for messages starting with "算卦" and routes to subcommands.
"""
from __future__ import annotations

import logging
from typing import Dict

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.platform import message as platform_message

from src.image_renderer import markdown_to_message_chain

logger = logging.getLogger(__name__)

# Subcommand alias mapping (must match suangua.py)
SUBCMD_ALIASES: Dict[str, str] = {
    "help": "help",
    "帮助": "help",
    "history": "history",
    "历史": "history",
    "myid": "myid",
    "我的id": "myid",
    "id": "myid",
    "我的ID": "myid",
    "set": "set",
    "设置": "set",
    "reset": "reset",
    "重置": "reset",
    "stats": "stats",
    "统计": "stats",
}


class DivinationEventListener(EventListener):
    """Event listener for 算卦 prefix messages."""

    async def initialize(self):
        """Register event handlers for person and group normal messages."""
        await super().initialize()

        @self.handler(events.PersonNormalMessageReceived)
        async def handle_person(ctx: context.EventContext):
            await self._handle_message(ctx)

        @self.handler(events.GroupNormalMessageReceived)
        async def handle_group(ctx: context.EventContext):
            await self._handle_message(ctx)

    def _resolve_subcommand(self, first_token: str) -> str:
        """Resolve a token to a canonical subcommand name.

        Returns the canonical name (help/history/myid/set/reset/stats) or
        empty string for divination (unknown/no token).
        """
        if not first_token:
            return ""
        return SUBCMD_ALIASES.get(first_token.lower(), "")

    # ── message routing ──────────────────────────────────────────────

    async def _handle_message(self, ctx: context.EventContext):
        """Main entry point for all incoming messages.

        Matches messages starting with "算卦" and routes to subcommands.
        Non-matching messages are silently ignored.
        """
        try:
            text = ctx.event.text_message.strip()
            if not text.startswith("算卦"):
                return  # IGNORE silently

            # Extract content after "算卦"
            content = text[2:].strip()
            tokens = content.split(None, 1) if content else []
            first_token = tokens[0] if tokens else ""
            rest_text = tokens[1] if len(tokens) > 1 else ""

            # Subcommand routing
            subcommand = self._resolve_subcommand(first_token)
            if not subcommand:
                # No recognized subcommand → treat entire content as divination question
                question = content
            else:
                question = rest_text

            # Identity info from event
            launcher_type = ctx.event.launcher_type  # "person" or "group"
            sender_id = str(ctx.event.sender_id)

            # Dispatch
            if subcommand == "help":
                await self._handle_help(ctx)
            elif subcommand == "history":
                await self._handle_history(ctx, launcher_type, sender_id)
            elif subcommand == "myid":
                await self._handle_myid(ctx, launcher_type, sender_id)
            elif subcommand in ("set", "reset", "stats"):
                await self._handle_admin(ctx, subcommand, launcher_type, sender_id, question)
            else:
                # divination (subcommand == "")
                await self._handle_divination(ctx, question, launcher_type, sender_id)

            # 阻止主 pipeline 重复处理此消息
            ctx.prevent_default()

        except Exception:
            logger.error("Error handling 算卦 message", exc_info=True)
            await ctx.reply(
                platform_message.MessageChain([
                    platform_message.Plain(text="❌ 处理算卦消息时出错，请稍后再试。"),
                ])
            )

    # ── subcommand handlers ───────────────────────────────────────────

    async def _handle_help(self, ctx: context.EventContext):
        """Reply with the divination help text."""
        help_text = self.plugin._get_help_text()
        await ctx.reply(
            platform_message.MessageChain([
                platform_message.Plain(text=help_text),
            ])
        )

    async def _handle_history(self, ctx: context.EventContext, launcher_type: str, sender_id: str):
        """Reply with the user's recent divination history."""
        try:
            records = self.plugin.history.get_recent_records(
                launcher_type, sender_id, limit=10
            )
        except Exception:
            logger.error(f"Failed to load history for {launcher_type}_{sender_id}", exc_info=True)
            records = []

        if not records:
            response = "您还没有算卦记录"
        else:
            lines = ["您的算卦历史记录（最近10条）：", ""]
            for i, record in enumerate(records, 1):
                timestamp = record.get("timestamp", "未知时间")
                question = record.get("question", "无问题")
                hexagram_original = record.get("hexagram_original", "")
                summary = record.get("result_summary", hexagram_original or "未知卦象")

                lines.append(f"{i}. {timestamp}")
                lines.append(f"   问题：{question}")
                lines.append(f"   卦象：{summary}")
                lines.append("")
            response = "\n".join(lines)

        await ctx.reply(
            platform_message.MessageChain([
                platform_message.Plain(text=response),
            ])
        )

    async def _handle_myid(self, ctx: context.EventContext, launcher_type: str, sender_id: str):
        """Reply with the sender's user ID and launcher type."""
        response = (
            f"您的信息：\n"
            f"  用户ID: {sender_id}\n"
            f"  会话类型: {'群聊' if launcher_type == 'group' else '私聊'}\n"
            f"  会话ID: {str(ctx.event.launcher_id)}"
        )
        await ctx.reply(
            platform_message.MessageChain([
                platform_message.Plain(text=response),
            ])
        )

    async def _handle_admin(
        self,
        ctx: context.EventContext,
        subcommand: str,
        launcher_type: str,
        sender_id: str,
        rest_text: str,
    ):
        """Handle admin-only subcommands (set/reset/stats)."""
        # Admin permission check
        if not self.plugin._is_admin(sender_id):
            await ctx.reply(
                platform_message.MessageChain([
                    platform_message.Plain(text="❌ 此命令仅限管理员使用"),
                ])
            )
            return

        if subcommand == "set":
            await self._admin_set(ctx, launcher_type, rest_text)
        elif subcommand == "reset":
            await self._admin_reset(ctx, launcher_type, rest_text)
        elif subcommand == "stats":
            await self._admin_stats(ctx)

    async def _admin_set(self, ctx: context.EventContext, launcher_type: str, args: str):
        """Admin: set user daily limit — currently unsupported."""
        await ctx.reply(
            platform_message.MessageChain([
                platform_message.Plain(text="❌ 设置用户限额功能暂未实现，请通过插件配置修改全局每日限额。"),
            ])
        )

    async def _admin_reset(self, ctx: context.EventContext, launcher_type: str, args: str):
        """Admin: reset a user's daily usage count."""
        if not args.strip():
            await ctx.reply(
                platform_message.MessageChain([
                    platform_message.Plain(text="❌ 用法：算卦 reset <用户ID>"),
                ])
            )
            return

        # First token is the target user ID
        target_user = args.split(None, 1)[0].strip()
        try:
            self.plugin.limit.reset_user(launcher_type="person", user_id=target_user)
            await ctx.reply(
                platform_message.MessageChain([
                    platform_message.Plain(
                        text=f"✅ 已重置用户 {target_user} 的今日使用次数"
                    ),
                ])
            )
        except Exception as e:
            logger.error(f"Failed to reset user {target_user}: {e}", exc_info=True)
            await ctx.reply(
                platform_message.MessageChain([
                    platform_message.Plain(text=f"❌ 重置失败: {str(e)}"),
                ])
            )

    async def _admin_stats(self, ctx: context.EventContext):
        """Admin: show global usage statistics."""
        try:
            usage_stats = self.plugin.limit.get_usage_statistics()
            stats_text = (
                f"📊 系统使用统计：\n"
                f"总用户数：{usage_stats.get('total_users', 0)}\n"
                f"总使用次数：{usage_stats.get('total_usage', 0)}\n"
                f"上次重置：{usage_stats.get('last_reset', '未知')}"
            )
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}", exc_info=True)
            stats_text = f"❌ 获取统计信息失败: {str(e)}"

        await ctx.reply(
            platform_message.MessageChain([
                platform_message.Plain(text=stats_text),
            ])
        )

    # ── divination ────────────────────────────────────────────────────

    async def _handle_divination(
        self,
        ctx: context.EventContext,
        question: str,
        launcher_type: str,
        sender_id: str,
    ):
        """Process a divination request."""
        if not question.strip():
            await ctx.reply(
                platform_message.MessageChain([
                    platform_message.Plain(
                        text="请输入您的问题。发送「算卦 help」查看使用说明。"
                    ),
                ])
            )
            return

        # Pre-check daily limit (new API with launcher_type)
        if not self.plugin.limit.check_user_limit(launcher_type, sender_id):
            remaining_time = self.plugin.limit.get_reset_time()
            daily_max = self.plugin.plugin_config.get("limit", {}).get("daily_max", 3)
            await ctx.reply(
                platform_message.MessageChain([
                    platform_message.Plain(
                        text=(
                            f"您今日的算卦次数已达上限（{daily_max}次/天），请等待重置。\n"
                            f"下次重置时间: {remaining_time}"
                        ),
                    ),
                ])
            )
            return

        # Process divination via plugin
        try:
            result = await self.plugin.process_divination(
                question=question.strip(),
                launcher_type=launcher_type,
                sender_id=sender_id,
            )
        except Exception:
            logger.error(f"Divination failed for {sender_id}", exc_info=True)
            result = "❌ 算卦过程出现错误，请稍后再试。"

        await ctx.reply(
            await markdown_to_message_chain(result)
        )
