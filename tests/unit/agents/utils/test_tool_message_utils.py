# -*- coding: utf-8 -*-
"""Focused tests for tool_message_utils."""
# pylint: disable=redefined-outer-name
import json
from unittest.mock import MagicMock

from qwenpaw.agents.utils.tool_message_utils import (
    _dedup_tool_blocks,
    _repair_empty_tool_inputs,
    check_valid_messages,
    extract_tool_ids,
)


def _msg(content):
    msg = MagicMock()
    msg.content = content
    return msg


def _tool_use(tool_id, name="tool"):
    return {"type": "tool_use", "id": tool_id, "name": name}


def _tool_result(tool_id):
    return {"type": "tool_result", "id": tool_id}


def test_extract_tool_ids_returns_both_sets():
    uses, results = extract_tool_ids(
        _msg([_tool_use("u1"), _tool_result("r1")]),
    )
    assert uses == {"u1"}
    assert results == {"r1"}


def test_check_valid_messages_requires_paired_tool_ids():
    valid = [_msg([_tool_use("id1")]), _msg([_tool_result("id1")])]
    invalid = [_msg([_tool_use("id1")])]
    assert check_valid_messages(valid) is True
    assert check_valid_messages(invalid) is False


def test_dedup_tool_blocks_removes_duplicate_tool_use_ids():
    msg = _msg([_tool_use("id1"), _tool_use("id1"), _tool_result("id1")])
    result = _dedup_tool_blocks([msg])
    assert [block["type"] for block in result[0].content] == [
        "tool_use",
        "tool_result",
    ]


def test_repair_empty_tool_inputs_uses_raw_input_json():
    msg = _msg(
        [
            {
                "type": "tool_use",
                "id": "id1",
                "name": "tool",
                "input": {},
                "raw_input": json.dumps({"path": "demo.txt"}),
            },
        ],
    )
    result = _repair_empty_tool_inputs([msg])
    assert result[0].content[0]["input"] == {"path": "demo.txt"}
