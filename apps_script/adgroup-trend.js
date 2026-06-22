/**
 * ★ 2026-06-17 — 광고그룹별 성과 추이 (통합대시보드 R60~R130 영역)
 *
 * 사장님 결정:
 *   - 기간: 7일 / 14일 / 30일 (3일은 데이터 노이즈 큼 = 비채택)
 *   - 차트: 1개 multi-axis (CTR/문의율 좌축% + CPC 우축원)
 *   - 채널: 메타·당근·네이버 (2단 드롭다운: 채널 → 광고그룹)
 *   - 문의율 정의 = 문의수 / 카톡클릭 (사장님 정의)
 *
 * 시트 영역 (통합대시보드):
 *   R60     : 헤더 (병합 A60:O60)
 *   R61     : 토글 — A채널: / B[드롭다운] / D광고그룹: / E[동적] / G기간: / H[드롭다운]
 *   R62     : 안내
 *   R63     : 데이터 헤더 (날짜/노출/클릭/CTR/CPC/카톡클릭/문의수/문의율)
 *   R64~R93 : 데이터 (최대 30일)
 *   R95~    : 차트
 *   W60     : 동적 광고그룹 unique 리스트 (B61 채널에 따라 UNIQUE+FILTER 수식)
 *
 * 사용:
 *   1회: 메뉴 🚀 폰스팟 통합 → 📊 광고그룹 추이 차트 셋업
 *   매번: B61/E61/H61 변경 → 메뉴 🚀 폰스팟 통합 → 🔄 광고그룹 추이 갱신
 */

const ADGROUP_TREND_DASH = '통합대시보드';
const ADGROUP_TREND_DATA_MAX_ROWS = 30;

// 채널별 컬럼 매핑 (1-based)
const ADGROUP_TREND_CHANNELS = {
  '메타': {
    sheet: '메타_통합',
    startRow: 2,
    colDate: 1,       // A
    colName: 5,       // E 광고그룹명
    colImp: 6,        // F 노출
    colClick: 7,      // G 클릭
    colSpend: 8,      // H 지출
    colKakaoClick: 12, // L 카톡클릭
    colInquiry: 18    // R 문의수 (페북+인스타+스레드 합산)
  },
  '당근': {
    sheet: '당근_통합',
    startRow: 2,
    colDate: 1,       // A
    colName: 3,       // C 광고그룹명
    colImp: 4,        // D 노출
    colClick: 5,      // E 클릭
    colSpend: 6,      // F 지출
    colKakaoClick: 10, // J 카톡클릭
    colKakaoInq: 16,  // P 카톡문의
    colAppInq: 17     // Q 앱문의 (수기)
  },
  '네이버': {
    sheet: '네이버_통합',
    startRow: 2,
    colDate: 1,
    colName: 5,
    colImp: 6,
    colClick: 7,
    colSpend: 8,
    colKakaoClick: 12,
    colInquiry: 18
  }
};

// 메뉴 빌더 — Code.js의 onOpen에서 try-catch로 호출
function buildAdgroupTrendMenu_(ui) {
  ui.createMenu('📊 광고그룹 추이')
    .addItem('🆕 차트 셋업 (1회)', 'setupAdgroupTrendChart')
    .addItem('🔄 추이 갱신 (토글 변경 후)', 'refreshAdgroupTrendChart')
    .addItem('⏰ 야간 자동 갱신 트리거 (02:50)', 'setupAdgroupTrendTrigger')
    .addToUi();
}

