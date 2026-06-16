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
  'GA4세션', '카톡클릭', '전화클릭', '시티마켓 클릭', '시티마켓 직접',
  '카톡전환률', '카톡당CPC',
  '카톡문의', '앱문의', 'CPL', '개통수', '메모'
];

const DANGGN_UTM_HEADERS = [
  '당근 광고그룹명(한글)', 'utm_campaign(영문)', '첫 발견일', '상태', '메모'
];

// ============ 문의접수 시트 표준화 (모든 브랜드 공통, 2026-06-15) ============

/**
 * 문의접수 D열 표준값 (드롭다운).
 * ★ 다른 브랜드 시트(KT/국민/진짜폰스팟) 신설 시 = 같은 함수 호출로 동일 셋업.
 */
const INQUIRY_D_OPTIONS = [
  '구글', '네이버', '카카오', '페북', '당근',
  '인스타', '스레드', '뽐뿌', '내방', '지인', '기타'
];

/**
 * 옛 값 → 새 값 일괄 치환 (브랜드 신설 시 옛 데이터 이관 자동화)
 * - "메타" → "페북" (호칭 변경)
 * - "불확실" → "기타" (통합)
 *
 * 당근: D열은 "당근" 1개 (카톡 문의 = 자동 매칭). 앱문의는 당근_통합 Q열 수기 입력 (API 없음).
 */
const INQUIRY_D_LEGACY_MAPPING = {
  '메타': '페북',
  '불확실': '기타'
};

/**
 * 문의접수 C열 표준값 (개통여부, 옛 가이드 유지).
 */
const INQUIRY_C_OPTIONS = ['개통', '진행중', '미상'];

/**
 * 1회 실행: 문의접수 시트 D열 드롭다운 자동 설정 + 옛 값 치환 + C열 드롭다운.
 * idempotent — 매번 실행해도 안전.
 *
 * 미래 브랜드 신설(KT/국민/진짜폰스팟)에서도 같은 함수 호출하면 동일 셋업.
 */
