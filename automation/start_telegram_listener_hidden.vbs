' run telegram listener hidden (no console window). log: automation\_state\listener_log.txt
Set sh = CreateObject("WScript.Shell")
sh.Run """C:\backup\phonespot_cardnews\automation\start_telegram_listener.bat""", 0, False
