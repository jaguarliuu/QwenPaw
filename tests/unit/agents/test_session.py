# -*- coding: utf-8 -*-
"""Tests for SafeJSONSession JSON corruption resilience."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile

import pytest

from qwenpaw.app.runner.session import SafeJSONSession, sanitize_filename


@pytest.fixture
def tmp_session_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sess(tmp_session_dir):
    return SafeJSONSession(save_dir=tmp_session_dir)


def _corrupt_file(path, valid_json, tail_garbage):
    with open(path, "w", encoding="utf-8") as f:
        f.write(valid_json + tail_garbage)


class FakeModule:
    def __init__(self):
        self.data = None

    def state_dict(self):
        return self.data

    def load_state_dict(self, data):
        self.data = data


def test_sanitize_filename_replaces_windows_unsafe_chars():
    assert sanitize_filename('discord:dm:12345?*"<>|') == "discord--dm--12345------------"
    assert sanitize_filename("normal-name") == "normal-name"


@pytest.mark.asyncio
async def test_load_valid_json(sess, tmp_session_dir):
    path = os.path.join(tmp_session_dir, "test--session.json")
    data = {"memory": {"content": ["hello"], "_compressed_summary": ""}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    mod = FakeModule()
    await sess.load_session_state("test:session", user_id="", memory=mod)

    assert mod.data == data["memory"]


@pytest.mark.asyncio
async def test_load_corrupted_json_extra_data(sess, tmp_session_dir):
    path = os.path.join(tmp_session_dir, "test--session.json")
    valid = json.dumps(
        {"memory": {"content": [], "_compressed_summary": ""}},
        ensure_ascii=False,
    )
    _corrupt_file(path, valid, '=============="}}')

    mod = FakeModule()
    await sess.load_session_state("test:session", user_id="", memory=mod)

    assert mod.data == {"content": [], "_compressed_summary": ""}


@pytest.mark.asyncio
async def test_update_corrupted_json_writes_back_clean_json(
    sess,
    tmp_session_dir,
):
    path = os.path.join(tmp_session_dir, "test--session.json")
    valid = json.dumps(
        {"memory": {"content": [], "_compressed_summary": ""}},
        ensure_ascii=False,
    )
    _corrupt_file(path, valid, "EXTRA")

    await sess.update_session_state(
        "test:session",
        key="memory.content",
        value=["updated"],
        user_id="",
    )

    with open(path, encoding="utf-8") as f:
        result = json.load(f)

    assert result["memory"]["content"] == ["updated"]


@pytest.mark.asyncio
async def test_get_empty_file_returns_empty_dict(sess, tmp_session_dir):
    path = os.path.join(tmp_session_dir, "test--session.json")
    pathlib.Path(path).touch()

    result = await sess.get_session_state_dict("test:session", user_id="")

    assert result == {}


@pytest.mark.asyncio
async def test_load_missing_file_is_allowed_by_default(sess):
    mod = FakeModule()
    await sess.load_session_state("missing:session", user_id="", memory=mod)
    assert mod.data is None


@pytest.mark.asyncio
async def test_get_missing_file_returns_empty_dict_by_default(sess):
    result = await sess.get_session_state_dict("missing:session", user_id="")
    assert result == {}


@pytest.mark.asyncio
async def test_update_session_state_can_create_nested_path(sess, tmp_session_dir):
    path = os.path.join(tmp_session_dir, "test--session.json")

    await sess.update_session_state(
        "test:session",
        key="memory.summary.latest",
        value="done",
        user_id="",
    )

    with open(path, encoding="utf-8") as f:
        result = json.load(f)

    assert result["memory"]["summary"]["latest"] == "done"
