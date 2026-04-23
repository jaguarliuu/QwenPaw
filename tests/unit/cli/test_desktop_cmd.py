# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import importlib
import sys
import threading
from pathlib import Path


class _FakeWindow:
    def __init__(self) -> None:
        self.minimize_calls = 0
        self.destroy_calls = 0
        self.run_js_calls: list[str] = []
        self.confirm_result = True

    def minimize(self) -> None:
        self.minimize_calls += 1

    def destroy(self) -> None:
        self.destroy_calls += 1

    def run_js(self, script: str) -> None:
        self.run_js_calls.append(script)

    def create_confirmation_dialog(self, _title: str, _message: str) -> bool:
        return self.confirm_result


class _FakeShellIntegration:
    def __init__(self, minimize_result: bool = True) -> None:
        self.minimize_result = minimize_result
        self.initialize_calls = 0
        self.minimize_calls = 0
        self.shutdown_calls = 0
        self.request_window_close_calls = 0
        self.exit_callback = None

    def set_exit_requested(self, callback) -> None:
        self.exit_callback = callback

    def initialize(self) -> None:
        self.initialize_calls += 1

    def minimize_to_tray(self) -> bool:
        self.minimize_calls += 1
        return self.minimize_result

    def shutdown(self) -> None:
        self.shutdown_calls += 1

    def request_window_close(self) -> bool:
        self.request_window_close_calls += 1
        return True


class _FakeEventHook:
    def __init__(self) -> None:
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


class _FakeWindowEvents:
    def __init__(self) -> None:
        self.loaded = _FakeEventHook()
        self.closing = _FakeEventHook()


class _FakeWindowWithEvents:
    def __init__(self) -> None:
        self.events = _FakeWindowEvents()


def test_desktop_close_action_round_trip(tmp_path: Path, monkeypatch) -> None:
    from qwenpaw.cli import desktop_cmd as desktop_cmd_module

    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(
        desktop_cmd_module,
        "_DESKTOP_SETTINGS_FILE",
        settings_file,
    )

    desktop_cmd_module._save_desktop_close_action("minimize")
    assert desktop_cmd_module._load_desktop_close_action() == "minimize"

    desktop_cmd_module._save_desktop_close_action("exit")
    assert desktop_cmd_module._load_desktop_close_action() == "exit"

    desktop_cmd_module._save_desktop_close_action(None)
    assert desktop_cmd_module._load_desktop_close_action() is None


def test_closing_with_saved_minimize_cancels_close_and_minimizes(
    monkeypatch,
) -> None:
    from qwenpaw.cli.desktop_cmd import DesktopCloseController

    window = _FakeWindow()
    shell = _FakeShellIntegration()
    controller = DesktopCloseController(window, shell_integration=shell)
    monkeypatch.setattr(
        "qwenpaw.cli.desktop_cmd._load_desktop_close_action",
        lambda: "minimize",
    )

    assert controller.on_closing() is False
    assert shell.minimize_calls == 1
    assert window.minimize_calls == 0
    assert window.destroy_calls == 0


def test_closing_with_saved_exit_allows_close(monkeypatch) -> None:
    from qwenpaw.cli.desktop_cmd import DesktopCloseController

    shell = _FakeShellIntegration()
    controller = DesktopCloseController(_FakeWindow(), shell_integration=shell)
    monkeypatch.setattr(
        "qwenpaw.cli.desktop_cmd._load_desktop_close_action",
        lambda: "exit",
    )

    assert controller.on_closing() is True
    assert shell.shutdown_calls == 1


def test_closing_without_preference_requests_frontend_prompt(
    monkeypatch,
) -> None:
    from qwenpaw.cli.desktop_cmd import DesktopCloseController

    window = _FakeWindow()
    controller = DesktopCloseController(window)
    controller.on_loaded()
    monkeypatch.setattr(
        "qwenpaw.cli.desktop_cmd._load_desktop_close_action",
        lambda: None,
    )

    assert controller.on_closing() is False
    assert len(window.run_js_calls) == 1
    assert "stategrid-desktop-close-request" in window.run_js_calls[0]


