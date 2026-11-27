; AudioTranscriber installer (NSIS 3, Modern UI 2) - Install / Repair / Uninstall
; Build:  makensis AudioTranscriber.nsi      ->  AudioTranscriber_Setup.exe
;
; The installer does the whole setup itself, step by step with a visible log (no PowerShell anywhere):
; program files, Python, packages, CUDA, Ollama + translator model, Whisper + voice models, shortcuts.
; It keeps a copy of itself as Setup.exe in the app folder: AudioTranscriber.exe opens it for Repair.
;   AudioTranscriber_Setup.exe /REPAIR   repair the installed copy directly

Unicode true
ManifestDPIAware true
RequestExecutionLevel user
SetCompressor /SOLID lzma

!define APP        "AudioTranscriber"
!define VERSION    "1.6.0"
!define PUBLISHER  "Gabrydl"
!define EXE        "AudioTranscriber.exe"
!define REGKEY     "Software\AudioTranscriber"
!define UNINSTKEY  "Software\Microsoft\Windows\CurrentVersion\Uninstall\AudioTranscriber"
!define RUNKEY     "Software\Microsoft\Windows\CurrentVersion\Run"
!define SRC        "..\payload"
!define PYVER      "3.11.9"

Name "${APP}"
OutFile "AudioTranscriber_Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP}"
BrandingText "${APP} ${VERSION}"
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "${APP}"
VIAddVersionKey "FileDescription" "${APP} Setup"
VIAddVersionKey "CompanyName" "${PUBLISHER}"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2026 ${PUBLISHER}"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "WinMessages.nsh"
!include "nsDialogs.nsh"

!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "welcome.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "welcome.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "header.bmp"
!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING

Var Repair        ; 1 = repair the installed copy (no welcome / folder pages)
Var Installed     ; folder of an existing install, or ""
Var Drive         ; drive of $INSTDIR, e.g. G:
Var Py            ; Python used to create the app's environment
Var PyArgs
Var VPy           ; the app's own python.exe
Var RadioRepair
Var RadioRemove
Var BestDrive
Var BestFree
Var LangCode      ; interface language picked here, handed to the app (lang.txt)
Var LangAsked     ; 1 = the language was picked in this run

; ---------------------------------------------------------------- pages
!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipIfRepair
!define MUI_WELCOMEPAGE_TITLE "$(WELCOME_TITLE)"
!define MUI_WELCOMEPAGE_TEXT "$(WELCOME_TEXT)"
!insertmacro MUI_PAGE_WELCOME

Page custom MaintenancePage MaintenanceLeave

!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipIfRepair
!define MUI_DIRECTORYPAGE_TEXT_TOP "$(DIR_TEXT)"
!insertmacro MUI_PAGE_DIRECTORY

!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "$(FIN_HEAD)"
!define MUI_INSTFILESPAGE_FINISHHEADER_SUBTEXT "$(FIN_SUB)"
!define MUI_INSTFILESPAGE_ABORTHEADER_TEXT "$(ABORT_HEAD)"
!define MUI_INSTFILESPAGE_ABORTHEADER_SUBTEXT "$(ABORT_SUB)"
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_TITLE "$(FIN_TITLE)"
!define MUI_FINISHPAGE_TEXT "$(FIN_TEXT)"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "$(RUN_TEXT)"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\readme\README_$LangCode.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "$(README_TEXT)"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; interface languages: the first screen asks, with the Windows language already selected
!define MUI_LANGDLL_ALLLANGUAGES
!define MUI_LANGDLL_WINDOWTITLE "${APP}"
!define MUI_LANGDLL_INFO "Language / Lingua / Idioma / Sprache / Langue / Wika / Pinulongan / Jazyk / Język"
!insertmacro MUI_LANGUAGEEX "lang" "English"
!insertmacro MUI_LANGUAGEEX "lang" "Italian"
!insertmacro MUI_LANGUAGEEX "lang" "PortugueseBR"
!insertmacro MUI_LANGUAGEEX "lang" "Portuguese"
!insertmacro MUI_LANGUAGEEX "lang" "Spanish"
!insertmacro MUI_LANGUAGEEX "lang" "SpanishLatAm"
!insertmacro MUI_LANGUAGEEX "lang" "German"
!insertmacro MUI_LANGUAGEEX "lang" "French"
!insertmacro MUI_LANGUAGEEX "lang" "Tagalog"
!insertmacro MUI_LANGUAGEEX "lang" "Cebuano"
!insertmacro MUI_LANGUAGEEX "lang" "Czech"
!insertmacro MUI_LANGUAGEEX "lang" "Polish"
!insertmacro MUI_RESERVEFILE_LANGDLL
!include "strings.nsh"

