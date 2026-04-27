# -*- coding: utf-8 -*-
"""Tests for message_processing utils."""
# pylint: disable=redefined-outer-name
from unittest.mock import MagicMock

from qwenpaw.agents.utils.message_processing import (
    is_first_user_interaction,
    prepend_to_message_content,
)


def _msg(role: str, content="content"):
    msg = MagicMock()
    msg.role = role
    msg.content = content
    return msg


class TestIsFirstUserInteraction:
    def test_empty_messages_returns_false(self):
        assert is_first_user_interaction([]) is False

    def test_single_user_no_assistant_is_first(self):
        assert is_first_user_interaction([_msg("user")]) is True

    def test_user_with_assistant_is_not_first(self):
        msgs = [_msg("user"), _msg("assistant")]
        assert is_first_user_interaction(msgs) is False

    def test_system_then_user_is_first(self):
        msgs = [_msg("system"), _msg("user")]
        assert is_first_user_interaction(msgs) is True

    def test_only_system_messages_returns_false(self):
        msgs = [_msg("system"), _msg("system")]
        assert is_first_user_interaction(msgs) is False


class TestPrependToMessageContent:
    def test_prepend_to_string_content(self):
        msg = _msg("user", content="hello")
        prepend_to_message_content(msg, "guidance")
        assert msg.content == "guidance\n\nhello"

    def test_prepend_to_list_with_text_block(self):
        msg = _msg(
            "user",
            content=[{"type": "text", "text": "original"}],
        )
        prepend_to_message_content(msg, "guidance")
        assert msg.content[0]["text"] == "guidance\n\noriginal"

    def test_prepend_inserts_text_block_when_missing(self):
        msg = _msg(
            "user",
            content=[{"type": "image", "url": "http://img"}],
        )
        prepend_to_message_content(msg, "guidance")
        assert msg.content[0] == {"type": "text", "text": "guidance"}

    def test_prepend_non_string_non_list_content_is_noop(self):
        msg = _msg("user", content=42)
        prepend_to_message_content(msg, "guidance")
        assert msg.content == 42
