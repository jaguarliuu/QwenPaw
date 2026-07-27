# -*- coding: utf-8 -*-
from __future__ import annotations

import ipaddress
import logging
import os
import ssl
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTNAMES = {"localhost"}


def is_loopback_host(host: str) -> bool:
    """Return True when *host* is localhost or a loopback IP address."""
    normalized = host.strip().strip("[]").lower().rstrip(".")
    if normalized in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def is_loopback_url(url: str) -> bool:
    """Return True when *url* targets a localhost or loopback address."""
    return is_loopback_host(urlparse(url).hostname or "")


def trust_env_for_url(url: str) -> bool:
    """Return whether httpx should trust proxy/cert env vars for *url*."""
    return not is_loopback_url(url)


# ── Internal-network TLS trust ───────────────────────────────────────────
#
# Some deployments sit behind a private CA (e.g. ``25.75.3.1`` in the
# QwenPaw internal plugin mirror). The recommended way to trust such
# certificates is:
#
#   1. Prefer the operating system trust store — administrators add the
#      internal CA once via ``security add-trusted-cert`` (macOS) or
#      ``update-ca-certificates`` (Debian/Ubuntu) etc. Nothing in the
#      Python code has to change.
#   2. When (1) is impractical (Docker images, air-gapped nodes, or
#      httpx which by default reads certifi and *not* the OS store),
#      set the env var ``QWENPAW_INTERNAL_CA_BUNDLE`` to an absolute
#      path to a PEM file. The functions below will layer that CA on
#      top of the system default trust — never replacing it — so
#      public HTTPS traffic keeps working unchanged.
#
# Three-state semantics for the env var:
#   * unset / empty   → return ``None`` → callers fall back to library
#                       defaults (``ssl.create_default_context()`` for
#                       ``urllib``; certifi for ``httpx``).
#   * valid file      → build a context extending the system trust
#                       with the given PEM bundle.
#   * non-existent    → log a warning and behave like "unset" so a
#                       misconfigured env never crashes the request
#                       path (fail-open on trust, not on service).

INTERNAL_CA_BUNDLE_ENV = "QWENPAW_INTERNAL_CA_BUNDLE"


def _resolve_ca_bundle_path() -> Path | None:
    """Return a resolved existing PEM path, or ``None``.

    Never raises. Logs a single warning line for misconfigured paths.
    """
    raw = os.environ.get(INTERNAL_CA_BUNDLE_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_file():
        logger.warning(
            "%s is set to %r but that file does not exist; "
            "falling back to system default TLS trust store.",
            INTERNAL_CA_BUNDLE_ENV,
            str(path),
        )
        return None
    return path.resolve()


def build_internal_ssl_context() -> ssl.SSLContext | None:
    """Build an ``ssl.SSLContext`` for internal-network HTTPS callers.

    Returns ``None`` when no extra CA is configured, letting callers
    pass ``context=None`` (or simply omit the kwarg) to
    :func:`urllib.request.urlopen` for maximum forward compatibility.

    When an extra CA bundle is configured, the returned context
    *extends* the OS trust store rather than replacing it, so calls
    to public HTTPS endpoints continue to work.
    """
    ca_path = _resolve_ca_bundle_path()
    if ca_path is None:
        return None

    ctx = ssl.create_default_context()
    try:
        ctx.load_verify_locations(cafile=str(ca_path))
    except (ssl.SSLError, OSError) as exc:
        logger.warning(
            "Failed to load internal CA bundle %s (%s); "
            "falling back to system default TLS trust store.",
            ca_path,
            exc,
        )
        return None
    logger.debug(
        "Internal CA bundle %s layered on top of system trust store.",
        ca_path,
    )
    return ctx


def build_httpx_verify() -> Union[bool, str, ssl.SSLContext]:
    """Return a value suitable for ``httpx.AsyncClient(verify=...)``.

    httpx accepts a filesystem path *or* an :class:`ssl.SSLContext`
    (>=0.27), *or* ``True`` (its default: certifi trust store).

    We prefer returning a *full context* when a bundle is configured,
    because that mirrors :func:`build_internal_ssl_context` and keeps
    the OS trust store layered underneath. When no bundle is
    configured we return ``True`` — httpx's own default — so this
    helper is safe to sprinkle throughout the codebase without
    changing behavior for callers that do not need internal TLS.
    """
    ctx = build_internal_ssl_context()
    if ctx is not None:
        return ctx
    return True
