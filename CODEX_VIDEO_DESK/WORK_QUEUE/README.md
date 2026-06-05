# PhoneSpot 작업 큐 V1

이 폴더는 카드뉴스/영상 제작 상태를 한 표로 모으기 위한 중간 허브입니다.

생성 파일:

- `phonespot_work_queue.csv`  
  엑셀/구글시트 가져오기용
- `phonespot_work_queue.tsv`  
  구글시트에 전체 복붙하기 좋은 탭 구분 파일
- `phonespot_work_queue.json`  
  패널/자동화용 원본 데이터
- `phonespot_work_queue.md`  
  사람이 빠르게 보는 요약표

권장 운영:

1. 카드뉴스 생성 후 작업 큐 새로고침
2. 구글시트에 `phonespot_work_queue.tsv`를 붙여넣거나 가져오기
3. 검수/담당자/발행상태는 시트에서 관리
4. 다음 단계에서 패널 리스트를 이 큐 기준으로 바꿀 수 있음

주의:

- 렌더링 자체는 여전히 각 PC 로컬에서 합니다.
- Google Sheets API 직접 연동은 V2 단계에서 붙입니다.
