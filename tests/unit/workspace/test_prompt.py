# -*- coding: utf-8 -*-
"""Tests for agent identity in system prompt."""
import tempfile
import json
from pathlib import Path
import pytest
from qwenpaw.agents.prompt import (
    DEFAULT_SYS_PROMPT,
    build_system_prompt_from_working_dir,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


def test_prompt_without_agent_id(temp_workspace):  # pylint: disable=W0621
    """Test system prompt without agent_id."""
    # Create a simple AGENTS.md
    agents_md = temp_workspace / "AGENTS.md"
    agents_md.write_text("You are a helpful assistant.", encoding="utf-8")

    prompt = build_system_prompt_from_working_dir(
        working_dir=temp_workspace,
        agent_id=None,
    )

    assert "You are a helpful assistant" in prompt
    assert "Agent Identity" not in prompt
    assert "You are agent" not in prompt


def test_prompt_with_default_agent_id(
    temp_workspace,
):  # pylint: disable=W0621
    """Test system prompt with 'default' agent_id."""
    agents_md = temp_workspace / "AGENTS.md"
    agents_md.write_text("You are a helpful assistant.", encoding="utf-8")

    prompt = build_system_prompt_from_working_dir(
        working_dir=temp_workspace,
        agent_id="default",
    )

    # 'default' agent should also have identity header
    # so it knows its own agent_id
    assert "You are a helpful assistant" in prompt
    assert "Agent Identity" in prompt
    assert "Your agent id is `default`" in prompt


def test_prompt_with_custom_agent_id(
    temp_workspace,
):  # pylint: disable=W0621
    """Test system prompt with custom agent_id."""
    agents_md = temp_workspace / "AGENTS.md"
    agents_md.write_text("You are a helpful assistant.", encoding="utf-8")

    prompt = build_system_prompt_from_working_dir(
        working_dir=temp_workspace,
        agent_id="abc123",
    )

    # Custom agent should have identity header
    assert "Agent Identity" in prompt
    assert "Your agent id is `abc123`" in prompt
    assert "You are a helpful assistant" in prompt
    # Identity should be at the beginning
    assert prompt.index("Agent Identity") < prompt.index("helpful assistant")


def test_prompt_with_empty_workspace(
    temp_workspace,
):  # pylint: disable=W0621
    """Test system prompt with empty workspace."""
    prompt = build_system_prompt_from_working_dir(
        working_dir=temp_workspace,
        agent_id="xyz789",
    )

    # Should still add identity header even with no markdown files
    assert "Agent Identity" in prompt
    assert "Your agent id is `xyz789`" in prompt


def test_prompt_identity_format(temp_workspace):  # pylint: disable=W0621
    """Test the exact format of identity header."""
    prompt = build_system_prompt_from_working_dir(
        working_dir=temp_workspace,
        agent_id="test99",
    )

    expected_header = (
        "# Agent Identity\n\n"
        "Your agent id is `test99`. "
        "This is your unique identifier in the multi-agent system.\n\n"
    )
    assert expected_header in prompt


def test_default_system_prompt_uses_stategrid_identity():
    """Default fallback prompt should use the internal assistant identity."""
    assert "国家电网智能办公应用助手" in DEFAULT_SYS_PROMPT
    assert "helpful assistant" not in DEFAULT_SYS_PROMPT


def test_tokenizer_chat_template_uses_stategrid_identity():
    """Tokenizer fallback prompt should not expose Qwen identity."""
    tokenizer_config = Path(
        "src/qwenpaw/tokenizer/tokenizer_config.json",
    )
    data = json.loads(tokenizer_config.read_text(encoding="utf-8"))
    chat_template = data["chat_template"]

    assert "国家电网智能办公应用助手" in chat_template
    assert "You are Qwen, created by Alibaba Cloud" not in chat_template
