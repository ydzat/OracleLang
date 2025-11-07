# Changelog

All notable changes to OracleLang plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-11-07

### Changed
- **BREAKING**: 从事件监听器模式迁移到命令模式
- **BREAKING**: 命令触发词从 `算卦` 改为 `!suangua` 或 `！suangua`
- **重大改进**: LLM 集成重构，使用 LangBot 4.0 内置 LLM API
- 简化配置：LLM 配置项从 6 个减少到 1 个（`llm_enabled`）
- 插件自动使用 LangBot 中配置的第一个可用 LLM 模型

### Added
- 命令组件架构，支持更灵活的命令路由
- 自动 LLM 模型选择和降级机制
- 更详细的错误日志和调试信息
- GitHub Actions 自动打包和发布

### Removed
- 移除独立的 LLM API 配置（api_type, api_key, api_base, api_secret, llm_model）
- 移除 aiohttp 依赖
- 移除事件监听器组件
- 移除测试文件（迁移到独立的测试仓库）
- 移除迁移文档（MIGRATION.md, MIGRATION_FIXES.md, Design.md）

### Fixed
- 修复 LangBot `get_llm_models()` API 返回格式兼容性问题
- 改进 LLM 调用错误处理
- 修复命令路由逻辑

## [2.0.2] - 2025-11-06

### Fixed
- 替换 `self.ap.logger` 为标准 Python `logging.getLogger(__name__)`
- 修复日志记录问题

## [2.0.1] - 2025-11-06

### Fixed
- 将相对导入改为绝对导入以提高插件兼容性

## [2.0.0] - 2025-11-06

### Changed
- **重大更新**: 迁移到 LangBot 4.0 插件系统
- 使用新的组件化架构（manifest.yaml + components）
- 通过 WebUI 配置插件参数
- 使用新的事件监听器组件处理消息

### Added
- 完整的配置验证功能
- 可配置时区支持（不再硬编码 UTC+8）
- 完整的测试覆盖
- 更好的错误处理和日志记录

### Removed
- 移除未使用的依赖（numpy、requests、pyyaml）

## [1.0.2] - 2025-04-25

### Changed
- 优化配置文件管理，自动生成默认配置

### Removed
- 删除多余的 config.yaml.example 文件

### Documentation
- 完善 README 文档，明确配置文件自动生成机制

## [1.0.1] - 2025-04-24

### Changed
- 将静态数据从代码中分离，统一到 data_constants.py 模块
- 完善 HEXAGRAM_UNICODE 映射表，支持所有 64 卦显示

### Added
- 添加 HEXAGRAM_NAMES 常量，便于卦象名称查询

## [1.0.0] - 2025-04-24

### Added
- 首次发布
- 支持多种起卦方式（文本、数字、时间）
- 实现基本卦象解读功能
- 添加用户使用限制
- 支持历史记录查询
- 可选的大语言模型集成

[2.1.0]: https://github.com/ydzat/OracleLang/compare/v2.0.2...v2.1.0
[2.0.2]: https://github.com/ydzat/OracleLang/compare/v2.0.1...v2.0.2
[2.0.1]: https://github.com/ydzat/OracleLang/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/ydzat/OracleLang/compare/v1.0.2...v2.0.0
[1.0.2]: https://github.com/ydzat/OracleLang/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/ydzat/OracleLang/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/ydzat/OracleLang/releases/tag/v1.0.0

