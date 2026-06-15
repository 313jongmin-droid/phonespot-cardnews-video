/**
 * 당근 광고 운영 자동화 (광고운영 task, 2026-06-15 신설)
 *
 * 당근은 API 없음 → 운영 데이터(노출/클릭/지출)는 사장님 수기 입력.
 * GA4 데이터(세션/카톡클릭/전화클릭/시티마켓)만 SUMIFS 수식으로 자동 매칭.
 *
 * 시트 구조 (17컬럼 단순화, 메타_통합/네이버_통합 19컬럼에서 캠페인ID/광고그룹ID 제외):
 *   A 날짜 (수기)
 *   B 캠페인명 (수기, 자유 입력)
 *   C 광고그룹명 (수기, 매핑 키)
 *   D 노출 (수기)
 *   E 클릭 (수기)
 *   F 지출 (수기)
 *   G CTR (자동 수식 =E/D)
 *   H CPC (자동 수식 =F/E)
 *   I GA4세션 (자동 매칭)
 *   J 카톡클릭 (자동 매칭)
 *   K 전화클릭 (자동 매칭)
 *   L 시티마켓 (자동 매칭)
 *   M 카톡전환률 (자동 수식 =J/I)
 *   N 카톡당CPC (자동 수식 =F/J)
 *   O 문의수 (수기)
 *   P 개통수 (수기)
 *   Q 메모 (수기)
 *
 * GA4 매칭 키:
 *   GA4_자동!A열(date) = 당근_통합!A열 (YYYYMMDD 텍스트로 변환)
 *   GA4_자동!B열(sessionSource) = DANGGN_UTM_SOURCE (Script Properties, 기본 "danggn")
 *   GA4_자동!D열(sessionCampaignName) = 당근_UTM_매핑 VLOOKUP (광고그룹명 → 영문 utm_campaign)
 *   GA4_자동!E열(eventName) = session_start / kakao_chat_click / phone_click / citymarket_click
 *
 * 사장님 1회 셋업 (Apps Script 콘솔에서 함수 실행):
 *   1. createDanggnIntegratedSheet() — 당근_통합 + 당근_UTM_매핑 시트 신설
 *   2. Script Properties에 DANGGN_UTM_SOURCE 등록 (기본값 "danggn", GA4 실제 값과 일치해야 함)
 *   3. setupDanggnTrigger() — 매일 02:30 자동 트리거 등록
 *   4. (시트에 데이터 입력 후) syncDanggnGA4() 수동 1회 실행 → 검증
 *
 * 정본: ads/DANGGN_AUTOMATION.md (신설 예정)
 */

const DANGGN_SHEET = '당근_통합';
const DANGGN_UTM_SHEET = '당근_UTM_매핑';

const DANGGN_HEADERS = [
  '날짜', '캠페인명', '광고그룹명',
  '노출', '클릭', '지출',
  'CTR', 'CPC',
  'GA4세션', '카톡클릭', '전화클릭', '시티마켓',
  '카톡전환률', '카톡당CPC',
  '문의수', '개통수', '메모'
];

const DANGGN_UTM_HEADERS = [
  '당근 광고그룹명(한글)', 'utm_campaign(영문)', '첫 발견일', '상태', '메모'
];

/**
 * 1회 실행: 당근_통합 + 당근_UTM_매핑 시트 신설 + 헤더 박음
 * 이미 있으면 헤더만 갱신 (데이터 유지).
 */
function createDanggnIntegratedSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // 1. 당근_통합 시트
  let sheet = ss.getSheetByName(DANGGN_SHEET);
  let created1 = false;
  if (!sheet) {
    sheet = ss.insertSheet(DANGGN_SHEET);
    created1 = true;
  }

  sheet.getRange(1, 1, 1, DANGGN_HEADERS.length).setValues([DANGGN_HEADERS]);
  sheet.getRange(1, 1, 1, DANGGN_HEADERS.length)
    .setFontWeight('bold')
    .setBackground('#FFE0B2')
    .setHorizontalAlignment('center');
  sheet.setFrozenRows(1);

  // 열 너비
  sheet.setColumnWidth(1, 100);   // 날짜
  sheet.setColumnWidth(2, 180);   // 캠페인명
  sheet.setColumnWidth(3, 180);   // 광고그룹명

  Logger.log(DANGGN_SHEET + ' 시트 ' + (created1 ? '생성' : '헤더 갱신') + ' 완료');

  // 2. 당근_UTM_매핑 시트
  let utmSheet = ss.getSheetByName(DANGGN_UTM_SHEET);
  let created2 = false;
  if (!utmSheet) {
    utmSheet = ss.insertSheet(DANGGN_UTM_SHEET);
    created2 = true;
  }

  utmSheet.getRange(1, 1, 1, DANGGN_UTM_HEADERS.length).setValues([DANGGN_UTM_HEADERS]);
  utmSheet.getRange(1, 1, 1, DANGGN_UTM_HEADERS.length)
    .setFontWeight('bold')
    .setBackground('#FFE0B2')
    .setHorizontalAlignment('center');
  utmSheet.setFrozenRows(1);

  // 안내 행
  if (utmSheet.getLastRow() < 2) {
    const utmGuide = [
      '※ 당근 광고그룹명 (수기 입력)',
      '※ GA4 utm_campaign 값 (수기 입력)',
      '', '', '※ 예: danggn_kids, danggn_iphone'
    ];
    utmSheet.getRange(2, 1, 1, DANGGN_UTM_HEADERS.length).setValues([utmGuide]);
    utmSheet.getRange(2, 1, 1, DANGGN_UTM_HEADERS.length)
      .setBackground('#F5F5F5')
      .setFontStyle('italic')
      .setFontSize(9);
  }

  utmSheet.setColumnWidth(1, 250);
  utmSheet.setColumnWidth(2, 200);

  Logger.log(DANGGN_UTM_SHEET + ' 시트 ' + (created2 ? '생성' : '헤더 갱신') + ' 완료');

  SpreadsheetApp.flush();

  return {
    danggn: { sheetId: sheet.getSheetId(), created: created1 },
    danggn_utm: { sheetId: utmSheet.getSheetId(), created: created2 }
  };
}

/**
 * 당근_통합 시트의 각 데이터 행에 GA4 매칭 수식 박음
 *
 * 매일 02:30 KST 자동 호출 (setupDanggnTrigger에서 등록).
 * 수동 호출 가능 (시트 첫 입력 후 검증용).
 *
 * 빈 행 (날짜 또는 광고그룹명 없음) = 스킵.
 * 광고그룹명이 당근_UTM_매핑에 없으면 = VLOOKUP 빈 결과 = GA4 매칭 0.
 */