// 1회 셋업 — 헤더+토글+드롭다운+동적 광고그룹 리스트+빈 데이터 영역+차트 박음
function setupAdgroupTrendChart() {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName(ADGROUP_TREND_DASH);
  if (!sh) {
    SpreadsheetApp.getUi().alert('"통합대시보드" 시트 없음');
    return;
  }

  // R60: 헤더 (병합 A60:O60)
  try { sh.getRange(60, 1, 1, 15).breakApart(); } catch (e) {}
  sh.getRange(60, 1, 1, 15).merge();
  sh.getRange(60, 1)
    .setValue('★ 광고그룹별 성과 추이 (클릭율·CPC·문의율)')
    .setFontWeight('bold').setFontSize(14)
    .setBackground('#1F4E78').setFontColor('#FFFFFF')
    .setHorizontalAlignment('center');

  // R61: 토글 라벨
  sh.getRange(61, 1).setValue('채널:').setFontWeight('bold');
  sh.getRange(61, 4).setValue('광고그룹:').setFontWeight('bold');
  sh.getRange(61, 7).setValue('기간:').setFontWeight('bold');

  // B61 채널 드롭다운
  const channelRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(Object.keys(ADGROUP_TREND_CHANNELS), true)
    .setAllowInvalid(false).build();
  sh.getRange(61, 2).setDataValidation(channelRule);
  if (!sh.getRange(61, 2).getValue()) sh.getRange(61, 2).setValue('메타');

  // E61 광고그룹 동적 드롭다운 (W60:W500 영역 참조)
  const adgroupRule = SpreadsheetApp.newDataValidation()
    .requireValueInRange(sh.getRange('W60:W500'), true)
    .setAllowInvalid(true).build();
  sh.getRange(61, 5).setDataValidation(adgroupRule);

  // H61 기간 드롭다운
  const periodRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['7일', '14일', '30일'], true)
    .setAllowInvalid(false).build();
  sh.getRange(61, 8).setDataValidation(periodRule);
  if (!sh.getRange(61, 8).getValue()) sh.getRange(61, 8).setValue('30일');

  // W60: 채널별 광고그룹 unique 리스트 (B61 변경 시 자동 갱신)
  sh.getRange(60, 23).setFormula(
    '=IFERROR(IF(B61="메타", UNIQUE(FILTER(메타_통합!E2:E, 메타_통합!E2:E<>"")), ' +
    'IF(B61="당근", UNIQUE(FILTER(당근_통합!C2:C, 당근_통합!C2:C<>"")), ' +
    'UNIQUE(FILTER(네이버_통합!E2:E, 네이버_통합!E2:E<>"")))), "")'
  );
  sh.getRange(60, 23).setNote('동적 광고그룹 리스트 (E61 드롭다운 데이터). 숨겨두기 가능.');

  // R62: 안내
  try { sh.getRange(62, 1, 1, 15).breakApart(); } catch (e) {}
  sh.getRange(62, 1, 1, 15).merge();
  sh.getRange(62, 1)
    .setValue('↑ 토글 변경 후 메뉴 📊 광고그룹 추이 → 🔄 추이 갱신 클릭')
    .setFontStyle('italic').setFontColor('#666666');

  // R63: 데이터 헤더
  const dataHeaders = ['날짜', '노출', '클릭', 'CTR', 'CPC', '카톡클릭', '문의수', '문의율', 'CPL'];
  sh.getRange(63, 1, 1, 9).setValues([dataHeaders])
    .setBackground('#f5f5f7').setFontWeight('bold')
    .setHorizontalAlignment('center');

  // R64~R93: 빈 영역
  sh.getRange(64, 1, ADGROUP_TREND_DATA_MAX_ROWS, 9).clearContent();

  // 차트 셋업
  ensureAdgroupTrendChart_(sh);

  SpreadsheetApp.getUi().alert(
    '✅ 광고그룹 추이 셋업 완료.\n\n' +
    '1. R61 토글에서 채널·광고그룹·기간 선택\n' +
    '2. 메뉴 📊 광고그룹 추이 → 🔄 추이 갱신 클릭\n' +
    '3. R64~R93 데이터 + R95~ 차트 자동 갱신'
  );
}

