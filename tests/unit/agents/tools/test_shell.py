# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import tempfile


def test_execute_subprocess_sync_adds_no_window_flag_on_windows(monkeypatch):
    from qwenpaw.agents.tools import shell as shell_module

    popen_calls: list[dict[str, object]] = []

    class _FakeProcess:
        pid = 123
        returncode = 0

        def wait(self, timeout=None):
            return 0

    def fake_popen(*args, **kwargs):
        popen_calls.append(kwargs)
        return _FakeProcess()

    monkeypatch.setattr(shell_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        shell_module.subprocess,
        "CREATE_NEW_PROCESS_GROUP",
        0x00000200,
        raising=False,
    )
    monkeypatch.setattr(
        shell_module.subprocess,
        "CREATE_NO_WINDOW",
        0x08000000,
        raising=False,
    )
    monkeypatch.setattr(shell_module, "_read_temp_file", lambda _path: "")
    monkeypatch.setattr(shell_module.os, "unlink", lambda _path: None)

    returncode, stdout, stderr = shell_module._execute_subprocess_sync(
        "echo hi",
        cwd=tempfile.gettempdir(),
        timeout=1,
        env=os.environ.copy(),
    )

    assert returncode == 0
    assert stdout == ""
    assert stderr == ""
    assert popen_calls
    assert popen_calls[0]["creationflags"] == 0x00000200 | 0x08000000

