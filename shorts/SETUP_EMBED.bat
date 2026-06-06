@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title PhoneSpot - 일러스트 의미 임베딩 설치/점검 (PC당 1회)

rem 무료 로컬 임베딩 엔진 설치. 첫 실행 시 모델(약 220MB)을 1회 다운로드하고,
rem 이후에는 오프라인으로 동작합니다. 설치 안 돼도 파이프라인은 lexical 폴백으로 동작합니다.

pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] shorts 폴더에 접근할 수 없습니다: %~dp0
  pause
  exit /b 1
)

rem ── 파이썬 명령 자동 탐지 (python -> py -3 -> python3) ─────────────
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py -3" )
if not defined PY ( where python3 >nul 2>nul && set "PY=python3" )
if not defined PY (
  echo [ERROR] Python 을 찾지 못했습니다. Python 설치 후 다시 실행하세요.
  popd & pause & exit /b 1
)
echo 사용할 Python: %PY%

echo.
echo ===== 1/3: 패키지 설치 (fastembed / numpy / socksio) =====
%PY% -m pip install --upgrade fastembed numpy socksio
if errorlevel 1 (
  echo [WARN] 일반 설치 실패 - 사용자 영역(--user)으로 재시도합니다.
  %PY% -m pip install --user --upgrade fastembed numpy socksio
)

echo.
echo ===== 2/3: 모델 다운로드 + self-test (질의별 점수 표시) =====
echo (처음이면 모델 받느라 1~2분 걸릴 수 있습니다)
%PY% scripts\codex_illust_embed.py selftest

echo.
echo ===== 3/3: 임베딩 사용 가능 여부 최종 점검 =====
%PY% scripts\codex_illust_embed.py check
if errorlevel 1 (
  echo.
  echo [결과] 임베딩 사용 불가 ^(False^). 모델 다운로드가 막혔거나 패키지 설치가 안 됐습니다.
  echo        - 인터넷/프록시 확인 후 이 배치를 다시 실행하세요.
  echo        - 그래도 파이프라인은 lexical 폴백으로 동작합니다.
  set "RESULT=FALSE"
) else (
  echo.
  echo [결과] 임베딩 사용 가능 ^(True^). 이제 패널의 "1. 영상용 프롬프트 준비"를 누르면
  echo        개념 발굴/매칭이 '의미 기반'으로 동작합니다.
  set "RESULT=TRUE"
)

popd
echo.
echo ===== 완료: 임베딩 활성화 = !RESULT! =====
pause
