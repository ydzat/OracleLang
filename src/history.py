"""Per-user history persisted by the LangBot SDK."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path


class HistoryManager:
    def __init__(self, storage, history_dir=None, logger=None):
        self.storage = storage
        self.history_dir = Path(history_dir) if history_dir else None
        self.logger = logger or logging.getLogger(__name__)

    def _location(self, launcher_type, user_id):
        identity = json.dumps([str(launcher_type), str(user_id)], ensure_ascii=False)
        key = "oraclelang/history/" + hashlib.sha256(identity.encode()).hexdigest()
        legacy = None
        filename = f"{launcher_type}_{user_id}.json"
        if self.history_dir is not None and not any(c in filename for c in ("/", "\\", "\x00")):
            candidate = self.history_dir / filename
            if candidate.resolve().parent == self.history_dir.resolve():
                legacy = candidate
        return key, legacy

    async def _read(self, key, legacy):
        records = await self.storage.read(key, [], legacy)
        if not isinstance(records, list):
            raise ValueError("Invalid OracleLang history: expected a list")
        return records

    async def save_record(self, launcher_type, user_id, question, hexagram_data, interpretation):
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

        key, legacy = self._location(launcher_type, user_id)
        async with self.storage.lock:
            history = await self._read(key, legacy)
            history.append(record)
            await self.storage.write(key, history[-20:])
        return True

    async def get_recent_records(self, launcher_type, user_id, limit=5):
        key, legacy = self._location(launcher_type, user_id)
        async with self.storage.lock:
            history = await self._read(key, legacy)
        return history[-limit:][::-1] if limit > 0 else []

    async def get_record_by_index(self, launcher_type, user_id, index):
        records = await self.get_recent_records(launcher_type, user_id, limit=20)
        return records[index - 1] if 0 < index <= len(records) else None

    async def clear_history(self, launcher_type, user_id):
        key, legacy = self._location(launcher_type, user_id)
        async with self.storage.lock:
            history = await self._read(key, legacy)
            # Keep an empty value so old files cannot resurrect cleared history.
            await self.storage.write(key, [])
        return bool(history)
