@echo off
chcp 65001 >nul
setlocal
title PhoneSpot - 일러스트 라이브러리 공유 동기화
set "ROOT=%~dp0.."
set "PY=%ROOT%\.phonespot_runtime\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  일러스트 라이브러리 공유 동기화 (양방향 추가병합, 비파괴)
echo ============================================================
echo  공유 허브 경로 지정:
echo    - 환경변수 PHONESPOT_LIBRARY_SHARE=^<공유폴더^>  또는
echo    - 파일 한 줄:  shorts\config\library_share_path.txt
echo.
echo  미리보기만 하려면 이 창에 인자로 --dry-run 을 줄 수 있습니다.
echo.
"%PY%" "%ROOT%\shorts\scripts\codex_library_sync.py" %*
echo.
pause
