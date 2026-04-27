# -*- coding: utf-8 -*-
"""Tests for BootstrapHook."""
# pylint: disable=redefined-outer-name
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def working_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def hook(working_dir):
    from qwenpaw.agents.hooks.bootstrap import BootstrapHook

    return BootstrapHook(working_dir=working_dir)


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.memory.get_memory = AsyncMock(return_value=[])
    return agent


class TestBootstrapHookInit:
    def test_stores_working_dir(self, working_dir):
        from qwenpaw.agents.hooks.bootstrap import BootstrapHook

        instance = BootstrapHook(working_dir=working_dir)
        assert instance.working_dir == working_dir

    def test_default_language_is_zh(self, working_dir):
        from qwenpaw.agents.hooks.bootstrap import BootstrapHook

        instance = BootstrapHook(working_dir=working_dir)
        assert instance.language == "zh"

    def test_custom_language_is_stored(self, working_dir):
        from qwenpaw.agents.hooks.bootstrap import BootstrapHook

        instance = BootstrapHook(working_dir=working_dir, language="en")
        assert instance.language == "en"


class TestBootstrapHookCall:
    async def test_skips_when_completed_flag_exists(self, hook, mock_agent):
        (hook.working_dir / ".bootstrap_completed").touch()
        result = await hook(mock_agent, {})
        assert result is None
        mock_agent.memory.get_memory.assert_not_called()

    async def test_skips_when_bootstrap_file_missing(self, hook, mock_agent):
        result = await hook(mock_agent, {})
        assert result is None
        mock_agent.memory.get_memory.assert_not_called()

    async def test_skips_when_not_first_interaction(self, hook, mock_agent):
        (hook.working_dir / "BOOTSTRAP.md").write_text("# Bootstrap")
        with patch(
            "qwenpaw.agents.hooks.bootstrap.is_first_user_interaction",
            return_value=False,
        ):
            result = await hook(mock_agent, {})
        assert result is None

    async def test_prepends_guidance_to_first_user_message(
        self,
        hook,
        mock_agent,
    ):
        (hook.working_dir / "BOOTSTRAP.md").write_text("# Bootstrap")
        user_msg = MagicMock()
        user_msg.role = "user"
        mock_agent.memory.get_memory = AsyncMock(return_value=[user_msg])

        with patch(
            "qwenpaw.agents.hooks.bootstrap.is_first_user_interaction",
            return_value=True,
        ), patch(
            "qwenpaw.agents.hooks.bootstrap.build_bootstrap_guidance",
            return_value="guidance text",
        ) as mock_build, patch(
            "qwenpaw.agents.hooks.bootstrap.prepend_to_message_content",
        ) as mock_prepend:
            result = await hook(mock_agent, {})

        assert result is None
        mock_build.assert_called_once_with("zh")
        mock_prepend.assert_called_once_with(user_msg, "guidance text")
        assert (hook.working_dir / ".bootstrap_completed").exists()

    async def test_skips_system_messages_and_uses_first_user(
        self,
        hook,
        mock_agent,
    ):
        (hook.working_dir / "BOOTSTRAP.md").write_text("# Bootstrap")
        system_msg = MagicMock()
        system_msg.role = "system"
        user_msg = MagicMock()
        user_msg.role = "user"
        mock_agent.memory.get_memory = AsyncMock(
            return_value=[system_msg, user_msg],
        )

        with patch(
            "qwenpaw.agents.hooks.bootstrap.is_first_user_interaction",
            return_value=True,
        ), patch(
            "qwenpaw.agents.hooks.bootstrap.build_bootstrap_guidance",
            return_value="guidance",
        ), patch(
            "qwenpaw.agents.hooks.bootstrap.prepend_to_message_content",
        ) as mock_prepend:
            await hook(mock_agent, {})

        mock_prepend.assert_called_once_with(user_msg, "guidance")

    async def test_handles_memory_errors_gracefully(self, hook, mock_agent):
        (hook.working_dir / "BOOTSTRAP.md").write_text("# Bootstrap")
        mock_agent.memory.get_memory = AsyncMock(
            side_effect=RuntimeError("memory error"),
        )
        result = await hook(mock_agent, {})
        assert result is None
