# -*- coding: utf-8 -*-
from __future__ import annotations

from qwenpaw.security.tool_guard.guardians import file_guardian
from qwenpaw.security.tool_guard.guardians.file_guardian import (
    FilePathToolGuardian,
    _extract_paths_from_shell_command,
    _normalize_path,
)


def test_normalize_windows_path_uses_stable_lowercase_form() -> None:
    normalized = _normalize_path(r"C:\Users\Lenovo\Work\Demo.txt")

    assert normalized == "c:/users/lenovo/work/demo.txt"


def test_extract_paths_from_shell_command_keeps_windows_paths(
    monkeypatch,
) -> None:
    monkeypatch.setattr(file_guardian.os, "name", "nt")

    paths = _extract_paths_from_shell_command(
        r'type "C:\Users\Lenovo\demo.txt" > "C:\Temp\out.txt"',
    )

    assert paths == [r"C:\Users\Lenovo\demo.txt", r"C:\Temp\out.txt"]


def test_file_guardian_blocks_windows_sensitive_path() -> None:
    guardian = FilePathToolGuardian(
        sensitive_files=[r"C:\Users\Lenovo\.qwenpaw.secret\\"],
    )

    findings = guardian.guard(
        "write_file",
        {"file_path": r"C:\Users\Lenovo\.qwenpaw.secret\auth.json"},
    )

    assert len(findings) == 1
    assert findings[0].metadata["resolved_path"] == (
        "c:/users/lenovo/.qwenpaw.secret/auth.json"
    )
