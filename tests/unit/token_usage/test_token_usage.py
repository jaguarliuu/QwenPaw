# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from qwenpaw.token_usage.buffer import (
    TokenUsageBuffer,
    _UsageEvent,
    _apply_event,
)
from qwenpaw.token_usage.manager import TokenUsageManager
from qwenpaw.token_usage.model_wrapper import TokenRecordingModelWrapper
from qwenpaw.token_usage.storage import load_data, save_data_sync


@pytest.fixture(autouse=True)
def _isolate_token_usage_manager():
    TokenUsageManager._instance = None
    yield
    TokenUsageManager._instance = None


def test_apply_event_accumulates_same_model() -> None:
    cache = {}
    for _ in range(3):
        _apply_event(
            cache,
            _UsageEvent(
                provider_id="openai",
                model_name="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                date_str="2026-04-24",
                now_iso="2026-04-24T10:00:00+00:00",
            ),
        )

    entry = cache["2026-04-24"]["openai:gpt-4"]
    assert entry["prompt_tokens"] == 300
    assert entry["completion_tokens"] == 150
    assert entry["call_count"] == 3


@pytest.mark.asyncio
async def test_load_data_corrupt_json_returns_empty(tmp_path) -> None:
    path = tmp_path / "token_usage.json"
    path.write_text("{invalid json}")

    data = await load_data(path)

    assert data == {}


def test_save_data_sync_writes_file(tmp_path) -> None:
    path = tmp_path / "token_usage.json"
    data = {"2026-04-24": {"openai:gpt-4": {"prompt_tokens": 100}}}

    save_data_sync(path, data)

    assert path.exists()
    assert json.loads(path.read_text()) == data


@pytest.mark.asyncio
async def test_token_usage_buffer_processes_events(tmp_path) -> None:
    buffer = TokenUsageBuffer(tmp_path / "test.json")
    buffer.start()

    for _ in range(2):
        buffer.enqueue(
            _UsageEvent(
                provider_id="openai",
                model_name="gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                date_str="2026-04-24",
                now_iso="2026-04-24T10:00:00+00:00",
            ),
        )

    await asyncio.sleep(0.2)
    await buffer.stop()

    entry = buffer._disk_cache["2026-04-24"]["openai:gpt-4"]
    assert entry["prompt_tokens"] == 200
    assert entry["completion_tokens"] == 100
    assert entry["call_count"] == 2


@pytest.mark.asyncio
async def test_token_usage_manager_summary_uses_buffered_data(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("qwenpaw.token_usage.manager.WORKING_DIR", tmp_path)
    monkeypatch.setattr(
        "qwenpaw.token_usage.manager.TOKEN_USAGE_FILE",
        "test_token_usage.json",
    )

    manager = TokenUsageManager()
    manager.start(flush_interval=10)
    await manager.record(
        provider_id="openai",
        model_name="gpt-4",
        prompt_tokens=100,
        completion_tokens=50,
    )

    summary = await manager.get_summary()

    assert summary.total_prompt_tokens == 100
    assert summary.total_completion_tokens == 50
    assert summary.total_calls == 1
    await manager.stop()


def test_token_recording_model_wrapper_enqueues_usage(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("qwenpaw.token_usage.manager.WORKING_DIR", tmp_path)
    monkeypatch.setattr(
        "qwenpaw.token_usage.manager.TOKEN_USAGE_FILE",
        "test_token_usage.json",
    )

    mock_model = MagicMock()
    mock_model.model_name = "gpt-4"
    wrapper = TokenRecordingModelWrapper(
        provider_id="openai",
        model=mock_model,
    )

    captured = {}

    class _FakeManager:
        def enqueue(self, event):
            captured["event"] = event

    monkeypatch.setattr(
        "qwenpaw.token_usage.model_wrapper.get_token_usage_manager",
        lambda: _FakeManager(),
    )

    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50

    wrapper._record_usage(usage)

    event = captured["event"]
    assert event.provider_id == "openai"
    assert event.model_name == "gpt-4"
    assert event.prompt_tokens == 100
    assert event.completion_tokens == 50
