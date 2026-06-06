@echo off
chcp 65001 >nul
setlocal
title PhoneSpot - 일러스트 라이브러리 백업
set "ROOT=%~dp0.."
set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  일러스트 라이브러리 백업 (타임스탬프 스냅샷, 회전보관)
echo ============================================================
echo  보관 위치: 환경변수 PHONESPOT_LIBRARY_BACKUP (없으면 저장소 옆 phonespot_library_backups)
echo  보관 개수: PHONESPOT_LIBRARY_BACKUP_KEEP (기본 10)
echo  허브 경로(PHONESPOT_LIBRARY_SHARE)가 설정돼 있으면 허브도 함께 백업합니다.
echo.
"%PY%" "%ROOT%\shorts\scripts\codex_library_backup.py"
echo.
pause
