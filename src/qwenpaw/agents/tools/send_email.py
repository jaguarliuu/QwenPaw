# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import mimetypes
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from agentscope.message import TextBlock
from agentscope.tool import ToolResponse

from ...config.config import EmailToolConfig, load_agent_config
from .file_io import _resolve_file_path


def get_current_agent_id() -> str:
    from ...app.agent_context import get_current_agent_id as _get_current_agent_id

    return _get_current_agent_id()


def _normalize_recipients(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = value.split(",")
    else:
        items = list(value)
    return [item.strip() for item in items if item and item.strip()]


def _format_sender(config: EmailToolConfig) -> str:
    from_address = config.from_address.strip()
    from_name = config.from_name.strip()
    if from_name:
        return f"{from_name} <{from_address}>"
    return from_address


def _build_ssl_context(config: EmailToolConfig) -> ssl.SSLContext:
    if config.allow_untrusted_tls:
        return ssl._create_unverified_context()  # type: ignore[attr-defined]
    return ssl.create_default_context()


def _attach_files(message: EmailMessage, attachment_paths: Iterable[str]) -> None:
    for attachment_path in attachment_paths:
        resolved_path = Path(_resolve_file_path(attachment_path)).expanduser()
        if not resolved_path.exists() or not resolved_path.is_file():
            raise FileNotFoundError(f"Attachment not found: {resolved_path}")
        mime_type, _ = mimetypes.guess_type(str(resolved_path))
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        message.add_attachment(
            resolved_path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=resolved_path.name,
        )


def _load_email_config() -> EmailToolConfig:
    agent_id = get_current_agent_id()
    agent_config = load_agent_config(agent_id)
    return getattr(agent_config, "email", EmailToolConfig())


def _send_email_sync(
    config: EmailToolConfig,
    *,
    to: list[str],
    cc: list[str],
    bcc: list[str],
    subject: str,
    body_text: str,
    body_html: str,
    reply_to: str,
    attachment_paths: list[str],
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = _format_sender(config)
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)

    if reply_to:
        message["Reply-To"] = reply_to
    elif config.reply_to.strip():
        message["Reply-To"] = config.reply_to.strip()

    if body_text.strip():
        message.set_content(body_text)
    else:
        message.set_content("HTML email")
    if body_html.strip():
        message.add_alternative(body_html, subtype="html")

    _attach_files(message, attachment_paths)

    recipients = [*to, *cc, *bcc]
    ssl_context = _build_ssl_context(config)
    if config.use_ssl:
        with smtplib.SMTP_SSL(
            config.host,
            config.port,
            timeout=config.timeout_sec,
        ) as smtp:
            if config.username.strip():
                smtp.login(config.username, config.password)
            smtp.send_message(message, to_addrs=recipients)
    else:
        with smtplib.SMTP(
            config.host,
            config.port,
            timeout=config.timeout_sec,
        ) as smtp:
            if config.use_starttls:
                smtp.starttls(context=ssl_context)
            if config.username.strip():
                smtp.login(config.username, config.password)
            smtp.send_message(message, to_addrs=recipients)
    return message


async def send_email(
    to: list[str] | str,
    subject: str,
    body_text: str = "",
    body_html: str = "",
    cc: list[str] | str | None = None,
    bcc: list[str] | str | None = None,
    reply_to: str = "",
    attachment_paths: list[str] | str | None = None,
) -> ToolResponse:
    """Send an email using the configured SMTP server."""

    config = _load_email_config()
    to_recipients = _normalize_recipients(to)
    cc_recipients = _normalize_recipients(cc)
    bcc_recipients = _normalize_recipients(bcc)
    attachments = _normalize_recipients(attachment_paths)

    if not to_recipients:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text="Error: At least one recipient is required.",
                ),
            ],
        )

    if not subject.strip():
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text="Error: Email subject is required.",
                ),
            ],
        )

    if not body_text.strip() and not body_html.strip():
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text="Error: body_text or body_html is required.",
                ),
            ],
        )

    if not config.host.strip() or not config.from_address.strip():
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=(
                        "Error: SMTP is not configured. "
                        "Set host and from_address in the send_email tool settings."
                    ),
                ),
            ],
        )

    try:
        message = await asyncio.to_thread(
            _send_email_sync,
            config,
            to=to_recipients,
            cc=cc_recipients,
            bcc=bcc_recipients,
            subject=subject.strip(),
            body_text=body_text,
            body_html=body_html,
            reply_to=reply_to.strip(),
            attachment_paths=attachments,
        )
    except Exception as exc:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text=f"Error: Failed to send email.\n{exc}",
                ),
            ],
        )

    success_text = (
        f"Email sent successfully to {message['To']}"
        + (f" (cc: {message['Cc']})" if message.get("Cc") else "")
        + f" with subject: {message['Subject']}"
    )
    return ToolResponse(content=[TextBlock(type="text", text=success_text)])
