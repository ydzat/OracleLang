#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试时区处理功能
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.limit import UsageLimit


def test_timezone_configuration():
    """测试时区配置"""
    print("测试时区配置...")
    
    # 创建临时目录
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    # 测试默认时区（Asia/Shanghai）
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "timezone": "Asia/Shanghai"
    }
    
    limit = UsageLimit(config, temp_dir)
    assert limit.timezone is not None
    print(f"✓ 默认时区设置成功: {limit.timezone}")
    
    # 测试其他时区
    config["timezone"] = "America/New_York"
    limit = UsageLimit(config, temp_dir)
    assert limit.timezone is not None
    print(f"✓ 美国东部时区设置成功: {limit.timezone}")
    
    config["timezone"] = "Europe/London"
    limit = UsageLimit(config, temp_dir)
    assert limit.timezone is not None
    print(f"✓ 伦敦时区设置成功: {limit.timezone}")
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)


def test_current_date():
    """测试获取当前日期"""
    print("\n测试获取当前日期...")
    
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "timezone": "Asia/Shanghai"
    }
    
    limit = UsageLimit(config, temp_dir)
    current_date = limit._get_current_date()
    
    # 验证日期格式
    assert len(current_date) == 10  # YYYY-MM-DD
    assert current_date.count("-") == 2
    
    # 验证可以解析为日期
    datetime.strptime(current_date, "%Y-%m-%d")
    
    print(f"✓ 当前日期: {current_date}")
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)


def test_reset_time():
    """测试重置时间计算"""
    print("\n测试重置时间计算...")
    
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    # 测试默认重置时间（0点）
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "timezone": "Asia/Shanghai"
    }
    
    limit = UsageLimit(config, temp_dir)
    reset_time = limit.get_reset_time()
    
    # 验证时间格式
    assert len(reset_time) == 19  # YYYY-MM-DD HH:MM:SS
    
    # 验证可以解析为日期时间
    datetime.strptime(reset_time, "%Y-%m-%d %H:%M:%S")
    
    print(f"✓ 下次重置时间（0点）: {reset_time}")
    
    # 测试自定义重置时间（6点）
    config["limit"]["reset_hour"] = 6
    limit = UsageLimit(config, temp_dir)
    reset_time = limit.get_reset_time()
    
    # 验证时间中包含 06:00:00
    assert "06:00:00" in reset_time
    
    print(f"✓ 下次重置时间（6点）: {reset_time}")
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)


def test_timezone_fallback():
    """测试时区回退机制"""
    print("\n测试时区回退机制...")
    
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    # 测试无效时区
    config = {
        "limit": {"daily_max": 3, "reset_hour": 0},
        "timezone": "Invalid/Timezone"
    }
    
    limit = UsageLimit(config, temp_dir)
    
    # 应该回退到 Asia/Shanghai
    assert limit.timezone is not None
    current_date = limit._get_current_date()
    assert len(current_date) == 10
    
    print(f"✓ 无效时区正确回退到默认时区")
    
    # 清理
    import shutil
    shutil.rmtree(temp_dir)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("时区处理测试")
    print("=" * 60)
    
    try:
        test_timezone_configuration()
        test_current_date()
        test_reset_time()
        test_timezone_fallback()
        
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

