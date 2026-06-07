@echo off
chcp 65001 >nul
rem 이 PC에서 매일 09:00 에 일러스트 라이브러리 자동 백업(스냅샷)을 등록합니다.
rem 관리자 권한 불필요(사용자 작업). PC가 꺼져 있으면 그 날은 건너뜁니다.
set "HERE=%~dp0"
set "RUNCMD=%HERE%dashboard\run_library_backup.cmd"

if not exist "%RUNCMD%" (
  echo [실패] 실행 파일이 없습니다: %RUNCMD%
  pause
  exit /b 1
)

schtasks /create /tn "PhoneSpot Library Backup" /tr "\"%RUNCMD%\"" /sc DAILY /st 09:00 /f
if errorlevel 1 (
  echo.
  echo [실패] 스케줄 등록 실패. 위 메시지를 확인하세요.
) else (
  echo.
  echo [OK] 매일 09:00 라이브러리 자동 백업 등록 완료.
  echo  - 작업 이름 : PhoneSpot Library Backup
  echo  - 시간 변경 : 작업 스케줄러에서 "PhoneSpot Library Backup" 트리거 수정
  echo  - 해제      : 라이브러리_자동백업_스케줄_해제.bat
  echo  - 로그      : CODEX_VIDEO_DESK\TEMP\panel\panel_logs\library_backup_scheduled.log
)
pause
