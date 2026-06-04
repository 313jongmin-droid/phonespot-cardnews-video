@echo off
chcp 65001 >nul
title YouTube → 관리대장 sync
cd /d C:\Users\di898\Documents\phonespot_cardnews

echo ====================================
echo  YouTube → 관리대장 시트 sync
echo  %date% %time%
echo ====================================
echo.

python ads\integrations\youtube\push_to_sheet.py

set RC=%errorlevel%
echo.
echo ====================================
if %RC%==0 (
    echo  [OK] 완료
) else (
    echo  [ERR] 실패 - 코드 %RC%
    echo  위 에러 메시지 확인
)
echo ====================================
echo.
echo 아무 키나 누르면 창이 닫힙니다.
pause >nul
