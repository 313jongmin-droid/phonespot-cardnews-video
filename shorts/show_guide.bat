@echo off
chcp 65001 >nul
title 학습 가이드 — 영상 만들기 전 확인
cd /d C:\Users\di898\Documents\phonespot_cardnews

set GUIDE=shorts\_state\content_guide.md

echo ============================================
echo  폰스팟 유튜브 학습 가이드
echo  영상 만들기 시작 전 위 가이드 검토
echo ============================================
echo.

if not exist "%GUIDE%" (
    echo  가이드 파일 없음: %GUIDE%
    echo.
    echo  먼저 갱신하세요:
    echo    ads\integrations\youtube\run_youtube_sync.bat
    echo.
    pause
    exit /b 1
)

type "%GUIDE%"

echo.
echo ============================================
echo  최근 갱신 시각이 오래됐으면 먼저 sync:
echo    ads\integrations\youtube\run_youtube_sync.bat
echo.
echo  영상 만들기 진행하려면 아무 키나
echo ============================================
pause >nul
