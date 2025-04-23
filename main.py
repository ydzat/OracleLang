import os
import re
import time
import asyncio
from typing import List, Dict, Any, Optional
import pathlib

from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import PersonNormalMessageReceived, GroupNormalMessageReceived

# 修改导入路径，使用相对导入
from .src.calculator import HexagramCalculator
from .src.interpreter import HexagramInterpreter
from .src.glyphs import HexagramRenderer
from .src.history import HistoryManager
from .src.limit import UsageLimit
from . import config


# 注册插件
@register(
    name="OracleLang",
    description="一个基于易经原理的智能算卦插件。支持多种起卦方式，提供专业的卦象解读。",
    version="0.1.0",
    author="ydzat"
)
class OracleLangPlugin(BasePlugin):
    # 命令前缀
    CMD_PREFIX = "算卦"
    
    # 添加锁和队列，确保线程安全
    lock = asyncio.Lock()
    command_queue = asyncio.Queue()
    
    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.host = host
        print("OracleLang 插件初始化中...")
        
        # 获取插件所在目录
        self.plugin_dir = pathlib.Path(__file__).parent.absolute()
        
        # 确保数据目录存在
        os.makedirs(os.path.join(self.plugin_dir, "data/history"), exist_ok=True)
        os.makedirs(os.path.join(self.plugin_dir, "data/static"), exist_ok=True)
        os.makedirs(os.path.join(self.plugin_dir, "data/limits"), exist_ok=True)
        
        # 初始化各模块
        self.config = config.load_config(self.plugin_dir)
        self.calculator = HexagramCalculator()
        self.interpreter = HexagramInterpreter(self.config, self.plugin_dir)
        self.renderer = HexagramRenderer()
        self.history = HistoryManager(os.path.join(self.plugin_dir, "data/history"))
        self.limit = UsageLimit(self.config, os.path.join(self.plugin_dir, "data/limits"))
        
        print("OracleLang 插件初始化完成")

    # 异步初始化
    async def initialize(self):
        # 加载静态数据
        print("正在加载卦象数据...")
        await self.interpreter.load_data()
        print("卦象数据加载完成")

    # 当收到个人消息时触发
    @handler(PersonNormalMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext):
        await self.command_queue.put(ctx)  # 将命令上下文放入队列
        await self.process_commands()  # 处理命令

    # 当收到群消息时触发
    @handler(GroupNormalMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        await self.command_queue.put(ctx)  # 将命令上下文放入队列
        await self.process_commands()  # 处理命令

    # 添加命令处理队列
    async def process_commands(self):
        while not self.command_queue.empty():  # 当队列不为空时
            ctx = await self.command_queue.get()  # 从队列中获取命令上下文
            await self._process_message(ctx)  # 执行命令处理
            await asyncio.sleep(0.5)  # 添加短暂延迟以防止过于频繁的处理

    async def _process_message(self, ctx: EventContext):
        async with self.lock:  # 使用锁确保线程安全
            msg = ctx.event.text_message
            sender_id = ctx.event.sender_id
            
            # 清理文本，移除@信息
            cleaned_text = re.sub(r'@\S+\s*', '', msg).strip()
            
            # 检查是否是算卦命令
            if not cleaned_text.startswith(self.CMD_PREFIX):
                return
                
            # 提取命令参数
            cmd_args = cleaned_text[len(self.CMD_PREFIX):].strip()
            
            # 处理用户ID查询命令
            if cmd_args.strip() == "我的ID":
                ctx.add_return("reply", [f"您的用户ID是: {sender_id}"])
                ctx.prevent_default()
                return
            
            # 处理管理命令（仅管理员可用）
            if self._is_admin(sender_id) and (cmd_args.startswith("设置") or cmd_args.startswith("重置") or cmd_args.startswith("统计")):
                await self._handle_admin_commands(ctx, cmd_args)
                ctx.prevent_default()
                return
            
            # 检查用户当日使用次数
            if not self.limit.check_user_limit(sender_id):
                remaining_time = self.limit.get_reset_time()
                ctx.add_return("reply", [f"您今日的算卦次数已达上限（{self.config['limit']['daily_max']}次/天），请等待重置。\n"
                                         f"下次重置时间: {remaining_time}"])
                ctx.prevent_default()
                return
                
            # 解析命令参数
            method, params, question = self._parse_command(cmd_args)
            
            # 处理历史记录查询
            if method == "历史":
                await self._show_history(ctx, sender_id)
                ctx.prevent_default()
                return
                
            # 生成卦象
            try:
                print(f"用户 {sender_id} 使用方法 {method} 算卦，参数：{params}，问题：{question}")
                hexagram_data = await self.calculator.calculate(
                    method=method,
                    input_text=params or question,
                    user_id=sender_id
                )
                
                # 生成卦象图示
                style = self.config["display"]["style"]
                visual = self.renderer.render_hexagram(
                    hexagram_data["original"],
                    hexagram_data["changed"],
                    hexagram_data["moving"],
                    style=style
                )
                
                # 获取卦象解释
                interpretation = await self.interpreter.interpret(
                    hexagram_original=hexagram_data["hexagram_original"],
                    hexagram_changed=hexagram_data["hexagram_changed"],
                    moving=hexagram_data["moving"],
                    question=question,
                    use_llm=self.config["llm"]["enabled"]
                )
                
                # 构建响应消息
                result_msg = self._format_response(question, hexagram_data, interpretation, visual)
                
                # 记录到历史
                self.history.save_record(
                    user_id=sender_id,
                    question=question,
                    hexagram_data=hexagram_data,
                    interpretation=interpretation
                )
                
                # 更新用户使用次数
                self.limit.update_usage(sender_id)
                remaining = self.limit.get_remaining(sender_id)
                
                # 添加使用次数提示
                result_msg += f"\n\n今日剩余算卦次数: {remaining}/{self.config['limit']['daily_max']}"
                
                # 返回结果
                ctx.add_return("reply", [result_msg])
                ctx.prevent_default()
                
            except Exception as e:
                print(f"算卦过程出错: {str(e)}")
                ctx.add_return("reply", [f"算卦过程出现错误: {str(e)}\n请稍后再试或联系管理员。"])
                ctx.prevent_default()

    def _parse_command(self, cmd_args: str) -> tuple:
        """解析命令参数，返回 (起卦方法, 方法参数, 问题)"""
        # 支持的起卦方法
        methods = ["数字", "时间", "历史"]
        
        method = "text"  # 默认为文本起卦
        params = None
        question = cmd_args
        
        # 检查是否指定了起卦方法
        parts = cmd_args.split(maxsplit=2)
        if parts and parts[0] in methods:
            method = parts[0]
            if len(parts) >= 2:
                params = parts[1]
                question = parts[2] if len(parts) >= 3 else ""
        
        return method, params, question
    
    def _format_response(self, question: str, hexagram_data: Dict, interpretation: Dict, visual: str) -> str:
        """格式化响应消息"""
        original_name = interpretation["original"]["name"]
        changed_name = interpretation["changed"]["name"]
        
        response = [
            f"📝 问题: {question}" if question else "🔮 随缘一卦",
            f"\n{visual}",
            f"\n📌 卦象: {original_name} {'→' if hexagram_data['moving'].count(1) > 0 else ''} {changed_name if hexagram_data['moving'].count(1) > 0 else ''}",
            f"\n✨ 卦辞: {interpretation['original']['gua_ci']}",
        ]
        
        # 动爻解释
        if hexagram_data['moving'].count(1) > 0:
            response.append("\n🔄 动爻:")
            for i, line in enumerate(interpretation["moving_lines_meaning"]):
                if line:
                    response.append(f"  {line}")
        
        # 总体解释
        response.append(f"\n📜 解释: {interpretation['overall_meaning']}")
        
        # 建议
        if "advice" in interpretation:
            response.append(f"\n💡 建议: {interpretation['advice']}")
            
        return "\n".join(response)
        
    async def _show_history(self, ctx: EventContext, user_id: str):
        """显示用户历史记录"""
        records = self.history.get_recent_records(user_id, limit=5)
        
        if not records:
            ctx.add_return("reply", ["您还没有算卦记录。"])
            return
            
        result = ["您的近期算卦记录：\n"]
        for i, record in enumerate(records, 1):
            timestamp = record.get("timestamp", "未知时间")
            question = record.get("question", "无问题")
            result.append(f"{i}. [{timestamp}] {question}")
            
            # 添加简要结果
            summary = record.get("result_summary", "")
            if summary:
                result.append(f"   {summary}")
                
        ctx.add_return("reply", ["\n".join(result)])
        
    async def _handle_admin_commands(self, ctx: EventContext, cmd: str):
        """处理管理员命令"""
        sender_id = ctx.event.sender_id
        parts = cmd.split()
        
        if parts[0] == "设置" and len(parts) >= 3 and parts[1] == "次数":
            try:
                new_limit = int(parts[2])
                if new_limit > 0:
                    self.config["limit"]["daily_max"] = new_limit
                    config.save_config(self.config, self.plugin_dir)
                    ctx.add_return("reply", [f"每日算卦次数上限已设置为 {new_limit} 次"])
                else:
                    ctx.add_return("reply", ["次数必须为正整数"])
            except ValueError:
                ctx.add_return("reply", ["格式错误，请使用数字设置次数"])
                
        elif parts[0] == "重置" and len(parts) >= 2:
            target_user = parts[1]
            self.limit.reset_user(target_user)
            ctx.add_return("reply", [f"已重置用户 {target_user} 的算卦次数"])
            
        elif parts[0] == "统计":
            stats = self.limit.get_usage_statistics()
            total_users = stats.get("total_users", 0)
            total_usage = stats.get("total_usage", 0)
            ctx.add_return("reply", [f"算卦统计:\n总用户数: {total_users}\n总使用次数: {total_usage}"])
        
        else:
            ctx.add_return("reply", ["无效的管理命令，支持的命令：\n算卦 设置 次数 [数字]\n算卦 重置 [用户ID]\n算卦 统计"])
    
    def _is_admin(self, user_id: str) -> bool:
        """检查用户是否是管理员"""
        # 这里可以根据配置文件或其他方式判断用户是否是管理员
        # 临时简单实现，实际应从配置读取
        admin_list = self.config.get("admin_users", [])
        return user_id in admin_list

    # 插件卸载时触发
    def __del__(self):
        try:
            print("OracleLang 插件已卸载")
        except:
            # 避免在卸载过程中出现属性错误
            pass
