# -*- coding: utf-8 -*-
"""CLI command: run the desktop app on a free port in a native webview window."""
# pylint:disable=too-many-branches,too-many-statements,consider-using-with
from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

import click

from ..constant import LOG_LEVEL_ENV, WORKING_DIR
from ..utils.logging import setup_logger

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

try:
    import webview
except ImportError:
    webview = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_DESKTOP_WINDOW_TITLE = "StateGrid Desktop"
_DESKTOP_SETTINGS_FILE = WORKING_DIR / "settings.json"
_DESKTOP_CLOSE_ACTION_KEY = "desktop_close_action"
_DESKTOP_CLOSE_EVENT_NAME = "stategrid-desktop-close-request"
_DESKTOP_CLOSE_ACTIONS = {"minimize", "exit"}


def _find_desktop_icon_path() -> Path | None:
    """Resolve the Windows icon used by the packaged desktop app."""
    packaged_icon = Path(sys.executable).resolve().parent / "icon.ico"
    if packaged_icon.is_file():
        return packaged_icon

    repo_icon = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "pack"
        / "assets"
        / "icon.ico"
    )
    if repo_icon.is_file():
        return repo_icon

    return None


if sys.platform == "win32":
    _WM_COMMAND = 0x0111
    _WM_CLOSE = 0x0010
    _WM_DESTROY = 0x0002
    _WM_NULL = 0x0000
    _WM_SETICON = 0x0080
    _WM_APP = 0x8000
    _ICON_SMALL = 0
    _ICON_BIG = 1
    _SW_HIDE = 0
    _SW_SHOW = 5
    _SW_RESTORE = 9
    _IMAGE_ICON = 1
    _LR_LOADFROMFILE = 0x0010
    _LR_DEFAULTSIZE = 0x0040
    _NIM_ADD = 0x00000000
    _NIM_MODIFY = 0x00000001
    _NIM_DELETE = 0x00000002
    _NIM_SETVERSION = 0x00000004
    _NIF_MESSAGE = 0x00000001
    _NIF_ICON = 0x00000002
    _NIF_TIP = 0x00000004
    _NOTIFYICON_VERSION_4 = 4
    _TPM_LEFTALIGN = 0x0000
    _TPM_RIGHTBUTTON = 0x0002
    _MF_STRING = 0x0000
    _GCLP_HICON = -14
    _GCLP_HICONSM = -34
    _TRAY_CALLBACK_MESSAGE = _WM_APP + 1
    _TRAY_MENU_RESTORE_ID = 1001
    _TRAY_MENU_EXIT_ID = 1002
    # Some packaged Python runtimes on Windows omit a few wintypes aliases.
    # Fall back to pointer-sized primitives for missing handle/result types.
    _LRESULT = getattr(wintypes, "LRESULT", ctypes.c_ssize_t)
    _HCURSOR = getattr(wintypes, "HCURSOR", ctypes.c_void_p)

    class _GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class _POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class _MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", _POINT),
            ("lPrivate", wintypes.DWORD),
        ]

    _WNDPROC = ctypes.WINFUNCTYPE(
        _LRESULT,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    class _WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", _WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", _HCURSOR),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    class _NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uVersion", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
            ("guidItem", _GUID),
            ("hBalloonIcon", wintypes.HICON),
        ]

    class WindowsDesktopShellIntegration:
        """Apply Windows runtime shell integration for the desktop app."""

        def __init__(self, window_title: str, icon_path: Path | None) -> None:
            self.window_title = window_title
            self.icon_path = icon_path
            self._hwnd = None
            self._tray_hwnd = None
            self._icon_handle = None
            self._tray_icon_visible = False
            self._thread = None
            self._ready = threading.Event()
            self._stop_lock = threading.Lock()
            self._restore_requested = False
            self._exit_requested = None
            self._class_name = (
                f"StateGridDesktopTrayWindow_{os.getpid()}_{id(self)}"
            )
            self._wndproc = _WNDPROC(self._window_proc)

        def set_exit_requested(self, callback) -> None:
            self._exit_requested = callback

        def initialize(self) -> None:
            self._set_app_user_model_id()
            self._ensure_window_handle()
            self._apply_window_icon()

        def minimize_to_tray(self) -> bool:
            hwnd = self._ensure_window_handle()
            if not hwnd:
                return False
            if not self._ensure_tray_window():
                return False
            self._show_tray_icon()
            ctypes.windll.user32.ShowWindow(hwnd, _SW_HIDE)
            return True

        def restore_from_tray(self) -> bool:
            hwnd = self._ensure_window_handle()
            if not hwnd:
                return False
            self._hide_tray_icon()
            user32 = ctypes.windll.user32
            user32.ShowWindow(hwnd, _SW_RESTORE)
            user32.ShowWindow(hwnd, _SW_SHOW)
            user32.SetForegroundWindow(hwnd)
            return True

        def request_window_close(self) -> bool:
            hwnd = self._ensure_window_handle(timeout_sec=0.2)
            if not hwnd:
                return False
            ctypes.windll.user32.PostMessageW(hwnd, _WM_CLOSE, 0, 0)
            return True

        def shutdown(self) -> None:
            with self._stop_lock:
                self._hide_tray_icon()
                tray_hwnd = self._tray_hwnd
                if tray_hwnd:
                    ctypes.windll.user32.PostMessageW(tray_hwnd, _WM_CLOSE, 0, 0)
                thread = self._thread
                if (
                    thread
                    and thread.is_alive()
                    and threading.current_thread() is not thread
                ):
                    thread.join(timeout=2.0)
                self._thread = None
                self._tray_hwnd = None
                self._ready.clear()
                if self._icon_handle:
                    try:
                        ctypes.windll.user32.DestroyIcon(self._icon_handle)
                    except Exception:
                        pass
                    self._icon_handle = None

        def _set_app_user_model_id(self) -> None:
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "StateGridDesktop",
                )
            except Exception as e:
                logger.debug("Failed to set AppUserModelID: %s", e)

        def _ensure_window_handle(
            self,
            timeout_sec: float = 5.0,
        ):
            user32 = ctypes.windll.user32
            if self._hwnd and user32.IsWindow(self._hwnd):
                return self._hwnd

            pid = os.getpid()
            deadline = time.monotonic() + timeout_sec
            found = {"hwnd": None}

            def _enum_proc(hwnd, _lparam):
                process_id = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
                if process_id.value != pid:
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                if self.window_title in title.value:
                    found["hwnd"] = hwnd
                    return False
                return True

            enum_windows_proc = _WNDPROC(_enum_proc)
            while time.monotonic() < deadline:
                found["hwnd"] = None
                user32.EnumWindows(enum_windows_proc, 0)
                if found["hwnd"]:
                    self._hwnd = found["hwnd"]
                    return self._hwnd
                time.sleep(0.1)

            logger.warning(
                "Failed to resolve desktop window handle for '%s'",
                self.window_title,
            )
            return None

        def _load_icon_handle(self):
            if self._icon_handle:
                return self._icon_handle
            if not self.icon_path or not self.icon_path.is_file():
                logger.warning("Desktop icon file not found: %s", self.icon_path)
                return None

            handle = ctypes.windll.user32.LoadImageW(
                None,
                str(self.icon_path),
                _IMAGE_ICON,
                0,
                0,
                _LR_LOADFROMFILE | _LR_DEFAULTSIZE,
            )
            if not handle:
                logger.warning("Failed to load desktop icon from %s", self.icon_path)
                return None

            self._icon_handle = handle
            return handle

        def _apply_window_icon(self) -> None:
            hwnd = self._ensure_window_handle()
            hicon = self._load_icon_handle()
            if not hwnd or not hicon:
                return

            user32 = ctypes.windll.user32
            user32.SendMessageW(hwnd, _WM_SETICON, _ICON_SMALL, hicon)
            user32.SendMessageW(hwnd, _WM_SETICON, _ICON_BIG, hicon)

            set_class_long = getattr(user32, "SetClassLongPtrW", None)
            if set_class_long is None:
                set_class_long = getattr(user32, "SetClassLongW", None)
            if set_class_long is None:
                return

            try:
                set_class_long(hwnd, _GCLP_HICON, hicon)
                set_class_long(hwnd, _GCLP_HICONSM, hicon)
            except Exception as e:
                logger.debug("Failed to update window class icon: %s", e)

        def _ensure_tray_window(self) -> bool:
            if self._thread and self._thread.is_alive():
                return self._ready.wait(timeout=2.0)

            self._ready.clear()
            self._thread = threading.Thread(
                target=self._tray_message_loop,
                name="stategrid-tray",
                daemon=True,
            )
            self._thread.start()
            return self._ready.wait(timeout=2.0)

        def _show_tray_icon(self) -> None:
            if not self._tray_hwnd or self._tray_icon_visible:
                return
            hicon = self._load_icon_handle()
            if not hicon:
                return
            data = self._build_notify_icon_data()
            if not ctypes.windll.shell32.Shell_NotifyIconW(_NIM_ADD, ctypes.byref(data)):
                logger.warning("Failed to add tray icon.")
                return
            data.uVersion = _NOTIFYICON_VERSION_4
            ctypes.windll.shell32.Shell_NotifyIconW(_NIM_SETVERSION, ctypes.byref(data))
            self._tray_icon_visible = True

        def _hide_tray_icon(self) -> None:
            if not self._tray_hwnd or not self._tray_icon_visible:
                return
            data = self._build_notify_icon_data()
            ctypes.windll.shell32.Shell_NotifyIconW(_NIM_DELETE, ctypes.byref(data))
            self._tray_icon_visible = False

        def _build_notify_icon_data(self) -> _NOTIFYICONDATAW:
            data = _NOTIFYICONDATAW()
            data.cbSize = ctypes.sizeof(_NOTIFYICONDATAW)
            data.hWnd = self._tray_hwnd
            data.uID = 1
            data.uFlags = _NIF_MESSAGE | _NIF_ICON | _NIF_TIP
            data.uCallbackMessage = _TRAY_CALLBACK_MESSAGE
            data.hIcon = self._load_icon_handle() or 0
            data.szTip = _DESKTOP_WINDOW_TITLE
            return data

        def _tray_message_loop(self) -> None:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hinstance = kernel32.GetModuleHandleW(None)

            wnd_class = _WNDCLASSW()
            wnd_class.lpfnWndProc = self._wndproc
            wnd_class.hInstance = hinstance
            wnd_class.lpszClassName = self._class_name

            atom = user32.RegisterClassW(ctypes.byref(wnd_class))
            if not atom:
                logger.warning("Failed to register desktop tray window class.")
                self._ready.set()
                return

            hwnd = user32.CreateWindowExW(
                0,
                self._class_name,
                self._class_name,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                hinstance,
                None,
            )
            if not hwnd:
                logger.warning("Failed to create desktop tray window.")
                self._ready.set()
                return

            self._tray_hwnd = hwnd
            self._ready.set()

            msg = _MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            try:
                user32.UnregisterClassW(self._class_name, hinstance)
            except Exception:
                pass

        def _window_proc(self, hwnd, msg, wparam, lparam):
            user32 = ctypes.windll.user32
            if msg == _TRAY_CALLBACK_MESSAGE:
                if lparam in (0x0202, 0x0203):
                    self.restore_from_tray()
                    return 0
                if lparam in (0x0205, 0x007B):
                    self._show_tray_menu(hwnd)
                    return 0
            elif msg == _WM_COMMAND:
                command_id = wparam & 0xFFFF
                if command_id == _TRAY_MENU_RESTORE_ID:
                    self.restore_from_tray()
                    return 0
                if command_id == _TRAY_MENU_EXIT_ID:
                    if callable(self._exit_requested):
                        self._exit_requested()
                    else:
                        self.request_window_close()
                    return 0
            elif msg == _WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            elif msg == _WM_DESTROY:
                self._hide_tray_icon()
                user32.PostQuitMessage(0)
                return 0

            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        def _show_tray_menu(self, hwnd) -> None:
            user32 = ctypes.windll.user32
            menu = user32.CreatePopupMenu()
            if not menu:
                return

            try:
                user32.AppendMenuW(
                    menu,
                    _MF_STRING,
                    _TRAY_MENU_RESTORE_ID,
                    f"Open {_DESKTOP_WINDOW_TITLE}",
                )
                user32.AppendMenuW(
                    menu,
                    _MF_STRING,
                    _TRAY_MENU_EXIT_ID,
                    "Exit",
                )
                point = _POINT()
                user32.GetCursorPos(ctypes.byref(point))
                user32.SetForegroundWindow(hwnd)
                user32.TrackPopupMenu(
                    menu,
                    _TPM_LEFTALIGN | _TPM_RIGHTBUTTON,
                    point.x,
                    point.y,
                    0,
                    hwnd,
                    None,
                )
                user32.PostMessageW(hwnd, _WM_NULL, 0, 0)
            finally:
                user32.DestroyMenu(menu)


