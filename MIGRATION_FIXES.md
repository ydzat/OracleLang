# OracleLang Plugin - LangBot 4.0 Migration Fixes

## Date: 2025-11-07 (Final - Command Component Implementation)

This document records all fixes applied to migrate OracleLang plugin to LangBot 4.0.

## ⚠️ CRITICAL DISCOVERIES

### 1. Logger Usage
**LangBot 4.0 plugins do NOT have `self.ap.logger` attribute!**

- `BasePlugin` does NOT have an `ap` attribute
- `BasePlugin` does NOT have a `logger` attribute  
- The official documentation mentioning `self.ap.logger` is **INCORRECT or OUTDATED**

**✅ Correct approach: Use standard Python `logging.getLogger(__name__)`**

### 2. Component Architecture
**LangBot 4.0 uses Command Component instead of Event Listener for commands**

- Commands are triggered by `!` prefix (e.g., `!算卦`)
- Event listeners are for intercepting pipeline events
- For command-based functionality, use Command component, not Event Listener

## Issues Fixed

### 1. ✅ `.env.example` File
**Status**: Already existed with correct content.

### 2. ✅ Logger Usage
**Status**: Fixed - Using Standard Python Logging

**Changes**:
- Added `import logging` and `logger = logging.getLogger(__name__)` in all files
- Replaced all `self.ap.logger` with `logger`
- Applied to: `main.py`, command components

### 3. ✅ Component Architecture - Command Component
**Status**: Migrated from Event Listener to Command Component

**Problem**: 
- Original implementation used Event Listener to intercept messages
- This doesn't align with LangBot 4.0's command architecture
- Commands should use the Command component

**Solution**:
- Removed Event Listener component
- Created Command component: `components/command/suangua.py`
- Registered command with name "算卦"
- Users now trigger with `!算卦` or `！算卦`

**Command Structure**:
```python
# Root command: !算卦 [args]
@self.subcommand(name="", ...)
async def divination(...)

# Subcommands:
@self.subcommand(name="帮助", ...)  # !算卦 帮助
@self.subcommand(name="历史", ...)  # !算卦 历史
@self.subcommand(name="我的ID", ...)  # !算卦 我的ID
```

**Usage Examples**:
- `!算卦 我今天的工作运势如何？`
- `!算卦 时间 我今天的工作运势如何？`
- `!算卦 数字 123 456 我今天的工作运势如何？`
- `!算卦 帮助`
- `!算卦 历史`
- `!算卦 我的ID`

## Migration Checklist

- [x] Plugin structure follows LangBot 4.0 component architecture
- [x] `manifest.yaml` correctly configured
- [x] `main.py` correctly inherits from `BasePlugin`
- [x] **Command component created and registered** ⭐
- [x] `.env.example` file exists for debugging
- [x] **Logger uses standard Python `logging.getLogger(__name__)`** ⭐
- [x] All component `__init__.py` files exist
- [x] No syntax errors or import issues

## Package Information

**Latest Package**: `plugins/OracleLang/dist/OracleLang-v2.0.2.lbpkg`
**MD5 Checksum**: `45aa7d552f5114bff35e39d24b5a5c2e`
**Generated**: 2025-11-07
**Size**: 80K

## Key Takeaways

**For LangBot 4.0 Plugin Development:**

### Logger Usage:
- ❌ DO NOT use `self.ap.logger`
- ❌ DO NOT use `self.plugin.ap.logger`  
- ✅ DO use `logging.getLogger(__name__)` in all plugin files

### Component Selection:
- ✅ Use **Command Component** for commands triggered by `!` prefix
- ✅ Use **Event Listener** for intercepting pipeline events
- ✅ Use **Tool Component** for LLM function calling

### Command Component:
- Commands are triggered by `!<command_name>` (e.g., `!算卦`)
- Use `@self.subcommand(name="", ...)` for root command
- Use `@self.subcommand(name="subname", ...)` for subcommands
- Access parameters via `context.crt_params`
- Return results using `yield CommandReturn(text=...)`

## References

- [LangBot 4.0 Plugin Development Tutorial](https://docs.langbot.app/zh/plugin/dev/tutor.html)
- [Command Component Guide](https://docs.langbot.app/zh/plugin/dev/components/command.html)
- [Pipeline Events](https://docs.langbot.app/zh/plugin/dev/apis/pipeline-events.html)
