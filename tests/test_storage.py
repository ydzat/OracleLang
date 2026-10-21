"""Storage regression tests using the real SDK proxy and a local test transport.

The SQLite transport exercises serialization and persistence, not a live Host.
Run this suite in a read-only bind mount to verify the Cloud filesystem boundary.
"""
from __future__ import annotations

import asyncio
import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from main import OracleLangPlugin
from components.pages.admin import OracleAdminPage
from src.history import HistoryManager
from src.limit import UsageLimit
from src.storage import PluginStorage
from langbot_plugin.entities.io.actions.enums import PluginToRuntimeAction


class StorageTransport:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS kv (scope TEXT, key TEXT, value BLOB, PRIMARY KEY(scope,key))")
        self.scope = "installation-a"
        self.fail_writes = False

    async def call_action(self, action, data):
        await asyncio.sleep(0)
        if action == PluginToRuntimeAction.GET_PLUGIN_STORAGE_KEYS:
            return {"keys": [row[0] for row in self.db.execute("SELECT key FROM kv WHERE scope=?", (self.scope,))]}
        if action == PluginToRuntimeAction.GET_PLUGIN_STORAGE:
            row = self.db.execute("SELECT value FROM kv WHERE scope=? AND key=?", (self.scope, data["key"])).fetchone()
            if row is None:
                raise KeyError(data["key"])
            return {"value_base64": base64.b64encode(row[0]).decode()}
        if action == PluginToRuntimeAction.SET_PLUGIN_STORAGE:
            if self.fail_writes:
                raise OSError("Storage unavailable")
            self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?,?)", (self.scope, data["key"], base64.b64decode(data["value_base64"])))
            self.db.commit()
            return {}
        raise AssertionError(action)


class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.transport = StorageTransport(self.path / "host.sqlite3")
        self.addCleanup(self.transport.db.close)
        self.plugin = await self.new_plugin()

    async def new_plugin(self):
        plugin = OracleLangPlugin()
        plugin.config = {"llm_enabled": False, "display_style": "text"}
        plugin.plugin_runtime_handler = self.transport
        await plugin.initialize()
        return plugin

    async def test_initialize_and_divination_survive_restart(self):
        self.assertEqual(len(self.plugin.interpreter.hexagrams_data), 64)
        text = await self.plugin.process_divination("测试", "person", "storage-test")
        self.assertTrue(text)
        # Close/reopen the backing store as well as constructing a new plugin.
        self.transport.db.close()
        self.transport = StorageTransport(self.path / "host.sqlite3")
        self.addCleanup(self.transport.db.close)
        restarted = await self.new_plugin()
        records = await restarted.history.get_recent_records("person", "storage-test")
        self.assertEqual(records[0]["question"], "测试")
        self.assertEqual(await restarted.limit.get_remaining("person", "storage-test"), 2)
        self.assertIn("测试", await restarted._get_history_text("person", "storage-test"))
        page = OracleAdminPage()
        page.plugin = restarted
        stats = await page._get_stats()
        users = await page._get_users()
        self.assertEqual(stats.data["today_usage"], 1)
        self.assertEqual(users.data["total_users"], 1)

    async def test_history_migration_cap_clear_and_identity(self):
        legacy = self.path / "person_old.json"
        legacy.write_text(json.dumps([{"question": str(i)} for i in range(25)]))
        history = HistoryManager(PluginStorage(self.plugin), self.path)
        self.assertEqual((await history.get_recent_records("person", "old"))[0]["question"], "24")
        hexagram = {"hexagram_original": 1, "hexagram_changed": 1, "moving": [0]*6}
        meaning = {"original": {"name": "乾"}, "changed": {"name": "乾"}}
        await history.save_record("person", "old", "new", hexagram, meaning)
        self.assertEqual(len(await history.get_recent_records("person", "old", 100)), 20)
        self.assertEqual(await history.get_recent_records("group", "old"), [])
        self.assertTrue(await history.clear_history("person", "old"))
        restarted = HistoryManager(PluginStorage(self.plugin), self.path)
        self.assertEqual(await restarted.get_recent_records("person", "old"), [])
        self.assertEqual(len(json.loads(legacy.read_text())), 25)
        self.assertEqual(list(self.path.glob("*.lock")), [])

    async def test_usage_migration_reset_and_concurrency(self):
        legacy = self.path / "daily_usage.json"
        today = self.plugin.limit._get_current_date()
        legacy.write_text(json.dumps({"last_reset": today, "users": {"person_old": {"count": 2}}}))
        limit = UsageLimit(self.plugin.plugin_config, PluginStorage(self.plugin), self.path)
        self.assertEqual(await limit.get_remaining("person", "old"), 1)
        await asyncio.gather(*(limit.update_usage("person", "old") for _ in range(12)))
        self.assertEqual((await limit.get_usage_statistics())["total_usage"], 14)
        self.assertFalse(await limit.check_user_limit("person", "old"))
        await limit.reset_user("person", "old")
        self.assertEqual(await limit.get_remaining("person", "old"), 3)
        self.assertEqual(json.loads(legacy.read_text())["users"]["person_old"]["count"], 2)

    async def test_daily_rollover(self):
        await self.plugin.limit.storage.write(UsageLimit.KEY, {"last_reset": "2000-01-01", "users": {"person_old": {"count": 3}}})
        self.assertEqual(await self.plugin.limit.get_remaining("person", "old"), 3)
        self.assertEqual((await self.plugin.limit.get_usage_statistics())["total_usage"], 0)

    async def test_no_cross_installation_cache(self):
        await self.plugin.limit.update_usage("person", "same")
        self.transport.scope = "installation-b"
        self.assertEqual(await self.plugin.limit.get_remaining("person", "same"), 3)
        self.transport.scope = "installation-a"
        self.assertEqual(await self.plugin.limit.get_remaining("person", "same"), 2)

    async def test_corrupt_data_and_transport_failure_are_not_hidden(self):
        legacy = self.path / "person_bad.json"
        legacy.write_text("not json")
        history = HistoryManager(PluginStorage(self.plugin), self.path)
        with self.assertRaises(json.JSONDecodeError):
            await history.get_recent_records("person", "bad")
        self.assertEqual(legacy.read_text(), "not json")
        self.transport.fail_writes = True
        with self.assertRaises(OSError):
            await self.plugin.limit.update_usage("person", "test")


if __name__ == "__main__":
    unittest.main()
