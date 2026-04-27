# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace

from qwenpaw.app import auth as auth_module
import qwenpaw.config as config_module
from qwenpaw.config.config import Config


def _request(path: str, host: str, method: str = "GET"):
    return SimpleNamespace(
        method=method,
        url=SimpleNamespace(path=path),
        client=SimpleNamespace(host=host),
    )


def test_should_skip_auth_allows_configured_host(monkeypatch) -> None:
    config = Config()
    config.security.allow_no_auth_hosts = ["127.0.0.1", "10.0.0.8"]

    monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth_module, "has_registered_users", lambda: True)
    monkeypatch.setattr(config_module, "load_config", lambda: config)

    request = _request("/api/chat/query", "10.0.0.8")

    assert auth_module.AuthMiddleware._should_skip_auth(request) is True


def test_should_skip_auth_rejects_unlisted_host(monkeypatch) -> None:
    config = Config()
    config.security.allow_no_auth_hosts = ["127.0.0.1", "::1"]

    monkeypatch.setattr(auth_module, "is_auth_enabled", lambda: True)
    monkeypatch.setattr(auth_module, "has_registered_users", lambda: True)
    monkeypatch.setattr(config_module, "load_config", lambda: config)

    request = _request("/api/chat/query", "10.0.0.9")

    assert auth_module.AuthMiddleware._should_skip_auth(request) is False
