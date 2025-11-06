"""
Test script to validate HEXAGRAM_MAP correctness
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_constants import HEXAGRAM_MAP, HEXAGRAM_UNICODE, HEXAGRAM_NAMES


def test_hexagram_map_completeness():
    """Test that all 64 binary values are mapped"""
    print("Testing HEXAGRAM_MAP completeness...")
    
    # Check we have exactly 64 entries
    assert len(HEXAGRAM_MAP) == 64, f"Expected 64 entries, got {len(HEXAGRAM_MAP)}"
    print(f"✓ HEXAGRAM_MAP has 64 entries")
    
    # Check all binary values from 0 to 63 are present
    expected_keys = set(range(64))
    actual_keys = set(HEXAGRAM_MAP.keys())
    
    missing = expected_keys - actual_keys
    if missing:
        print(f"✗ Missing binary values: {sorted(missing)}")
        return False
    
    extra = actual_keys - expected_keys
    if extra:
        print(f"✗ Extra binary values: {sorted(extra)}")
        return False
    
    print(f"✓ All binary values 0-63 are mapped")
    return True


def test_hexagram_map_uniqueness():
    """Test that all hexagram numbers are unique (no duplicates)"""
    print("\nTesting HEXAGRAM_MAP uniqueness...")
    
    values = list(HEXAGRAM_MAP.values())
    unique_values = set(values)
    
    if len(values) != len(unique_values):
        print(f"✗ Found duplicate hexagram numbers!")
        
        # Find duplicates
        from collections import Counter
        counts = Counter(values)
        duplicates = {k: v for k, v in counts.items() if v > 1}
        
        for hex_num, count in duplicates.items():
            print(f"  Hexagram {hex_num} appears {count} times")
            # Find which binary values map to this
            binary_vals = [bin(k) for k, v in HEXAGRAM_MAP.items() if v == hex_num]
            print(f"    Binary values: {binary_vals}")
        
        return False
    
    print(f"✓ All hexagram numbers are unique")
    return True


def test_hexagram_map_range():
    """Test that all hexagram numbers are in range 1-64"""
    print("\nTesting HEXAGRAM_MAP value range...")
    
    values = HEXAGRAM_MAP.values()
    min_val = min(values)
    max_val = max(values)
    
    if min_val < 1 or max_val > 64:
        print(f"✗ Values out of range: min={min_val}, max={max_val}")
        return False
    
    print(f"✓ All values in range 1-64 (min={min_val}, max={max_val})")
    
    # Check all numbers 1-64 are present
    expected_values = set(range(1, 65))
    actual_values = set(values)
    
    missing = expected_values - actual_values
    if missing:
        print(f"✗ Missing hexagram numbers: {sorted(missing)}")
        return False
    
    print(f"✓ All hexagram numbers 1-64 are present")
    return True


def test_unicode_map_consistency():
    """Test that HEXAGRAM_UNICODE has same keys as HEXAGRAM_MAP"""
    print("\nTesting HEXAGRAM_UNICODE consistency...")
    
    if len(HEXAGRAM_UNICODE) != 64:
        print(f"✗ HEXAGRAM_UNICODE has {len(HEXAGRAM_UNICODE)} entries, expected 64")
        return False
    
    map_keys = set(HEXAGRAM_MAP.keys())
    unicode_keys = set(HEXAGRAM_UNICODE.keys())
    
    if map_keys != unicode_keys:
        missing = map_keys - unicode_keys
        extra = unicode_keys - map_keys
        if missing:
            print(f"✗ HEXAGRAM_UNICODE missing keys: {sorted(missing)}")
        if extra:
            print(f"✗ HEXAGRAM_UNICODE has extra keys: {sorted(extra)}")
        return False
    
    print(f"✓ HEXAGRAM_UNICODE has matching keys with HEXAGRAM_MAP")
    return True


def print_sample_mappings():
    """Print some sample mappings for verification"""
    print("\nSample mappings:")
    print("-" * 60)
    
    samples = [
        0b111111,  # Should be 乾 (1)
        0b000000,  # Should be 坤 (2)
        0b010010,  # Should be 坎 (29)
        0b110101,  # Should be 离 (30)
    ]
    
    for binary in samples:
        hex_num = HEXAGRAM_MAP.get(binary, "NOT FOUND")
        unicode_char = HEXAGRAM_UNICODE.get(binary, "?")
        hex_name = HEXAGRAM_NAMES.get(hex_num, "Unknown") if hex_num != "NOT FOUND" else "Unknown"
        
        print(f"Binary {bin(binary):>10s} ({binary:2d}) -> Hexagram {hex_num:2} {unicode_char} {hex_name}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("HEXAGRAM_MAP Validation Tests")
    print("=" * 60)
    
    tests = [
        test_hexagram_map_completeness,
        test_hexagram_map_uniqueness,
        test_hexagram_map_range,
        test_unicode_map_consistency,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print_sample_mappings()
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

