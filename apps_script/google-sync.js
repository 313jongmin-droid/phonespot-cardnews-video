/**
 * 구글 광고 운영 자동화 (2026-06-19 신설, 당근 패턴 복제)
 *
 * 구글 Ads API 미연동 → 운영 데이터(노출/클릭/지출)는 사장님 수기 입력.
 * GA4 데이터(세션/카톡클릭/전화클릭/시티마켓)만 SUMIFS 수식으로 자동 매칭.
 *
 * 당근과의 차이:
 *   - GA4 source = "google" 리터럴 (당근의 DANGGN_UTM_SOURCE Script Property 불필요).
 *   - 통합 UTM_매핑(채널="구글") 사용 (별도 UTM 시트 없음).
 *   - 카톡문의 매칭 = 문의접수 D열="구글".
 *
 * 시트 구조 (20컬럼, 당근_통합 동일):
 *   A 날짜 / B 캠페인명 / C 광고그룹명(매핑키) / D 노출 / E 클릭 / F 지출 (여기까지 수기)
 *   G CTR / H CPC (자동수식) / I GA4세션 / J 카톡클릭 / K 전화클릭 / L 시티마켓클릭 / M 시티마켓직접 (자동매칭)
 *   N 카톡전환률 / O 카톡당CPC (자동수식) / P 카톡문의(문의접수 자동) / Q 웹문의(수기) / R CPL / S 개통수 / T 메모
 *
 * GA4 매칭 키: GA4_자동!A(date)=A열 / B(source)="google" / D(campaign)=UTM_매핑(채널=구글) VLOOKUP / E(event)
 *
 * 1회 셋업: createGoogleIntegratedSheet() → UTM_매핑에 채널=구글 행 입력 → syncGoogleGA4() → setupGoogleTrigger()
 */

const GOOGLE_SHEET = '구글_통합';

const GOOGLE_HEADERS = [
  '날짜', '캠페인명', '광고그룹명',
  '노출', '클릭', '지출',
  'CTR', 'CPC',
  'GA4세션', '카톡클릭', '전화클릭', '시티마켓 클릭', '시티마켓 직접',
  '카톡전환률', '카톡당CPC',
  '카톡문의', '웹문의', 'CPL', '개통수', '메모'
];

// ============ 1회 셋업: 구글_통합 시트 신설 ============
function createGoogleIntegratedSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(GOOGLE_SHEET);
  let created = false;
  if (!sheet) { sheet = ss.insertSheet(GOOGLE_SHEET); created = true; }

  sheet.getRange(1, 1, 1, GOOGLE_HEADERS.length).setValues([GOOGLE_HEADERS]);
  sheet.getRange(1, 1, 1, GOOGLE_HEADERS.length)
    .setFontWeight('bold').setBackground('#C9DAF8').setHorizontalAlignment('center');
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 100); sheet.setColumnWidth(2, 180); sheet.setColumnWidth(3, 180);

  Logger.log(GOOGLE_SHEET + ' 시트 ' + (created ? '생성' : '헤더 갱신') + ' 완료');
  SpreadsheetApp.flush();
  try {
    SpreadsheetApp.getUi().alert('✅ 구글_통합 시트 ' + (created ? '생성' : '헤더 갱신') + ' 완료.\n\n' +
      'A~F(날짜/캠페인명/광고그룹명/노출/클릭/지출) 수기 입력 → UTM_매핑에 채널=구글 행 추가(광고그룹명→utm_campaign) → 🔄 GA4 매칭 새로고침.');
  } catch (e) {}
  return { sheetId: sheet.getSheetId(), created: created };
}