def test_handle_close_choice_exit_remembers_and_destroys(
    monkeypatch,
) -> None:
    from qwenpaw.cli.desktop_cmd import DesktopCloseController

    saved: list[str | None] = []
    monkeypatch.setattr(
        "qwenpaw.cli.desktop_cmd._save_desktop_close_action",
        lambda action: saved.append(action),
    )

    window = _FakeWindow()
    shell = _FakeShellIntegration()
    controller = DesktopCloseController(window, shell_integration=shell)
    controller.handle_close_choice("exit", remember=True)

    assert saved == ["exit"]
    assert shell.shutdown_calls == 1
    assert window.destroy_calls == 1


def test_handle_close_choice_cancel_reopens_prompt_later(monkeypatch) -> None:
    from qwenpaw.cli.desktop_cmd import DesktopCloseController

    window = _FakeWindow()
    controller = DesktopCloseController(window)
    controller.on_loaded()
    monkeypatch.setattr(
        "qwenpaw.cli.desktop_cmd._load_desktop_close_action",
        lambda: None,
    )

    assert controller.on_closing() is False
    assert len(window.run_js_calls) == 1

    controller.handle_close_choice("cancel", remember=False)

    assert controller.on_closing() is False
    assert len(window.run_js_calls) == 2


def test_handle_close_choice_minimize_prefers_tray_integration() -> None:
    from qwenpaw.cli.desktop_cmd import DesktopCloseController

    window = _FakeWindow()
    shell = _FakeShellIntegration(minimize_result=True)
    controller = DesktopCloseController(window, shell_integration=shell)

    controller.handle_close_choice("minimize", remember=False)

    assert shell.minimize_calls == 1
    assert window.minimize_calls == 0
    assert window.destroy_calls == 0


def test_exit_from_tray_requests_native_window_close() -> None:
    from qwenpaw.cli.desktop_cmd import DesktopCloseController

    window = _FakeWindow()
    shell = _FakeShellIntegration()
    controller = DesktopCloseController(window, shell_integration=shell)

    controller.exit_from_tray()

    assert shell.shutdown_calls == 1
    assert shell.request_window_close_calls == 1
    assert window.destroy_calls == 0


def test_desktop_cmd_imports_when_wintypes_win_handles_missing(
    monkeypatch,
) -> None:
    from ctypes import wintypes

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delattr(wintypes, "LRESULT", raising=False)
    monkeypatch.delattr(wintypes, "HCURSOR", raising=False)
    monkeypatch.setattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE, raising=False)

    sys.modules.pop("qwenpaw.cli.desktop_cmd", None)
    module = importlib.import_module("qwenpaw.cli.desktop_cmd")

    assert hasattr(module, "desktop_cmd")


def test_webview_api_dispatches_close_choice_asynchronously() -> None:
    from qwenpaw.cli.desktop_cmd import WebViewAPI

    called = threading.Event()
    caller_ident = threading.get_ident()
    observed: dict[str, object] = {}

    class _FakeController:
        def handle_close_choice(self, action: str, remember: bool) -> None:
            observed["action"] = action
            observed["remember"] = remember
            observed["thread_ident"] = threading.get_ident()
            called.set()

    api = WebViewAPI()
    api.bind_close_controller(_FakeController())

    api.handle_close_choice("exit", remember=True)

    assert called.wait(timeout=1.0)
    assert observed == {
        "action": "exit",
        "remember": True,
        "thread_ident": observed["thread_ident"],
    }
    assert observed["thread_ident"] != caller_ident


def test_bind_desktop_window_events_registers_loaded_only() -> None:
    from qwenpaw.cli.desktop_cmd import _bind_desktop_window_events

    called = []

    class _Shell:
        def initialize(self) -> None:
            called.append("initialize")

    window = _FakeWindowWithEvents()
    _bind_desktop_window_events(window, shell_integration=_Shell())

    assert len(window.events.loaded.handlers) == 1
    assert len(window.events.closing.handlers) == 0

    window.events.loaded.handlers[0]()
    assert called == ["initialize"]
