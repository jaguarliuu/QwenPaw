# -*- coding: utf-8 -*-
"""OpenAI chat model compatibility wrappers."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from types import SimpleNamespace
from typing import Any, AsyncGenerator, Type

from agentscope.model import OpenAIChatModel
from agentscope.model._model_response import ChatResponse
from pydantic import BaseModel

from qwenpaw.local_models.tag_parser import (
    parse_tool_calls_from_text,
    text_contains_tool_call_tag,
)

logger = logging.getLogger(__name__)


def _preview_value(value: Any, limit: int = 240) -> str:
    """Return a bounded preview string for debug logs."""
    try:
        text = repr(value)
    except Exception:  # pragma: no cover - defensive logging helper
        text = f"<unreprable {type(value).__name__}>"
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _summarize_stream_item(item: Any) -> str:
    """Summarize a raw OpenAI-compatible stream item for diagnostics."""
    chunk = getattr(item, "chunk", item)
    choices = getattr(chunk, "choices", None) or []
    summary: dict[str, Any] = {
        "item_type": type(item).__name__,
        "chunk_type": type(chunk).__name__,
        "choices": len(choices),
    }
    if choices:
        choice = choices[0]
        delta = getattr(choice, "delta", None)
        summary["finish_reason"] = getattr(choice, "finish_reason", None)
        summary["has_delta"] = delta is not None
        if delta is not None:
            content = getattr(delta, "content", None)
            if isinstance(content, str):
                summary["content_preview"] = content[:120]
            elif content is not None:
                summary["content_type"] = type(content).__name__
            reasoning = getattr(delta, "reasoning_content", None)
            if isinstance(reasoning, str) and reasoning:
                summary["reasoning_preview"] = reasoning[:120]
            tool_calls = getattr(delta, "tool_calls", None) or []
            if tool_calls:
                summary["tool_calls"] = len(tool_calls)
                summary["tool_call_ids"] = [
                    getattr(tc, "id", None) for tc in tool_calls[:3]
                ]
    return _preview_value(summary, limit=400)


def _clone_with_overrides(obj: Any, **overrides: Any) -> Any:
    """Clone a stream object into a mutable namespace with overrides."""
    data = dict(getattr(obj, "__dict__", {}))
    data.update(overrides)
    return SimpleNamespace(**data)


def _sanitize_tool_call(tool_call: Any) -> Any | None:
    """Normalize a tool call for parser safety, or drop it if unusable."""
    if not hasattr(tool_call, "index"):
        return None

    function = getattr(tool_call, "function", None)
    if function is None:
        return None

    has_name = hasattr(function, "name")
    has_arguments = hasattr(function, "arguments")

    raw_name = getattr(function, "name", "")
    if isinstance(raw_name, str):
        safe_name = raw_name
    elif raw_name is None:
        safe_name = ""
    else:
        safe_name = str(raw_name)

    raw_arguments = getattr(function, "arguments", "")
    if isinstance(raw_arguments, str):
        safe_arguments = raw_arguments
    elif raw_arguments is None:
        safe_arguments = ""
    else:
        try:
            safe_arguments = json.dumps(raw_arguments, ensure_ascii=False)
        except (TypeError, ValueError):
            safe_arguments = str(raw_arguments)

    if (
        has_name
        and has_arguments
        and isinstance(raw_name, str)
        and isinstance(
            raw_arguments,
            str,
        )
    ):
        return tool_call

    safe_function = SimpleNamespace(
        name=safe_name,
        arguments=safe_arguments,
    )
    return _clone_with_overrides(tool_call, function=safe_function)


def _sanitize_chunk(chunk: Any) -> Any:
    """Drop/normalize malformed tool-calls in a streaming chunk."""
    choices = getattr(chunk, "choices", None)
    if not choices:
        return chunk

    sanitized_choices: list[Any] = []
    changed = False

    for choice in choices:
        delta = getattr(choice, "delta", None)
        if delta is None:
            sanitized_choices.append(choice)
            continue

        raw_tool_calls = getattr(delta, "tool_calls", None)
        if not raw_tool_calls:
            sanitized_choices.append(choice)
            continue

        choice_changed = False
        sanitized_tool_calls: list[Any] = []
        for tool_call in raw_tool_calls:
            sanitized = _sanitize_tool_call(tool_call)
            if sanitized is not tool_call:
                choice_changed = True
            if sanitized is not None:
                sanitized_tool_calls.append(sanitized)

        if choice_changed:
            changed = True
            sanitized_delta = _clone_with_overrides(
                delta,
                tool_calls=sanitized_tool_calls,
            )
            sanitized_choice = _clone_with_overrides(
                choice,
                delta=sanitized_delta,
            )
            sanitized_choices.append(sanitized_choice)
            continue

        sanitized_choices.append(choice)

    if not changed:
        return chunk
    return _clone_with_overrides(chunk, choices=sanitized_choices)


def _sanitize_stream_item(item: Any) -> Any:
    """Sanitize either plain stream chunks or structured stream items."""
    if hasattr(item, "chunk"):
        chunk = item.chunk
        sanitized_chunk = _sanitize_chunk(chunk)
        if sanitized_chunk is chunk:
            return item
        return _clone_with_overrides(item, chunk=sanitized_chunk)

    return _sanitize_chunk(item)


class _SanitizedStream:
    """Proxy OpenAI async stream that sanitizes each emitted item and
    captures ``extra_content`` from tool-call chunks (used by Gemini
    thinking models to carry ``thought_signature``)."""

    def __init__(self, stream: Any, *, model_name: str | None = None):
        self._stream = stream
        self._ctx_stream: Any | None = None
        self.extra_contents: dict[str, Any] = {}
        self._model_name = model_name or ""
        self._item_index = 0

    async def __aenter__(self) -> "_SanitizedStream":
        if not hasattr(self._stream, "__aenter__"):
            logger.warning(
                "OpenAI-compatible stream protocol mismatch: model=%s "
                "stream_type=%s preview=%s",
                self._model_name or "<unknown>",
                type(self._stream).__name__,
                _preview_value(self._stream),
            )
        elif logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "OpenAI-compatible stream enter: model=%s stream_type=%s",
                self._model_name or "<unknown>",
                type(self._stream).__name__,
            )
        self._ctx_stream = await self._stream.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc: Any,
        tb: Any,
    ) -> bool | None:
        return await self._stream.__aexit__(exc_type, exc, tb)

    def __aiter__(self) -> "_SanitizedStream":
        return self

    async def __anext__(self) -> Any:
        if self._ctx_stream is None:
            raise StopAsyncIteration
        item = await self._ctx_stream.__anext__()
        self._item_index += 1
        if logger.isEnabledFor(logging.DEBUG) and self._item_index <= 5:
            logger.debug(
                "OpenAI-compatible raw stream item #%s model=%s %s",
                self._item_index,
                self._model_name or "<unknown>",
                _summarize_stream_item(item),
            )
        self._capture_extra_content(item)
        return _sanitize_stream_item(item)

    def _capture_extra_content(self, item: Any) -> None:
        """Store ``extra_content`` keyed by tool-call id."""
        chunk = getattr(item, "chunk", item)
        choices = getattr(chunk, "choices", None) or []
        for choice in choices:
            delta = getattr(choice, "delta", None)
            if not delta:
                continue
            for tc in getattr(delta, "tool_calls", None) or []:
                tc_id = getattr(tc, "id", None)
                if not tc_id:
                    continue
                extra = getattr(tc, "extra_content", None)
                if extra is None:
                    model_extra = getattr(tc, "model_extra", None)
                    if isinstance(model_extra, dict):
                        extra = model_extra.get("extra_content")
                if extra:
                    self.extra_contents[tc_id] = extra


class OpenAIChatModelCompat(OpenAIChatModel):
    """OpenAIChatModel with robust parsing for malformed tool-call chunks
    and transparent ``extra_content`` (Gemini thought_signature) relay."""

    # pylint: disable=too-many-branches
    async def _parse_openai_stream_response(
        self,
        start_datetime: datetime,
        response: Any,
        structured_model: Type[BaseModel] | None = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        model_name = getattr(self, "model_name", None)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "OpenAI-compatible parse start: model=%s response_type=%s "
                "structured_model=%s",
                model_name or "<unknown>",
                type(response).__name__,
                getattr(structured_model, "__name__", None),
            )

        sanitized_response = _SanitizedStream(
            response,
            model_name=model_name,
        )

        # Stable tag-extracted tool-call blocks across streaming chunks.
        # Keyed by positional strings so IDs stay consistent as chunks
        # accumulate.  Two sources: "thinking" blocks and plain "text" blocks.
        _think_tool_calls: dict[str, dict] = {}
        _text_tool_calls: dict[str, dict] = {}
        parsed_index = 0

        async for parsed in super()._parse_openai_stream_response(
            start_datetime=start_datetime,
            response=sanitized_response,
            structured_model=structured_model,
        ):
            parsed_index += 1
            if logger.isEnabledFor(logging.DEBUG) and parsed_index <= 5:
                logger.debug(
                    "OpenAI-compatible parsed response #%s model=%s "
                    "blocks=%s",
                    parsed_index,
                    model_name or "<unknown>",
                    [
                        block.get("type")
                        for block in getattr(parsed, "content", [])[:10]
                    ],
                )
            # Attach extra_content (Gemini thought_signature) to tool_use
            # blocks.
            if sanitized_response.extra_contents:
                for block in parsed.content:
                    if block.get("type") != "tool_use":
                        continue
                    tool_id = block.get("id")
                    if not isinstance(tool_id, str):
                        continue
                    ec = sanitized_response.extra_contents.get(tool_id)
                    if ec:
                        block["extra_content"] = ec

            # Check whether the response already carries structured tool_use
            # blocks (either from the model or from extra_content above).
            has_tool_use = any(
                b.get("type") == "tool_use" for b in parsed.content
            )

            if has_tool_use:
                # Structured tool calls arrived — discard any tag-derived
                # ones, so we don't produce duplicates.
                _think_tool_calls.clear()
                _text_tool_calls.clear()
            else:
                # --- 1. Scan thinking blocks ---
                for block in parsed.content:
                    if block.get("type") != "thinking":
                        continue
                    thinking_text = block.get("thinking") or ""
                    if not text_contains_tool_call_tag(thinking_text):
                        continue

                    think_parsed = parse_tool_calls_from_text(thinking_text)
                    if not think_parsed.tool_calls:
                        continue

                    # Keep only the text before the first <tool_call>.
                    # Everything after is the model's simulated continuation
                    # (may include </tool_response>, </think> artefacts).
                    block["thinking"] = think_parsed.text_before.strip()

                    _think_tool_calls = {
                        f"thinking_{i}": {
                            "type": "tool_use",
                            "id": f"think_call_{i}",
                            "name": ptc.name,
                            "input": ptc.arguments,
                            "raw_input": ptc.raw_arguments,
                        }
                        for i, ptc in enumerate(think_parsed.tool_calls)
                    }

                # --- 2. Scan text/content blocks ---
                # Some models emit <tool_call> tags directly in their
                # response text instead of (or in addition to) thinking.
                new_content: list | None = None
                for i, block in enumerate(parsed.content):
                    if block.get("type") != "text":
                        continue
                    text = block.get("text") or ""
                    if not text_contains_tool_call_tag(text):
                        continue

                    text_parsed = parse_tool_calls_from_text(text)
                    # Keep only text_before; discard the tag block and
                    # everything after (same rationale as thinking).
                    clean_text = text_parsed.text_before.strip()
                    block["text"] = clean_text

                    if text_parsed.tool_calls:
                        _text_tool_calls = {
                            f"text_{j}": {
                                "type": "tool_use",
                                "id": f"text_call_{j}",
                                "name": ptc.name,
                                "input": ptc.arguments,
                                "raw_input": ptc.raw_arguments,
                            }
                            for j, ptc in enumerate(text_parsed.tool_calls)
                        }

                    # If the text block is now empty, mark it for removal.
                    if not clean_text:
                        if new_content is None:
                            new_content = list(parsed.content)
                        new_content[i] = None  # type: ignore[index]

                if new_content is not None:
                    parsed.content = [b for b in new_content if b is not None]

                extra = list(_think_tool_calls.values()) + list(
                    _text_tool_calls.values(),
                )
                if extra:
                    parsed.content = list(parsed.content) + extra

            yield parsed
