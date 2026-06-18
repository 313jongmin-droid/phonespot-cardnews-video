/**
 * ★ 2026-06-11 패치 — 네이버 검색광고 자동 동기화
 *
 * 적용:
 *   1. 기존 meta-sync.gs 끝에 이 블록 통째 박기
 *   2. setupTriggers() 에 syncNaverDaily 트리거 추가 (안내 ↓)
 *   3. buildMetaSyncMenu_(ui) 에 메뉴 1줄 추가
 *   4. 메뉴 → ⏰ Daily Trigger 설정 1회 재실행
 *   5. (테스트) 메뉴 → 🔍 네이버 동기화 1회
 *
 * 사전 조건 (PropertiesService 등록):
 *   - NAVER_API_LICENSE  (Access License)
 *   - NAVER_SECRET_KEY   (비밀 키, 알려주지 말고 직접 등록만)
 *   - NAVER_CUSTOMER_ID  (광고주 ID — 1559128)
 *
 * 네이버 시트 컬럼 매핑:
 *   A 날짜 | B 캠페인/소재 | C 진행사항 | D 비고 | E 노출 | F 클릭 | G 지출
 *   매칭 키: A 날짜 — 있으면 E·F·G 갱신, 없으면 신규 행 append
 *
 * 인증: HMAC-SHA256 시그니처
 *   message = timestamp + "." + method + "." + uri
 *   signature = base64(HMAC-SHA256(SECRET_KEY, message))
 *   headers: X-Timestamp, X-API-KEY, X-Customer, X-Signature
 */

// ============ 네이버 광고 API ============
const NAVER_API_BASE = 'https://api.searchad.naver.com';
const SHEET_NAVER = '네이버';
const NAVER_DATA_START_ROW = 3;  // 행 1 헤더 영역, 행 2 시작 가정 — 다르면 알려줘서 조정


// ============ 메인 ============

function syncNaverDaily(targetDate) {
  Logger.log('=== syncNaverDaily 시작 ===');

  const ymd = targetDate || getYesterday();
  Logger.log('날짜: ' + ymd);

  // 1) 캠페인 목록 조회
  const campaigns = naverFetch_('GET', '/ncc/campaigns');
  if (!campaigns || !Array.isArray(campaigns) || campaigns.length === 0) {
    Logger.log('캠페인 없음');
    if (typeof logSync_ === 'function') logSync_('syncNaverDaily', 'OK (캠페인 0건)');
    return;
  }

  const campaignIds = campaigns.map(c => c.nccCampaignId).filter(Boolean);
  Logger.log('캠페인 ' + campaignIds.length + '개 발견');

  // 2) 어제 통계 (즉시 조회)
  const statsParams = {
    ids: JSON.stringify(campaignIds),
    fields: JSON.stringify(['impCnt', 'clkCnt', 'salesAmt', 'ctr', 'cpc']),
    timeRange: JSON.stringify({ since: ymd, until: ymd }),
    statType: 'CAMPAIGN'
  };

  const stats = naverFetch_('GET', '/stats', statsParams);

  // 3) 합산
  let impressions = 0, clicks = 0, spend = 0;
  const rows = (stats && stats.data) ? stats.data : (Array.isArray(stats) ? stats : []);
  rows.forEach(row => {
    impressions += Number(row.impCnt) || 0;
    clicks += Number(row.clkCnt) || 0;
    spend += Number(row.salesAmt) || 0;
  });
  Logger.log('합계 — 노출:' + impressions + ' 클릭:' + clicks + ' 지출:' + spend + '원');

  // 4) 시트 update/append
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAVER);
  if (!sheet) throw new Error('네이버 시트 없음');

  const targetRow = findNaverDateRow_(sheet, ymd);
  if (targetRow === -1) {
    sheet.appendRow([ymd, '', '', '', impressions, clicks, spend]);
    Logger.log('신규 행 추가 (날짜: ' + ymd + ')');
  } else {
    sheet.getRange(targetRow, 5).setValue(impressions);
    sheet.getRange(targetRow, 6).setValue(clicks);
    sheet.getRange(targetRow, 7).setValue(spend);
    Logger.log('행 ' + targetRow + ' 갱신');
  }

  if (typeof logSync_ === 'function') {
    logSync_('syncNaverDaily', 'OK (노출 ' + impressions + ' / 클릭 ' + clicks + ' / 지출 ' + spend + '원)');
  }
}


