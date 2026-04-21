# -*- coding: utf-8 -*-
"""Load image or video files into the LLM context for analysis."""

import logging
import mimetypes
import os
import inspect
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Optional

from agentscope.message import ImageBlock, TextBlock, VideoBlock
from agentscope.tool import ToolResponse

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
}

_VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mpeg",
    ".mov",
    ".avi",
    ".mkv",
}


def _is_url(path: str) -> bool:
    """Return True if *path* looks like an HTTP(S) URL."""
    return path.startswith(("http://", "https://"))


def _validate_url_extension(
    url: str,
    allowed_extensions: set[str],
    mime_prefix: str,
) -> Optional[ToolResponse]:
    """Optionally validate that the URL path has an allowed extension.

    Returns an error ``ToolResponse`` when the extension is clearly
    unsupported, or ``None`` to let it through (including when the URL
    has no recognisable extension, e.g. dynamic endpoints).
    """
    url_path = urllib.parse.urlparse(url).path
    ext = Path(url_path).suffix.lower()
    if not ext:
        return None
    mime, _ = mimetypes.guess_type(url_path)
    if ext not in allowed_extensions and (
        not mime or not mime.startswith(f"{mime_prefix}/")
    ):
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error: URL does not point to a "
                    f"supported {mime_prefix} format: {url}",
                ),
            ],
        )
    return None


def _validate_media_path(
    file_path: str,
    allowed_extensions: set[str],
    mime_prefix: str,
) -> tuple[Path, Optional[ToolResponse]]:
    """Validate a local media file path.

    Returns ``(resolved_path, None)`` on success or
    ``(_, error_response)`` on failure.
    """
    file_path = unicodedata.normalize(
        "NFC",
        os.path.expanduser(file_path),
    )
    resolved = Path(file_path).resolve()

    if not resolved.exists() or not resolved.is_file():
        return resolved, ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error: {file_path} does not exist "
                    "or is not a file.",
                ),
            ],
        )

    ext = resolved.suffix.lower()
    mime, _ = mimetypes.guess_type(str(resolved))
    if ext not in allowed_extensions and (
        not mime or not mime.startswith(f"{mime_prefix}/")
    ):
        return resolved, ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error: {resolved.name} is not a "
                    f"supported {mime_prefix} format.",
                ),
            ],
        )

    return resolved, None


async def _probe_multimodal_if_needed(
    media_type: str = "image",
) -> bool | None:
    """Probe active-model media capability when the current state is unknown."""
    try:
        from ..prompt import _get_active_model_info
        from ...providers.provider_manager import ProviderManager

        model_info, _ = _get_active_model_info()
        if model_info is None or model_info.supports_multimodal is not None:
            return None

        manager = ProviderManager.get_instance()
        active = None
        try:
            from ...app.agent_context import get_current_agent_id
            from ...config.config import load_agent_config

            agent_id = get_current_agent_id()
            agent_config = load_agent_config(agent_id)
            if agent_config.active_model:
                active = agent_config.active_model
        except Exception:
            pass
        if not active:
            active = manager.get_active_model()
        if not active:
            return None

        result = await manager.probe_model_multimodal(
            active.provider_id,
            active.model,
        )
        if media_type == "video":
            return result.get("supports_video")
        return (
            result.get("supports_image") or result.get("supports_multimodal")
        )
    except Exception as exc:
        logger.warning("Auto-probe in view_media failed: %s", exc)
        return None


def _check_multimodal_support(media_type: str = "image") -> bool:
    """Check whether the active model already supports the requested media."""
    try:
        from ..prompt import _get_active_model_info

        model_info, _ = _get_active_model_info()
        if model_info is None:
            return True
        if media_type == "video":
            return model_info.supports_video is True
        return (
            model_info.supports_image is True
            or model_info.supports_multimodal is True
        )
    except Exception:
        return True


