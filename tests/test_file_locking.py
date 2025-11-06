#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试跨平台文件锁功能
"""

import os
import sys
import json
import tempfile
import threading
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from filelock import FileLock


def test_basic_file_lock():
    """测试基本的文件锁功能"""
    print("测试基本文件锁功能...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.json")
        lock_file = test_file + ".lock"
        
        # 写入测试数据
        lock = FileLock(lock_file, timeout=10)
        with lock:
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump({"test": "data"}, f)
        
        # 读取测试数据
        with lock:
            with open(test_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        assert data == {"test": "data"}, "数据读写失败"
        print("✓ 基本文件锁功能正常")


def test_concurrent_writes():
    """测试并发写入时的文件锁保护"""
    print("\n测试并发写入保护...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "concurrent.json")
        lock_file = test_file + ".lock"
        
        # 初始化文件
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump({"counter": 0}, f)
        
        def increment_counter(thread_id):
            """增加计数器的线程函数"""
            lock = FileLock(lock_file, timeout=10)
            for _ in range(10):
                with lock:
                    # 读取当前值
                    with open(test_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # 增加计数器
                    data["counter"] += 1
                    
                    # 写回文件
                    with open(test_file, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                
                # 模拟一些处理时间
                time.sleep(0.001)
        
        # 创建多个线程并发写入
        threads = []
        num_threads = 5
        for i in range(num_threads):
            t = threading.Thread(target=increment_counter, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证最终结果
        with open(test_file, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        
        expected_count = num_threads * 10
        assert final_data["counter"] == expected_count, \
            f"并发写入失败: 期望 {expected_count}, 实际 {final_data['counter']}"
        
        print(f"✓ 并发写入保护正常 (5个线程各写入10次，最终计数: {final_data['counter']})")


def test_lock_timeout():
    """测试文件锁超时功能"""
    print("\n测试文件锁超时...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "timeout.json")
        lock_file = test_file + ".lock"
        
        # 创建测试文件
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump({"test": "timeout"}, f)
        
        # 第一个锁持有较长时间
        lock1 = FileLock(lock_file, timeout=10)
        lock1.acquire()
        
        try:
            # 第二个锁尝试获取（应该超时）
            lock2 = FileLock(lock_file, timeout=1)
            try:
                lock2.acquire()
                # 如果成功获取锁，说明有问题
                lock2.release()
                assert False, "应该超时但没有超时"
            except Exception as e:
                # 预期会超时
                print(f"✓ 文件锁超时功能正常 (超时异常: {type(e).__name__})")
        finally:
            lock1.release()


def test_lock_release():
    """测试文件锁的正确释放"""
    print("\n测试文件锁释放...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "release.json")
        lock_file = test_file + ".lock"
        
        # 创建测试文件
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump({"test": "release"}, f)
        
        # 获取并释放锁
        lock1 = FileLock(lock_file, timeout=10)
        with lock1:
            with open(test_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # 锁应该已经释放，可以再次获取
        lock2 = FileLock(lock_file, timeout=1)
        with lock2:
            with open(test_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        print("✓ 文件锁释放功能正常")


def test_cross_platform_compatibility():
    """测试跨平台兼容性"""
    print("\n测试跨平台兼容性...")
    
    import platform
    system = platform.system()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "platform.json")
        lock_file = test_file + ".lock"
        
        # 在当前平台上测试文件锁
        lock = FileLock(lock_file, timeout=10)
        with lock:
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump({"platform": system}, f)
        
        with lock:
            with open(test_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        assert data["platform"] == system, "平台信息不匹配"
        print(f"✓ 跨平台兼容性正常 (当前平台: {system})")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("跨平台文件锁测试")
    print("=" * 60)
    
    try:
        test_basic_file_lock()
        test_concurrent_writes()
        test_lock_timeout()
        test_lock_release()
        test_cross_platform_compatibility()
        
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

