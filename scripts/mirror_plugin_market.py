#!/usr/bin/env python3
"""Mirror the AgentScope plugin market to a local directory.

Fetches everything needed to serve the QwenPaw plugin market from an
intranet mirror (later uploaded to Tencent COS or similar):

1. **Plugin market list API** — paginated call to
   ``https://platform.agentscope.io/openapi/v1/plugins`` for every page.
   Both the flattened list and each raw page are saved so an intranet
   HTTP server can serve them as static JSON.

2. **Plugin ZIPs (per entry)** — for every ``entry.id`` in the form
   ``@owner/name`` the master-branch archive
   ``https://platform.agentscope.io/plugins/{owner}/{name}/archive/zip/master``
   is fetched and saved under
   ``mirror/plugins/{owner}/{name}/master.zip``.

3. **Official download catalog CDN** — the QwenPaw ``download`` CDN
   (``https://download.qwenpaw.agentscope.io``) is walked starting from
   ``/metadata/index.json``; every referenced sub-index and plugin ZIP
   is mirrored with its original relative path preserved so URLs are
   drop-in compatible after upload.

Layout produced (relative to ``--output``)::

    mirror/
    ├── openapi/v1/plugins.json            # flattened aggregate response
    ├── openapi/v1/plugins.page-01.json    # raw page snapshots
    ├── openapi/v1/plugins.page-02.json
    ├── plugins/{owner}/{name}/master.zip
    ├── metadata/index.json
    ├── metadata/plugins/index.json
    ├── metadata/plugins/{plugin_id}-{version}.zip
    ├── MANIFEST.txt                       # one line per file: path\tsize\tsha256
    └── errors.log                         # non-fatal failures encountered

Usage (from repo root)::

    python scripts/mirror_plugin_market.py --output ./mirror
    python scripts/mirror_plugin_market.py --output ./mirror --force
    python scripts/mirror_plugin_market.py --output ./mirror \\
        --market-base https://platform.agentscope.io \\
        --cdn-base https://download.qwenpaw.agentscope.io \\
        --page-size 50 --timeout 60

The script is idempotent — rerun to refresh.  Existing non-empty files
are skipped unless ``--force`` is passed.  Failures for individual
plugins are logged and do not abort the whole run.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import shutil
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

DEFAULT_MARKET_BASE = "https://platform.agentscope.io"
DEFAULT_CDN_BASE = "https://download.qwenpaw.agentscope.io"
DEFAULT_PAGE_SIZE = 50
DEFAULT_TIMEOUT = 60  # seconds per HTTP call
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 2.0  # seconds; grows geometrically

USER_AGENT = "TinyC-PluginMirror/1.0 (+https://github.com/jaguarliuu/QwenPaw)"

logger = logging.getLogger("mirror_plugin_market")


# ── HTTP helpers ─────────────────────────────────────────────────────────


def _fetch_bytes(url: str, timeout: int, retries: int) -> bytes:
    """GET ``url`` and return raw body, retrying on transient errors."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if (
                    resp.headers.get("Content-Encoding") == "gzip"
                    or data[:2] == b"\x1f\x8b"
                ):
                    data = gzip.decompress(data)
                return data
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout) as exc:
            last_exc = exc
            if attempt < retries:
                sleep_s = DEFAULT_BACKOFF ** attempt
                logger.warning(
                    "Fetch %s failed (attempt %d/%d): %s — retrying in %.1fs",
                    url,
                    attempt,
                    retries,
                    exc,
                    sleep_s,
                )
                time.sleep(sleep_s)
    raise RuntimeError(f"Failed to fetch {url}: {last_exc}") from last_exc


def _fetch_json(url: str, timeout: int, retries: int) -> Any:
    return json.loads(_fetch_bytes(url, timeout, retries))