// ============ HMAC-SHA256 인증 + 호출 ============

function naverFetch_(method, uri, params) {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('NAVER_API_LICENSE');
  const secret = props.getProperty('NAVER_SECRET_KEY');
  const customerId = props.getProperty('NAVER_CUSTOMER_ID');

  if (!apiKey || !secret || !customerId) {
    throw new Error('NAVER_API_LICENSE / NAVER_SECRET_KEY / NAVER_CUSTOMER_ID 미등록');
  }

  const timestamp = String(Date.now());
  const message = timestamp + '.' + method.toUpperCase() + '.' + uri;
  const sigBytes = Utilities.computeHmacSha256Signature(message, secret);
  const signature = Utilities.base64Encode(sigBytes);

  let url = NAVER_API_BASE + uri;
  if (method === 'GET' && params) {
    const qs = Object.keys(params).map(k =>
      k + '=' + encodeURIComponent(params[k])
    ).join('&');
    url += '?' + qs;
  }

  const options = {
    method: method,
    headers: {
      'Content-Type': 'application/json; charset=UTF-8',
      'X-Timestamp': timestamp,
      'X-API-KEY': apiKey,
      'X-Customer': customerId,
      'X-Signature': signature
    },
    muteHttpExceptions: true
  };

  const res = UrlFetchApp.fetch(url, options);
  const code = res.getResponseCode();
  const text = res.getContentText();

  if (code !== 200) {
    throw new Error('Naver API ' + code + ': ' + text.slice(0, 400));
  }
  return JSON.parse(text);
}


// ============ 헬퍼 ============

function findNaverDateRow_(sheet, dateStr) {
  const lastRow = sheet.getLastRow();
  if (lastRow < NAVER_DATA_START_ROW) return -1;

  const data = sheet.getRange(NAVER_DATA_START_ROW, 1, lastRow - NAVER_DATA_START_ROW + 1, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    const cell = data[i][0];
    let normalized = '';
    if (cell instanceof Date) {
      normalized = Utilities.formatDate(cell, 'Asia/Seoul', 'yyyy-MM-dd');
    } else if (typeof cell === 'string') {
      normalized = cell.replace(/\./g, '-').replace(/\s/g, '');
    }
    if (normalized === dateStr) return NAVER_DATA_START_ROW + i;
  }
  return -1;
}


// ============ 30일 백필 (수동 1회) ============

function backfillNaver30Days() {
  const today = new Date();
  let success = 0, fail = 0;
  for (let i = 29; i >= 1; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const ymd = Utilities.formatDate(d, 'Asia/Seoul', 'yyyy-MM-dd');
    try {
      syncNaverDaily(ymd);
      success++;
      Utilities.sleep(500);
    } catch (e) {
      Logger.log(ymd + ' 실패: ' + e.message);
      fail++;
    }
  }
  SpreadsheetApp.getUi().alert('✅ 네이버 30일 백필 완료\n성공: ' + success + '일 / 실패: ' + fail + '일');
}


// ============ 연결 테스트 ============

function testNaverConnection() {
  try {
    const campaigns = naverFetch_('GET', '/ncc/campaigns');
    const count = Array.isArray(campaigns) ? campaigns.length : 0;
    Logger.log('✅ 네이버 연결 성공: 캠페인 ' + count + '개');
    if (count > 0) {
      Logger.log('첫 캠페인: ' + JSON.stringify(campaigns[0]).slice(0, 300));
    }
    SpreadsheetApp.getUi().alert('✅ 네이버 연결 성공\n캠페인 ' + count + '개');
  } catch (e) {
    Logger.log('❌ ' + e.message);
    SpreadsheetApp.getUi().alert('❌ 네이버 연결 실패\n' + e.message);
  }
}


