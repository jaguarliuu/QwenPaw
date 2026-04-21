# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_send_file_to_user_resolves_relative_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from qwenpaw.agents.tools.send_file import send_file_to_user

    target = tmp_path / "report.txt"
    target.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        "qwenpaw.agents.tools.send_file._resolve_file_path",
        lambda path: str(target) if path == "report.txt" else path,
    )

    result = await send_file_to_user("report.txt")

    assert result.content[0]["type"] == "file"
    assert result.content[0]["filename"] == "report.txt"
    assert result.content[0]["source"]["url"] == f"file://{target.resolve()}"

