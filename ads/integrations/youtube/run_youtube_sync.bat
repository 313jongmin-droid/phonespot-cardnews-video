@echo off
chcp 65001 >nul
title YouTube → 관리대장 sync + 가이드 갱신
cd /d C:\Users\di898\Documents\phonespot_cardnews

echo ====================================
echo  YouTube sync (시트 → 가이드)
echo  %date% %time%
echo ====================================
echo.

echo [1/2] 시트 push...
python ads\integrations\youtube\push_to_sheet.py
set RC1=%errorlevel%
echo.

if not %RC1%==0 (
    echo ====================================
    echo  [ERR] 시트 push 실패 - 코드 %RC1%
    echo  가이드 갱신 건너뜀
    echo ====================================
    pause >nul
    exit /b %RC1%
)

echo [2/2] 가이드 재계산 (D-2 이상 영상만)...
python ads\integrations\youtube\run_analyze.py
set RC2=%errorlevel%
echo.

echo ====================================
if %RC2%==0 (
    echo  [OK] 완료
    echo  - 시트:  https://docs.google.com/spreadsheets/d/1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI/edit
    echo  - 가이드: cardnews\_state\content_guide.md
) else (
    echo  [WARN] 가이드 갱신 실패 - 코드 %RC2%
    echo  (시트는 push 됨)
)
echo ====================================
echo.
echo 아무 키나 누르면 닫힙니다.
pause >nul