// ============ 메뉴/트리거 추가 안내 ============
//
// 1. buildMetaSyncMenu_(ui) 안에 추가 (적당한 위치):
//      .addItem('🔍 네이버 동기화', 'syncNaverDaily')
//      .addItem('🔑 토큰 연결 테스트 (네이버)', 'testNaverConnection')
//      .addItem('⏪ 네이버 30일 백필', 'backfillNaver30Days')
//
// 2. setupTriggers() 함수 안 deleteTrigger 조건에 추가:
//      if (fn === 'syncAll' || ... || fn === 'syncNaverDaily') { ... }
//
// 3. setupTriggers() 함수에 트리거 추가 (매일 02:15 권장 — 메타 02:00 다음):
//      ScriptApp.newTrigger('syncNaverDaily')
//        .timeBased().everyDays(1).atHour(2).nearMinute(15).create();



function listAllAdgroups() {
  const campaigns = naverFetch_('GET', '/ncc/campaigns');
  Logger.log('===== 캠페인 ' + campaigns.length + '개 =====');

  campaigns.forEach((c, i) => {
    Logger.log('');
    Logger.log('▶ [' + (i+1) + '] ' + c.name);
    Logger.log('  ID: ' + c.nccCampaignId);
    Logger.log('  customerId: ' + c.customerId);
    Logger.log('  type: ' + c.campaignTp + ' / status: ' + c.status);

    try {
      const adgroups = naverFetch_('GET', '/ncc/adgroups',
        { nccCampaignId: c.nccCampaignId });

      Logger.log('  → 광고그룹 ' + adgroups.length + '개:');
      adgroups.forEach((g, j) => {
        Logger.log('    ' + (j+1) + ') ' + g.name +
                   ' (' + g.nccAdgroupId + ')' +
                   ' / status:' + g.status);
      });

      if (adgroups.length > 0) {
        Logger.log('  [첫 그룹 전체 필드]: ' +
                   JSON.stringify(adgroups[0]).substring(0, 400));
      }
    } catch (e) {
      Logger.log('  광고그룹 조회 실패: ' + e.message);
    }

    Utilities.sleep(300);
  });
}

/**
 * ★ 2026-06-11 패치 — 네이버 광고그룹별 통합 (메타_통합 패턴 그대로)
 *
 * 적용:
 *   1. naver-sync.gs 파일에 이 블록 통째 추가
 *   2. (선택) syncNaverDaily 폐기 — syncNaverIntegrated가 대체
 *   3. meta-sync.gs 의 setupTriggers + 메뉴에 syncNaverIntegrated 추가
 *
 * 신설 시트:
 *   - 네이버_통합 (19컬럼, 메타_통합 동일 구조)
 *   - 네이버_UTM_매핑 (별도, 메타와 분리)
 *
 * 동작 (매일 02:15 syncNaverIntegrated):
 *   1) /ncc/campaigns → 모든 캠페인 (KT 캠페인 자동 제외)
 *   2) 각 캠페인의 /ncc/adgroups → 광고그룹 목록
 *   3) /stats statType=ADGROUP → 광고그룹별 통계
 *   4) 네이버_UTM_매핑 자동 발견 (광고그룹명 → utm_campaign 매핑)
 *   5) 네이버_통합 시트에 광고그룹×일자 행 입력
 *   6) GA4 매칭 수식: utm_source=naver + VLOOKUP(광고그룹명, 네이버_UTM_매핑)
 *
 * KT 필터: 캠페인명에 'KT' 또는 '다이렉트샵' 포함 시 자동 제외
 */

// ============ 상수 ============
const SHEET_NAVER_INTEGRATED = '네이버_통합';
const SHEET_NAVER_UTM_MAPPING = 'UTM_매핑';  // ★ 2026-06-15 통합 (메타와 공용)
const NAVER_KT_FILTER = ['KT', '다이렉트샵'];


// ============ 메인 ============

