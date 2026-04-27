# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import qwenpaw.agents.tools as tools_pkg

from qwenpaw.agents.memory.reme_light_memory_manager import (
    ReMeLightMemoryManager,
)


def test_tokenize_query_splits_cjk_and_preserves_non_cjk_words() -> None:
    manager = ReMeLightMemoryManager.__new__(ReMeLightMemoryManager)

    tokens = manager.tokenize_query("国网 报告abc 生成")

    assert tokens == ["国", "网", "报", "告", "abc", "生", "成"]


def test_summary_toolkit_registers_file_tools_via_lazy_import(
    monkeypatch,
    tmp_path,
) -> None:
    import qwenpaw.agents.memory.reme_light_memory_manager as mod

    fake_read = object()
    fake_write = object()
    fake_edit = object()
    registered: list[object] = []

    class FakeToolkit:
        def register_tool_function(self, func: object) -> None:
            registered.append(func)

    class FakeReMeLight:
        def __init__(self, **_kwargs) -> None:
            self._started = False

    agent_config = MagicMock()
    agent_config.running.memory_summary.rebuild_memory_index_on_start = False
    agent_config.running.memory_summary.recursive_file_watcher = False

    monkeypatch.setattr(tools_pkg, "read_file", fake_read, raising=False)
    monkeypatch.setattr(tools_pkg, "write_file", fake_write, raising=False)
    monkeypatch.setattr(tools_pkg, "edit_file", fake_edit, raising=False)
    monkeypatch.setattr(mod, "Toolkit", FakeToolkit)
    monkeypatch.setattr(mod, "load_agent_config", lambda _agent_id: agent_config)
    monkeypatch.setattr(
        mod.ReMeLightMemoryManager,
        "get_embedding_config",
        lambda self: {
            "backend": "openai",
            "api_key": "",
            "base_url": "",
            "model_name": "",
            "dimensions": 1024,
            "enable_cache": True,
            "use_dimensions": False,
            "max_cache_size": 3000,
            "max_input_length": 8192,
            "max_batch_size": 10,
        },
    )
    monkeypatch.setattr(
        mod.EnvVarLoader,
        "get_str",
        lambda key, default=None: "local"
        if key == "MEMORY_STORE_BACKEND"
        else default,
    )
    monkeypatch.setattr(mod.EnvVarLoader, "get_bool", lambda *_args, **_kwargs: True)

    reme_pkg = ModuleType("reme")
    reme_light_module = ModuleType("reme.reme_light")
    reme_light_module.ReMeLight = FakeReMeLight
    monkeypatch.setitem(sys.modules, "reme", reme_pkg)
    monkeypatch.setitem(sys.modules, "reme.reme_light", reme_light_module)

    _ = ReMeLightMemoryManager(str(tmp_path), "default")

    assert registered == [fake_read, fake_write, fake_edit]
