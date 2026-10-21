"""JSON persistence through LangBot's installation-scoped storage API."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path


class PluginStorage:
    def __init__(self, plugin):
        self.plugin = plugin
        # Serialize read/modify/write operations within this plugin process.
        # Values are never cached: the SDK selects the current installation.
        self.lock = asyncio.Lock()

    async def read(self, key: str, default, legacy: Path | None = None):
        keys = await self.plugin.get_plugin_storage_keys()
        if key in keys:
            return json.loads(await self.plugin.get_plugin_storage(key))
        if legacy is not None and legacy.is_file():
            # Read-only migration; never create a lock or modify the old file.
            value = json.loads(legacy.read_text(encoding="utf-8"))
        else:
            value = default
        await self.write(key, value)
        return value

    async def write(self, key: str, value) -> None:
        await self.plugin.set_plugin_storage(
            key, json.dumps(value, ensure_ascii=False).encode("utf-8")
        )