function syncNaverIntegrated(targetDate) {
  Logger.log('=== syncNaverIntegrated 시작 ===');
  const ymd = targetDate || getYesterday();
  Logger.log('날짜: ' + ymd);

  // 1) 캠페인 + KT 필터
  const allCampaigns = naverFetch_('GET', '/ncc/campaigns');
  if (!allCampaigns || allCampaigns.length === 0) {
    Logger.log('캠페인 없음');
    return;
  }
  const campaigns = allCampaigns.filter(c => {
    const name = String(c.name || '');
    const isKt = NAVER_KT_FILTER.some(k => name.indexOf(k) >= 0);
    if (isKt) Logger.log('  제외 (KT): ' + name);
    return !isKt;
  });
  Logger.log('필터 후 폰스팟 캠페인 ' + campaigns.length + '개');

  // 2) 각 캠페인의 광고그룹 + 어제 통계
  const rows = [];

  for (const c of campaigns) {
    let adgroups;
    try {
      adgroups = naverFetch_('GET', '/ncc/adgroups', { nccCampaignId: c.nccCampaignId });
    } catch (e) {
      Logger.log('광고그룹 조회 실패 ' + c.name + ': ' + e.message);
      continue;
    }
    if (!adgroups || adgroups.length === 0) continue;
    const adgroupIds = adgroups.map(g => g.nccAdgroupId);

    let stats;
    try {
      stats = naverFetch_('GET', '/stats', {
        ids: adgroupIds.join(','),
        fields: JSON.stringify(['impCnt', 'clkCnt', 'salesAmt']),
        timeRange: JSON.stringify({ since: ymd, until: ymd }),
      });
    } catch (e) {
      Logger.log('통계 실패 ' + c.name + ': ' + e.message);
      continue;
    }

    const statByAdgroup = {};
    const statRows = (stats && stats.data) ? stats.data : (Array.isArray(stats) ? stats : []);
    statRows.forEach(row => {
      const id = row.id || row.nccAdgroupId;
      if (id) statByAdgroup[id] = row;
    });

    adgroups.forEach(g => {
      const s = statByAdgroup[g.nccAdgroupId];
      if (!s) return;
      const imp = Number(s.impCnt) || 0;
      const clk = Number(s.clkCnt) || 0;
      const spd = Math.round(Number(s.salesAmt) || 0);
      if (imp === 0 && clk === 0 && spd === 0) return;

      rows.push({
        campaignId: c.nccCampaignId,
        campaignName: c.name,
        adgroupId: g.nccAdgroupId,
        adgroupName: g.name,
        impressions: imp,
        clicks: clk,
        spend: spd
      });
    });

    Utilities.sleep(200);
  }

  if (rows.length === 0) {
    Logger.log('어제 통계 데이터 없음');
    if (typeof logSync_ === 'function') logSync_('syncNaverIntegrated', 'OK (0 광고그룹)');
    return;
  }
  Logger.log('데이터 ' + rows.length + '행');

  // 3) 네이버_통합 시트 준비
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(SHEET_NAVER_INTEGRATED);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAVER_INTEGRATED);
    const headers = ['날짜', '캠페인ID', '캠페인명', '광고그룹ID', '광고그룹명',
                     '노출', '클릭', '지출', 'CTR', 'CPC',
                     'GA4세션', '카톡클릭', '전화클릭', '시티마켓 클릭', '시티마켓 직접', '카톡전환률', '카톡당CPC',
                     '문의수', 'CPL', '개통수', '메모'];
    sh.getRange(1, 1, 1, headers.length).setValues([headers])
      .setBackground('#03C75A').setFontColor('#FFFFFF')
      .setFontWeight('bold').setHorizontalAlignment('center');
    sh.setFrozenRows(1);
    sh.setColumnWidth(1, 90);
    sh.setColumnWidth(2, 220); sh.setColumnWidth(3, 220);
    sh.setColumnWidth(4, 220); sh.setColumnWidth(5, 220);
    for (let c = 6; c <= 16; c++) sh.setColumnWidth(c, 90);
    for (let c = 17; c <= 19; c++) sh.setColumnWidth(c, 100);
  }

  // 4) UTM 자동 발견
  autoDiscoverNaverAdgroups_(rows, ymd);

  // 5) 같은 날짜 행 중복 제거
  const lastRow = sh.getLastRow();
  if (lastRow >= 2) {
    const dates = sh.getRange(2, 1, lastRow - 1, 1).getDisplayValues();
    for (let i = dates.length - 1; i >= 0; i--) {
      if (dates[i][0] === ymd) sh.deleteRow(i + 2);
    }
  }

  // 6) 데이터 추가
  const startRow = sh.getLastRow() + 1;
  rows.forEach((r, i) => {
    const row = startRow + i;
    sh.getRange(row, 1).setValue(new Date(ymd)).setNumberFormat('yyyy-mm-dd');
    sh.getRange(row, 2).setValue(r.campaignId);
    sh.getRange(row, 3).setValue(r.campaignName);
    sh.getRange(row, 4).setValue(r.adgroupId);
    sh.getRange(row, 5).setValue(r.adgroupName);
    sh.getRange(row, 6).setValue(r.impressions).setNumberFormat('#,##0');
    sh.getRange(row, 7).setValue(r.clicks).setNumberFormat('#,##0');
    sh.getRange(row, 8).setValue(r.spend).setNumberFormat('#,##0"원"');
    sh.getRange(row, 9).setFormula(`=IFERROR(G${row}/F${row},0)`).setNumberFormat('0.00%');
    sh.getRange(row, 10).setFormula(`=IFERROR(H${row}/G${row},0)`).setNumberFormat('#,##0"원"');

    // GA4 매칭 — 광고그룹명(E) → 네이버_UTM_매핑 VLOOKUP → 영문 슬러그
    const ymdText = `TEXT(A${row},"yyyymmdd")`;
    const utmSlug = `IFERROR(VLOOKUP(E${row}, FILTER('UTM_매핑'!B:C, 'UTM_매핑'!A:A="네이버"), 2, FALSE),E${row})`;
    const ga4Base = `'GA4_자동'!A:A,${ymdText},'GA4_자동'!B:B,"naver",'GA4_자동'!D:D,${utmSlug}`;
    sh.getRange(row, 11).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!G:G,${ga4Base},'GA4_자동'!E:E,"session_start"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(row, 12).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"kakao_chat_click"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(row, 13).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"phone_click"),0)`
    ).setNumberFormat('#,##0');
    // N (14) = 시티마켓 클릭 (리틀리 경유)
    sh.getRange(row, 14).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click"),0)`
    ).setNumberFormat('#,##0');
    // O (15) = 시티마켓 직접 (광고→시티마켓 직접 도달, GTM 2026-06-15)
    sh.getRange(row, 15).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_arrival"),0)`
    ).setNumberFormat('#,##0');
    // P (16) = 카톡전환률 (위치만 +1)
    sh.getRange(row, 16).setFormula(
      `=IFERROR(IF(K${row}=0,0,L${row}/K${row}),0)`
    ).setNumberFormat('0.00%');
    // Q (17) = 카톡당CPC (위치만 +1)
    sh.getRange(row, 17).setFormula(
      `=IFERROR(IF(L${row}=0,"-",H${row}/L${row}),"-")`
    ).setNumberFormat('#,##0"원"');
    // R (18) = 문의수 자동 매핑 = 문의접수 D열="네이버" + A열=날짜 (2026-06-15)
    sh.getRange(row, 18).setFormula(
      `=COUNTIFS('문의접수'!D:D,"네이버",'문의접수'!A:A,A${row})`
    ).setNumberFormat('#,##0');
    // S (19) = CPL = 지출 / 문의수
    sh.getRange(row, 19).setFormula(
      `=IFERROR(IF(R${row}=0,"-",H${row}/R${row}),"-")`
    ).setNumberFormat('#,##0"원"');
  });

  const msg = '✅ 네이버_통합 ' + ymd + ' ' + rows.length + '개 광고그룹 입력';
  Logger.log(msg);
  if (typeof logSync_ === 'function') logSync_('syncNaverIntegrated', msg);
}


