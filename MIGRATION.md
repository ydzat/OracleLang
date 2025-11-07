# OracleLang 插件迁移指南

本文档说明了 OracleLang 插件从 LangBot 3.x 迁移到 4.0 的主要变化。

## ✅ 迁移状态

**迁移完成日期**: 2025-11-07
**当前版本**: 2.0.2
**状态**: ✅ 已完成迁移并修复所有问题

所有必要的修复已完成,插件现已完全兼容 LangBot 4.0。详细的修复记录请参见 [MIGRATION_FIXES.md](./MIGRATION_FIXES.md)。

## 主要变化

### 1. 插件架构

**旧版本 (3.x)**:
- 单一 `main.py` 文件包含所有逻辑
- 使用 `@register` 装饰器注册插件
- 使用 `@handler` 装饰器注册事件处理器
- 配置通过 `config.yaml` 文件管理

**新版本 (4.0)**:
- 组件化架构，分离关注点
- `manifest.yaml` 定义插件元数据和配置schema
- `main.py` 包含插件主类
- `components/` 目录包含各种组件（事件监听器、命令、工具等）
- 配置通过 WebUI 管理

### 2. 文件结构

```
OracleLang/
├── manifest.yaml           # 插件清单（新增）
├── main.py                 # 插件主类（重构）
├── assets/                 # 资源文件（新增）
│   └── icon.svg           # 插件图标
├── components/             # 组件目录（新增）
│   ├── __init__.py
│   └── event_listener/    # 事件监听器组件
│       ├── __init__.py
│       ├── default.yaml   # 组件清单
│       └── default.py     # 组件实现
├── src/                    # 核心模块（保持不变）
│   ├── calculator.py
│   ├── interpreter.py
│   ├── glyphs.py
│   ├── history.py
│   ├── limit.py
│   └── data_constants.py
├── data/                   # 数据目录（保持不变）
│   ├── history/
│   ├── limits/
│   └── static/
├── requirements.txt        # 依赖（更新）
├── README.md              # 说明文档（更新）
├── .env.example           # 调试配置示例（新增）
└── config.yaml            # 旧配置文件（已废弃，保留用于兼容）
```

### 3. 代码变化

#### 导入变化

**旧版本**:
```python
from pkg.plugin.context import register, handler, BasePlugin, APIHost, EventContext
from pkg.plugin.events import PersonNormalMessageReceived, GroupNormalMessageReceived
```

**新版本**:
```python
from langbot_plugin.api.definition.plugin import BasePlugin
from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import events, context
from langbot_plugin.api.entities.builtin.platform import message as platform_message
```

#### 插件类变化

**旧版本**:
```python
@register(
    name="OracleLang",
    description="...",
    version="1.0.2",
    author="ydzat"
)
class OracleLangPlugin(BasePlugin):
    def __init__(self, host: APIHost):
        self.host = host
        # 初始化代码
    
    @handler(PersonNormalMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext):
        # 处理消息
```

**新版本**:
```python
class OracleLangPlugin(BasePlugin):
    async def initialize(self):
        await super().initialize()
        # 初始化代码
        config_data = self.get_config()
        # 使用配置
    
    async def process_divination_message(self, msg: str, sender_id: str) -> str:
        # 处理消息逻辑
        # 返回响应文本
```

#### 事件处理变化

**旧版本**: 在插件主类中使用装饰器
```python
@handler(PersonNormalMessageReceived)
async def person_normal_message_received(self, ctx: EventContext):
    # 处理逻辑
    ctx.add_return("reply", [response])
    ctx.prevent_default()
```

**新版本**: 在事件监听器组件中注册
```python
# components/event_listener/default.py
class DefaultEventListener(EventListener):
    async def initialize(self):
        await super().initialize()
        
        @self.handler(events.PersonMessageReceived)
        async def on_person_message(event_context: context.EventContext):
            # 调用插件方法处理
            response = await self.plugin.process_divination_message(msg, sender_id)
            if response:
                await event_context.reply(
                    platform_message.MessageChain([
                        platform_message.Plain(text=response)
                    ])
                )
                event_context.prevent_default()
```

### 4. 配置管理变化

**旧版本**:
- 直接读写 `config.yaml` 文件
- 使用自定义的 `config.py` 模块

**新版本**:
- 配置schema在 `manifest.yaml` 中定义
- 通过 `self.get_config()` 获取配置
- 配置通过 WebUI 修改
- 运行时配置修改不会持久化（需要通过WebUI修改）

### 5. 日志记录变化

**旧版本**:
```python
print("OracleLang 插件初始化中...")
```

**新版本**:
```python
self.ap.logger.info("OracleLang plugin initializing...")
self.ap.logger.error("Error message", exc_info=True)
```

## 迁移步骤

如果您要从旧版本迁移到新版本：

1. **备份数据**: 备份 `data/` 目录中的所有数据
2. **更新 LangBot**: 确保 LangBot 已升级到 4.0 或更高版本
3. **卸载旧版本**: 在 WebUI 中卸载旧版本的 OracleLang 插件
4. **安装新版本**: 通过 WebUI 或手动安装新版本
5. **配置插件**: 在 WebUI 中配置插件参数
6. **恢复数据**: 如果需要，将备份的数据复制回 `data/` 目录
7. **测试功能**: 测试所有功能是否正常工作

## 兼容性说明

- 新版本需要 LangBot 4.0 或更高版本
- 旧版本的 `config.yaml` 文件将被忽略
- 历史记录和使用限制数据格式保持不变，可以直接迁移
- 所有核心功能（算卦、历史记录、使用限制等）保持不变

## 获取帮助

如果在迁移过程中遇到问题：

1. 查看 LangBot 日志获取错误信息
2. 参考 [LangBot 插件开发文档](https://docs.langbot.app/zh/plugin/dev/tutor.html)
3. 在 GitHub 仓库提交 Issue
4. 加入 LangBot 社区寻求帮助

## 参考资源

- [LangBot 4.0 插件开发教程](https://docs.langbot.app/zh/plugin/dev/tutor.html)
- [LangBot 插件迁移指南](https://docs.langbot.app/zh/plugin/dev/migration.html)
- [LangBot GitHub 仓库](https://github.com/langbot-app/LangBot)