; ---------------------------------------------------------------- init
; GetDrives callback: the fixed drive (not the Windows drive) with the most free space
Function PickDrive
    StrCpy $R1 $WINDIR 3
    ${If} $9 == $R1
        Push $0
        Return
    ${EndIf}
    ${DriveSpace} $9 "/D=F /S=G" $R0
    ${If} $R0 > $BestFree
        StrCpy $BestFree $R0
        StrCpy $BestDrive $9
    ${EndIf}
    Push $0
FunctionEnd

Function .onInit
    StrCpy $Repair 0
    StrCpy $Installed ""
    ReadRegStr $0 HKCU "${REGKEY}" "InstallDir"
    ${If} $0 != ""
    ${AndIf} ${FileExists} "$0\${EXE}"
        StrCpy $Installed $0
        StrCpy $INSTDIR $0
    ${EndIf}

    ${GetParameters} $1
    ClearErrors
    ${GetOptions} $1 "/REPAIR" $2
    ${IfNot} ${Errors}
        ${If} $Installed == ""
            ; Setup.exe inside the app folder: repair that folder
            ${GetParent} "$EXEPATH" $3
            ${If} ${FileExists} "$3\${EXE}"
                StrCpy $Installed $3
                StrCpy $INSTDIR $3
            ${EndIf}
        ${EndIf}
        ${If} $Installed != ""
            StrCpy $Repair 1
        ${EndIf}
    ${EndIf}

    ; language: Repair keeps the one picked at install, otherwise ask (Windows language preselected)
    ReadRegStr $0 HKCU "${REGKEY}" "Language"
    ${If} $0 != ""
        StrCpy $LANGUAGE $0
    ${Else}
        ; Spanish outside Spain -> Latin American Spanish (NSIS would pick Spain's)
        System::Call 'kernel32::GetUserDefaultUILanguage() i .r1'
        IntOp $2 $1 & 0x3FF
        ${If} $2 == 0x0A
        ${AndIf} $1 != 1034
        ${AndIf} $1 != 3082
            StrCpy $LANGUAGE 2058
        ${EndIf}
    ${EndIf}
    StrCpy $LangAsked 0
    ${If} $Repair != 1
        !insertmacro MUI_LANGDLL_DISPLAY
        StrCpy $LangAsked 1
    ${EndIf}
    StrCpy $LangCode "$(LANG_CODE)"

    ${If} $Installed == ""
        ; keep the big downloads off the Windows drive when another drive has room (15 GB+)
        StrCpy $BestFree 0
        StrCpy $BestDrive ""
        ${GetDrives} "HDD" "PickDrive"
        ${If} $BestDrive != ""
        ${AndIf} $BestFree >= 15
            StrCpy $INSTDIR "$BestDrive${APP}"
        ${EndIf}
    ${EndIf}
FunctionEnd

Function un.onInit
    ReadRegStr $0 HKCU "${REGKEY}" "Language"
    ${If} $0 != ""
        StrCpy $LANGUAGE $0
    ${EndIf}
FunctionEnd

Function .onVerifyInstDir
    StrLen $0 $INSTDIR
    ${If} $0 <= 3          ; never straight into the root of a drive
        Abort
    ${EndIf}
FunctionEnd

Function SkipIfRepair
    ${If} $Repair == 1
        Abort
    ${EndIf}
    ${If} $Installed != ""         ; folder page: keep the existing folder
        Abort
    ${EndIf}
FunctionEnd

; ---------------------------------------------------------------- maintenance page (already installed)
Function MaintenancePage
    ${If} $Installed == ""
    ${OrIf} $Repair == 1
        Abort
    ${EndIf}
    !insertmacro MUI_HEADER_TEXT "$(MAINT_TITLE)" "$(MAINT_SUB)"
    nsDialogs::Create 1018
    Pop $0
    ${NSD_CreateLabel} 0 0 100% 24u "$(CHOOSE)"
    Pop $0
    ${NSD_CreateRadioButton} 10u 28u 100% 12u "$(REPAIR)"
    Pop $RadioRepair
    ${NSD_CreateLabel} 24u 41u 90% 20u "$(REPAIR_DESC)"
    Pop $0
    ${NSD_CreateRadioButton} 10u 70u 100% 12u "$(UNINSTALL)"
    Pop $RadioRemove
    ${NSD_CreateLabel} 24u 83u 90% 20u "$(UNINSTALL_DESC)"
    Pop $0
    ${NSD_Check} $RadioRepair
    nsDialogs::Show
FunctionEnd

Function MaintenanceLeave
    ${NSD_GetState} $RadioRemove $0
    ${If} $0 == ${BST_CHECKED}
        Exec '"$Installed\Uninstall.exe"'
        Quit
    ${EndIf}
    StrCpy $Repair 1
FunctionEnd

; ---------------------------------------------------------------- helpers
; Is AudioTranscriber running? (its single-instance pipe exists)
!macro APP_RUNNING_CHECK UN
Function ${UN}WaitAppClosed
    ReadEnvStr $0 USERNAME
    check:
    System::Call 'kernel32::WaitNamedPipeW(w "\\.\pipe\AudioTranscriber-$0", i 1) i .r1 ?e'
    Pop $2
    ${If} $1 != 0
    ${OrIf} $2 == 121
        MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(RUNNING)" /SD IDCANCEL IDRETRY check
        Abort
    ${EndIf}
FunctionEnd
!macroend
!insertmacro APP_RUNNING_CHECK ""
!insertmacro APP_RUNNING_CHECK "un."

!ifndef LVM_GETITEMCOUNT
!define LVM_GETITEMCOUNT 0x1004
!endif
!ifndef LVM_GETITEMTEXTW
!define LVM_GETITEMTEXTW 0x1073
!endif
; Save the details list to a file. Usage: Push "file" / Call DumpLog
Function DumpLog
    Exch $5
    Push $0
    Push $1
    Push $2
    Push $3
    Push $4
    Push $6
    FindWindow $0 "#32770" "" $HWNDPARENT
    GetDlgItem $0 $0 1016
    StrCmp $0 0 done
    FileOpen $5 $5 "w"
    StrCmp $5 "" done
    SendMessage $0 ${LVM_GETITEMCOUNT} 0 0 $6
    System::Call '*(&t${NSIS_MAX_STRLEN})p.r3'
    System::Call "*(i, i, i, i, i, p, i, i, i) p (0, 0, 0, 0, 0, r3, ${NSIS_MAX_STRLEN}) .r1"
    StrCpy $2 0
    loop:
        StrCmp $2 $6 close
        System::Call "User32::SendMessage(p, i, p, p) p ($0, ${LVM_GETITEMTEXTW}, $2, r1)"
        System::Call "*$3(&t${NSIS_MAX_STRLEN} .r4)"
        FileWrite $5 "$4$\r$\n"
        IntOp $2 $2 + 1
        Goto loop
    close:
    FileClose $5
    System::Free $1
    System::Free $3
    done:
    Pop $6
    Pop $4
    Pop $3
    Pop $2
    Pop $1
    Pop $0
    Pop $5
FunctionEnd

; Stop with a clear message. The program files stay, so Repair can continue later.
!macro FAIL MSG
    DetailPrint ""
    DetailPrint "$(ERROR) ${MSG}"
    SetDetailsView show
    Push "$INSTDIR\setup.log"
    Call DumpLog
    MessageBox MB_OK|MB_ICONSTOP "${MSG}$\r$\n$\r$\n$(FAIL_TAIL)" /SD IDOK
    Abort
!macroend

; Run one step of app\setup_tasks.py with the app's Python
!macro TASK NAME MSG
    nsExec::ExecToLog '"$VPy" -u "$INSTDIR\app\setup_tasks.py" ${NAME} "$INSTDIR"'
    Pop $0
    ${If} $0 != 0
        !insertmacro FAIL "${MSG}"
    ${EndIf}
!macroend

; Try a Python: sets $Py / $PyArgs when it is 3.10 - 3.13 with venv
!macro TRY_PY EXE ARGS
    ${If} $Py == ""
        nsExec::ExecToStack '"${EXE}" ${ARGS} -c "import sys, venv, ensurepip; print(sys.version_info[0]*100 + sys.version_info[1])"'
        Pop $0
        Pop $1
        StrCpy $1 $1 3
        ${If} $0 == 0
        ${AndIf} $1 >= 310
        ${AndIf} $1 <= 313
            StrCpy $Py "${EXE}"
            StrCpy $PyArgs "${ARGS}"
        ${EndIf}
    ${EndIf}
!macroend

; ---------------------------------------------------------------- install / repair
Section "Install"
    AddSize 8800000
    SetDetailsView show
    Call WaitAppClosed
    StrCpy $Drive $INSTDIR 2
    StrCpy $VPy "$INSTDIR\.venv\Scripts\python.exe"
    DetailPrint "${APP} ${VERSION} - $INSTDIR"

    ; ------------------------------------------------ 1. program files
    DetailPrint ""
    DetailPrint "$(S1)"
    SetOutPath "$INSTDIR"
    File "${SRC}\${EXE}"
    File "${SRC}\README.txt"
    File "${SRC}\requirements.txt"
    SetOutPath "$INSTDIR\app"
    RMDir /r "$INSTDIR\app\__pycache__"
    File "${SRC}\app\*.py"
    SetOutPath "$INSTDIR\app\locales"
    File "${SRC}\app\locales\*.txt"
    SetOutPath "$INSTDIR\readme"
    File "${SRC}\readme\*.txt"
    SetOutPath "$INSTDIR\assets"
    File "${SRC}\assets\*.*"
    SetOutPath "$INSTDIR"
    Delete "$INSTDIR\*.bat"
    Delete "$INSTDIR\setup.ps1"
    ${If} "$EXEPATH" != "$INSTDIR\Setup.exe"
        CopyFiles /SILENT "$EXEPATH" "$INSTDIR\Setup.exe"
    ${EndIf}
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    CreateShortcut "$SMPROGRAMS\${APP}.lnk" "$INSTDIR\${EXE}" "" "$INSTDIR\${EXE}" 0 SW_SHOWNORMAL "" "$(SHORTCUT)"
    CreateShortcut "$DESKTOP\${APP}.lnk" "$INSTDIR\${EXE}" "" "$INSTDIR\${EXE}" 0 SW_SHOWNORMAL "" "$(SHORTCUT)"
    ReadRegStr $0 HKCU "${RUNKEY}" "${APP}"
    ${If} $0 != ""
        WriteRegStr HKCU "${RUNKEY}" "${APP}" '"$INSTDIR\${EXE}" --tray'
    ${EndIf}
    WriteRegStr HKCU "${REGKEY}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "${REGKEY}" "Language" "$LANGUAGE"
    ${If} $LangAsked == 1                   ; picked in this setup: the app opens in that language
        FileOpen $0 "$INSTDIR\lang.txt" w
        FileWrite $0 "$LangCode"
        FileClose $0
    ${EndIf}
    WriteRegStr HKCU "${UNINSTKEY}" "DisplayName" "${APP}"
    WriteRegStr HKCU "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKCU "${UNINSTKEY}" "Publisher" "${PUBLISHER}"
    WriteRegStr HKCU "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\${EXE},0"
    WriteRegStr HKCU "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKCU "${UNINSTKEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegStr HKCU "${UNINSTKEY}" "ModifyPath" '"$INSTDIR\Setup.exe" /REPAIR'
    WriteRegDWORD HKCU "${UNINSTKEY}" "NoRepair" 1
    WriteRegDWORD HKCU "${UNINSTKEY}" "EstimatedSize" 8800000
    DetailPrint "$(DONE)"

    ; environment for every program started below
    System::Call 'kernel32::SetEnvironmentVariableW(w "PIP_CACHE_DIR", w "$Drive\pip_cache")'
    System::Call 'kernel32::SetEnvironmentVariableW(w "PIP_DISABLE_PIP_VERSION_CHECK", w "1")'
    System::Call 'kernel32::SetEnvironmentVariableW(w "PYTHONIOENCODING", w "utf-8")'
    System::Call 'kernel32::SetEnvironmentVariableW(w "PYTHONUTF8", w "1")'
    System::Call 'kernel32::SetEnvironmentVariableW(w "PYTHONNOUSERSITE", w "1")'

    ; ------------------------------------------------ 2. Python
    DetailPrint ""
    DetailPrint "$(S2)"
    StrCpy $Py ""
    StrCpy $PyArgs ""
    !insertmacro TRY_PY "$VPy" ""
    ${If} $Py != ""
        DetailPrint "$(PY_OK)"
    ${Else}
        !insertmacro TRY_PY "$Drive\py311\python.exe" ""
        !insertmacro TRY_PY "$Drive\Python311\python.exe" ""
        !insertmacro TRY_PY "G:\py311\python.exe" ""
        !insertmacro TRY_PY "$LOCALAPPDATA\Programs\Python\Python311\python.exe" ""
        !insertmacro TRY_PY "$LOCALAPPDATA\Programs\Python\Python312\python.exe" ""
        !insertmacro TRY_PY "$LOCALAPPDATA\Programs\Python\Python313\python.exe" ""
        !insertmacro TRY_PY "$LOCALAPPDATA\Programs\Python\Python310\python.exe" ""
        !insertmacro TRY_PY "$WINDIR\py.exe" "-3.11"
        !insertmacro TRY_PY "$WINDIR\py.exe" "-3.12"
        ${If} $Py == ""
            DetailPrint "$(PY_NONE)"
            nsExec::ExecToLog '"$SYSDIR\curl.exe" -L --fail -s -S -o "$TEMP\python-${PYVER}-amd64.exe" "https://www.python.org/ftp/python/${PYVER}/python-${PYVER}-amd64.exe"'
            Pop $0
            ${If} $0 != 0
                !insertmacro FAIL "$(F_PYDL)"
            ${EndIf}
            ExecWait '"$TEMP\python-${PYVER}-amd64.exe" /quiet InstallAllUsers=0 TargetDir="$Drive\Python311" Include_launcher=0 PrependPath=0 Shortcuts=0 Include_test=0 Include_doc=0' $0
            Delete "$TEMP\python-${PYVER}-amd64.exe"
            !insertmacro TRY_PY "$Drive\Python311\python.exe" ""
            ${If} $Py == ""
                !insertmacro FAIL "$(F_PYINST)"
            ${EndIf}
        ${EndIf}
        DetailPrint "$(PY_USE) $Py $PyArgs"
        DetailPrint "$(PY_VENV)"
        nsExec::ExecToLog '"$Py" $PyArgs -m venv --clear "$INSTDIR\.venv"'
        Pop $0
        ${If} $0 != 0
            !insertmacro FAIL "$(F_VENV)"
        ${EndIf}
    ${EndIf}

    ; ------------------------------------------------ 3. earlier copy
    DetailPrint ""
    DetailPrint "$(S3)"
    !insertmacro TASK "reuse" "$(F_REUSE)"

    ; ------------------------------------------------ 4. packages
    DetailPrint ""
    DetailPrint "$(S4)"
    nsExec::ExecToLog '"$VPy" -m pip install --upgrade --progress-bar off pip wheel'
    Pop $0
    nsExec::ExecToLog '"$VPy" -m pip install --progress-bar off -r "$INSTDIR\requirements.txt"'
    Pop $0
    ${If} $0 != 0
        !insertmacro FAIL "$(F_PIP)"
    ${EndIf}

    ; ------------------------------------------------ 5. GPU
    DetailPrint ""
    DetailPrint "$(S5)"
    !insertmacro TASK "cuda" "$(F_CUDA)"

    ; ------------------------------------------------ 6. translator
    DetailPrint ""
    DetailPrint "$(S6)"
    !insertmacro TASK "ollama" "$(F_OLLAMA)"

    ; ------------------------------------------------ 7. models
    DetailPrint ""
    DetailPrint "$(S7)"
    !insertmacro TASK "models" "$(F_MODELS)"

    ; ------------------------------------------------ 8. check
    DetailPrint ""
    DetailPrint "$(S8)"
    !insertmacro TASK "check" "$(F_CHECK)"

    DetailPrint ""
    DetailPrint "$(READY)"
    Push "$INSTDIR\setup.log"
    Call DumpLog
SectionEnd

; ---------------------------------------------------------------- uninstall
Section "Uninstall"
    Call un.WaitAppClosed

    Delete "$INSTDIR\${EXE}"
    Delete "$INSTDIR\Setup.exe"
    Delete "$INSTDIR\README.txt"
    Delete "$INSTDIR\requirements.txt"
    Delete "$INSTDIR\setup.log"
    RMDir /r "$INSTDIR\app"
    RMDir /r "$INSTDIR\assets"
    RMDir /r "$INSTDIR\readme"
    Delete "$INSTDIR\lang.txt"

    Delete "$SMPROGRAMS\${APP}.lnk"
    Delete "$DESKTOP\${APP}.lnk"
    DeleteRegValue HKCU "${RUNKEY}" "${APP}"
    DeleteRegKey HKCU "${UNINSTKEY}"
    DeleteRegKey HKCU "${REGKEY}"

    MessageBox MB_YESNO|MB_ICONQUESTION "$(UN_ASK)" /SD IDNO IDNO keep
        RMDir /r "$INSTDIR\.venv"
        RMDir /r "$INSTDIR\models"
        RMDir /r "$INSTDIR\ollama_models"
        RMDir /r "$INSTDIR\transcripts"
        RMDir /r "$INSTDIR\gpu"
        Delete "$INSTDIR\settings.json"
        Delete "$INSTDIR\speakers.json"
        Delete "$INSTDIR\speakers_before_discord.json"
        Delete "$INSTDIR\discord_token.json"
        Delete "$INSTDIR\audiotranscriber.log"
        ReadRegStr $0 HKCU "Environment" "OLLAMA_MODELS"
        ${If} $0 == "$INSTDIR\ollama_models"
            DeleteRegValue HKCU "Environment" "OLLAMA_MODELS"
            SendMessage ${HWND_BROADCAST} ${WM_WININICHANGE} 0 "STR:Environment" /TIMEOUT=2000
        ${EndIf}
    keep:
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"
SectionEnd