// ============ UTM_매핑 통합 시트 + 자동 발견 (2026-06-15 통합 갱신) ============
// 통합 시트 구조: A 채널 | B 광고그룹명(한글) | C utm_campaign(영문) | D 첫발견일 | E 상태 | F 메모

function ensureNaverUtmMappingSheet_() {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(SHEET_NAVER_UTM_MAPPING);
  if (sh) return sh;

  sh = ss.insertSheet(SHEET_NAVER_UTM_MAPPING);
  sh.getRange(1, 1, 1, 6).setValues([
    ['채널', '광고그룹명(한글)', 'utm_campaign(영문)', '첫 발견일', '상태', '메모']
  ])
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold')
    .setHorizontalAlignment('center').setBorder(true, true, true, true, true, true);
  sh.setColumnWidth(1, 90); sh.setColumnWidth(2, 220); sh.setColumnWidth(3, 180);
  sh.setColumnWidth(4, 110); sh.setColumnWidth(5, 110); sh.setColumnWidth(6, 240);
  sh.setFrozenRows(1);

  // 채널 드롭다운
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['페북', '네이버', '당근', '구글', '카카오'], true).build();
  sh.getRange(2, 1, sh.getMaxRows() - 1, 1).setDataValidation(rule);

  const rules = [
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('⚠️ 매핑 필요')
      .setBackground('#FFE5E5').setFontColor('#C0392B').setBold(true)
      .setRanges([sh.getRange('E2:E1000')]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('✅ 매핑됨')
      .setBackground('#E8F5E9').setFontColor('#1B5E20')
      .setRanges([sh.getRange('E2:E1000')]).build()
  ];
  sh.setConditionalFormatRules(rules);

  Logger.log('UTM_매핑 통합 시트 생성 완료');
  return sh;
}