def _load_desktop_close_action() -> str | None:
    """Return the remembered desktop close action, if any."""
    settings_path = Path(_DESKTOP_SETTINGS_FILE).expanduser()
    if not settings_path.is_file():
        return None
    try:
        data = json.loads(settings_path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError, TypeError):
        return None

    action = data.get(_DESKTOP_CLOSE_ACTION_KEY)
    if action in _DESKTOP_CLOSE_ACTIONS:
        return action
    return None


def _save_desktop_close_action(action: str | None) -> None:
    """Persist the remembered desktop close action."""
    settings_path = Path(_DESKTOP_SETTINGS_FILE).expanduser()
    try:
        if settings_path.is_file():
            data = json.loads(settings_path.read_text("utf-8"))
            if not isinstance(data, dict):
                data = {}
        else:
            data = {}
    except (json.JSONDecodeError, OSError, TypeError):
        data = {}

    if action in _DESKTOP_CLOSE_ACTIONS:
        data[_DESKTOP_CLOSE_ACTION_KEY] = action
    else:
        data.pop(_DESKTOP_CLOSE_ACTION_KEY, None)

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        "utf-8",
    )


class DesktopCloseController:
    """Control close behavior for the desktop webview window."""

    def __init__(self, window, shell_integration=None) -> None:
        self.window = window
        self.shell_integration = shell_integration
        self._frontend_ready = False
        self._allow_close = False
        self._prompt_open = False
        self._lock = threading.Lock()

        if self.shell_integration is not None:
            set_exit_requested = getattr(
                self.shell_integration,
                "set_exit_requested",
                None,
            )
            if callable(set_exit_requested):
                set_exit_requested(self.exit_from_tray)

    def on_loaded(self, *_args) -> None:
        """Mark the frontend as ready to receive close prompts."""
        self._frontend_ready = True
        if self.shell_integration is not None:
            try:
                self.shell_integration.initialize()
            except Exception as e:
                logger.warning("Failed to initialize desktop shell integration: %s", e)

    def on_closing(self, *_args) -> bool:
        """Intercept the native close event and apply remembered behavior."""
        with self._lock:
            if self._allow_close:
                self._prepare_for_exit()
                return True

        action = _load_desktop_close_action()
        if action == "exit":
            self._prepare_for_exit()
            return True
        if action == "minimize":
            self._minimize_window()
            return False

        with self._lock:
            if self._prompt_open:
                return False
            self._prompt_open = True

        if self._frontend_ready:
            try:
                self.window.run_js(
                    "window.dispatchEvent("
                    f"new CustomEvent('{_DESKTOP_CLOSE_EVENT_NAME}')"
                    ");",
                )
                return False
            except Exception as e:
                logger.warning(
                    "Failed to dispatch desktop close event to frontend: %s",
                    e,
                )

        self._set_prompt_open(False)
        self._show_native_fallback_prompt()
        return False

    def handle_close_choice(
        self,
        action: str,
        remember: bool = False,
    ) -> None:
        """Handle the close decision sent from the frontend dialog."""
        if action == "cancel":
            self._set_prompt_open(False)
            return

        if action not in _DESKTOP_CLOSE_ACTIONS:
            logger.warning("Unknown desktop close action: %s", action)
            self._set_prompt_open(False)
            return

        if remember:
            try:
                _save_desktop_close_action(action)
            except Exception as e:
                logger.warning(
                    "Failed to save desktop close action '%s': %s",
                    action,
                    e,
                )

        self._set_prompt_open(False)

        if action == "minimize":
            self._minimize_window()
            return

        self._prepare_for_exit()
        with self._lock:
            self._allow_close = True
        self.window.destroy()

    def exit_from_tray(self) -> None:
        """Close the app from the system tray without re-showing the prompt."""
        self._set_prompt_open(False)
        self._prepare_for_exit()
        with self._lock:
            self._allow_close = True

        if self.shell_integration is not None:
            request_window_close = getattr(
                self.shell_integration,
                "request_window_close",
                None,
            )
            if callable(request_window_close) and request_window_close():
                return
        self.window.destroy()

    def _prepare_for_exit(self) -> None:
        if self.shell_integration is None:
            return
        try:
            self.shell_integration.shutdown()
        except Exception as e:
            logger.warning("Failed to stop desktop shell integration: %s", e)

    def _set_prompt_open(self, open_: bool) -> None:
        with self._lock:
            self._prompt_open = open_

    def _minimize_window(self) -> None:
        if self.shell_integration is not None:
            try:
                if self.shell_integration.minimize_to_tray():
                    return
            except Exception as e:
                logger.warning(
                    "Desktop shell integration minimize failed: %s",
                    e,
                )

        minimize = getattr(self.window, "minimize", None)
        hide = getattr(self.window, "hide", None)

        if callable(minimize):
            minimize()
            return
        if callable(hide):
            hide()
            return

        logger.warning(
            "Desktop window does not support minimize/hide; closing instead",
        )
        with self._lock:
            self._allow_close = True
        self.window.destroy()

    def _show_native_fallback_prompt(self) -> None:
        """Fallback prompt when the frontend dialog cannot be shown."""
        try:
            minimize = self.window.create_confirmation_dialog(
                _DESKTOP_WINDOW_TITLE,
                "Click OK to minimize to background. "
                "Click Cancel to exit the app.",
            )
        except Exception as e:
            logger.warning("Native desktop close fallback dialog failed: %s", e)
            minimize = False

        if minimize:
            self._minimize_window()
            return

        with self._lock:
            self._allow_close = True
        self.window.destroy()


