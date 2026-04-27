# -*- coding: utf-8 -*-
"""In-memory write buffer with async producer-consumer for token usage.
"""

import asyncio
import copy
import logging
from pathlib import Path
from typing import NamedTuple, Optional

from .storage import load_data, save_data_sync

logger = logging.getLogger(__name__)

_DEFAULT_FLUSH_INTERVAL = 10  # seconds


class _UsageEvent(NamedTuple):
    """Immutable record placed on the queue by the producer."""

    provider_id: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    date_str: str
    now_iso: str


class TokenUsageBuffer:
    """Async producer-consumer buffer that periodically flushes to disk."""

    def __init__(
        self,
        path: Path,
        flush_interval: int = _DEFAULT_FLUSH_INTERVAL,
    ) -> None:
        self._path = path
        self._flush_interval = flush_interval
        self._disk_cache: dict = {}
        self._cache_loaded = False
        self._dirty = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._consumer_task: Optional[asyncio.Task] = None
        self._flush_task: Optional[asyncio.Task] = None
        self._stopped = False

    def start(self) -> None:
        """Start consumer and flush tasks."""
        if self._consumer_task is not None:
            return
        self._stopped = False
        self._consumer_task = asyncio.create_task(
            self._consumer_loop(),
            name="token-usage-consumer",
        )
        self._flush_task = asyncio.create_task(
            self._flush_loop(),
            name="token-usage-flush",
        )

    async def stop(self) -> None:
        """Drain queue, stop tasks, perform final flush."""
        self._stopped = True

        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

        if self._consumer_task is not None:
            await self._queue.join()
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
            self._consumer_task = None

        await self._flush_once(force=True)

    def enqueue(self, event: _UsageEvent) -> None:
        """Put an event on the queue without awaiting."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                "token_usage: queue full, dropping event for %s:%s",
                event.provider_id,
                event.model_name,
            )

    async def get_merged_data(self) -> dict:
        """Return a consistent view of disk cache plus pending queue items."""
        if not self._cache_loaded:
            await self._seed_cache()

        result = copy.deepcopy(self._disk_cache)
        pending = list(self._queue._queue)  # type: ignore[attr-defined]
        for ev in pending:
            _apply_event(result, ev)
        return result

    async def _consumer_loop(self) -> None:
        """Drain events from the queue one by one."""
        if not self._cache_loaded:
            await self._seed_cache()
        try:
            while True:
                event = await self._queue.get()
                try:
                    _apply_event(self._disk_cache, event)
                    self._dirty = True
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            while not self._queue.empty():
                try:
                    event = self._queue.get_nowait()
                    _apply_event(self._disk_cache, event)
                    self._dirty = True
                    self._queue.task_done()
                except asyncio.QueueEmpty:
                    break

    async def _flush_once(self, force: bool = False) -> None:
        """Write cache to disk if dirty."""
        if not self._dirty and not force:
            return
        self._dirty = False

        snapshot = copy.deepcopy(self._disk_cache)
        await asyncio.to_thread(save_data_sync, self._path, snapshot)
        logger.debug("token_usage: flushed cache to disk")

    async def _flush_loop(self) -> None:
        """Periodically flush the cache to disk."""
        try:
            while not self._stopped:
                await asyncio.sleep(self._flush_interval)
                try:
                    await self._flush_once()
                except Exception:
                    logger.exception("token_usage: error during periodic flush")
        except asyncio.CancelledError:
            pass

    async def _seed_cache(self) -> None:
        """Load existing data from disk into cache once."""
        if self._cache_loaded:
            return
        self._disk_cache = await load_data(self._path)
        self._cache_loaded = True
        logger.debug("token_usage: cache seeded from disk")


def _apply_event(cache: dict, ev: _UsageEvent) -> None:
    """Accumulate a single usage event into *cache* in-place."""
    composite_key = f"{ev.provider_id}:{ev.model_name}"
    day_bucket = cache.setdefault(ev.date_str, {})
    entry = day_bucket.setdefault(
        composite_key,
        {
            "provider_id": ev.provider_id,
            "model_name": ev.model_name,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "call_count": 0,
        },
    )
    entry["prompt_tokens"] += ev.prompt_tokens
    entry["completion_tokens"] += ev.completion_tokens
    entry["call_count"] += 1


__all__ = ["TokenUsageBuffer", "_UsageEvent"]
