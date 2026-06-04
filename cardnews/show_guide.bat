@echo off
chcp 65001 >nul
title 학습 가이드 — 카드뉴스 시작 전 확인
cd /d C:\Users\di898\Documents\phonespot_cardnews

set GUIDE=cardnews\_state\content_guide.md

echo ============================================
echo  폰스팟 콘텐츠 학습 가이드 (카드뉴스 진입점)
echo  새 카드뉴스 시작 전 검토
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
echo  카드뉴스 시작 (run_pngs.bat) 진행 시 아무 키
echo ============================================
pause >nul
