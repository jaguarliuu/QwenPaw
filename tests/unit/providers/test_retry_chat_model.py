# -*- coding: utf-8 -*-
from __future__ import annotations

import httpx

from qwenpaw.providers.retry_chat_model import _is_retryable


def test_remote_protocol_error_is_retryable() -> None:
    exc = httpx.RemoteProtocolError(
        "peer closed connection without sending complete message body",
    )

    assert _is_retryable(exc) is True


def test_timeout_exception_is_retryable() -> None:
    exc = httpx.TimeoutException("timed out")

    assert _is_retryable(exc) is True
