import os
import json
import time
import fcntl
from datetime import datetime
from typing import Dict, List, Any, Optional

class HistoryManager:
    """
    用户历史记录管理类，用于保存和读取用户的算卦历史
    """
    
    def __init__(self, history_dir: str = None):
        if history_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.history_dir = os.path.join(base_dir, "data/history")
        else:
            self.history_dir = history_dir
            
        os.makedirs(self.history_dir, exist_ok=True)
        
    def save_record(self, user_id: str, question: str, hexagram_data: Dict, interpretation: Dict) -> bool:
        """
        保存用户的算卦记录
        
        参数:
            user_id: 用户ID
            question: 用户问题
            hexagram_data: 卦象数据
            interpretation: 卦象解释
            
        返回:
            保存是否成功
        """
        try:
            # 准备记录数据
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 生成结果摘要
            original_name = interpretation["original"]["name"]
            changed_name = interpretation["changed"]["name"]
            has_moving = sum(hexagram_data["moving"]) > 0
            
            if has_moving:
                result_summary = f"{original_name}变{changed_name}，{interpretation.get('fortune', '平')}。{interpretation.get('advice', '')}"
            else:
                result_summary = f"{original_name}，{interpretation.get('fortune', '平')}。{interpretation.get('advice', '')}"
                
            # 创建记录
            record = {
                "timestamp": timestamp,
                "question": question,
                "hexagram_original": hexagram_data["hexagram_original"],
                "hexagram_changed": hexagram_data["hexagram_changed"],
                "moving": hexagram_data["moving"],
                "result_summary": result_summary,
                "interpretation_summary": interpretation.get("overall_meaning", "")
            }
            
            # 读取现有历史数据
            history_file = os.path.join(self.history_dir, f"{user_id}.json")
            history = []
            
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        # 获取读取锁
                        fcntl.flock(f, fcntl.LOCK_SH)
                        history = json.load(f)
                        fcntl.flock(f, fcntl.LOCK_UN)
                except:
                    history = []
            
            # 添加新记录
            history.append(record)
            
            # 如果记录过多，只保留最近的20条
            if len(history) > 20:
                history = history[-20:]
                
            # 保存回文件
            with open(history_file, "w", encoding="utf-8") as f:
                # 获取写入锁
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(history, f, ensure_ascii=False, indent=2)
                fcntl.flock(f, fcntl.LOCK_UN)
                
            return True
            
        except Exception as e:
            print(f"保存历史记录失败: {str(e)}")
            return False
            
    def get_recent_records(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        获取用户最近的算卦记录
        
        参数:
            user_id: 用户ID
            limit: 最大记录数
            
        返回:
            记录列表，从新到旧排序
        """
        history_file = os.path.join(self.history_dir, f"{user_id}.json")
        
        if not os.path.exists(history_file):
            return []
            
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                # 获取读取锁
                fcntl.flock(f, fcntl.LOCK_SH)
                history = json.load(f)
                fcntl.flock(f, fcntl.LOCK_UN)
                
            # 返回最近的n条记录
            return history[-limit:][::-1]
            
        except Exception as e:
            print(f"读取历史记录失败: {str(e)}")
            return []
            
    def get_record_by_index(self, user_id: str, index: int) -> Optional[Dict]:
        """
        根据索引获取特定的历史记录
        
        参数:
            user_id: 用户ID
            index: 记录索引，从1开始计数
            
        返回:
            记录数据，如果不存在则返回None
        """
        records = self.get_recent_records(user_id, limit=20)
        
        if not records or index <= 0 or index > len(records):
            return None
            
        return records[index - 1]
        
    def clear_history(self, user_id: str) -> bool:
        """
        清除用户的所有历史记录
        
        参数:
            user_id: 用户ID
            
        返回:
            操作是否成功
        """
        history_file = os.path.join(self.history_dir, f"{user_id}.json")
        
        if os.path.exists(history_file):
            try:
                os.remove(history_file)
                return True
            except Exception as e:
                print(f"清除历史记录失败: {str(e)}")
                
        return False