def _stream_download(
    url: str,
    dest: Path,
    timeout: int,
    retries: int,
) -> None:
    """Stream ``url`` to ``dest`` atomically (write to .part then rename)."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                with open(tmp, "wb") as fh:
                    shutil.copyfileobj(resp, fh, length=256 * 1024)
            tmp.replace(dest)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout) as exc:
            last_exc = exc
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            if attempt < retries:
                sleep_s = DEFAULT_BACKOFF ** attempt
                logger.warning(
                    "Download %s failed (attempt %d/%d): %s — retry in %.1fs",
                    url,
                    attempt,
                    retries,
                    exc,
                    sleep_s,
                )
                time.sleep(sleep_s)
    raise RuntimeError(f"Failed to download {url}: {last_exc}") from last_exc


# ── Plugin market list API ───────────────────────────────────────────────


def _iter_market_pages(
    market_base: str,
    page_size: int,
    timeout: int,
    retries: int,
) -> Iterator[tuple[int, dict]]:
    """Yield ``(page_number, raw_json)`` until the API stops returning items."""
    page = 1
    while True:
        params = urllib.parse.urlencode(
            {"page_number": page, "page_size": page_size},
        )
        url = f"{market_base}/openapi/v1/plugins?{params}"
        logger.info("Fetching market page %d: %s", page, url)
        raw = _fetch_json(url, timeout, retries)

        data = raw.get("data") if isinstance(raw, dict) else None
        plugins: list = []
        total: int | None = None
        if isinstance(data, dict):
            plugins = data.get("plugins") or []
            total = data.get("total")

        yield page, raw

        if not plugins:
            logger.info("Empty page — reached end at page %d", page)
            return

        if total is not None:
            if page * page_size >= total:
                logger.info(
                    "Fetched all %d plugins across %d pages",
                    total,
                    page,
                )
                return

        page += 1


def _flatten_market(pages: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for raw in pages:
        data = raw.get("data") if isinstance(raw, dict) else None
        if not isinstance(data, dict):
            continue
        for entry in data.get("plugins") or []:
            plugin_id = entry.get("id")
            if isinstance(plugin_id, str) and plugin_id and plugin_id not in seen:
                seen[plugin_id] = entry
    return list(seen.values())


# ── ZIP mirroring per plugin ─────────────────────────────────────────────


def _owner_name_from_entry(entry: dict) -> tuple[str, str] | None:
    """Return ``(owner, name)`` for a market entry, or ``None`` if malformed."""
    raw_id = entry.get("id")
    if not isinstance(raw_id, str) or not raw_id:
        return None
    stripped = raw_id[1:] if raw_id.startswith("@") else raw_id
    if "/" not in stripped:
        return None
    owner, _, name = stripped.partition("/")
    owner = owner.strip()
    name = name.strip()
    if not owner or not name:
        return None
    return owner, name


def _mirror_plugin_zips(
    entries: list[dict],
    market_base: str,
    output: Path,
    timeout: int,
    retries: int,
    force: bool,
    errors: list[str],
) -> tuple[int, int, int]:
    """Download the master-branch ZIP for every entry.

    Returns ``(ok, skipped, failed)``.
    """
    ok = skipped = failed = 0
    for i, entry in enumerate(entries, start=1):
        pair = _owner_name_from_entry(entry)
        if pair is None:
            logger.warning(
                "[%d/%d] Skip entry with malformed id: %r",
                i,
                len(entries),
                entry.get("id"),
            )
            failed += 1
            errors.append(f"malformed-id\t{entry.get('id')!r}")
            continue
        owner, name = pair
        url = f"{market_base}/plugins/{owner}/{name}/archive/zip/master"
        dest = output / "plugins" / owner / name / "master.zip"

        if dest.exists() and dest.stat().st_size > 0 and not force:
            logger.info(
                "[%d/%d] Skip %s/%s (already mirrored)",
                i,
                len(entries),
                owner,
                name,
            )
            skipped += 1
            continue

        try:
            logger.info(
                "[%d/%d] Downloading %s/%s ...",
                i,
                len(entries),
                owner,
                name,
            )
            _stream_download(url, dest, timeout, retries)
            ok += 1
        except KeyboardInterrupt:
            logger.warning(
                "[%d/%d] Interrupted by user while downloading %s/%s — "
                "flushing state and exiting cleanly",
                i,
                len(entries),
                owner,
                name,
            )
            errors.append(f"plugin-zip\t{owner}/{name}\tInterrupted by user")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[%d/%d] Failed %s/%s: %s",
                i,
                len(entries),
                owner,
                name,
                exc,
            )
            failed += 1
            errors.append(f"plugin-zip\t{owner}/{name}\t{exc}")
    return ok, skipped, failed


# ── Official download CDN mirror ─────────────────────────────────────────


def _mirror_download_cdn(
    cdn_base: str,
    output: Path,
    timeout: int,
    retries: int,
    force: bool,
    errors: list[str],
) -> tuple[int, int, int]:
    """Mirror ``metadata/index.json`` plus every plugin ZIP it references.

    The CDN layout is::

        /metadata/index.json                    # main index (multi-product)
        /metadata/plugins/index.json            # plugins sub-index
        /metadata/plugins/{plugin_id}-{ver}.zip # ZIP artefacts

    Returns ``(ok, skipped, failed)``.
    """
    ok = skipped = failed = 0
    base = cdn_base.rstrip("/")

    try:
        main_url = f"{base}/metadata/index.json"
        main_bytes = _fetch_bytes(main_url, timeout, retries)
        main_dest = output / "metadata" / "index.json"
        main_dest.parent.mkdir(parents=True, exist_ok=True)
        main_dest.write_bytes(main_bytes)
        logger.info("Mirrored main CDN index: %s", main_dest)
        ok += 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch main CDN index: %s", exc)
        errors.append(f"cdn-main-index\t{exc}")
        return ok, skipped, failed + 1

    try:
        main_index = json.loads(main_bytes)
    except json.JSONDecodeError as exc:
        logger.error("Main CDN index is not valid JSON: %s", exc)
        errors.append(f"cdn-main-index-json\t{exc}")
        return ok, skipped, failed + 1

    products = main_index.get("products") or {}
    plugins_product = products.get("plugins")
    if not isinstance(plugins_product, dict):
        logger.warning("Main CDN index has no 'plugins' product — done")
        return ok, skipped, failed

    plugins_index_path = str(plugins_product.get("index_url") or "")
    if not plugins_index_path.startswith("/"):
        logger.error(
            "plugins.index_url is not a relative path: %r",
            plugins_index_path,
        )
        errors.append(f"cdn-plugins-index-url\t{plugins_index_path!r}")
        return ok, skipped, failed + 1

    try:
        plugins_index_url = f"{base}{plugins_index_path}"
        plugins_index_bytes = _fetch_bytes(
            plugins_index_url,
            timeout,
            retries,
        )
        plugins_index_dest = output / plugins_index_path.lstrip("/")
        plugins_index_dest.parent.mkdir(parents=True, exist_ok=True)
        plugins_index_dest.write_bytes(plugins_index_bytes)
        logger.info(
            "Mirrored plugins CDN index: %s",
            plugins_index_dest,
        )
        ok += 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch plugins CDN index: %s", exc)
        errors.append(f"cdn-plugins-index\t{exc}")
        return ok, skipped, failed + 1

    try:
        plugins_index = json.loads(plugins_index_bytes)
    except json.JSONDecodeError as exc:
        logger.error("plugins index is not valid JSON: %s", exc)
        errors.append(f"cdn-plugins-index-json\t{exc}")
        return ok, skipped, failed + 1

    files = plugins_index.get("files") or {}
    for file_id, entry in files.items():
        if not isinstance(entry, dict):
            continue
        rel_url = str(entry.get("url") or "")
        if not rel_url.startswith("/"):
            failed += 1
            errors.append(f"cdn-file-bad-url\t{file_id}\t{rel_url!r}")
            continue
        dest = output / rel_url.lstrip("/")
        if dest.exists() and dest.stat().st_size > 0 and not force:
            logger.info("Skip CDN %s (already mirrored)", rel_url)
            skipped += 1
            continue
        try:
            logger.info("Downloading CDN %s ...", rel_url)
            _stream_download(f"{base}{rel_url}", dest, timeout, retries)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed CDN %s: %s", rel_url, exc)
            errors.append(f"cdn-file\t{rel_url}\t{exc}")
            failed += 1

    return ok, skipped, failed


# ── Manifest & summary ───────────────────────────────────────────────────


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_manifest(output: Path) -> Path:
    """Walk ``output`` and write ``MANIFEST.txt`` with per-file hash & size."""
    manifest = output / "MANIFEST.txt"
    lines: list[str] = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path == manifest:
            continue
        rel = path.relative_to(output).as_posix()
        size = path.stat().st_size
        digest = _sha256_file(path)
        lines.append(f"{rel}\t{size}\t{digest}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def _write_errors(output: Path, errors: list[str]) -> Path | None:
    if not errors:
        return None
    path = output / "errors.log"
    path.write_text("\n".join(errors) + "\n", encoding="utf-8")
    return path


# ── Entrypoint ───────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("mirror"),
        help="Local mirror directory (default: ./mirror)",
    )
    parser.add_argument(
        "--market-base",
        default=DEFAULT_MARKET_BASE,
        help=f"Market API base URL (default: {DEFAULT_MARKET_BASE})",
    )
    parser.add_argument(
        "--cdn-base",
        default=DEFAULT_CDN_BASE,
        help=f"Download CDN base URL (default: {DEFAULT_CDN_BASE})",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"Page size for market API (default: {DEFAULT_PAGE_SIZE})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Retry count per URL (default: {DEFAULT_RETRIES})",
    )
    parser.add_argument(
        "--socket-timeout",
        type=float,
        default=30.0,
        help=(
            "Per-socket-op timeout in seconds (default: 30). Kills stalled body "
            "reads that would otherwise hang forever after handshake."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload files even if they already exist locally",
    )
    parser.add_argument(
        "--skip-market",
        action="store_true",
        help="Skip mirroring the plugin market list + ZIPs",
    )
    parser.add_argument(
        "--skip-cdn",
        action="store_true",
        help="Skip mirroring the official download CDN",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only mirror the first N plugin ZIPs (0 = all; for smoke tests)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    socket.setdefaulttimeout(args.socket_timeout)

    output: Path = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    logger.info("Mirroring to %s", output)
    logger.info("Socket op timeout: %.1fs (kills stalled body reads)", args.socket_timeout)

    errors: list[str] = []
    totals = {"ok": 0, "skipped": 0, "failed": 0}

    # ── 1. Plugin market list API ───────────────────────────────────────
    entries: list[dict] = []
    if not args.skip_market:
        pages: list[dict] = []
        openapi_dir = output / "openapi" / "v1"
        openapi_dir.mkdir(parents=True, exist_ok=True)
        try:
            for page_num, raw in _iter_market_pages(
                args.market_base,
                args.page_size,
                args.timeout,
                args.retries,
            ):
                page_path = openapi_dir / f"plugins.page-{page_num:02d}.json"
                page_path.write_text(
                    json.dumps(raw, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                pages.append(raw)
                totals["ok"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("Market list fetch aborted: %s", exc)
            errors.append(f"market-list\t{exc}")
            totals["failed"] += 1

        entries = _flatten_market(pages)
        (openapi_dir / "plugins.json").write_text(
            json.dumps(
                {
                    "success": True,
                    "message": "mirrored",
                    "data": {"total": len(entries), "plugins": entries},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(
            "Flattened market list: %d unique plugins across %d pages",
            len(entries),
            len(pages),
        )

        if args.limit > 0:
            logger.warning(
                "Applying --limit %d (of %d entries) for smoke test",
                args.limit,
                len(entries),
            )
            entries = entries[: args.limit]

        # ── 2. Per-plugin master.zip ────────────────────────────────────
        ok, skipped, failed = _mirror_plugin_zips(
            entries,
            args.market_base,
            output,
            args.timeout,
            args.retries,
            args.force,
            errors,
        )
        totals["ok"] += ok
        totals["skipped"] += skipped
        totals["failed"] += failed

    # ── 3. Official download CDN mirror ─────────────────────────────────
    if not args.skip_cdn:
        ok, skipped, failed = _mirror_download_cdn(
            args.cdn_base,
            output,
            args.timeout,
            args.retries,
            args.force,
            errors,
        )
        totals["ok"] += ok
        totals["skipped"] += skipped
        totals["failed"] += failed

    # ── 4. Manifest & error log ─────────────────────────────────────────
    manifest_path = _write_manifest(output)
    error_path = _write_errors(output, errors)

    logger.info("=" * 60)
    logger.info("Mirror complete: %s", output)
    logger.info(
        "  ok=%d  skipped=%d  failed=%d",
        totals["ok"],
        totals["skipped"],
        totals["failed"],
    )
    logger.info("  manifest: %s", manifest_path)
    if error_path is not None:
        logger.warning("  errors:   %s (%d entries)", error_path, len(errors))
    logger.info("=" * 60)

    return 0 if totals["failed"] == 0 else 1


def _cli_entry() -> int:
    try:
        return main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user (Ctrl-C). Partial mirror preserved on disk.")
        return 130


if __name__ == "__main__":
    sys.exit(_cli_entry())
