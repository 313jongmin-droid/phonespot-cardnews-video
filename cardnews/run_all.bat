@echo off
cd /d %~dp0
set PYTHONIOENCODING=utf-8

echo === run_all start %date% %time% > run_all_log.txt
echo. >> run_all_log.txt

where py >nul 2>&1
if errorlevel 1 (
    echo [using python] >> run_all_log.txt
    python -u scripts\run_all.py >> run_all_log.txt 2>&1
) else (
    echo [using py] >> run_all_log.txt
    py -3 -u scripts\run_all.py >> run_all_log.txt 2>&1
)

echo. >> run_all_log.txt
echo === run_all end %date% %time% >> run_all_log.txt

type run_all_log.txt
pause
