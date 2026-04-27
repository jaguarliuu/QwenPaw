# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest
from fastapi import HTTPException

from qwenpaw.app.routers import config as config_router
from qwenpaw.config.config import Config


@pytest.mark.asyncio
async def test_get_allow_no_auth_hosts(monkeypatch) -> None:
    config = Config()
    config.security.allow_no_auth_hosts = ["127.0.0.1", "10.0.0.8"]

    monkeypatch.setattr(config_router, "load_config", lambda: config)

    response = await config_router.get_allow_no_auth_hosts()

    assert response.hosts == ["127.0.0.1", "10.0.0.8"]


@pytest.mark.asyncio
async def test_put_allow_no_auth_hosts_normalizes_and_dedups(
    monkeypatch,
) -> None:
    config = Config()
    saved: list[list[str]] = []

    monkeypatch.setattr(config_router, "load_config", lambda: config)
    monkeypatch.setattr(
        config_router,
        "save_config",
        lambda updated: saved.append(
            list(updated.security.allow_no_auth_hosts),
        ),
    )

    response = await config_router.put_allow_no_auth_hosts(
        config_router.AllowNoAuthHostsUpdateBody(
            hosts=[" 127.0.0.1 ", "::1", "127.0.0.1", "2001:0db8::1", ""],
        ),
    )

    assert response.hosts == ["127.0.0.1", "::1", "2001:db8::1"]
    assert config.security.allow_no_auth_hosts == [
        "127.0.0.1",
        "::1",
        "2001:db8::1",
    ]
    assert saved == [["127.0.0.1", "::1", "2001:db8::1"]]


@pytest.mark.asyncio
async def test_put_allow_no_auth_hosts_rejects_invalid_ip(
    monkeypatch,
) -> None:
    config = Config()

    monkeypatch.setattr(config_router, "load_config", lambda: config)

    with pytest.raises(HTTPException, match="Invalid IP address"):
        await config_router.put_allow_no_auth_hosts(
            config_router.AllowNoAuthHostsUpdateBody(
                hosts=["127.0.0.1", "not-an-ip"],
            ),
        )
