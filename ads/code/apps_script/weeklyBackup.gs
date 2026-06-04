// ════════════════════════════════════════════════════════════
//  weeklyBackup — 정기 백업 (시트 → Drive 사본)
//  추가일: 2026-05-30
//
//  셋업:
//  1) 이 코드를 Code.gs 맨 아래에 붙여넣기 → 저장
//  2) 함수 셀렉터에서 weeklyBackup 1회 실행 → 권한 승인 (DriveApp scope)
//  3) Apps Script 트리거 메뉴(왼쪽 ⏰ 아이콘) → + 트리거 추가
//     · 함수: weeklyBackup
//     · 배포: Head
//     · 이벤트 소스: 시간 기반
//     · 트리거 유형: 주별 타이머
//     · 요일: 일요일
//     · 시간: 오전 2~3시 (Asia/Seoul)
//  → 매주 일요일 새벽 시트 사본이 Drive '폰스팟_광고운영_백업' 폴더에 생성됨
//  → 28일(4주) 이상 된 백업은 자동 휴지통
// ════════════════════════════════════════════════════════════
function weeklyBackup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const tz = 'Asia/Seoul';
  const ymd = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');
  const backupName = '폰스팟_광고운영_백업_' + ymd;

  // Drive 백업 폴더 (없으면 생성)
  const folderName = '폰스팟_광고운영_백업';
  let folder;
  const folders = DriveApp.getFoldersByName(folderName);
  if (folders.hasNext()) {
    folder = folders.next();
  } else {
    folder = DriveApp.createFolder(folderName);
  }

  // 시트 사본 생성
  const file = DriveApp.getFileById(ss.getId());
  file.makeCopy(backupName, folder);

  // 4주 이상 된 백업 자동 휴지통 (Drive 용량 관리)
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 28);
  const all = folder.getFilesByType(MimeType.GOOGLE_SHEETS);
  let trashed = 0;
  while (all.hasNext()) {
    const f = all.next();
    if (f.getDateCreated() < cutoff) {
      f.setTrashed(true);
      trashed++;
    }
  }
  Logger.log('백업 완료: ' + backupName + ' / 정리(휴지통): ' + trashed);
}
