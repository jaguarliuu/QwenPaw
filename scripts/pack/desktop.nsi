; StateGrid Desktop NSIS installer. Run makensis from repo root after
; building dist/win-unpacked (see scripts/pack/build_win.ps1).
; Usage: makensis /DQWENPAW_VERSION=1.2.3 /DOUTPUT_EXE=dist\StateGrid-Desktop-Setup-1.2.3.exe scripts\pack\desktop.nsi

!include "MUI2.nsh"
!define MUI_ABORTWARNING
; Use custom icon from unpacked env (copied by build_win.ps1)
!define MUI_ICON "${UNPACKED}\icon.ico"
!define MUI_UNICON "${UNPACKED}\icon.ico"

!ifndef QWENPAW_VERSION
  !define QWENPAW_VERSION "0.0.0"
!endif
!ifndef OUTPUT_EXE
  !define OUTPUT_EXE "dist\StateGrid-Desktop-Setup-${QWENPAW_VERSION}.exe"
!endif

Name "StateGrid Desktop"
OutFile "${OUTPUT_EXE}"
InstallDir "$LOCALAPPDATA\StateGridDesktop"
InstallDirRegKey HKCU "Software\StateGridDesktop" "InstallPath"
RequestExecutionLevel user

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

; Pass /DUNPACKED=full_path from build_win.ps1 so path works when cwd != repo root
!ifndef UNPACKED
  !define UNPACKED "dist\win-unpacked"
!endif

Section "StateGrid Desktop" SEC01
  SetOutPath "$INSTDIR"
  File /r "${UNPACKED}\*.*"
  WriteRegStr HKCU "Software\StateGridDesktop" "InstallPath" "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Main shortcut - uses VBS to hide console window
  CreateShortcut "$SMPROGRAMS\StateGrid Desktop.lnk" "$INSTDIR\StateGrid Desktop.vbs" "" "$INSTDIR\icon.ico" 0
  CreateShortcut "$DESKTOP\StateGrid Desktop.lnk" "$INSTDIR\StateGrid Desktop.vbs" "" "$INSTDIR\icon.ico" 0
  
  ; Debug shortcut - shows console window for troubleshooting
  CreateShortcut "$SMPROGRAMS\StateGrid Desktop (Debug).lnk" "$INSTDIR\StateGrid Desktop (Debug).bat" "" "$INSTDIR\icon.ico" 0
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\StateGrid Desktop.lnk"
  Delete "$SMPROGRAMS\StateGrid Desktop (Debug).lnk"
  Delete "$DESKTOP\StateGrid Desktop.lnk"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\StateGridDesktop"
SectionEnd