function autoDiscoverNaverAdgroups_(rows, ymd) {
  const sh = ensureNaverUtmMappingSheet_();
  const dataStartRow = 2;
  const lastRow = sh.getLastRow();

  // 네이버 채널 행만 추출
  const existing = new Set();
  if (lastRow >= dataStartRow) {
    sh.getRange(dataStartRow, 1, lastRow - dataStartRow + 1, 2).getValues()
      .forEach(r => {
        if (r[0] === '네이버' && r[1]) existing.add(String(r[1]).trim());
      });
  }

  const newRows = [];
  rows.forEach(r => {
    const name = String(r.adgroupName || '').trim();
    if (name && !existing.has(name)) {
      newRows.push(['네이버', name, '', ymd, '⚠️ 매핑 필요', '']);
      existing.add(name);
    }
  });

  if (newRows.length > 0) {
    sh.getRange(sh.getLastRow() + 1, 1, newRows.length, 6).setValues(newRows);
    Logger.log('UTM_매핑: 신규 네이버 광고그룹 ' + newRows.length + '건 추가');
  }

  // 상태 갱신 (네이버 행만)
  const newLastRow = sh.getLastRow();
  if (newLastRow >= dataStartRow) {
    const range = sh.getRange(dataStartRow, 1, newLastRow - dataStartRow + 1, 5).getValues();
    range.forEach((row, i) => {
      if (row[0] !== '네이버') return;
      const utm = String(row[2] || '').trim();
      const status = String(row[4] || '').trim();
      const desired = utm ? '✅ 매핑됨' : '⚠️ 매핑 필요';
      if (status !== desired) {
        sh.getRange(dataStartRow + i, 5).setValue(desired);
      }
    });
  }
}



// ============ 미매핑 네이버 광고그룹 보기 (메뉴 호출) ============
function showUnmappedNaverAdgroups() {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(SHEET_NAVER_UTM_MAPPING);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('UTM_매핑 시트 아직 없음. syncNaverIntegrated 1회 실행 후 확인.');
    return;
  }
  if (sheet.getLastRow() < 2) {
    SpreadsheetApp.getUi().alert('UTM_매핑 시트 비어있음.');
    return;
  }
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 3).getValues();
  const unmapped = data.filter(r => r[0] === '네이버' && r[1] && !r[2]);
  if (unmapped.length === 0) {
    SpreadsheetApp.getUi().alert('✅ 미매핑 네이버 광고그룹 없음.');
    return;
  }
  const msg = unmapped.map((r, i) => `${i + 1}. ${r[1]}`).join('\n');
  SpreadsheetApp.getUi().alert(
    `⚠️ 미매핑 네이버 광고그룹 ${unmapped.length}개\n\n${msg}\n\n` +
    `UTM_매핑 시트 C열에 영문 슬러그 박기. 박으면 네이버_통합 GA4 컬럼 자동 매칭.`
  );
}