function syncDanggnGA4(opts) {
  opts = opts || {};
  const interactive = opts.interactive !== false;  // 기본 = 메뉴 호출, 트리거에선 opts.interactive=false 전달
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(DANGGN_SHEET);
  if (!sheet) {
    const msg = '❌ 당근_통합 시트가 없습니다.\n\n시트 메뉴 → 🥕 당근 자동화 → 🆕 시트 신설 / 헤더 갱신 먼저 실행하세요.';
    Logger.log(msg);
    logSync_('syncDanggnGA4', 'fail', '당근_통합 시트 없음');
    if (interactive) { try { SpreadsheetApp.getUi().alert(msg); } catch (e) {} }
    return { ok: false, error: 'sheet not found' };
  }

  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    const msg = '⚠️ 당근_통합 시트가 비어있습니다 (헤더만).\n\n시트에 데이터 (A 날짜, B 캠페인명, C 광고그룹명, D~F 노출/클릭/지출) 먼저 입력하세요.';
    Logger.log(msg);
    if (interactive) { try { SpreadsheetApp.getUi().alert(msg); } catch (e) {} }
    return { ok: true, updated: 0 };
  }

  const utmSource = PropertiesService.getScriptProperties().getProperty('DANGGN_UTM_SOURCE') || 'danggn';

  let updated = 0;
  let skipped = 0;

  for (let row = 2; row <= lastRow; row++) {
    const dateCell = sheet.getRange(row, 1).getValue();
    const adgroupName = sheet.getRange(row, 3).getValue();

    if (!dateCell || !adgroupName) {
      skipped++;
      continue;
    }

    // 날짜 → YYYYMMDD 숫자 (GA4_자동 A열 형식)
    let ymdText;
    if (dateCell instanceof Date) {
      ymdText = Utilities.formatDate(dateCell, 'Asia/Seoul', 'yyyyMMdd');
    } else {
      ymdText = String(dateCell).replace(/[-/]/g, '');
    }

    // 광고그룹명 escape (따옴표 처리)
    const escapedName = String(adgroupName).replace(/"/g, '""');
    const slugLookup = `IFERROR(VLOOKUP("${escapedName}",'${DANGGN_UTM_SHEET}'!A:B,2,FALSE),"")`;
    const ga4Base = `'GA4_자동'!A:A,${ymdText},'GA4_자동'!B:B,"${utmSource}",'GA4_자동'!D:D,${slugLookup}`;

    // G CTR (수식, =E/D)
    sheet.getRange(row, 7).setFormula(`=IFERROR(E${row}/D${row},"")`);
    // H CPC (=F/E)
    sheet.getRange(row, 8).setFormula(`=IFERROR(F${row}/E${row},"")`);

    // I GA4세션
    sheet.getRange(row, 9).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!G:G,${ga4Base},'GA4_자동'!E:E,"session_start"),0)`
    );
    // J 카톡클릭
    sheet.getRange(row, 10).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"kakao_chat_click"),0)`
    );
    // K 전화클릭
    sheet.getRange(row, 11).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"phone_click"),0)`
    );
    // L 시티마켓 = citymarket_click(리틀리 클릭) + citymarket_arrival(직접 도달, GTM 2026-06-15)
    // 당근은 시티마켓 직접 유입이라 click 발생 X → arrival로 잡힘
    sheet.getRange(row, 12).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click")+SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_arrival"),0)`
    );

    // M 카톡전환률 (=J/I)
    sheet.getRange(row, 13).setFormula(`=IFERROR(J${row}/I${row},"")`);
    // N 카톡당CPC (=F/J)
    sheet.getRange(row, 14).setFormula(`=IFERROR(F${row}/J${row},"")`);

    updated++;
  }

  Logger.log('syncDanggnGA4: updated=' + updated + ' skipped=' + skipped);
  logSync_('syncDanggnGA4', 'ok', `당근_통합 ${updated} rows GA4 매칭 (skipped: ${skipped})`);

  if (interactive) {
    try {
      const utmSource = PropertiesService.getScriptProperties().getProperty('DANGGN_UTM_SOURCE') || 'danggn(기본값)';
      SpreadsheetApp.getUi().alert(
        '✅ GA4 매칭 새로고침 완료\n\n' +
        '· 갱신: ' + updated + '개 행\n' +
        '· 스킵: ' + skipped + '개 (날짜 또는 광고그룹명 빈 행)\n' +
        '· utm_source: "' + utmSource + '" 기준\n\n' +
        (updated > 0 ? '시트 가서 I~N (GA4 컬럼) 확인하세요. 매칭 0이면:\n1. 시트 메뉴 → 🔍 미매핑 광고그룹 보기\n2. 메뉴 → 🔑 utm_source 값 확인'
                     : '갱신된 행 없음. 시트에 데이터 입력 필요.')
      );
    } catch (uiErr) {
      // 트리거 환경 등 UI 없는 곳에서 호출되면 무시
    }
  }

  return { ok: true, updated: updated, skipped: skipped };
}

/**
 * 매일 02:30 KST 자동 트리거 등록 (1회 실행)
 * 기존 트리거 있으면 제거 후 재등록 (idempotent).
 */
function setupDanggnTrigger() {
  let removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'syncDanggnGA4') {
      ScriptApp.deleteTrigger(t);
      removed++;
    }
  });

  ScriptApp.newTrigger('syncDanggnGA4')
    .timeBased()
    .atHour(2)
    .nearMinute(30)
    .everyDays(1)
    .create();

  Logger.log('당근 GA4 매칭 트리거 등록: 매일 02:30 KST (removed old: ' + removed + ')');
}

/**
 * 동기화_로그 시트에 1줄 박음 (Code.gs / meta-sync.js / naver-sync.js 와 동일 패턴)
 */