def _get_multimodal_fallback_hint(media_type: str, path: str) -> str:
    """Build a hint when media is shown to the user but unavailable to the model."""
    try:
        from ..prompt import get_active_model_multimodal_raw

        raw_support = get_active_model_multimodal_raw()
    except Exception:
        raw_support = None

    if raw_support is None:
        logger.warning(
            "view_%s called with unknown multimodal capability; path=%s",
            media_type,
            path,
        )
        return (
            f"[Note: this model cannot directly perceive this {media_type}. "
            f"The {media_type} has been shown to the user, but you cannot "
            f"analyze its content until multimodal support is confirmed.]"
        )

    logger.warning(
        "view_%s called on a text-only model; path=%s",
        media_type,
        path,
    )
    return (
        f"[Note: the current model cannot directly perceive this {media_type}. "
        f"The {media_type} has been shown to the user, but you cannot "
        f"analyze its content with the current model.]"
    )


async def _maybe_await_probe_result(
    probe_result: bool | None | object,
) -> bool | None:
    """Accept either a direct boolean probe result or an awaitable."""
    if inspect.isawaitable(probe_result):
        return await probe_result
    return probe_result


async def view_image(image_path: str) -> ToolResponse:
    """Load an image file into the LLM context so the model can see it.

    Use this after desktop_screenshot, browser_use, or any tool that
    produces an image file path.  Also accepts an HTTP(S) URL for
    online images — the URL is passed directly to the model without
    downloading.

    Args:
        image_path (`str`):
            Local path or HTTP(S) URL of the image to view.

    Returns:
        `ToolResponse`:
            An ImageBlock the model can inspect, or an error message.
    """
    fallback_hint: str | None = None
    if not _check_multimodal_support("image"):
        probe_result = await _maybe_await_probe_result(
            _probe_multimodal_if_needed("image"),
        )
        if probe_result is not True:
            fallback_hint = _get_multimodal_fallback_hint(
                "image",
                image_path,
            )

    if _is_url(image_path):
        err = _validate_url_extension(
            image_path,
            _IMAGE_EXTENSIONS,
            "image",
        )
        if err is not None:
            return err
        text_msg = (
            fallback_hint
            if fallback_hint
            else f"Image loaded from URL: {image_path}"
        )
        return ToolResponse(
            content=[
                ImageBlock(
                    type="image",
                    source={"type": "url", "url": image_path},
                ),
                TextBlock(type="text", text=text_msg),
            ],
        )

    resolved, err = _validate_media_path(
        image_path,
        _IMAGE_EXTENSIONS,
        "image",
    )
    if err is not None:
        return err

    text_msg = (
        fallback_hint if fallback_hint else f"Image loaded: {resolved.name}"
    )
    return ToolResponse(
        content=[
            ImageBlock(
                type="image",
                source={"type": "url", "url": str(resolved)},
            ),
            TextBlock(type="text", text=text_msg),
        ],
    )


async def view_video(video_path: str) -> ToolResponse:
    """Load a video file into the LLM context so the model can see it.

    Use this when the user asks about a video file or when another
    tool produces a video file path.  Also accepts an HTTP(S) URL —
    the URL is passed directly to the model without downloading.

    Args:
        video_path (`str`):
            Local path or HTTP(S) URL of the video to view.

    Returns:
        `ToolResponse`:
            A VideoBlock the model can inspect, or an error message.
    """
    fallback_hint: str | None = None
    if not _check_multimodal_support("video"):
        probe_result = await _maybe_await_probe_result(
            _probe_multimodal_if_needed("video"),
        )
        if probe_result is not True:
            fallback_hint = _get_multimodal_fallback_hint(
                "video",
                video_path,
            )

    if _is_url(video_path):
        err = _validate_url_extension(
            video_path,
            _VIDEO_EXTENSIONS,
            "video",
        )
        if err is not None:
            return err
        text_msg = (
            fallback_hint
            if fallback_hint
            else f"Video loaded from URL: {video_path}"
        )
        return ToolResponse(
            content=[
                VideoBlock(
                    type="video",
                    source={"type": "url", "url": video_path},
                ),
                TextBlock(type="text", text=text_msg),
            ],
        )

    resolved, err = _validate_media_path(
        video_path,
        _VIDEO_EXTENSIONS,
        "video",
    )
    if err is not None:
        return err

    text_msg = (
        fallback_hint if fallback_hint else f"Video loaded: {resolved.name}"
    )
    return ToolResponse(
        content=[
            VideoBlock(
                type="video",
                source={"type": "url", "url": str(resolved)},
            ),
            TextBlock(type="text", text=text_msg),
        ],
    )
