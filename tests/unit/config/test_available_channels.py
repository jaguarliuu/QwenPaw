# -*- coding: utf-8 -*-
from __future__ import annotations

from qwenpaw.config import utils as config_utils


def test_get_available_channels_only_exposes_console(monkeypatch):
    monkeypatch.setattr(
        "qwenpaw.app.channels.registry.get_channel_registry",
        lambda: {
            "console": object(),
            "dingtalk": object(),
            "feishu": object(),
        },
    )

    assert config_utils.get_available_channels() == ("console",)
