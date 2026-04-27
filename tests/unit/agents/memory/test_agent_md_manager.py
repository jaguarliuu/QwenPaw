# -*- coding: utf-8 -*-
"""Tests for AgentMdManager."""
# pylint: disable=redefined-outer-name
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def manager(tmp_path):
    from qwenpaw.agents.memory.agent_md_manager import AgentMdManager

    return AgentMdManager(working_dir=tmp_path)


class TestAgentMdManagerInit:
    def test_working_dir_is_set(self, manager, tmp_path):
        assert manager.working_dir == tmp_path

    def test_memory_dir_is_subdirectory(self, manager, tmp_path):
        assert manager.memory_dir == tmp_path / "memory"

    def test_accepts_string_path(self, tmp_path):
        from qwenpaw.agents.memory.agent_md_manager import AgentMdManager

        instance = AgentMdManager(working_dir=str(tmp_path))
        assert isinstance(instance.working_dir, Path)


class TestWorkingMarkdowns:
    def test_list_working_mds_empty(self, manager):
        assert manager.list_working_mds() == []

    def test_list_working_mds_ignores_non_md_files(self, manager, tmp_path):
        (tmp_path / "note.txt").write_text("x")
        (tmp_path / "note.md").write_text("# hello")
        result = manager.list_working_mds()
        assert len(result) == 1
        assert result[0]["filename"] == "note.md"

    def test_read_working_md_supports_missing_extension(self, manager, tmp_path):
        (tmp_path / "notes.md").write_text("content", encoding="utf-8")
        assert manager.read_working_md("notes") == "content"

    def test_read_working_md_uses_encoding_fallback(self, manager, tmp_path):
        (tmp_path / "enc.md").write_text("hello", encoding="utf-8")
        with patch(
            "qwenpaw.agents.memory.agent_md_manager.read_text_file_with_encoding_fallback",
            return_value="patched",
        ) as mock_read:
            result = manager.read_working_md("enc.md")
        mock_read.assert_called_once()
        assert result == "patched"

    def test_write_working_md_appends_extension(self, manager, tmp_path):
        manager.write_working_md("doc", "hello")
        assert (tmp_path / "doc.md").read_text(encoding="utf-8") == "hello"

    def test_read_working_md_raises_when_missing(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.read_working_md("missing.md")


class TestMemoryMarkdowns:
    def test_list_memory_mds_only_reads_memory_dir(self, manager, tmp_path):
        (tmp_path / "working.md").write_text("x")
        (tmp_path / "memory" / "session.md").write_text("y")
        result = manager.list_memory_mds()
        assert len(result) == 1
        assert result[0]["filename"] == "session.md"

    def test_read_memory_md_supports_missing_extension(self, manager, tmp_path):
        (tmp_path / "memory" / "ctx.md").write_text("context", encoding="utf-8")
        assert manager.read_memory_md("ctx") == "context"

    def test_write_memory_md_appends_extension(self, manager, tmp_path):
        manager.write_memory_md("summary", "done")
        assert (tmp_path / "memory" / "summary.md").read_text(
            encoding="utf-8",
        ) == "done"

    def test_read_memory_md_raises_when_missing(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.read_memory_md("missing.md")
