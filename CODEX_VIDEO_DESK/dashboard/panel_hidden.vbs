' PhoneSpot panel - fully hidden launcher (no console window at all).
' Runs 00_PHONE_SPOT_PANEL.bat with a hidden window so nothing shows in the taskbar.
' The server itself is started with pythonw.exe (console-less) by start_hidden.ps1,
' so once this returns there is no lingering cmd window.
Option Explicit
Dim fso, sh, deskDir, batPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")
' ScriptFullName = ...\CODEX_VIDEO_DESK\dashboard\panel_hidden.vbs
' parent(parent(...)) = ...\CODEX_VIDEO_DESK
deskDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
batPath = deskDir & "\00_PHONE_SPOT_PANEL.bat"
If Not fso.FileExists(batPath) Then
  WScript.Quit 1
End If
' Run hidden (0), do not wait (False).
sh.Run """" & batPath & """", 0, False
