#!/usr/bin/env python3
"""
测试卦象数据的完整性和正确性
"""

import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_hexagram_data_completeness():
    """测试卦象数据的完整性"""
    
    # 加载数据文件
    data_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data/static/hexagrams.json"
    )
    
    print(f"Loading hexagram data from: {data_file}")
    
    with open(data_file, "r", encoding="utf-8") as f:
        hexagrams = json.load(f)
    
    # 测试1: 检查是否有64卦
    print(f"\n✓ Test 1: Checking if all 64 hexagrams exist...")
    assert len(hexagrams) == 64, f"Expected 64 hexagrams, got {len(hexagrams)}"
    print(f"  PASS: Found all 64 hexagrams")
    
    # 测试2: 检查每一卦的编号是否正确（1-64）
    print(f"\n✓ Test 2: Checking hexagram numbers...")
    for i in range(1, 65):
        assert str(i) in hexagrams, f"Hexagram {i} is missing"
    print(f"  PASS: All hexagram numbers (1-64) are present")
    
    # 测试3: 检查每一卦的必需字段
    print(f"\n✓ Test 3: Checking required fields for each hexagram...")
    required_fields = ["name", "gua_ci", "description", "lines"]
    
    for num, data in hexagrams.items():
        for field in required_fields:
            assert field in data, f"Hexagram {num} is missing field: {field}"
        
        # 检查爻辞数量（应该是6个或7个，7个包含用九/用六）
        assert len(data["lines"]) >= 6, f"Hexagram {num} has only {len(data['lines'])} lines, expected at least 6"
        
        # 检查字段不为空
        assert data["name"], f"Hexagram {num} has empty name"
        assert data["gua_ci"], f"Hexagram {num} has empty gua_ci"
        assert data["description"], f"Hexagram {num} has empty description"
    
    print(f"  PASS: All hexagrams have required fields")
    
    # 测试4: 显示一些示例数据
    print(f"\n✓ Test 4: Sample hexagram data:")
    for num in ["1", "2", "29", "30", "63", "64"]:
        data = hexagrams[num]
        print(f"\n  Hexagram {num}: {data['name']}")
        print(f"    卦辞: {data['gua_ci'][:30]}...")
        print(f"    描述: {data['description'][:40]}...")
        print(f"    爻辞数量: {len(data['lines'])}")
    
    print(f"\n{'='*60}")
    print(f"✅ ALL TESTS PASSED!")
    print(f"{'='*60}")
    print(f"Total hexagrams: {len(hexagrams)}")
    print(f"Data file: {data_file}")
    
    return True


if __name__ == "__main__":
    try:
        test_hexagram_data_completeness()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

