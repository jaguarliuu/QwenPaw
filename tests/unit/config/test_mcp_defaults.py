# -*- coding: utf-8 -*-
from __future__ import annotations

from qwenpaw.config.config import MCPConfig


def test_tavily_search_mcp_is_disabled_by_default():
    config = MCPConfig()

    tavily = config.clients["tavily_search"]

    assert tavily.enabled is False
    assert tavily.env == {"TAVILY_API_KEY": ""}