function setupInquirySheetDropdowns() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('문의접수');
  const ui = SpreadsheetApp.getUi();

  if (!sheet) {
    try { ui.alert('❌ 문의접수 시트가 없습니다.'); } catch (e) {}
    return;
  }

  const results = [];

  // ===== 1. D열 (4) 드롭다운 설정 = 2행~ =====
  const targetLastRow = Math.max(sheet.getLastRow(), 2000);  // 미래 행 대비 2000행
  const dRange = sheet.getRange(2, 4, targetLastRow - 1, 1);
  const dRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(INQUIRY_D_OPTIONS, true)
    .setAllowInvalid(true)  // 옛 값 보존 (치환 전)
    .build();
  dRange.setDataValidation(dRule);
  results.push(`✅ D열 드롭다운 설정 (${INQUIRY_D_OPTIONS.length}개 옵션, ${targetLastRow}행까지)`);

  // ===== 2. C열 (3) 드롭다운 설정 (개통여부) =====
  const cRange = sheet.getRange(2, 3, targetLastRow - 1, 1);
  const cRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(INQUIRY_C_OPTIONS, true)
    .setAllowInvalid(true)
    .build();
  cRange.setDataValidation(cRule);
  results.push(`✅ C열 드롭다운 설정 (개통/진행중/미상)`);

  // ===== 3. 옛 D열 값 일괄 치환 =====
  const dataLastRow = sheet.getLastRow();
  if (dataLastRow >= 2) {
    const dataRange = sheet.getRange(2, 4, dataLastRow - 1, 1);
    const values = dataRange.getValues();
    const changedCount = {};
    for (let i = 0; i < values.length; i++) {
      const v = values[i][0];
      if (INQUIRY_D_LEGACY_MAPPING.hasOwnProperty(v)) {
        values[i][0] = INQUIRY_D_LEGACY_MAPPING[v];
        changedCount[v] = (changedCount[v] || 0) + 1;
      }
    }
    const totalChanged = Object.values(changedCount).reduce((a, b) => a + b, 0);
    if (totalChanged > 0) {
      dataRange.setValues(values);
      const detail = Object.keys(changedCount).map(k => `"${k}"→"${INQUIRY_D_LEGACY_MAPPING[k]}" (${changedCount[k]}행)`).join(', ');
      results.push(`✅ 옛 값 치환: ${detail}`);
    } else {
      results.push(`ℹ️ 치환할 옛 값 없음 (이미 새 표준값)`);
    }
  }

  // ===== 4. 결과 출력 =====
  const msg = '문의접수 시트 표준화 완료:\n\n' + results.join('\n') +
    '\n\n다음 = 메뉴에서 각 광고 시트 sync 실행 → 문의수 자동 매칭 활성화.';
  Logger.log(msg);
  try { ui.alert(msg); } catch (e) {}
}



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
    // ★ 2026-06-15: UTM 매핑 통합 시트(UTM_매핑) + A채널="당근" 필터
    const slugLookup = `IFERROR(VLOOKUP("${escapedName}", FILTER('UTM_매핑'!B:C, 'UTM_매핑'!A:A="당근"), 2, FALSE),"")`;
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
    // L (12) 시티마켓 클릭 (리틀리 경유, 당근 광고에 리틀리 URL 포함 시)
    sheet.getRange(row, 12).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click"),0)`
    );
    // M (13) 시티마켓 직접 (광고→시티마켓 직접 도달, citymarket_arrival, GTM 2026-06-15)
    sheet.getRange(row, 13).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_arrival"),0)`
    );

    // N (14) 카톡전환률 (=J/I)
    sheet.getRange(row, 14).setFormula(`=IFERROR(J${row}/I${row},"")`);
    // O (15) 카톡당CPC (=F/J)
    sheet.getRange(row, 15).setFormula(`=IFERROR(F${row}/J${row},"")`);
    // P (16) 카톡문의 = 문의접수 D열="당근" 자동 매칭
    sheet.getRange(row, 16).setFormula(
      `=COUNTIFS('문의접수'!D:D,"당근",'문의접수'!A:A,A${row})`
    );
    // Q (17) 앱문의 = ★ 수기 입력 (당근 API 없음, 사장님이 당근 앱에서 직접 확인하고 박음).
    //   setFormula 박지 않음 = 매번 sync 실행 시 사장님 수기 입력값 보존.
    // R (18) CPL = 지출 / (카톡문의 + 앱문의 합산)
    sheet.getRange(row, 18).setFormula(
      `=IFERROR(IF((P${row}+Q${row})=0,"-",F${row}/(P${row}+Q${row})),"-")`
    );

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
  ui.createMenu('🟠 당근 자동화')
    .addItem('🔄 GA4 매칭 새로고침 (전체 행)', 'syncDanggnGA4')
    .addSeparator()
    .addItem('🆕 시트 신설 / 헤더 갱신', 'createDanggnIntegratedSheet')
    .addItem('🔍 미매핑 광고그룹 보기', 'showUnmappedDanggnAdgroups')
    .addItem('📋 문의접수 D열 표준화', 'setupInquirySheetDropdowns')
    .addItem('🔄 UTM 매핑 통합 마이그레이션 (1회)', 'migrateUtmMappingsUnified')
    .addSeparator()
    .addItem('⏰ 당근 Daily Trigger 설정 (02:30)', 'setupDanggnTrigger')
    .addItem('🔑 utm_source 값 확인', 'showDanggnUtmSource')
    .addToUi();
}

/**
 * 미매핑 광고그룹 보기 (통합 시트 채널="당근" 행 중 utm_campaign 빈 것)
 */
function showUnmappedDanggnAdgroups() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('UTM_매핑');
  const ui = SpreadsheetApp.getUi();
  if (!sheet) { ui.alert('UTM_매핑 시트 없음.'); return; }
  if (sheet.getLastRow() < 2) { ui.alert('UTM_매핑 비어있음.'); return; }
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 3).getValues();
  const unmapped = data.filter(r => r[0] === '당근' && r[1] && !r[2]);
  if (unmapped.length === 0) { ui.alert('✅ 미매핑 당근 광고그룹 없음.'); return; }
  ui.alert(`⚠️ 미매핑 당근 ${unmapped.length}개:\n\n` + unmapped.map((r, i) => `${i+1}. ${r[1]}`).join('\n'));
}

/**
 * DANGGN_UTM_SOURCE 값 확인
 */
function showDanggnUtmSource() {
  const val = PropertiesService.getScriptProperties().getProperty('DANGGN_UTM_SOURCE') || '(미설정, 기본값 "danggn" 사용)';
  SpreadsheetApp.getUi().alert(`DANGGN_UTM_SOURCE = "${val}"\n\nGA4_자동 시트 B열(sessionSource)과 일치해야 매칭됨. (정답: "daangn")`);
}


// ============ UTM 매핑 통합 마이그레이션 (1회용, 2026-06-15) ============

