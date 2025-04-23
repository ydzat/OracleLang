import os
import json
import time
import fcntl
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class UsageLimit:
    """
    用户使用限制类，管理每日算卦次数限制
    """
    
    def __init__(self, config: Dict, limit_dir: str = None):
        self.config = config
        
        if limit_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.limit_dir = os.path.join(base_dir, "data/limits")
        else:
            self.limit_dir = limit_dir
            
        self.limit_file = os.path.join(self.limit_dir, "daily_usage.json")
        
        # 确保目录存在
        os.makedirs(self.limit_dir, exist_ok=True)
        
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
                with open(self.limit_file, "r", encoding="utf-8") as f:
                    # 获取文件锁
                    fcntl.flock(f, fcntl.LOCK_SH)
                    # 读取数据
                    data = json.load(f)
                    # 释放文件锁
                    fcntl.flock(f, fcntl.LOCK_UN)
                    
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
                print(f"加载使用数据失败: {str(e)}")
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

            # 使用文件锁确保文件写入的原子性
            with open(self.limit_file, "w", encoding="utf-8") as f:
                # 获取文件锁
                fcntl.flock(f, fcntl.LOCK_EX)
                # 写入数据
                json.dump(self.usage_data, f, ensure_ascii=False, indent=2)
                # 释放文件锁
                fcntl.flock(f, fcntl.LOCK_UN)
                
        except Exception as e:
            print(f"保存使用数据失败: {str(e)}")
            
    def _get_current_date(self) -> str:
        """获取当前日期字符串（东八区时间）"""
        # 使用UTC+8时间
        now = datetime.utcnow() + timedelta(hours=8)
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
        # 使用UTC+8时间
        now = datetime.utcnow() + timedelta(hours=8)
        
        # 计算下一个0点
        next_day = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # 格式化时间
        return next_day.strftime("%Y-%m-%d %H:%M:%S")
