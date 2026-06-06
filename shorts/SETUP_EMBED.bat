@echo off
setlocal
chcp 65001 >nul
title PhoneSpot - 일러스트 의미 임베딩 설치/점검 (PC당 1회)

rem 무료 로컬 임베딩 엔진 설치. 첫 실행 시 모델(약 220MB)을 1회 다운로드하고,
rem 이후에는 오프라인으로 동작합니다.

pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] shorts 폴더에 접근할 수 없습니다: %~dp0
  pause
  exit /b 1
)

echo.
echo ===== 1/2: 패키지 설치 (fastembed / numpy) =====
python -m pip install --upgrade fastembed numpy
if errorlevel 1 (
  python3 -m pip install --upgrade fastembed numpy
)

echo.
echo ===== 2/2: 모델 다운로드 + 의미매칭 self-test =====
echo (처음이면 모델을 받느라 1~2분 걸릴 수 있습니다)
python scripts\codex_illust_embed.py selftest
if errorlevel 1 (
  python3 scripts\codex_illust_embed.py selftest
)

popd
echo.
echo 완료. 위 결과에서 '임베딩 사용 가능: True' 이고 질의별 점수가 보이면 정상입니다.
echo False 면 인터넷/프록시를 확인하거나 다시 실행하세요. (그래도 lexical 폴백으로 동작은 합니다)
pause
