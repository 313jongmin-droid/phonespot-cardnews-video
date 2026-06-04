"""오늘 날짜를 YYYYMMDD 형식으로 출력. 배치 파일의 출력 파일명 부착용."""
import datetime
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

print(datetime.date.today().strftime("%Y%m%d"))