function logSync_(funcName, status, message) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const logSheet = ss.getSheetByName('동기화_로그');
    if (!logSheet) return;
    const emoji = status === 'ok' ? '✅ 성공' : (status === 'fail' ? '❌ 실패' : '⚠️ 경고');
    logSheet.appendRow([new Date(), funcName, emoji, message]);
  } catch (err) {
    // 로그 실패는 무시
  }
}


// ============ 당근 자동화 메뉴 (네이버 패턴 그대로) ============

/**
 * 시트 메뉴에 🥕 당근 자동화 박음
 * Code.js onOpen에서 buildDanggnSyncMenu_(SpreadsheetApp.getUi()) 호출.
 */
function buildDanggnSyncMenu_(ui) {
  ui.createMenu('🥕 당근 자동화')
    .addItem('🔄 GA4 매칭 새로고침 (전체 행)', 'syncDanggnGA4')
    .addSeparator()
    .addItem('🆕 시트 신설 / 헤더 갱신', 'createDanggnIntegratedSheet')
    .addItem('🔍 미매핑 광고그룹 보기', 'showUnmappedDanggnAdgroups')
    .addSeparator()
    .addItem('⏰ 당근 Daily Trigger 설정 (02:30)', 'setupDanggnTrigger')
    .addItem('🔑 utm_source 값 확인', 'showDanggnUtmSource')
    .addToUi();
}

/**
 * 당근_통합 시트의 광고그룹명 중 당근_UTM_매핑에 없는 것 찾기
 */
function showUnmappedDanggnAdgroups() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(DANGGN_SHEET);
  const utmSheet = ss.getSheetByName(DANGGN_UTM_SHEET);

  if (!sheet || !utmSheet) {
    SpreadsheetApp.getUi().alert('당근_통합 또는 당근_UTM_매핑 시트가 없습니다. 먼저 "🆕 시트 신설" 실행.');
    return;
  }

  // 당근_통합 광고그룹명 (C열)
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    SpreadsheetApp.getUi().alert('당근_통합 시트에 데이터가 없습니다.');
    return;
  }
  const adgroupNames = sheet.getRange(2, 3, lastRow - 1, 1).getValues()
    .map(function (r) { return r[0]; })
    .filter(function (v) { return v; });
  const uniqueNames = Array.from(new Set(adgroupNames));

  // 당근_UTM_매핑 (A열 = 광고그룹명, B열 = utm_campaign)
  const utmLastRow = utmSheet.getLastRow();
  const mappings = {};
  if (utmLastRow >= 2) {
    const utmData = utmSheet.getRange(2, 1, utmLastRow - 1, 2).getValues();
    utmData.forEach(function (r) {
      if (r[0]) mappings[r[0]] = r[1] || '';
    });
  }

  const unmapped = uniqueNames.filter(function (name) {
    return !mappings.hasOwnProperty(name) || !mappings[name];
  });

  if (unmapped.length === 0) {
    SpreadsheetApp.getUi().alert('✅ 모든 광고그룹이 utm_campaign에 매핑되어 있습니다 (' + uniqueNames.length + '개).');
    return;
  }

  SpreadsheetApp.getUi().alert(
    '⚠️ 미매핑 광고그룹 ' + unmapped.length + '개:\n\n' + unmapped.join('\n') +
    '\n\n→ 당근_UTM_매핑 시트에 추가해 주세요.'
  );
}

/**
 * 현재 등록된 DANGGN_UTM_SOURCE 값 표시
 */
function showDanggnUtmSource() {
  const value = PropertiesService.getScriptProperties().getProperty('DANGGN_UTM_SOURCE');
  const ui = SpreadsheetApp.getUi();
  if (!value) {
    ui.alert(
      '⚠️ DANGGN_UTM_SOURCE 미설정\n\n' +
      'Apps Script 콘솔 → 프로젝트 설정 → 스크립트 속성에서\n' +
      '속성 "DANGGN_UTM_SOURCE", 값 "danggn" (또는 GA4 실제 값) 등록 필요.\n\n' +
      '미설정 시 기본값 "danggn" 사용.'
    );
  } else {
    ui.alert('✅ DANGGN_UTM_SOURCE = "' + value + '"\n\nGA4 sessionSource와 일치하는지 확인하세요.');
  }
}
