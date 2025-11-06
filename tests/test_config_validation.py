#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置验证功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_validator import validate_config


def test_valid_config():
    """测试有效的配置"""
    print("测试有效配置...")
    
    config = {
        "limit": {
            "daily_max": 5,
            "reset_hour": 0
        },
        "llm": {
            "enabled": False,
            "api_type": "openai",
            "api_key": "",
            "api_base": "",
            "model": "gpt-3.5-turbo"
        },
        "display": {
            "style": "detailed",
            "language": "zh"
        },
        "admin_users": ["user1", "user2"],
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    
    assert is_valid, f"配置应该有效，但验证失败: {errors}"
    print("✓ 有效配置验证通过")


def test_invalid_daily_max():
    """测试无效的 daily_max"""
    print("\n测试无效的 daily_max...")
    
    # 测试负数
    config = {
        "limit": {"daily_max": -1, "reset_hour": 0},
        "llm": {"enabled": False},
        "display": {"style": "detailed"},
        "admin_users": [],
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "daily_max 为负数时应该验证失败"
    assert any("daily_max" in e and "大于 0" in e for e in errors), f"应该有 daily_max 错误: {errors}"
    print("✓ 负数 daily_max 正确被拒绝")
    
    # 测试非整数
    config["limit"]["daily_max"] = "5"
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "daily_max 为字符串时应该验证失败"
    assert any("daily_max" in e and "整数" in e for e in errors), f"应该有类型错误: {errors}"
    print("✓ 字符串 daily_max 正确被拒绝")


def test_invalid_reset_hour():
    """测试无效的 reset_hour"""
    print("\n测试无效的 reset_hour...")
    
    # 测试超出范围
    config = {
        "limit": {"daily_max": 3, "reset_hour": 25},
        "llm": {"enabled": False},
        "display": {"style": "detailed"},
        "admin_users": [],
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "reset_hour 超出范围时应该验证失败"
    assert any("reset_hour" in e and "0-23" in e for e in errors), f"应该有 reset_hour 范围错误: {errors}"
    print("✓ 超出范围的 reset_hour 正确被拒绝")


def test_llm_enabled_without_api_key():
    """测试启用 LLM 但没有 API key"""
    print("\n测试启用 LLM 但缺少配置...")
    
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "llm": {
            "enabled": True,
            "api_type": "openai",
            "api_key": "",  # 空 API key
            "api_base": "",
            "model": ""  # 空 model
        },
        "display": {"style": "detailed"},
        "admin_users": [],
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "LLM 启用但缺少必要配置时应该验证失败"
    assert any("api_key" in e for e in errors), f"应该有 api_key 错误: {errors}"
    assert any("model" in e for e in errors), f"应该有 model 错误: {errors}"
    print("✓ LLM 配置不完整正确被拒绝")


def test_invalid_api_type():
    """测试无效的 API 类型"""
    print("\n测试无效的 API 类型...")
    
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "llm": {
            "enabled": True,
            "api_type": "invalid_api",
            "api_key": "test-key-1234567890",
            "api_base": "",
            "model": "gpt-3.5-turbo"
        },
        "display": {"style": "detailed"},
        "admin_users": [],
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "无效的 api_type 应该验证失败"
    assert any("api_type" in e for e in errors), f"应该有 api_type 错误: {errors}"
    print("✓ 无效的 API 类型正确被拒绝")


def test_azure_without_api_base():
    """测试 Azure 配置缺少 api_base"""
    print("\n测试 Azure 配置缺少 api_base...")
    
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "llm": {
            "enabled": True,
            "api_type": "azure",
            "api_key": "test-key-1234567890",
            "api_base": "",  # Azure 需要 api_base
            "model": "gpt-35-turbo"
        },
        "display": {"style": "detailed"},
        "admin_users": [],
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "Azure 配置缺少 api_base 时应该验证失败"
    assert any("api_base" in e and "Azure" in e for e in errors), f"应该有 Azure api_base 错误: {errors}"
    print("✓ Azure 缺少 api_base 正确被拒绝")


def test_invalid_display_style():
    """测试无效的显示风格"""
    print("\n测试无效的显示风格...")
    
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "llm": {"enabled": False},
        "display": {"style": "invalid_style", "language": "zh"},
        "admin_users": [],
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "无效的 display.style 应该验证失败"
    assert any("display.style" in e for e in errors), f"应该有 display.style 错误: {errors}"
    print("✓ 无效的显示风格正确被拒绝")


def test_invalid_admin_users():
    """测试无效的管理员用户列表"""
    print("\n测试无效的管理员用户列表...")
    
    # 测试非列表类型
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "llm": {"enabled": False},
        "display": {"style": "detailed"},
        "admin_users": "not_a_list",
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "admin_users 不是列表时应该验证失败"
    assert any("admin_users" in e and "列表" in e for e in errors), f"应该有 admin_users 类型错误: {errors}"
    print("✓ 非列表的 admin_users 正确被拒绝")
    
    # 测试列表中包含非字符串元素
    config["admin_users"] = ["user1", 123, "user2"]
    is_valid, errors, warnings = validate_config(config)
    assert not is_valid, "admin_users 包含非字符串元素时应该验证失败"
    assert any("admin_users[1]" in e for e in errors), f"应该有元素类型错误: {errors}"
    print("✓ 包含非字符串元素的 admin_users 正确被拒绝")


def test_warnings():
    """测试警告情况"""
    print("\n测试警告情况...")
    
    config = {
        "limit": {"daily_max": 150, "reset_hour": 0},  # 过高的值
        "llm": {"enabled": False},
        "display": {"style": "detailed"},
        "admin_users": ["user1", ""],  # 包含空字符串
        "debug": False
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert is_valid, "配置应该有效（只有警告）"
    assert len(warnings) > 0, "应该有警告"
    assert any("daily_max" in w for w in warnings), f"应该有 daily_max 警告: {warnings}"
    print(f"✓ 警告正确生成 ({len(warnings)} 个警告)")


def test_complete_valid_llm_config():
    """测试完整有效的 LLM 配置"""
    print("\n测试完整有效的 LLM 配置...")
    
    # OpenAI 配置
    config = {
        "limit": {"daily_max": 5, "reset_hour": 0},
        "llm": {
            "enabled": True,
            "api_type": "openai",
            "api_key": "sk-1234567890abcdef",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-4"
        },
        "display": {"style": "detailed", "language": "zh"},
        "admin_users": ["admin1"],
        "debug": True
    }
    
    is_valid, errors, warnings = validate_config(config)
    assert is_valid, f"OpenAI 配置应该有效: {errors}"
    print("✓ OpenAI 配置验证通过")
    
    # Azure 配置
    config["llm"]["api_type"] = "azure"
    config["llm"]["api_base"] = "https://your-resource.openai.azure.com"
    
    is_valid, errors, warnings = validate_config(config)
    assert is_valid, f"Azure 配置应该有效: {errors}"
    print("✓ Azure 配置验证通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("配置验证测试")
    print("=" * 60)
    
    try:
        test_valid_config()
        test_invalid_daily_max()
        test_invalid_reset_hour()
        test_llm_enabled_without_api_key()
        test_invalid_api_type()
        test_azure_without_api_base()
        test_invalid_display_style()
        test_invalid_admin_users()
        test_warnings()
        test_complete_valid_llm_config()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

