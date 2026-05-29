; OmniCon NSIS Installer Script
; Generates a Windows installer for the OmniCon Universal File Converter

!include "MUI2.nsh"
!include "FileFunc.nsh"

; ---- General Settings ----
Name "OmniCon"
OutFile "dist\OmniConSetup.exe"
InstallDir "$PROGRAMFILES64\OmniCon"
InstallDirRegKey HKLM "Software\OmniCon" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
SetCompressorDictSize 64

; ---- Version Info ----
!define PRODUCT_NAME "OmniCon"
!define PRODUCT_VERSION "0.1.0"
!define PRODUCT_PUBLISHER "Chenglin Qiu (SHC - Super Han Chinese)"
!define PRODUCT_WEB_SITE "https://github.com/omnicon"

VIProductVersion "0.1.0.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "FileDescription" "OmniCon Universal File Converter Installer"
VIAddVersionKey "LegalCopyright" "Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved."
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"

; ---- MUI Settings ----
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Welcome to OmniCon Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will install OmniCon — Universal File Converter on your computer.$\r$\n$\r$\nOmniCon converts between PDF, Word, PowerPoint, Excel, images, HTML, Markdown, and more.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\OmniCon.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch OmniCon"

; ---- Pages ----
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ---- Installer Section ----
Section "OmniCon (required)" SecMain
    SectionIn RO

    SetOutPath "$INSTDIR"

    ; Copy all files from dist/OmniCon
    File /r "dist\OmniCon\*.*"

    ; Write registry keys
    WriteRegStr HKLM "Software\OmniCon" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\OmniCon" "Version" "${PRODUCT_VERSION}"

    ; Add/Remove Programs entry
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "DisplayIcon" "$INSTDIR\OmniCon.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "NoRepair" 1

    ; Calculate installed size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon" \
        "EstimatedSize" $0

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Start menu shortcuts
    CreateDirectory "$SMPROGRAMS\OmniCon"
    CreateShortcut "$SMPROGRAMS\OmniCon\OmniCon.lnk" "$INSTDIR\OmniCon.exe"
    CreateShortcut "$SMPROGRAMS\OmniCon\Uninstall OmniCon.lnk" "$INSTDIR\Uninstall.exe"

    ; Desktop shortcut
    CreateShortcut "$DESKTOP\OmniCon.lnk" "$INSTDIR\OmniCon.exe"
SectionEnd

; ---- Uninstaller Section ----
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\OmniCon.lnk"
    RMDir /r "$SMPROGRAMS\OmniCon"

    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OmniCon"
    DeleteRegKey HKLM "Software\OmniCon"
SectionEnd
