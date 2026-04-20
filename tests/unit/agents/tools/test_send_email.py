# -*- coding: utf-8 -*-
from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace

import pytest
from agentscope.tool import Toolkit

from qwenpaw.config.config import EmailToolConfig


@pytest.mark.asyncio
async def test_send_email_requires_smtp_configuration(monkeypatch):
    send_email_module = import_module("qwenpaw.agents.tools.send_email")

    monkeypatch.setattr(send_email_module, "get_current_agent_id", lambda: "default")
    monkeypatch.setattr(
        send_email_module,
        "load_agent_config",
        lambda _agent_id: SimpleNamespace(email=EmailToolConfig()),
    )

    result = await send_email_module.send_email(
        to=["user@example.com"],
        subject="Status Update",
        body_text="Hello",
    )

    assert "SMTP is not configured" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_send_email_uses_smtp_ssl_and_sends_message(monkeypatch):
    send_email_module = import_module("qwenpaw.agents.tools.send_email")

    events: list[tuple[str, object]] = []

    class _FakeSMTP:
        def __init__(self, host, port, timeout):
            events.append(("connect", (host, port, timeout)))

        def __enter__(self):
            events.append(("enter", None))
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append(("exit", exc_type))
            return False

        def login(self, username, password):
            events.append(("login", (username, password)))

        def send_message(self, message, to_addrs=None):
            events.append(("send_message", (message, to_addrs)))

    monkeypatch.setattr(send_email_module, "get_current_agent_id", lambda: "default")
    monkeypatch.setattr(
        send_email_module,
        "load_agent_config",
        lambda _agent_id: SimpleNamespace(
            email=EmailToolConfig(
                host="smtp.example.com",
                port=465,
                username="bot@example.com",
                password="secret",
                from_address="bot@example.com",
                from_name="StateGrid Bot",
                use_ssl=True,
                use_starttls=False,
                timeout_sec=12,
            ),
        ),
    )
    monkeypatch.setattr(
        send_email_module.smtplib,
        "SMTP_SSL",
        _FakeSMTP,
    )

    result = await send_email_module.send_email(
        to=["user@example.com"],
        subject="Status Update",
        body_text="Hello",
    )

    assert "Email sent successfully" in result.content[0]["text"]
    assert ("connect", ("smtp.example.com", 465, 12)) in events
    assert ("login", ("bot@example.com", "secret")) in events
    sent_message, to_addrs = next(value for key, value in events if key == "send_message")
    assert sent_message["To"] == "user@example.com"
    assert sent_message["From"] == "StateGrid Bot <bot@example.com>"
    assert sent_message["Subject"] == "Status Update"
    assert to_addrs == ["user@example.com"]


def test_send_email_tool_can_be_registered_in_toolkit():
    send_email_module = import_module("qwenpaw.agents.tools.send_email")

    toolkit = Toolkit()
    toolkit.register_tool_function(send_email_module.send_email)

    schemas = toolkit.get_json_schemas()
    schema_names = {schema["function"]["name"] for schema in schemas}

    assert "send_email" in schema_names