// 데이터 갱신 — B61/E61/H61 토글 읽고 데이터 박음 + 차트 갱신
function refreshAdgroupTrendChart() {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName(ADGROUP_TREND_DASH);
  if (!sh) {
    try { SpreadsheetApp.getUi().alert('"통합대시보드" 시트 없음. 먼저 셋업 메뉴 실행.'); } catch (e) {}
    return;
  }

  const channel = String(sh.getRange(61, 2).getValue() || '').trim();
  const adgroupName = String(sh.getRange(61, 5).getValue() || '').trim();
  const periodStr = String(sh.getRange(61, 8).getValue() || '30일');
  const days = parseInt(periodStr.replace(/[^\d]/g, '')) || 30;

  // R64~R93 비움
  sh.getRange(64, 1, ADGROUP_TREND_DATA_MAX_ROWS, 9).clearContent();

  if (!channel || !adgroupName) {
    sh.getRange(64, 1).setValue('⚠️ 채널 + 광고그룹 선택 필요').setFontStyle('italic').setFontColor('#C0392B');
    return;
  }

  const cfg = ADGROUP_TREND_CHANNELS[channel];
  if (!cfg) {
    sh.getRange(64, 1).setValue('⚠️ 알 수 없는 채널: ' + channel).setFontStyle('italic');
    return;
  }

  const sourceSheet = ss.getSheetByName(cfg.sheet);
  if (!sourceSheet || sourceSheet.getLastRow() < 2) {
    sh.getRange(64, 1).setValue('⚠️ "' + cfg.sheet + '" 시트 비어있음').setFontStyle('italic');
    return;
  }

  // 데이터 추출 (필요 컬럼만)
  const lastRow = sourceSheet.getLastRow();
  const maxCol = Math.max(
    cfg.colInquiry || 0, cfg.colAppInq || 0, cfg.colKakaoInq || 0, 18
  );
  const data = sourceSheet.getRange(cfg.startRow, 1, lastRow - cfg.startRow + 1, maxCol).getValues();

  const tz = 'Asia/Seoul';
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const sinceDate = new Date(today);
  sinceDate.setDate(today.getDate() - days);

  // 일자별 합산 (광고그룹명 일치 + 기간 내)
  const dailyMap = {};
  data.forEach(function (row) {
    const dt = row[cfg.colDate - 1];
    const name = String(row[cfg.colName - 1] || '').trim();
    if (!(dt instanceof Date)) return;
    if (name !== adgroupName) return;
    if (dt < sinceDate) return;
    if (dt > today) return;

    const key = Utilities.formatDate(dt, tz, 'yyyy-MM-dd');
    if (!dailyMap[key]) {
      dailyMap[key] = { date: new Date(dt), imp: 0, click: 0, spend: 0, kakaoClick: 0, inquiry: 0 };
    }
    dailyMap[key].imp += Number(row[cfg.colImp - 1]) || 0;
    dailyMap[key].click += Number(row[cfg.colClick - 1]) || 0;
    dailyMap[key].spend += Number(row[cfg.colSpend - 1]) || 0;
    dailyMap[key].kakaoClick += Number(row[cfg.colKakaoClick - 1]) || 0;
    if (channel === '당근') {
      dailyMap[key].inquiry += (Number(row[cfg.colKakaoInq - 1]) || 0) + (Number(row[cfg.colAppInq - 1]) || 0);
    } else {
      dailyMap[key].inquiry += Number(row[cfg.colInquiry - 1]) || 0;
    }
  });

  // 날짜순 정렬
  const keys = Object.keys(dailyMap).sort();
  if (keys.length === 0) {
    sh.getRange(64, 1).setValue('해당 기간(' + days + '일) 데이터 없음').setFontStyle('italic').setFontColor('#666666');
    ensureAdgroupTrendChart_(sh);
    return;
  }

  const rows = keys.slice(-ADGROUP_TREND_DATA_MAX_ROWS).map(function (k) {
    const d = dailyMap[k];
    const ctr = d.imp > 0 ? d.click / d.imp : 0;
    const cpc = d.click > 0 ? d.spend / d.click : 0;
    const inquiryRate = d.kakaoClick > 0 ? d.inquiry / d.kakaoClick : 0;
    const cpl = d.inquiry > 0 ? d.spend / d.inquiry : 0;
    return [d.date, d.imp, d.click, ctr, cpc, d.kakaoClick, d.inquiry, inquiryRate, cpl];
  });

  // R64~ 박음
  sh.getRange(64, 1, rows.length, 9).setValues(rows);
  // 포맷
  sh.getRange(64, 1, rows.length, 1).setNumberFormat('yyyy-mm-dd');
  sh.getRange(64, 2, rows.length, 2).setNumberFormat('#,##0');
  sh.getRange(64, 4, rows.length, 1).setNumberFormat('0.00%');
  sh.getRange(64, 5, rows.length, 1).setNumberFormat('#,##0"원"');
  sh.getRange(64, 6, rows.length, 2).setNumberFormat('#,##0');
  sh.getRange(64, 8, rows.length, 1).setNumberFormat('0.00%');
  sh.getRange(64, 9, rows.length, 1).setNumberFormat('#,##0"원"'); // CPL

  // 차트 갱신
  ensureAdgroupTrendChart_(sh);

  Logger.log('refreshAdgroupTrendChart: ' + channel + ' / ' + adgroupName + ' / ' + days + '일 / ' + rows.length + '행');
}