class WebViewAPI:
    """API exposed to the webview for handling external links."""

    def __init__(self) -> None:
        self._close_controller: DesktopCloseController | None = None

    def bind_close_controller(
        self,
        close_controller: DesktopCloseController,
    ) -> None:
        self._close_controller = close_controller

    def open_external_link(self, url: str) -> None:
        """Open URL in system's default browser."""
        if not url.startswith(("http://", "https://")):
            return
        webbrowser.open(url)

    def handle_close_choice(self, action: str, remember: bool = False) -> None:
        """Handle desktop close decision from the frontend dialog."""
        if self._close_controller is None:
            return
        threading.Thread(
            target=self._handle_close_choice_async,
            args=(action, bool(remember)),
            name="stategrid-close-choice",
            daemon=True,
        ).start()

    def _handle_close_choice_async(
        self,
        action: str,
        remember: bool,
    ) -> None:
        try:
            if self._close_controller is None:
                return
            self._close_controller.handle_close_choice(action, remember)
        except Exception as e:
            logger.warning(
                "Failed to handle desktop close choice '%s': %s",
                action,
                e,
            )


def _bind_desktop_window_events(
    window,
    *,
    shell_integration=None,
) -> None:
    """Bind non-intrusive desktop window events.

    We intentionally do not hook the native closing event so the desktop app
    follows the platform default close behavior.
    """
    events = getattr(window, "events", None)
    if events is None:
        return

    if shell_integration is not None:
        try:
            events.loaded += shell_integration.initialize
        except Exception as e:
            logger.warning(
                "Failed to register desktop loaded event: %s",
                e,
            )


