#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置验证模块
用于验证插件配置的有效性
"""

import logging
from typing import Dict, Any, List, Tuple, Optional


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        验证配置的有效性
        
        参数:
            config: 配置字典
            
        返回:
            (is_valid, errors, warnings) 元组
            - is_valid: 配置是否有效
            - errors: 错误列表（导致配置无效）
            - warnings: 警告列表（不影响使用但建议修改）
        """
        self.errors = []
        self.warnings = []
        
        # 验证各个配置项
        self._validate_limit_config(config.get("limit", {}))
        self._validate_llm_config(config.get("llm", {}))
        self._validate_display_config(config.get("display", {}))
        self._validate_admin_users(config.get("admin_users", []))
        self._validate_debug(config.get("debug", False))
        
        is_valid = len(self.errors) == 0
        
        # 记录验证结果
        if is_valid:
            self.logger.info("Configuration validation passed")
            if self.warnings:
                for warning in self.warnings:
                    self.logger.warning(f"Config warning: {warning}")
        else:
            self.logger.error("Configuration validation failed")
            for error in self.errors:
                self.logger.error(f"Config error: {error}")
        
        return is_valid, self.errors.copy(), self.warnings.copy()
    
    def _validate_limit_config(self, limit_config: Dict[str, Any]):
        """验证使用限制配置"""
        # 验证 daily_max
        daily_max = limit_config.get("daily_max")
        if daily_max is None:
            self.warnings.append("limit.daily_max 未设置，将使用默认值 3")
        elif not isinstance(daily_max, int):
            self.errors.append(f"limit.daily_max 必须是整数，当前类型: {type(daily_max).__name__}")
        elif daily_max <= 0:
            self.errors.append(f"limit.daily_max 必须大于 0，当前值: {daily_max}")
        elif daily_max > 100:
            self.warnings.append(f"limit.daily_max 设置过高 ({daily_max})，建议设置在 1-100 之间")
        
        # 验证 reset_hour
        reset_hour = limit_config.get("reset_hour")
        if reset_hour is None:
            self.warnings.append("limit.reset_hour 未设置，将使用默认值 0")
        elif not isinstance(reset_hour, int):
            self.errors.append(f"limit.reset_hour 必须是整数，当前类型: {type(reset_hour).__name__}")
        elif reset_hour < 0 or reset_hour > 23:
            self.errors.append(f"limit.reset_hour 必须在 0-23 之间，当前值: {reset_hour}")
    
    def _validate_llm_config(self, llm_config: Dict[str, Any]):
        """验证 LLM 配置"""
        # 验证 enabled
        enabled = llm_config.get("enabled")
        if enabled is None:
            self.warnings.append("llm.enabled 未设置，将使用默认值 False")
        elif not isinstance(enabled, bool):
            self.errors.append(f"llm.enabled 必须是布尔值，当前类型: {type(enabled).__name__}")
        
        # 如果启用了 LLM，验证相关配置
        if enabled:
            # 验证 api_type
            api_type = llm_config.get("api_type")
            valid_api_types = ["openai", "deepseek", "qianfan", "azure"]
            
            if not api_type:
                self.errors.append("llm.enabled 为 True 时，llm.api_type 不能为空")
            elif api_type not in valid_api_types:
                self.errors.append(
                    f"llm.api_type 必须是以下之一: {', '.join(valid_api_types)}，当前值: {api_type}"
                )
            
            # 验证 api_key
            api_key = llm_config.get("api_key")
            if not api_key or not isinstance(api_key, str) or not api_key.strip():
                self.errors.append("llm.enabled 为 True 时，llm.api_key 不能为空")
            elif len(api_key) < 10:
                self.warnings.append(f"llm.api_key 长度过短 ({len(api_key)} 字符)，可能无效")
            
            # 验证 api_base（Azure 必需）
            api_base = llm_config.get("api_base", "")
            if api_type == "azure":
                if not api_base or not isinstance(api_base, str) or not api_base.strip():
                    self.errors.append("使用 Azure OpenAI 时，llm.api_base 不能为空")
                elif not api_base.startswith(("http://", "https://")):
                    self.errors.append(f"llm.api_base 必须是有效的 URL，当前值: {api_base}")
            elif api_base and not api_base.startswith(("http://", "https://")):
                self.warnings.append(f"llm.api_base 可能不是有效的 URL: {api_base}")
            
            # 验证 model
            model = llm_config.get("model")
            if not model or not isinstance(model, str) or not model.strip():
                self.errors.append("llm.enabled 为 True 时，llm.model 不能为空")
            
            # 验证 api_secret（千帆需要）
            if api_type == "qianfan":
                api_secret = llm_config.get("api_secret", "")
                if not api_secret or not isinstance(api_secret, str) or not api_secret.strip():
                    self.warnings.append("使用百度千帆时，建议设置 llm.api_secret")
    
    def _validate_display_config(self, display_config: Dict[str, Any]):
        """验证显示配置"""
        # 验证 style
        style = display_config.get("style")
        valid_styles = ["simple", "traditional", "detailed"]
        
        if style is None:
            self.warnings.append("display.style 未设置，将使用默认值 'detailed'")
        elif not isinstance(style, str):
            self.errors.append(f"display.style 必须是字符串，当前类型: {type(style).__name__}")
        elif style not in valid_styles:
            self.errors.append(
                f"display.style 必须是以下之一: {', '.join(valid_styles)}，当前值: {style}"
            )
        
        # 验证 language
        language = display_config.get("language")
        valid_languages = ["zh", "en"]
        
        if language is None:
            self.warnings.append("display.language 未设置，将使用默认值 'zh'")
        elif not isinstance(language, str):
            self.errors.append(f"display.language 必须是字符串，当前类型: {type(language).__name__}")
        elif language not in valid_languages:
            self.warnings.append(
                f"display.language 建议使用: {', '.join(valid_languages)}，当前值: {language}"
            )
    
    def _validate_admin_users(self, admin_users: Any):
        """验证管理员用户列表"""
        if admin_users is None:
            self.warnings.append("admin_users 未设置，将使用默认值 []")
        elif not isinstance(admin_users, list):
            self.errors.append(f"admin_users 必须是列表，当前类型: {type(admin_users).__name__}")
        else:
            # 验证列表中的每个元素
            for i, user_id in enumerate(admin_users):
                if not isinstance(user_id, str):
                    self.errors.append(
                        f"admin_users[{i}] 必须是字符串，当前类型: {type(user_id).__name__}"
                    )
                elif not user_id.strip():
                    self.warnings.append(f"admin_users[{i}] 是空字符串，将被忽略")
    
    def _validate_debug(self, debug: Any):
        """验证调试模式配置"""
        if debug is None:
            self.warnings.append("debug 未设置，将使用默认值 False")
        elif not isinstance(debug, bool):
            self.errors.append(f"debug 必须是布尔值，当前类型: {type(debug).__name__}")


def validate_config(config: Dict[str, Any], logger: Optional[logging.Logger] = None) -> Tuple[bool, List[str], List[str]]:
    """
    验证配置的便捷函数
    
    参数:
        config: 配置字典
        logger: 日志记录器（可选）
        
    返回:
        (is_valid, errors, warnings) 元组
    """
    validator = ConfigValidator(logger)
    return validator.validate(config)

