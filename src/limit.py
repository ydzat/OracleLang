import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from filelock import FileLock

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    from datetime import timezone

    class ZoneInfo:
        """Minimal ZoneInfo fallback for Python < 3.9"""
        def __init__(self, key: str):
            # Simple UTC+8 fallback for Asia/Shanghai
            if "Shanghai" in key or "Hong_Kong" in key or "Taipei" in key:
                self.offset = 8
            else:
                self.offset = 0

        def __repr__(self):
            return f"ZoneInfo(UTC+{self.offset})"


class UsageLimit:
    """
    用户使用限制类，管理每日算卦次数限制
    """

    def __init__(self, config: Dict, limit_dir: str = None, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        if limit_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.limit_dir = os.path.join(base_dir, "data/limits")
        else:
            self.limit_dir = limit_dir

        self.limit_file = os.path.join(self.limit_dir, "daily_usage.json")

        # Get timezone from config, default to Asia/Shanghai (UTC+8)
        timezone_str = self.config.get("timezone", "Asia/Shanghai")
        try:
            self.timezone = ZoneInfo(timezone_str)
            self.logger.debug(f"Using timezone: {timezone_str}")
        except Exception as e:
            self.logger.warning(f"Invalid timezone '{timezone_str}', falling back to Asia/Shanghai: {e}")
            self.timezone = ZoneInfo("Asia/Shanghai")

        # 确保目录存在
        os.makedirs(self.limit_dir, exist_ok=True)
        self.logger.debug(f"UsageLimit initialized with directory: {self.limit_dir}")

        # 加载使用数据
        self.usage_data = self._load_usage_data()

        # 检查是否需要重置
        self._check_reset()

        # 文件锁，用于确保多进程安全
        self.file_lock = None
    
    def _load_usage_data(self) -> Dict:
        """加载使用数据文件，并确保用户 ID 的唯一性"""
        if os.path.exists(self.limit_file):
            try:
                # 使用跨平台文件锁
                lock_file = self.limit_file + ".lock"
                lock = FileLock(lock_file, timeout=10)

                with lock:
                    with open(self.limit_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                # 确保 users 字典存在
                if "users" not in data:
                    data["users"] = {}

                # 去重处理，确保用户 ID 唯一且为字符串类型
                unique_users = {}
                for user_id, user_data in data["users"].items():
                    unique_users[str(user_id)] = user_data

                data["users"] = unique_users
                return data
            except Exception as e:
                self.logger.error(f"Failed to load usage data: {str(e)}", exc_info=True)
                return {"last_reset": self._get_current_date(), "users": {}}
        else:
            return {"last_reset": self._get_current_date(), "users": {}}
            
    def _save_usage_data(self):
        """保存使用数据到文件"""
        try:
            # 在保存之前去重，确保用户 ID 唯一
            unique_users = {}
            for user_id, user_data in self.usage_data["users"].items():
                # 确保用户ID始终是字符串类型
                user_id_str = str(user_id)
                unique_users[user_id_str] = user_data

            self.usage_data["users"] = unique_users

            # 使用跨平台文件锁确保文件写入的原子性
            lock_file = self.limit_file + ".lock"
            lock = FileLock(lock_file, timeout=10)

            with lock:
                with open(self.limit_file, "w", encoding="utf-8") as f:
                    json.dump(self.usage_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save usage data: {str(e)}", exc_info=True)
            
    def _get_current_date(self) -> str:
        """获取当前日期字符串（使用配置的时区）"""
        now = datetime.now(self.timezone)
        return now.strftime("%Y-%m-%d")
        
    def _check_reset(self):
        """检查是否需要重置使用次数（每天0点）"""
        current_date = self._get_current_date()
        last_reset = self.usage_data.get("last_reset", "")
        
        if current_date != last_reset:
            # 重置所有用户的使用次数
            self.usage_data["users"] = {}
            self.usage_data["last_reset"] = current_date
            self._save_usage_data()
            
    def check_user_limit(self, user_id: str) -> bool:
        """
        检查用户是否超过当日使用限制
        
        参数:
            user_id: 用户ID
            
        返回:
            True: 未超过限制，可以使用
            False: 已超过限制，不可使用
        """
        # 检查是否需要重置
        self._check_reset()
        
        # 确保用户ID是字符串类型
        user_id_str = str(user_id)
        
        # 获取用户的使用情况
        user_data = self.usage_data.get("users", {}).get(user_id_str, {"count": 0})
        count = user_data.get("count", 0)
        
        # 检查是否超过限制
        max_count = self.config.get("limit", {}).get("daily_max", 3)
        return count < max_count
        
    def update_usage(self, user_id: str):
        """
        更新用户的使用次数
        
        参数:
            user_id: 用户ID
        """
        # 检查是否需要重置
        self._check_reset()
        
        # 确保用户ID是字符串类型
        user_id_str = str(user_id)
        
        # 确保users字典存在
        if "users" not in self.usage_data:
            self.usage_data["users"] = {}
            
        # 获取用户数据
        user_data = self.usage_data["users"].get(user_id_str, {"count": 0})
        
        # 增加使用次数
        user_data["count"] = user_data.get("count", 0) + 1
        user_data["last_usage"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新用户数据
        self.usage_data["users"][user_id_str] = user_data
        
        # 保存数据
        self._save_usage_data()
        
    def get_remaining(self, user_id: str) -> int:
        """
        获取用户当日剩余使用次数
        
        参数:
            user_id: 用户ID
            
        返回:
            剩余次数
        """
        # 检查是否需要重置
        self._check_reset()
        
        # 确保用户ID是字符串类型
        user_id_str = str(user_id)
        
        # 获取用户的使用情况
        user_data = self.usage_data.get("users", {}).get(user_id_str, {"count": 0})
        count = user_data.get("count", 0)
        
        # 计算剩余次数
        max_count = self.config.get("limit", {}).get("daily_max", 3)
        return max(0, max_count - count)
        
    def reset_user(self, user_id: str):
        """
        重置指定用户的使用次数（将 count 设为 0，更新时间为当前）
        
        参数:
            user_id: 用户 ID
        """
        # 检查是否需要重置
        self._check_reset()
        
        # 确保用户ID是字符串类型
        user_id_str = str(user_id)
        
        # 确保users字典存在
        if "users" not in self.usage_data:
            self.usage_data["users"] = {}
        
        # 先完全删除这个用户的记录，避免重复
        if user_id_str in self.usage_data["users"]:
            del self.usage_data["users"][user_id_str]
            
        # 创建新的用户数据记录
        user_data = {
            "count": 0,
            "last_usage": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 更新用户数据
        self.usage_data["users"][user_id_str] = user_data
        
        # 保存数据
        self._save_usage_data()
        
    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        获取使用统计信息
        
        返回:
            统计数据字典
        """
        # 检查是否需要重置
        self._check_reset()
        
        users = self.usage_data.get("users", {})
        
        # 计算总用户数和总使用次数
        total_users = len(users)
        total_usage = sum(user.get("count", 0) for user in users.values())
        
        return {
            "total_users": total_users,
            "total_usage": total_usage,
            "last_reset": self.usage_data.get("last_reset", "未知")
        }
        
    def get_reset_time(self) -> str:
        """
        获取下次重置时间

        返回:
            下次重置时间的字符串
        """
        # 使用配置的时区
        now = datetime.now(self.timezone)

        # Get reset hour from config (default 0)
        reset_hour = self.config.get("limit", {}).get("reset_hour", 0)

        # Calculate next reset time
        next_reset = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
        if now.hour >= reset_hour:
            # If current time is past reset hour, next reset is tomorrow
            next_reset += timedelta(days=1)

        # 格式化时间
        return next_reset.strftime("%Y-%m-%d %H:%M:%S")