// 차트 생성/갱신 — 기존 영역 차트 제거 후 새로 박음
function ensureAdgroupTrendChart_(sh) {
  // 기존 차트 제거 (R63~R94 영역 참조하는 차트만)
  sh.getCharts().forEach(function (c) {
    const ranges = c.getRanges();
    const hit = ranges.some(function (r) {
      return r.getRow() >= 63 && r.getRow() <= 94 && r.getColumn() <= 8;
    });
    if (hit) sh.removeChart(c);
  });

  // 데이터 범위 (날짜 + CTR + CPC + 문의율 3개 지표)
  const dateRange = sh.getRange(63, 1, ADGROUP_TREND_DATA_MAX_ROWS + 1, 1);  // A: 날짜
  const ctrRange = sh.getRange(63, 4, ADGROUP_TREND_DATA_MAX_ROWS + 1, 1);   // D: CTR
  const inqRange = sh.getRange(63, 8, ADGROUP_TREND_DATA_MAX_ROWS + 1, 1);   // H: 문의율
  const cplRange = sh.getRange(63, 9, ADGROUP_TREND_DATA_MAX_ROWS + 1, 1);   // I: CPL

  // 차트 = CTR·문의율(좌축 %) + CPL(우축 원). CPC는 표에만(스케일 충돌 회피).
  const chart = sh.newChart()
    .setChartType(Charts.ChartType.LINE)
    .addRange(dateRange)
    .addRange(ctrRange)
    .addRange(inqRange)
    .addRange(cplRange)
    .setNumHeaders(1)
    .setPosition(95, 1, 0, 0)
    .setOption('title', '광고그룹별 성과 추이 (CTR·문의율·CPL)')
    .setOption('width', 900)
    .setOption('height', 400)
    .setOption('useFirstColumnAsDomain', true)
    .setOption('series', {
      0: { targetAxisIndex: 0, color: '#1976D2', lineWidth: 2 },  // CTR
      1: { targetAxisIndex: 0, color: '#D32F2F', lineWidth: 2 },  // 문의율
      2: { targetAxisIndex: 1, color: '#388E3C', lineWidth: 3 }   // CPL
    })
    .setOption('vAxes', {
      0: { title: 'CTR·문의율 (%)', format: '0.00%' },
      1: { title: 'CPL (원)', format: '#,##0' }
    })
    .setOption('hAxis', { title: '날짜', format: 'M/d' })
    .setOption('legend', { position: 'right' })
    .setOption('pointSize', 4)
    .build();

  sh.insertChart(chart);
}


// ============ ★ 야간 광고그룹 추이 자동 갱신 트리거 (2026-06-18) ============
function setupAdgroupTrendTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'refreshAdgroupTrendChart') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('refreshAdgroupTrendChart').timeBased().atHour(2).nearMinute(50).everyDays(1).create();
  SpreadsheetApp.getUi().alert('✅ 광고그룹 추이 야간 트리거 등록 (매일 02:50). 현재 토글 기준 자동 갱신.');
}


// ============ ★ 2026-06-22 토글 편집 시 자동 갱신 (메뉴 클릭 불필요) ============
// 통합대시보드 B61(채널)/E61(광고그룹)/H61(기간) 편집 시 자동으로 추이 재계산+차트 갱신.
// 단순 onEdit 트리거(설치 불필요). SpreadsheetApp만 사용해 권한 문제 없음.
function onEdit(e) {
  try {
    if (!e || !e.range) return;
    const sh = e.range.getSheet();
    if (sh.getName() !== ADGROUP_TREND_DASH) return;
    const r = e.range.getRow(), c = e.range.getColumn();
    if (r !== 61) return;
    if (c !== 2 && c !== 5 && c !== 8) return; // B61 채널 / E61 광고그룹 / H61 기간
    refreshAdgroupTrendChart();
  } catch (err) {
    Logger.log('onEdit 추이 자동갱신 실패: ' + err.message);
  }
}