/**
 * 3개 UTM 매핑 시트 → 1개 통합 시트 (UTM_매핑, 6컬럼)
 *
 * 새 구조:
 *   A 채널 / B 광고그룹명(한글) / C utm_campaign(영문) / D 첫발견일 / E 상태 / F 메모
 *
 * 처리:
 *   1. UTM_매핑 시트 = A열에 "채널" 컬럼 삽입 + 기존 행 "페북" 박음 (5→6컬럼)
 *   2. 네이버_UTM_매핑 데이터 → UTM_매핑에 append (채널="네이버")
 *   3. 당근_UTM_매핑 데이터 → UTM_매핑에 append (채널="당근")
 *   4. 옛 네이버_UTM_매핑/당근_UTM_매핑 시트 자동 삭제
 *   5. A열 채널 드롭다운 설정
 *
 * idempotent — 이미 통합됐으면 스킵.
 * 안전: 실행 전 PhoneSpot Sheet Export → exportAllSheetsToDrive 백업 권장.
 */
function migrateUtmMappingsUnified() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();
  const results = [];

  const mainSheet = ss.getSheetByName('UTM_매핑');
  if (!mainSheet) {
    try { ui.alert('❌ UTM_매핑 시트가 없습니다. 메타 sync 1회 실행 후 다시 시도.'); } catch (e) {}
    return;
  }

  // 1. 채널 컬럼 점검 — 이미 있으면 스킵
  const firstHeader = mainSheet.getRange(1, 1).getValue();
  if (firstHeader !== '채널') {
    mainSheet.insertColumnBefore(1);
    mainSheet.getRange(1, 1).setValue('채널');
    mainSheet.getRange(1, 1).setFontWeight('bold').setBackground('#1F4E78').setFontColor('#FFFFFF').setHorizontalAlignment('center');
    const lastRow = mainSheet.getLastRow();
    if (lastRow >= 2) {
      const channels = [];
      for (let i = 0; i < lastRow - 1; i++) channels.push(['페북']);
      mainSheet.getRange(2, 1, lastRow - 1, 1).setValues(channels);
    }
    results.push('✅ UTM_매핑: A열 "채널" 컬럼 추가 + ' + (lastRow - 1) + '행 "페북" 박음');
  } else {
    results.push('ℹ️ UTM_매핑: 이미 통합됨 (채널 컬럼 있음)');
  }

  // 2. 네이버_UTM_매핑 → UTM_매핑 통합
  const naverSheet = ss.getSheetByName('네이버_UTM_매핑');
  if (naverSheet) {
    const lastRow = naverSheet.getLastRow();
    let moved = 0;
    if (lastRow >= 2) {
      const data = naverSheet.getRange(2, 1, lastRow - 1, 5).getValues();
      data.forEach(function (row) {
        if (row[0] && !String(row[0]).startsWith('※')) {
          mainSheet.appendRow(['네이버', row[0], row[1], row[2], row[3], row[4]]);
          moved++;
        }
      });
    }
    ss.deleteSheet(naverSheet);
    results.push('✅ 네이버_UTM_매핑 → UTM_매핑 (' + moved + '행 이관 + 시트 삭제)');
  } else {
    results.push('ℹ️ 네이버_UTM_매핑: 시트 없음 (이미 처리됨)');
  }

  // 3. 당근_UTM_매핑 → UTM_매핑 통합
  const danggnSheet = ss.getSheetByName('당근_UTM_매핑');
  if (danggnSheet) {
    const lastRow = danggnSheet.getLastRow();
    let moved = 0;
    if (lastRow >= 2) {
      const data = danggnSheet.getRange(2, 1, lastRow - 1, 5).getValues();
      data.forEach(function (row) {
        if (row[0] && !String(row[0]).startsWith('※')) {
          mainSheet.appendRow(['당근', row[0], row[1], row[2], row[3], row[4]]);
          moved++;
        }
      });
    }
    ss.deleteSheet(danggnSheet);
    results.push('✅ 당근_UTM_매핑 → UTM_매핑 (' + moved + '행 이관 + 시트 삭제)');
  } else {
    results.push('ℹ️ 당근_UTM_매핑: 시트 없음 (이미 처리됨)');
  }

  // 4. A열 채널 드롭다운 설정
  const finalLastRow = Math.max(mainSheet.getLastRow(), 1000);
  const channelRange = mainSheet.getRange(2, 1, finalLastRow - 1, 1);
  const channelRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['페북', '네이버', '당근', '구글', '카카오'], true)
    .setAllowInvalid(true)
    .build();
  channelRange.setDataValidation(channelRule);
  results.push('✅ A열 채널 드롭다운 설정 (페북/네이버/당근/구글/카카오)');

  const msg = 'UTM 매핑 통합 마이그레이션 완료:\n\n' + results.join('\n') +
    '\n\n다음 = 각 채널 sync 실행 → 새 매칭 적용.';
  Logger.log(msg);
  try { ui.alert(msg); } catch (e) {}
}
