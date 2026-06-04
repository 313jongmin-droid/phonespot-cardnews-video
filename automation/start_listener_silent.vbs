' Silent launcher for telegram_listener.bat
' Runs without showing a cmd window.
Set WshShell = CreateObject("WScript.Shell")
strPath = WScript.ScriptFullName
strDir = Left(strPath, InStrRev(strPath, "\"))
WshShell.Run """" & strDir & "start_telegram_listener.bat""", 0, False
Set WshShell = Nothing
