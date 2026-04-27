# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_view_image_returns_fallback_hint_when_multimodal_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from qwenpaw.agents.tools.view_media import view_image

    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"fake-image")

    monkeypatch.setattr(
        "qwenpaw.agents.tools.view_media._check_multimodal_support",
        lambda _media_type="image": False,
    )
    monkeypatch.setattr(
        "qwenpaw.agents.tools.view_media._probe_multimodal_if_needed",
        lambda _media_type="image": False,
    )

    result = await view_image(str(image_path))

    assert result.content[0]["type"] == "image"
    assert result.content[0]["source"]["url"] == image_path.resolve().as_uri()
    assert "cannot directly perceive this image" in result.content[1]["text"]


@pytest.mark.asyncio
async def test_view_video_returns_fallback_hint_when_multimodal_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from qwenpaw.agents.tools.view_media import view_video

    video_path = tmp_path / "sample.mp4"
    video_path.write_bytes(b"fake-video")

    monkeypatch.setattr(
        "qwenpaw.agents.tools.view_media._check_multimodal_support",
        lambda _media_type="video": False,
    )
    monkeypatch.setattr(
        "qwenpaw.agents.tools.view_media._probe_multimodal_if_needed",
        lambda _media_type="video": False,
    )

    result = await view_video(str(video_path))

    assert result.content[0]["type"] == "video"
    assert result.content[0]["source"]["url"] == video_path.resolve().as_uri()
    assert "cannot directly perceive this video" in result.content[1]["text"]
