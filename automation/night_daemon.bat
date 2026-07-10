@echo off
REM Windows Task Scheduler용 야간 daemon 실행 wrapper
REM 매일 02:00 실행 권장. 로그는 logs\night_daemon_log.txt에 누적.

cd /d %~dp0
set PYTHONIOENCODING=utf-8

echo. >> logs\night_daemon_log.txt
echo === night_daemon start %date% %time% >> logs\night_daemon_log.txt

where py >nul 2>&1
if errorlevel 1 (
    python scripts\night_daemon.py >> logs\night_daemon_log.txt 2>&1
) else (
    py -3 scripts\night_daemon.py >> logs\night_daemon_log.txt 2>&1
)

echo === night_daemon end %date% %time% >> logs\night_daemon_log.txt
