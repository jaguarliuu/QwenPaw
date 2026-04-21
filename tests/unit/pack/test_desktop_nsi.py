# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


INSTALLER_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "pack" / "desktop.nsi"
)
UNINSTALL_REG_PATH = (
    r'Software\Microsoft\Windows\CurrentVersion\Uninstall\StateGridDesktop'
)


def _read_installer_script() -> str:
    return INSTALLER_SCRIPT.read_text(encoding="utf-8")


def test_desktop_installer_registers_windows_apps_uninstall_entry():
    content = _read_installer_script()

    assert (
        f'WriteRegStr HKCU "{UNINSTALL_REG_PATH}" "DisplayName" '
        '"StateGrid Desktop"' in content
    )
    assert (
        f'WriteRegStr HKCU "{UNINSTALL_REG_PATH}" "UninstallString" '
        '"$\\"$INSTDIR\\Uninstall.exe$\\""' in content
    )
    assert (
        f'WriteRegStr HKCU "{UNINSTALL_REG_PATH}" "DisplayVersion" '
        '"${QWENPAW_VERSION}"' in content
    )


def test_desktop_uninstaller_removes_windows_apps_entry():
    content = _read_installer_script()

    assert f'DeleteRegKey HKCU "{UNINSTALL_REG_PATH}"' in content
