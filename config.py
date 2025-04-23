import os
import json
import yaml
import fcntl
from typing import Dict, Any

# 默认配置
DEFAULT_CONFIG = {
    "limit": {
        "daily_max": 3,        # 每人每日最大算卦次数
        "reset_hour": 0        # 重置时间点（东八区，0-23）
    },
    
    "llm": {
        "enabled": False,      # 是否启用大模型解释
        "api_type": "openai",  # 大模型类型：openai, qianfan, azure
        "api_key": "",         # API密钥
        "api_base": "",        # API基础URL（可选）
        "model": "gpt-3.5-turbo"  # 模型名称
    },
    
    "display": {
        "style": "detailed",   # 默认卦象显示风格：simple, traditional, detailed
        "language": "zh"       # 解释语言：zh, en
    },
    
    "admin_users": [],         # 管理员用户ID列表
    
    "debug": False             # 是否输出调试信息
}

def load_config(base_dir=None) -> Dict[str, Any]:
    """
    加载配置文件，如果文件不存在则创建默认配置
    
    参数:
        base_dir: 配置文件所在的基础目录
        
    返回:
        配置字典
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    config_path = os.path.join(base_dir, "config.yaml")
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_path):
        return create_default_config(config_path)
        
    # 读取配置文件
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            # 获取文件锁
            fcntl.flock(f, fcntl.LOCK_SH)
            config = yaml.safe_load(f)
            # 释放文件锁
            fcntl.flock(f, fcntl.LOCK_UN)
            
        # 确保所有必要的配置项都存在
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
                
        return config
        
    except Exception as e:
        print(f"加载配置文件失败: {str(e)}，使用默认配置")
        return create_default_config(config_path)
        
def create_default_config(config_path: str) -> Dict[str, Any]:
    """
    创建默认配置文件
    
    参数:
        config_path: 配置文件路径
        
    返回:
        默认配置字典
    """
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            # 获取文件锁
            fcntl.flock(f, fcntl.LOCK_EX)
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)
            # 释放文件锁
            fcntl.flock(f, fcntl.LOCK_UN)
            
        print(f"已创建默认配置文件 {config_path}")
        return DEFAULT_CONFIG
        
    except Exception as e:
        print(f"创建默认配置文件失败: {str(e)}")
        return DEFAULT_CONFIG
        
def save_config(config: Dict[str, Any], base_dir=None) -> bool:
    """
    保存配置到文件
    
    参数:
        config: 配置字典
        base_dir: 配置文件所在的基础目录
        
    返回:
        保存是否成功
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    config_path = os.path.join(base_dir, "config.yaml")
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            # 获取文件锁
            fcntl.flock(f, fcntl.LOCK_EX)
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            # 释放文件锁
            fcntl.flock(f, fcntl.LOCK_UN)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {str(e)}")
        return False