// ============ GA4 매칭 수식 박기 (전체 행) ============
function syncGoogleGA4(opts) {
  opts = opts || {};
  const interactive = opts.interactive !== false;
  if (typeof ensureUtmNamedRanges_ === 'function') ensureUtmNamedRanges_();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(GOOGLE_SHEET);
  if (!sheet) {
    const msg = '❌ 구글_통합 시트가 없습니다. 🔵 구글 자동화 → 🆕 시트 신설 먼저 실행하세요.';
    Logger.log(msg);
    if (typeof logSync_ === 'function') logSync_('syncGoogleGA4', 'fail', '구글_통합 시트 없음');
    if (interactive) { try { SpreadsheetApp.getUi().alert(msg); } catch (e) {} }
    return { ok: false, error: 'sheet not found' };
  }
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) {
    if (interactive) { try { SpreadsheetApp.getUi().alert('⚠️ 구글_통합 비어있음(헤더만). A~F 데이터 먼저 입력하세요.'); } catch (e) {} }
    return { ok: true, updated: 0 };
  }

  let updated = 0, skipped = 0;
  for (let row = 2; row <= lastRow; row++) {
    const dateCell = sheet.getRange(row, 1).getValue();
    const adgroupName = sheet.getRange(row, 3).getValue();
    if (!dateCell || !adgroupName) { skipped++; continue; }

    let ymdText;
    if (dateCell instanceof Date) ymdText = Utilities.formatDate(dateCell, 'Asia/Seoul', 'yyyyMMdd');
    else ymdText = String(dateCell).replace(/[-/]/g, '');

    const escapedName = String(adgroupName).replace(/"/g, '""');
    const slugLookup = `IFERROR(VLOOKUP("${escapedName}", FILTER(UTM_KEYVAL, UTM_CH="구글"), 2, FALSE),"")`;
    const ga4Base = `'GA4_자동'!A:A,${ymdText},'GA4_자동'!B:B,"google",'GA4_자동'!D:D,${slugLookup}`;

    sheet.getRange(row, 7).setFormula(`=IFERROR(E${row}/D${row},"")`);   // G CTR
    sheet.getRange(row, 8).setFormula(`=IFERROR(F${row}/E${row},"")`);   // H CPC
    sheet.getRange(row, 9).setFormula(`=IFERROR(SUMIFS('GA4_자동'!G:G,${ga4Base},'GA4_자동'!E:E,"session_start"),0)`);     // I GA4세션
    sheet.getRange(row, 10).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"kakao_chat_click"),0)`); // J 카톡클릭
    sheet.getRange(row, 11).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"phone_click"),0)`);      // K 전화클릭
    sheet.getRange(row, 12).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click"),0)`); // L 시티마켓클릭
    sheet.getRange(row, 13).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_arrival"),0)`); // M 시티마켓직접
    sheet.getRange(row, 14).setFormula(`=IFERROR(J${row}/I${row},"")`); // N 카톡전환률
    sheet.getRange(row, 15).setFormula(`=IFERROR(F${row}/J${row},"")`); // O 카톡당CPC
    sheet.getRange(row, 16).setFormula(`=COUNTIFS('문의접수'!D:D,"구글",'문의접수'!A:A,A${row})`); // P 카톡문의
    // Q(17) 웹문의 = 수기 (수식 안 박음, 보존)
    sheet.getRange(row, 18).setFormula(`=IFERROR(IF((P${row}+Q${row})=0,"-",F${row}/(P${row}+Q${row})),"-")`); // R CPL
    updated++;
  }

  Logger.log('syncGoogleGA4: updated=' + updated + ' skipped=' + skipped);
  if (typeof logSync_ === 'function') logSync_('syncGoogleGA4', 'ok', `구글_통합 ${updated} rows GA4 매칭 (skipped: ${skipped})`);
  if (interactive) {
    try {
      SpreadsheetApp.getUi().alert('✅ 구글 GA4 매칭 새로고침 완료\n\n· 갱신 ' + updated + '행 / 스킵 ' + skipped + '행\n· source="google" 기준\n\n' +
        (updated > 0 ? '시트 I~P 확인. 매칭 0이면 🔍 미매핑 광고그룹 보기 → UTM_매핑 채널=구글 행 점검.' : '갱신 행 없음. 데이터 입력 필요.'));
    } catch (e) {}
  }
  return { ok: true, updated: updated, skipped: skipped };
}

// ============ 미매핑 광고그룹 보기 ============
function showUnmappedGoogleAdgroups() {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(GOOGLE_SHEET);
  const utm = ss.getSheetByName('UTM_매핑');
  const ui = SpreadsheetApp.getUi();
  if (!sheet || sheet.getLastRow() < 2) { ui.alert('구글_통합 비어있음/없음.'); return; }
  if (!utm || utm.getLastRow() < 2) { ui.alert('UTM_매핑 시트 없음/비어있음.'); return; }
  // UTM_매핑(채널=구글, utm_campaign 채워진) 광고그룹명 집합
  const uv = utm.getRange(2, 1, utm.getLastRow() - 1, 3).getValues(); // A채널 B광고그룹명 C utm
  const mapped = {};
  uv.forEach(function (r) { if (String(r[0]).trim() === '구글' && r[1] && r[2]) mapped[String(r[1]).trim()] = 1; });
  // 구글_통합 광고그룹명(C) unique
  const gv = sheet.getRange(2, 3, sheet.getLastRow() - 1, 1).getValues();
  const seen = {}, unmapped = [];
  gv.forEach(function (r) {
    const n = String(r[0] || '').trim();
    if (!n || seen[n]) return; seen[n] = 1;
    if (!mapped[n]) unmapped.push(n);
  });
  if (!unmapped.length) { ui.alert('✅ 미매핑 구글 광고그룹 없음.'); return; }
  ui.alert('⚠️ 미매핑 구글 광고그룹 ' + unmapped.length + '개\n\n' + unmapped.map(function (n, i) { return (i + 1) + '. ' + n; }).join('\n') +
    '\n\nUTM_매핑에 [채널=구글 / 광고그룹명 / utm_campaign(GA4 실측값)] 행을 추가하세요.');
}

// ============ 트리거 (매일 02:35, 당근 02:30 다음) ============
function setupGoogleTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'syncGoogleGA4') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('syncGoogleGA4').timeBased().atHour(2).nearMinute(35).everyDays(1).create();
  Logger.log('구글 GA4 매칭 트리거 등록: 매일 02:35');
  try { SpreadsheetApp.getUi().alert('✅ 구글 GA4 매칭 트리거 등록 (매일 02:35).'); } catch (e) {}
}

// ============ 메뉴 ============
function buildGoogleSyncMenu_(ui) {
  ui.createMenu('🔵 구글')
    .addItem('🔄 GA4 매칭 새로고침 (전체 행)', 'syncGoogleGA4')
    .addSeparator()
    .addItem('🆕 시트 신설 / 헤더 갱신', 'createGoogleIntegratedSheet')
    .addItem('🔍 미매핑 광고그룹 보기', 'showUnmappedGoogleAdgroups')
    .addSeparator()
    .addItem('⏰ 구글 Daily Trigger 설정 (02:35)', 'setupGoogleTrigger')
    .addToUi();
}