// ============ 기존 행 GA4 수식 전체 재작성 (옛 네이버_UTM_매핑 참조 잔존 복구, 2026-06-18) ============
// 배경: syncNaverIntegrated는 광고그룹 0개 반환 시 기존 행을 건드리지 않음.
// 그래서 2026-06-16 UTM 통합 이전에 입력된 네이버_통합 행들이 옛
// VLOOKUP('네이버_UTM_매핑') 수식을 그대로 유지 → 해당 시트 삭제로 GA4 매칭 전 행 0.
// 이 함수는 데이터 전 행의 K~S(11~19) 수식을 현재 통합 UTM_매핑(채널="네이버") 기준으로 재작성.
// (당근의 '🔄 GA4 매칭 새로고침 (전체 행)'과 동일 개념. 네이버 집행 재개와 무관하게 1회 실행으로 복구.)
function refreshNaverGA4AllRows() {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName(SHEET_NAVER_INTEGRATED);
  const ui = SpreadsheetApp.getUi();
  if (!sh) { ui.alert('네이버_통합 시트 없음.'); return; }
  const last = sh.getLastRow();
  if (last < 2) { ui.alert('네이버_통합 데이터 행 없음.'); return; }

  for (let row = 2; row <= last; row++) {
    const ymdText = `TEXT(A${row},"yyyymmdd")`;
    const utmSlug = `IFERROR(VLOOKUP(E${row}, FILTER('UTM_매핑'!B:C, 'UTM_매핑'!A:A="네이버"), 2, FALSE),E${row})`;
    const ga4Base = `'GA4_자동'!A:A,${ymdText},'GA4_자동'!B:B,"naver",'GA4_자동'!D:D,${utmSlug}`;
    sh.getRange(row, 11).setFormula(`=IFERROR(SUMIFS('GA4_자동'!G:G,${ga4Base},'GA4_자동'!E:E,"session_start"),0)`);
    sh.getRange(row, 12).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"kakao_chat_click"),0)`);
    sh.getRange(row, 13).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"phone_click"),0)`);
    sh.getRange(row, 14).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click"),0)`);
    sh.getRange(row, 15).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_arrival"),0)`);
    sh.getRange(row, 16).setFormula(`=IFERROR(IF(K${row}=0,0,L${row}/K${row}),0)`);
    sh.getRange(row, 17).setFormula(`=IFERROR(IF(L${row}=0,"-",H${row}/L${row}),"-")`);
    sh.getRange(row, 18).setFormula(`=COUNTIFS('문의접수'!D:D,"네이버",'문의접수'!A:A,A${row})`);
    sh.getRange(row, 19).setFormula(`=IFERROR(IF(R${row}=0,"-",H${row}/R${row}),"-")`);
  }
  SpreadsheetApp.flush();
  const msg = '네이버_통합 ' + (last - 1) + '개 행 GA4 수식 재작성 (통합 UTM_매핑 기준)';
  Logger.log(msg);
  if (typeof logSync_ === 'function') logSync_('refreshNaverGA4AllRows', msg);
  ui.alert('✅ 완료', msg + '\n\nGA4세션·카톡·문의 컬럼이 다시 채워졌는지 확인하세요.', ui.ButtonSet.OK);
}


// ============ 30일 백필 ============

function backfillNaverIntegrated30Days() {
  const today = new Date();
  let success = 0, fail = 0;
  for (let i = 29; i >= 1; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const ymd = Utilities.formatDate(d, 'Asia/Seoul', 'yyyy-MM-dd');
    try {
      syncNaverIntegrated(ymd);
      success++;
      Utilities.sleep(500);
    } catch (e) {
      Logger.log(ymd + ' 실패: ' + e.message);
      fail++;
    }
  }
  SpreadsheetApp.getUi().alert('✅ 네이버_통합 30일 백필 완료\n성공: ' + success + '일 / 실패: ' + fail + '일');
}