def _find_free_port(host: str = "127.0.0.1") -> int:
    """Bind to port 0 and return the OS-assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        sock.listen(1)
        return sock.getsockname()[1]


def _wait_for_http(host: str, port: int, timeout_sec: float = 300.0) -> bool:
    """Return True when something accepts TCP on host:port."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect((host, port))
                return True
        except (OSError, socket.error):
            time.sleep(1)
    return False


def _stream_reader(in_stream, out_stream) -> None:
    """Read from in_stream line by line and write to out_stream.

    Used on Windows to prevent subprocess buffer blocking. Runs in a
    background thread to continuously drain the subprocess output.
    """
    try:
        for line in iter(in_stream.readline, ""):
            if not line:
                break
            out_stream.write(line)
            out_stream.flush()
    except Exception:
        pass
    finally:
        try:
            in_stream.close()
        except Exception:
            pass


@click.command("desktop")
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Bind host for the app server.",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "trace"],
        case_sensitive=False,
    ),
    show_default=True,
    help="Log level for the app process.",
)
def desktop_cmd(
    host: str,
    log_level: str,
) -> None:
    """Run the desktop app on an auto-selected free port in a webview window.

    Starts the FastAPI app in a subprocess on a free port, then opens a
    native webview window loading that URL. Use for a dedicated desktop
    window without conflicting with an existing app instance.
    """
    # Setup logger for desktop command (separate from backend subprocess)
    setup_logger(log_level)

    port = _find_free_port(host)
    url = f"http://{host}:{port}"
    click.echo(f"Starting StateGrid Desktop on {url} (port {port})")
    logger.info("Server subprocess starting...")

    env = os.environ.copy()
    env[LOG_LEVEL_ENV] = log_level

    if "SSL_CERT_FILE" in env:
        cert_file = env["SSL_CERT_FILE"]
        if os.path.exists(cert_file):
            logger.info(f"SSL certificate: {cert_file}")
        else:
            logger.warning(
                f"SSL_CERT_FILE set but not found: {cert_file}",
            )
    else:
        logger.warning("SSL_CERT_FILE not set on environment")

    is_windows = sys.platform == "win32"
    proc = None
    manually_terminated = (
        False  # Track if we intentionally terminated the process
    )
    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "qwenpaw",
                "app",
                "--host",
                host,
                "--port",
                str(port),
                "--log-level",
                log_level,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if is_windows else sys.stdout,
            stderr=subprocess.PIPE if is_windows else sys.stderr,
            env=env,
            bufsize=1,
            universal_newlines=True,
        )
        try:
            if is_windows:
                stdout_thread = threading.Thread(
                    target=_stream_reader,
                    args=(proc.stdout, sys.stdout),
                    daemon=True,
                )
                stderr_thread = threading.Thread(
                    target=_stream_reader,
                    args=(proc.stderr, sys.stderr),
                    daemon=True,
                )
                stdout_thread.start()
                stderr_thread.start()
            logger.info("Waiting for HTTP ready...")
            if _wait_for_http(host, port):
                logger.info("HTTP ready, creating webview window...")
                api = WebViewAPI()
                shell_integration = None
                if is_windows:
                    shell_integration = WindowsDesktopShellIntegration(
                        _DESKTOP_WINDOW_TITLE,
                        _find_desktop_icon_path(),
                    )
                window = webview.create_window(
                    _DESKTOP_WINDOW_TITLE,
                    url,
                    width=1280,
                    height=800,
                    text_select=True,
                    js_api=api,
                )
                _bind_desktop_window_events(
                    window,
                    shell_integration=shell_integration,
                )

                logger.info(
                    "Calling webview.start() (blocks until closed)...",
                )
                webview.start(
                    private_mode=False,
                )  # blocks until user closes the window
                logger.info("webview.start() returned (window closed).")
            else:
                logger.error("Server did not become ready in time.")
                click.echo(
                    "Server did not become ready in time; open manually: "
                    + url,
                    err=True,
                )
                try:
                    proc.wait()
                except KeyboardInterrupt:
                    pass  # will be handled in finally
        finally:
            # Ensure backend process is always cleaned up
            # Wrap all cleanup operations to handle race conditions:
            # - Process may exit between poll() and terminate()
            # - terminate()/kill() may raise ProcessLookupError/OSError
            # - We must not let cleanup exceptions mask the original error
            if proc and proc.poll() is None:  # process still running
                logger.info("Terminating backend server...")
                manually_terminated = (
                    True  # Mark that we're intentionally terminating
                )
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5.0)
                        logger.info("Backend server terminated cleanly.")
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "Backend did not exit in 5s, force killing...",
                        )
                        try:
                            proc.kill()
                            proc.wait()
                            logger.info("Backend server force killed.")
                        except (ProcessLookupError, OSError) as e:
                            # Process already exited, which is fine
                            logger.debug(
                                f"kill() raised {e.__class__.__name__} "
                                f"(process already exited)",
                            )
                except (ProcessLookupError, OSError) as e:
                    # Process already exited between poll() and terminate()
                    logger.debug(
                        f"terminate() raised {e.__class__.__name__} "
                        f"(process already exited)",
                    )
            elif proc:
                logger.info(
                    f"Backend already exited with code {proc.returncode}",
                )

        # Only report errors if process exited unexpectedly
        # (not manually terminated)
        # On Windows, terminate() doesn't use signals so exit codes vary
        # (1, 259, etc.)
        # On Unix/Linux/macOS, terminate() sends SIGTERM (exit code -15)
        # Using a flag is more reliable than checking specific exit codes
        if proc and proc.returncode != 0 and not manually_terminated:
            logger.error(
                f"Backend process exited unexpectedly with code "
                f"{proc.returncode}",
            )
            # Follow POSIX convention for exit codes:
            # - Negative (signal): 128 + signal_number
            # - Positive (normal): use as-is
            # Example: -15 (SIGTERM) -> 143 (128+15), -11 (SIGSEGV) ->
            # 139 (128+11)
            if proc.returncode < 0:
                sys.exit(128 + abs(proc.returncode))
            else:
                sys.exit(proc.returncode or 1)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt in main, cleaning up...")
        raise
    except Exception as e:
        logger.error(f"Exception: {e!r}")
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        raise
