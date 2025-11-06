#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LLM响应解析功能
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.interpreter import HexagramInterpreter


def test_json_parsing():
    """测试JSON格式解析"""
    print("测试 JSON 格式解析...")
    
    # 创建一个简单的配置
    config = {
        "llm": {
            "enabled": False,
            "api_key": "",
            "api_type": "openai",
            "model": "gpt-3.5-turbo"
        }
    }
    
    # 创建解释器实例（不需要logger，因为我们只测试解析方法）
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
        def debug(self, msg): pass
        def error(self, msg, exc_info=False): print(f"[ERROR] {msg}")
    
    interpreter = HexagramInterpreter(config, logger=MockLogger())
    
    # 测试用例1: 标准JSON格式
    json_response = json.dumps({
        "overall_meaning": "此卦象征着事物的开始和发展，具有强大的生命力。",
        "fortune": "吉",
        "advice": "顺势而为，把握时机，积极进取。"
    }, ensure_ascii=False)
    
    result = interpreter._parse_llm_response(json_response)
    assert result["overall_meaning"] == "此卦象征着事物的开始和发展，具有强大的生命力。"
    assert result["fortune"] == "吉"
    assert result["advice"] == "顺势而为，把握时机，积极进取。"
    print("✓ 标准JSON格式解析成功")
    
    # 测试用例2: 带markdown代码块的JSON
    markdown_json = """```json
{
  "overall_meaning": "当前处于困难时期，需要谨慎行事。",
  "fortune": "凶",
  "advice": "保持低调，等待时机。"
}
```"""
    
    result = interpreter._parse_llm_response(markdown_json)
    assert result["overall_meaning"] == "当前处于困难时期，需要谨慎行事。"
    assert result["fortune"] == "凶"
    assert result["advice"] == "保持低调，等待时机。"
    print("✓ Markdown代码块JSON解析成功")
    
    # 测试用例3: fortune字段规范化
    json_with_verbose_fortune = json.dumps({
        "overall_meaning": "平稳发展",
        "fortune": "此卦为吉卦",
        "advice": "继续努力"
    }, ensure_ascii=False)
    
    result = interpreter._parse_llm_response(json_with_verbose_fortune)
    assert result["fortune"] == "吉"
    print("✓ Fortune字段规范化成功")
    
    print("\n所有JSON解析测试通过！\n")


def test_text_parsing():
    """测试文本格式解析（备用方案）"""
    print("测试文本格式解析...")
    
    config = {
        "llm": {
            "enabled": False,
            "api_key": "",
            "api_type": "openai",
            "model": "gpt-3.5-turbo"
        }
    }
    
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
        def debug(self, msg): pass
        def error(self, msg, exc_info=False): print(f"[ERROR] {msg}")
    
    interpreter = HexagramInterpreter(config, logger=MockLogger())

    # 测试用例1: 数字编号格式
    text_response_1 = """1. 整体意义：此卦象征着天行健，君子以自强不息。代表着强大的创造力和进取精神。

2. 吉凶判断：吉

3. 建议：保持积极进取的态度，勇于开拓创新，但也要注意不要过于冒进。"""

    result = interpreter._parse_llm_response(text_response_1)
    print(f"DEBUG: 解析结果 = {result}")
    assert "天行健" in result["overall_meaning"], f"Expected '天行健' in '{result['overall_meaning']}'"
    assert result["fortune"] == "吉", f"Expected '吉', got '{result['fortune']}'"
    assert "积极进取" in result["advice"], f"Expected '积极进取' in '{result['advice']}'"
    print("✓ 数字编号格式解析成功")
    
    # 测试用例2: 中文编号格式
    text_response_2 = """一、整体意义：坤卦代表大地，象征着包容和承载。

二、吉凶判断：平

三、建议：以柔克刚，厚德载物。"""
    
    result = interpreter._parse_llm_response(text_response_2)
    assert "坤卦" in result["overall_meaning"]
    assert result["fortune"] == "平"
    assert "柔克刚" in result["advice"]
    print("✓ 中文编号格式解析成功")
    
    # 测试用例3: 冒号分隔格式
    text_response_3 = """整体意义：震卦象征雷动，代表着突然的变化和震动。

吉凶判断：凶

建议：面对突如其来的变化，要保持冷静，审时度势。"""
    
    result = interpreter._parse_llm_response(text_response_3)
    assert "震卦" in result["overall_meaning"]
    assert result["fortune"] == "凶"
    assert "保持冷静" in result["advice"]
    print("✓ 冒号分隔格式解析成功")
    
    print("\n所有文本解析测试通过！\n")


def test_edge_cases():
    """测试边界情况"""
    print("测试边界情况...")
    
    config = {
        "llm": {
            "enabled": False,
            "api_key": "",
            "api_type": "openai",
            "model": "gpt-3.5-turbo"
        }
    }
    
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
        def debug(self, msg): pass
        def error(self, msg, exc_info=False): print(f"[ERROR] {msg}")
    
    interpreter = HexagramInterpreter(config, logger=MockLogger())

    # 测试空字符串
    result = interpreter._parse_llm_response("")
    assert result == {}
    print("✓ 空字符串处理正确")
    
    # 测试无效JSON（应该回退到文本解析）
    invalid_json = "这不是有效的JSON格式"
    result = interpreter._parse_llm_response(invalid_json)
    assert "overall_meaning" in result
    assert "fortune" in result
    assert "advice" in result
    print("✓ 无效JSON回退到文本解析")
    
    # 测试fortune字段中同时包含吉和凶（应该判断为凶）
    mixed_fortune = json.dumps({
        "overall_meaning": "测试",
        "fortune": "有吉有凶",
        "advice": "谨慎行事"
    }, ensure_ascii=False)
    
    result = interpreter._parse_llm_response(mixed_fortune)
    assert result["fortune"] == "凶"  # 凶优先
    print("✓ 混合吉凶判断正确（凶优先）")
    
    print("\n所有边界情况测试通过！\n")


if __name__ == "__main__":
    print("=" * 60)
    print("LLM响应解析测试")
    print("=" * 60)
    print()
    
    try:
        test_json_parsing()
        test_text_parsing()
        test_edge_cases()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