// ============ 네이버 자동화 메뉴 (별도) ============

function buildNaverSyncMenu_(ui) {
  ui.createMenu('🟢 네이버 자동화')
    .addItem('📊 광고그룹별 통합 (어제)', 'syncNaverIntegrated')
    .addItem('⏪ 30일 백필', 'backfillNaverIntegrated30Days')
    .addSeparator()
    .addItem('🔍 미매핑 광고그룹 보기', 'showUnmappedNaverAdgroups')
    .addItem('🔄 GA4 수식 전체 재작성 (매핑 복구)', 'refreshNaverGA4AllRows')
    .addItem('🔑 연결 테스트', 'testNaverConnection')
    .addItem('📋 캠페인+그룹 목록 보기', 'listAllAdgroups')
    .addSeparator()
    .addItem('⏰ 네이버 Daily Trigger 설정', 'setupNaverTriggers')
    .addToUi();
}


// ============ 네이버 트리거 (별도) ============

function setupNaverTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'syncNaverIntegrated' || 
        t.getHandlerFunction() === 'syncNaverDaily') {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger('syncNaverIntegrated')
    .timeBased().everyDays(1).atHour(2).nearMinute(15).create();

  Logger.log('네이버 트리거 설정: 매일 02:15 syncNaverIntegrated');
  SpreadsheetApp.getUi().alert('✅ 네이버 트리거 등록',
    '02:15 syncNaverIntegrated\n매일 새벽 자동.',
    SpreadsheetApp.getUi().ButtonSet.OK);
}


function debugNaverStatsIds() {
  const ymd = '2026-05-23';

  const campaigns = naverFetch_('GET', '/ncc/campaigns');
  const target = campaigns.find(c => c.name.includes('리틀리'));
  if (!target) { Logger.log('리틀리 캠페인 없음'); return; }
  Logger.log('▶ 캠페인: ' + target.name + ' / status:' + target.status);

  const adgroups = naverFetch_('GET', '/ncc/adgroups',
    { nccCampaignId: target.nccCampaignId });
  const adgroupIds = adgroups.map(g => g.nccAdgroupId);
  Logger.log('광고그룹 ' + adgroupIds.length + '개');

  // 시도 A — 콤마 구분 다중
  Logger.log('━━━ [A: 콤마 구분 다중] ━━━');
  try {
    const r = naverFetch_('GET', '/stats', {
      ids: adgroupIds.join(','),
      fields: JSON.stringify(['impCnt', 'clkCnt', 'salesAmt']),
      timeRange: JSON.stringify({ since: ymd, until: ymd })
    });
    Logger.log('✅ ' + JSON.stringify(r).substring(0, 800));
  } catch (e) {
    Logger.log('❌ ' + e.message.substring(0, 200));
  }

  Utilities.sleep(500);

  // 시도 B — 단일 ID (첫 그룹)
  Logger.log('━━━ [B: 단일 첫 그룹] ━━━');
  try {
    const r = naverFetch_('GET', '/stats', {
      ids: adgroupIds[0],
      fields: JSON.stringify(['impCnt', 'clkCnt', 'salesAmt']),
      timeRange: JSON.stringify({ since: ymd, until: ymd })
    });
    Logger.log('✅ ' + JSON.stringify(r));
  } catch (e) {
    Logger.log('❌ ' + e.message);
  }

  Utilities.sleep(500);

  // 시도 C — JSON 배열
  Logger.log('━━━ [C: JSON 배열] ━━━');
  try {
    const r = naverFetch_('GET', '/stats', {
      ids: JSON.stringify(adgroupIds),
      fields: JSON.stringify(['impCnt', 'clkCnt', 'salesAmt']),
      timeRange: JSON.stringify({ since: ymd, until: ymd })
    });
    Logger.log('✅ ' + JSON.stringify(r).substring(0, 800));
  } catch (e) {
    Logger.log('❌ ' + e.message.substring(0, 200));
  }
}