"""Daily usage persisted by the LangBot SDK, without shared cached values."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


class UsageLimit:
    KEY = "oraclelang/daily_usage"

    def __init__(self, config, storage, limit_dir=None, logger=None):
        self.config = config
        self.storage = storage
        self.logger = logger or logging.getLogger(__name__)
        self.legacy = Path(limit_dir) / "daily_usage.json" if limit_dir else None
        try:
            self.timezone = ZoneInfo(config.get("timezone", "Asia/Shanghai"))
        except (KeyError, ValueError):
            self.logger.warning("Invalid timezone; using Asia/Shanghai")
            self.timezone = ZoneInfo("Asia/Shanghai")

    def _get_current_date(self):
        return datetime.now(self.timezone).strftime("%Y-%m-%d")

    async def _load(self):
        today = self._get_current_date()
        data = await self.storage.read(self.KEY, {"last_reset": today, "users": {}}, self.legacy)
        if not isinstance(data, dict) or not isinstance(data.get("users"), dict):
            raise ValueError("Invalid OracleLang usage data")
        if data.get("last_reset") != today:
            data = {"last_reset": today, "users": {}}
            await self.storage.write(self.KEY, data)
        return data

    async def check_user_limit(self, launcher_type, user_id):
        return await self.get_remaining(launcher_type, user_id) > 0

    async def _update_user(self, launcher_type, user_id, reset=False):
        async with self.storage.lock:
            data = await self._load()
            key = f"{launcher_type}_{user_id}"
            previous = data["users"].get(key, {}).get("count", 0)
            data["users"][key] = {
                "count": 0 if reset else previous + 1,
                "last_usage": datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S"),
            }
            await self.storage.write(self.KEY, data)

    async def update_usage(self, launcher_type, user_id):
        await self._update_user(launcher_type, user_id)

    async def reset_user(self, launcher_type, user_id):
        await self._update_user(launcher_type, user_id, reset=True)

    async def get_remaining(self, launcher_type, user_id):
        async with self.storage.lock:
            data = await self._load()
            count = data["users"].get(f"{launcher_type}_{user_id}", {}).get("count", 0)
        return max(0, self.config.get("limit", {}).get("daily_max", 3) - count)

    async def get_usage_statistics(self):
        async with self.storage.lock:
            data = await self._load()
        return {
            "total_users": len(data["users"]),
            "total_usage": sum(user.get("count", 0) for user in data["users"].values()),
            "last_reset": data["last_reset"],
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
