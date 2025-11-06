#!/usr/bin/env python3
"""
测试解释器能否正确加载完整的64卦数据
"""

import asyncio
import os
import sys
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.interpreter import HexagramInterpreter


async def test_interpreter_loading():
    """测试解释器加载数据"""
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print("="*60)
    print("Testing HexagramInterpreter data loading...")
    print("="*60)
    
    # 创建解释器实例
    config = {
        "llm": {
            "enabled": False
        }
    }
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    interpreter = HexagramInterpreter(config, base_dir=base_dir, logger=logger)
    
    # 加载数据
    print("\n✓ Test 1: Loading hexagram data...")
    await interpreter.load_data()
    
    # 检查数据是否加载成功
    assert interpreter.data_loaded, "Data should be loaded"
    assert len(interpreter.hexagrams_data) == 64, f"Expected 64 hexagrams, got {len(interpreter.hexagrams_data)}"
    print(f"  PASS: Loaded {len(interpreter.hexagrams_data)} hexagrams")
    
    # 测试几个特定的卦象
    print("\n✓ Test 2: Checking specific hexagrams...")
    test_hexagrams = [1, 2, 29, 30, 63, 64]
    
    for num in test_hexagrams:
        data = interpreter.hexagrams_data.get(str(num))
        assert data is not None, f"Hexagram {num} not found"
        assert "name" in data, f"Hexagram {num} missing 'name'"
        assert "gua_ci" in data, f"Hexagram {num} missing 'gua_ci'"
        assert "description" in data, f"Hexagram {num} missing 'description'"
        assert "lines" in data, f"Hexagram {num} missing 'lines'"
        assert len(data["lines"]) >= 6, f"Hexagram {num} has insufficient lines"
        
        print(f"  ✓ Hexagram {num}: {data['name']} - OK")
    
    print(f"  PASS: All test hexagrams verified")
    
    # 测试解释功能（不使用LLM）
    print("\n✓ Test 3: Testing interpret function...")
    result = await interpreter.interpret(
        hexagram_original=1,
        hexagram_changed=2,
        moving=[0, 0, 0, 0, 0, 0],
        question="测试问题",
        use_llm=False
    )

    assert "original" in result, "Result missing 'original'"
    assert "changed" in result, "Result missing 'changed'"
    assert result["original"]["name"] == "乾为天", f"Expected '乾为天', got '{result['original']['name']}'"
    # 没有动爻时，changed应该等于original
    assert result["changed"]["name"] == "乾为天", f"Expected '乾为天' (no moving lines), got '{result['changed']['name']}'"

    print(f"  PASS: Interpret function works correctly")
    print(f"    Original: {result['original']['name']}")
    print(f"    Changed: {result['changed']['name']}")
    print(f"    Overall meaning: {result.get('overall_meaning', '')[:50]}...")

    # 测试有动爻的情况
    print("\n✓ Test 4: Testing interpret with moving lines...")
    result_with_moving = await interpreter.interpret(
        hexagram_original=1,
        hexagram_changed=2,
        moving=[1, 0, 0, 0, 0, 0],  # 初爻动
        question="测试问题",
        use_llm=False
    )

    assert result_with_moving["original"]["name"] == "乾为天"
    assert result_with_moving["changed"]["name"] == "坤为地"
    assert any(result_with_moving["moving_lines_meaning"]), "Should have moving line meanings"

    print(f"  PASS: Interpret with moving lines works correctly")
    print(f"    Original: {result_with_moving['original']['name']}")
    print(f"    Changed: {result_with_moving['changed']['name']}")
    print(f"    Moving line: {result_with_moving['moving_lines_meaning'][0]}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_interpreter_loading())
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

