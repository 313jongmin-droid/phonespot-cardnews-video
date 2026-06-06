@echo off
chcp 65001 >nul
setlocal
title PhoneSpot - 라이브러리 중복 정리
set "ROOT=%~dp0.."
set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  라이브러리 중복 정리
echo ============================================================
echo  인자 없이 = 리포트만(읽기전용, 안전).
echo  실제 정리(삭제+병합) = 이 창에 인자 --apply 를 주세요.
echo  임계값 조절: set PHONESPOT_DEDUP_SIM=0.90  (낮을수록 더 많이 묶음)
echo  * --apply 전에 라이브러리 공유 동기화로 백업해 두길 권장.
echo.
"%PY%" "%ROOT%\shorts\scripts\codex_library_dedup.py" %*
echo.
pause
