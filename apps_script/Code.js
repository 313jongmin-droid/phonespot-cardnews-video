// ════════════════════════════════════════════════════════════
//  폰스팟 광고운영 관리대장 — Apps Script (메뉴 정리본: 2026-05-29)
//  ★ 2026-06-11 패치: updateChannelMatrixWithGA4 + updateKPISummary
//     메타 → 메타+, 네이버 → 네이버+ (광고그룹 단위 자동 합산)
//  [일상] 매일 자동/메뉴 실행  [수동] 필요시 직접 실행  [유틸] 보조
// ════════════════════════════════════════════════════════════

const GA4_PROP_ID = '534396517';
const GA4_AUTO_SHEET = 'GA4_자동';
const INQUIRY_SHEET = '문의접수';
// 카톡 리포트는 별도 시트가 아니라 문의접수 시트 우측 H:Q 영역에 내장
const KAKAO_REPORT_START_COL = 8; // H열
const KAKAO_REPORT_NUM_COLS = 10;
const KAKAO_REPORT_HEADER_ROW = 4;
const KAKAO_REPORT_DATA_ROW = 5;

// ──[일상]── 시트 열 때 커스텀 메뉴 생성
// ★ 브랜드 설정 접근자 (멀티브랜드, 2026-06-28) — 우선순위: _설정 시트 → Script Property → 폴백.
//   비밀값(토큰/키)은 여기 거치지 말 것(시트 노출 금지). 비밀 아닌 브랜드설정만.
var _brandCfgCache = null;
function getBrandConfig_(key, fallback) {
  if (_brandCfgCache === null) {
    _brandCfgCache = {};
    try {
      var sh = SpreadsheetApp.getActive().getSheetByName('_설정');
      if (sh && sh.getLastRow() >= 1) {
        sh.getRange(1, 1, sh.getLastRow(), 2).getValues().forEach(function (r) {
          var k = String(r[0] || '').trim();
          if (k) _brandCfgCache[k] = r[1];
        });
      }
    } catch (e) {}
  }
  var v = _brandCfgCache[key];
  if (v !== undefined && v !== null && String(v).trim() !== '') return v;
  try {
    var pv = PropertiesService.getScriptProperties().getProperty(key);
    if (pv !== null && String(pv).trim() !== '') return pv;
  } catch (e) {}
  return fallback;
}
// 캠페인 통신사 필터 — mode: exclude(키워드 제외=폰스팟)/include(키워드만=KT폰샵)/none(전부)
function passesCarrierFilter_(name) {
  var mode = String(getBrandConfig_('CARRIER_FILTER_MODE', 'exclude')).trim();
  if (mode === 'none') return true;
  var kws = String(getBrandConfig_('CARRIER_FILTER_KEYWORDS', 'KT,다이렉트샵'))
    .split(',').map(function (x) { return x.trim(); }).filter(Boolean);
  var hit = kws.some(function (k) { return String(name || '').indexOf(k) >= 0; });
  return (mode === 'include') ? hit : !hit;
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🚀 ' + getBrandConfig_('BRAND_NAME', '폰스팟') + ' 통합')
    .addItem('⚡ 전체 새로고침 (모든 채널)', 'refreshAll')
    .addSeparator()
    .addItem('🔄 GA4 최신 데이터 가져오기 (어제)', 'fetchGA4Daily')
    .addItem('📥 GA4 30일 다시 가져오기 (백필)', 'fetchGA4Backfill')
    .addSeparator()
    .addItem('📊 SNS 월별 합계 수식 복구', 'repairSNSMonthlySummaries')
    .addItem('🏷️ UTM 슬러그 드롭다운 갱신', 'refreshUtmSlugDropdowns')
    .addItem('🔍 GA4 미매핑 슬러그 → UTM 추가', 'appendUnmappedUtmFromGA4')
    .addItem('🔗 UTM named range 셋업/복구', 'setupUtmNamedRanges')
    .addItem('⏰ 야간 전체 새로고침 트리거 (02:45)', 'setupRefreshAllTrigger')
    .addToUi();

  // 📘 메타 자동화 메뉴 (meta-sync.gs)
  try { buildMetaSyncMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 🎥 유튜브 자동화 메뉴 (youtube_sync.gs)
  try { addYouTubeMenuItem(); } catch (e) {}

  // 🟢 네이버 자동화 메뉴 (naver-sync.gs)
  try { buildNaverSyncMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 🟠 당근 자동화 메뉴 (danggn-sync.gs, 2026-06-15)
  try { buildDanggnSyncMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 🔵 구글 자동화 메뉴 (google-sync.js, 2026-06-19)
  try { buildGoogleSyncMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 📊 광고그룹 추이 메뉴 (adgroup-trend.gs, 2026-06-17)
  try { buildAdgroupTrendMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 🔔 알림/모니터링 메뉴 (alerts.js, 2026-06-18)
  try { buildAlertsMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 🎨 소재 인사이트 메뉴 (creative_insights.js, 2026-06-18)
  try { buildCreativeInsightsMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 🤖 자연어 데이터 질문 메뉴 (nl_query.js, 2026-06-18)
  try { buildNlQueryMenu_(SpreadsheetApp.getUi()); } catch (e) {}
}

// ──[일상]── 전체 새로고침: 모든 채널 sync + 대시보드 빌드 + 인사이트 MD 생성 (2026-06-15 강화)
function refreshAll() {
  let ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) {}
  const errors = [];
  try { ensureUtmNamedRanges_(); } catch (e) {}

  // ★ 2026-06-22: GA4 원본 일일 수집 (이게 트리거에 빠져 있어 GA4_자동이 수동 실행 때만 갱신됐음)
  try { fetchGA4Daily(); } catch (e) { errors.push('fetchGA4Daily: ' + e.message); Logger.log(e); }

  // ===== 1단계: 외부 API 데이터 sync (모든 채널) =====
  try { syncAll(); }
  catch (e) { errors.push('syncAll(메타+GA4): ' + e.message); Logger.log(e); }

  // ★ 2026-06-15: 네이버 자동화 추가
  try { if (typeof syncNaverIntegrated === 'function') syncNaverIntegrated(); }
  catch (e) { errors.push('syncNaverIntegrated: ' + e.message); Logger.log(e); }

  // ★ 2026-06-15: 인스타 자동화 추가
  try { if (typeof syncInstagramDaily === 'function') syncInstagramDaily(); }
  catch (e) { errors.push('syncInstagramDaily: ' + e.message); Logger.log(e); }

  // ★ 2026-06-15: 당근 GA4 매칭 추가 (시트 비어있으면 silent)
  try { if (typeof syncDanggnGA4 === 'function') syncDanggnGA4({ interactive: false }); }
  catch (e) { errors.push('syncDanggnGA4: ' + e.message); Logger.log(e); }

  try { if (typeof syncGoogleGA4 === 'function') syncGoogleGA4({ interactive: false }); }
  catch (e) { errors.push('syncGoogleGA4: ' + e.message); Logger.log(e); }

  try { fetchYouTubeAnalyticsDaily(); }
  catch (e) { errors.push('fetchYouTubeAnalyticsDaily: ' + e.message); Logger.log(e); }

  // ===== 2단계: 인사이트 MD 생성 (Drive 저장) =====
  try { generateMetaInsightsMarkdown(); }
  catch (e) { errors.push('generateMetaInsightsMarkdown: ' + e.message); Logger.log(e); }

  try { generateYouTubeInsightsMarkdown(); }
  catch (e) { errors.push('generateYouTubeInsightsMarkdown: ' + e.message); Logger.log(e); }

  // ===== 3단계: 대시보드 빌드 (수식/UI 재구성) =====
  try { buildDashboardV2(); } catch (e) { errors.push('buildDashboardV2: ' + e.message); }
  try { repairSNSMonthlySummaries(false); } catch (e) { errors.push('repairSNSMonthlySummaries: ' + e.message); }
  try { addTimeSeriesChart(); } catch (e) { errors.push('addTimeSeriesChart: ' + e.message); }


  const stamp = recordLastRefresh_();

  if (typeof logSync_ === 'function') logSync_('refreshAll', errors.length ? ('부분완료 ' + errors.length + '건') : '완료 ' + stamp);
  if (errors.length === 0) {
    if (ui) ui.alert('✅ 전체 새로고침 완료\n🕐 ' + stamp +
             '\n\n· GA4 + 메타 + 네이버 + 인스타 + 당근 + 유튜브 sync\n· 메타 + 유튜브 인사이트 MD\n· 대시보드 + KPI 갱신');
  } else {
    if (ui) ui.alert('⚠️ 부분 완료\n🕐 ' + stamp +
             '\n\n실패 ' + errors.length + '건:\n' + errors.slice(0, 5).join('\n') +
             (errors.length > 5 ? '\n... 외 ' + (errors.length - 5) + '건' : ''));
  }
}

// ──[유틸]── 최근 전체 업데이트 시각 기록 (통합대시보드 A46) — refreshAll이 호출
function recordLastRefresh_() {
  // 2026-06-22: 통합대시보드 시각은 buildDashboardV2 푸터가 기록. 여기선 시각 문자열만 반환.
  return Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');
}

// ──[일상]── 어제 GA4 데이터 수집 (매일 새벽 트리거가 호출)
function fetchGA4Daily() {
  // ★ self-heal: 어제 1일 → 최근 N일 각각 importGA4(ymd,ymd) (날짜별 upsert라 중복 없음).
  //   GA4 일일 수집이 하루 실패/미실행해도 다음날 자동 보강(메타·네이버 self-heal과 동일 정책).
  const TZ = 'Asia/Seoul';
  var days = (typeof SELF_HEAL_DAYS !== 'undefined') ? SELF_HEAL_DAYS : 7;
  for (var i = days; i >= 1; i--) {
    var d = new Date(); d.setDate(d.getDate() - i);
    var ymd = Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
    try { importGA4(ymd, ymd, false); Utilities.sleep(300); }
    catch (e) { Logger.log('GA4 ' + ymd + ' 실패: ' + e.message); }
  }
}

// ──[수동]── 최근 30일 GA4 데이터 전체 다시 수집
function fetchGA4Backfill() {
  importGA4('30daysAgo', 'yesterday', true);
}

// ──[일상]── GA4 Data API 호출 → GA4_자동 시트 적재
function importGA4(startDate, endDate, clearAll) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(GA4_AUTO_SHEET);
  if (!sh) {
    sh = ss.insertSheet(GA4_AUTO_SHEET);
    sh.getRange('A1:H1').merge();
    sh.getRange('A1').setValue('■ GA4 자동 수집 (Data API, 매일 새벽 1시)')
      .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(12);
    sh.getRange('A2:H2').merge();
    sh.getRange('A2').setValue('※ 행 5~ 자동. 수동 입력 금지.')
      .setFontStyle('italic').setFontColor('#666');
    sh.getRange('A4:H4').setValues([['date','sessionSource','sessionMedium','sessionCampaignName','eventName','eventCount','sessions','totalUsers']])
      .setBackground('#D9E1F2').setFontWeight('bold');
    sh.setColumnWidths(1, 8, 130);
  }

  const request = {
    dateRanges: [{startDate: startDate, endDate: endDate}],
    dimensions: [
      {name: 'date'}, {name: 'sessionSource'}, {name: 'sessionMedium'},
      {name: 'sessionCampaignName'}, {name: 'eventName'}
    ],
    metrics: [
      {name: 'eventCount'}, {name: 'sessions'}, {name: 'totalUsers'}
    ],
    orderBys: [{dimension: {dimensionName: 'date'}, desc: true}],
    limit: 100000
  };

  const response = AnalyticsData.Properties.runReport(request, 'properties/' + getBrandConfig_('GA4_PROP_ID', GA4_PROP_ID));
  if (!response.rows || response.rows.length === 0) {
    Logger.log('No data ' + startDate + '~' + endDate);
    return;
  }

  if (clearAll) {
    const lastRow = sh.getLastRow();
    if (lastRow >= 5) sh.getRange(5, 1, lastRow - 4, 8).clearContent();
  } else {
    const ymdAPI = startDate.replace(/-/g, '');
    const dateCol = sh.getRange('A:A').getValues();
    const rowsToDelete = [];
    for (let i = 4; i < dateCol.length; i++) {
      if (dateCol[i][0] && String(dateCol[i][0]) === ymdAPI) rowsToDelete.push(i + 1);
    }
    for (let i = rowsToDelete.length - 1; i >= 0; i--) sh.deleteRow(rowsToDelete[i]);
  }

  const rows = response.rows.map(row => [
    row.dimensionValues[0].value,
    row.dimensionValues[1].value,
    row.dimensionValues[2].value,
    row.dimensionValues[3].value,
    row.dimensionValues[4].value,
    parseInt(row.metricValues[0].value),
    parseInt(row.metricValues[1].value),
    parseInt(row.metricValues[2].value)
  ]);

  let lastRow = 4;
  const dateCol2 = sh.getRange('A:A').getValues();
  for (let i = dateCol2.length - 1; i >= 0; i--) {
    if (dateCol2[i][0]) { lastRow = i + 1; break; }
  }
  sh.getRange(lastRow + 1, 1, rows.length, 8).setValues(rows);
  Logger.log('OK ' + startDate + '~' + endDate + ': ' + rows.length + ' rows');
}

// ──[일상]── 핵심 KPI 상세 (행 9-14) 재구성 — CPL 2종 (전체/추적)
// ★ 2026-06-11 패치: 메타 → 메타+(H), 네이버 → 네이버+(H)
function updateKPISummary() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('통합대시보드');

  // A9:I15 클리어 (어제/3일/7일/14일/30일 = 5행)
  sh.getRange('A9:I15').clearContent().clearFormat();

  // 행 9: 섹션 헤더
  sh.getRange('A9:I9').merge().setValue('★ 핵심 KPI 상세 (위 카드의 원천)')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(13);

  // 행 10: 컬럼 헤더 — CPL(전체) 컬럼 신규 추가
  const h = ['기간','광고소진','문의','출처확인','개통','개통률','리틀리CTR','CPL(추적)','CPL(전체)'];
  sh.getRange(10, 1, 1, 9).setValues([h])
    .setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center')
    .setBorder(true,true,true,true,true,true);

  const periods = [
    ['어제',       'TODAY()-1',  'TODAY()-1'],
    ['최근 3일',   'TODAY()-2',  'TODAY()'],
    ['최근 7일',   'TODAY()-6',  'TODAY()'],
    ['최근 14일',  'TODAY()-13', 'TODAY()'],
    ['최근 30일',  'TODAY()-29', 'TODAY()'],
  ];

  // ★ 패치: 채널별 광고비 시트/컬럼 매핑 (자동수집 채널은 통합 시트 H열 지출)
  const ADS = [
    {sh:'메타+',   spd:'H'},
    {sh:'구글',        spd:'G'},
    {sh:'네이버+', spd:'H'},
    {sh:'카카오',      spd:'G'},
    // 당근 KPI 광고비: 옛 당근 시트 G열. 전환 시 {sh:'당근+', spd:'F'} 로 교체
    {sh:'당근',        spd:'G'},
  ];

  periods.forEach(([lbl, st, en], i) => {
    const r = 11 + i;
    const sumPaid = ADS.map(a =>
      `SUMIFS('${a.sh}'!${a.spd}:${a.spd},'${a.sh}'!A:A,">="&${st},'${a.sh}'!A:A,"<="&${en})`
    ).join('+');
    const countInq = (extra='') => `COUNTIFS('문의접수'!A:A,">="&${st},'문의접수'!A:A,"<="&${en}${extra})`;
    const sumLi = (col) => `SUMIFS('리틀리'!${col}:${col},'리틀리'!A:A,">="&${st},'리틀리'!A:A,"<="&${en})`;

    sh.getRange(r, 1).setValue(lbl).setFontWeight('bold');
    sh.getRange(r, 2).setFormula(`=${sumPaid}`).setNumberFormat('#,##0"원"');
    sh.getRange(r, 3).setFormula(`=${countInq()}`).setNumberFormat('#,##0"건"');
    sh.getRange(r, 4).setFormula(`=${countInq()}-${countInq(",'문의접수'!D:D,\"불확실\"")}-${countInq(",'문의접수'!D:D,\"\"")}`).setNumberFormat('#,##0"건"');
    sh.getRange(r, 5).setFormula(`=${countInq(",'문의접수'!C:C,\"개통\"")}`).setNumberFormat('#,##0"건"');
    sh.getRange(r, 6).setFormula(`=IFERROR(E${r}/D${r},"-")`).setNumberFormat('0.0%');
    sh.getRange(r, 7).setFormula(`=IFERROR(${sumLi('C')}/${sumLi('B')},"-")`).setNumberFormat('0.0%');
    sh.getRange(r, 8).setFormula(`=IFERROR(B${r}/D${r},"-")`).setNumberFormat('#,##0"원"');
    sh.getRange(r, 9).setFormula(`=IFERROR(B${r}/C${r},"-")`).setNumberFormat('#,##0"원"');
    sh.getRange(r, 1, 1, 9).setBorder(true,true,true,true,true,true).setHorizontalAlignment('center');
  });

  SpreadsheetApp.getUi().alert('✅ 핵심 KPI 갱신 완료\n· 메타/네이버 = 통합 시트 합산 (광고그룹 단위)\n· CPL(추적): 출처확인된 문의 기준\n· CPL(전체): 모든 문의 기준');
}

// ──[일상]── 채널 매트릭스 재구성 (E16 드롭다운으로 기간 변경: 어제/7일/30일)
// ★ 2026-06-11 패치: 메타/네이버 = 통합 시트 F(노출)/G(클릭)/H(지출), 기타 = 기존 E/F/G
function updateChannelMatrixWithGA4() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('통합대시보드');

  // ── 행 16: 섹션 헤더 + 기간 드롭다운 ──
  sh.getRange('A16:Z16').breakApart();
  sh.getRange('A16:Z16').clearContent().clearFormat();
  sh.getRange('A16:C16').merge().setValue('★ 채널별 효율 매트릭스')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(13);

  sh.getRange('D16').setValue('📅 기간:').setFontWeight('bold').setHorizontalAlignment('right');
  sh.getRange('E16').setBackground('#FFF59D').setFontWeight('bold').setHorizontalAlignment('center')
    .setDataValidation(SpreadsheetApp.newDataValidation()
      .requireValueInList(['어제','최근 3일','최근 7일','최근 30일'], true).setAllowInvalid(false).build());
  if (sh.getRange('E16').getValue() === '') sh.getRange('E16').setValue('최근 30일');

  sh.getRange('M16').setValue('기간▶').setFontColor('#BBBBBB').setFontSize(8).setHorizontalAlignment('right');
  sh.getRange('N16').setFormula('=IF($E$16="어제",TODAY()-1,IF($E$16="최근 3일",TODAY()-2,IF($E$16="최근 7일",TODAY()-6,TODAY()-29)))')
    .setNumberFormat('m/d').setFontColor('#BBBBBB');
  sh.getRange('O16').setFormula('=IF($E$16="어제",TODAY()-1,TODAY())')
    .setNumberFormat('m/d').setFontColor('#BBBBBB');

  // A17:Z24 클리어 (행16, 행25 네비게이션 보존)
  sh.getRange('A17:Z24').clearContent().clearFormat();

  // 행 17 헤더
  const h = ['채널','노출','클릭','소진','광고문의','GA4세션','카톡클릭','전화클릭','시티마켓','카톡전환률','카톡당CPC','평가'];
  sh.getRange(17, 1, 1, 12).setValues([h])
    .setBackground('#1F4E78').setFontColor('#FFFFFF')
    .setFontWeight('bold').setHorizontalAlignment('center');

  // ★ 패치: 채널 정의 — adSheet/impCol/clkCol/spdCol 분리
  //   메타+ / 네이버+ = 광고그룹 단위 19컬럼 (F=노출 G=클릭 H=지출)
  //   구글 / 카카오 / 당근 = 수동 입력 시트 (E=노출 F=클릭 G=지출)
  const channels = [
    {row:18, name:'메타',   adSheet:'메타+',   impCol:'F', clkCol:'G', spdCol:'H', inq:'메타',   ga4:true,  sources:['meta','facebook.com','m.facebook.com','l.facebook.com']},
    {row:19, name:'구글',   adSheet:'구글',        impCol:'E', clkCol:'F', spdCol:'G', inq:'구글',   ga4:true,  sources:['google']},
    {row:20, name:'네이버', adSheet:'네이버+', impCol:'F', clkCol:'G', spdCol:'H', inq:'네이버', ga4:true,  sources:['naver','naver_blog','ad.search.naver.com','m.ad.search.naver.com','m.search.naver.com']},
    {row:21, name:'카카오', adSheet:'카카오',      impCol:'E', clkCol:'F', spdCol:'G', inq:'카카오', ga4:true,  sources:['kakao']},
    // 당근 (현재 = 옛 당근 시트 11컬럼 G열 지출 합산 유지. 다운그레이드 0)
    // ★ 2026-06-15 신설된 당근+ 시트 (17컬럼)로 전환 시 = 아래 줄로 교체:
    //   {row:22, name:'당근', adSheet:'당근+', impCol:'D', clkCol:'E', spdCol:'F', inq:'당근', ga4:true, sources:['daangn','danggn']},
    // 전환 조건: 사장님이 옛 당근 시트 입력 중단 + 당근+으로 일원화. 이중 합산 위험 회피.
    {row:22, name:'당근',   adSheet:'당근',        impCol:'E', clkCol:'F', spdCol:'G', inq:'당근',   ga4:true,  sources:['daangn','danggn']},
  ];

  const fmtKM = '[>=1000000]0.00,,"M";[>=1000]0.0,"K";#,##0';
  const fmtKMWon = '[>=1000000]0.00,,"M원";[>=1000]0.0,"K원";#,##0"원"';
  const ga4D = `'GA4_자동'!A:A,">="&TEXT($N$16,"yyyymmdd"),'GA4_자동'!A:A,"<="&TEXT($O$16,"yyyymmdd")`;

  channels.forEach(({row, name, adSheet, impCol, clkCol, spdCol, inq, ga4, sources}) => {
    sh.getRange(row, 1).setValue(name).setFontWeight('bold');
    const ad = (col) => `SUMIFS('${adSheet}'!${col}:${col},'${adSheet}'!A:A,">="&$N$16,'${adSheet}'!A:A,"<="&$O$16)`;
    sh.getRange(row, 2).setFormula(`=IFERROR(${ad(impCol)},0)`).setNumberFormat(fmtKM);
    sh.getRange(row, 3).setFormula(`=IFERROR(${ad(clkCol)},0)`).setNumberFormat(fmtKM);
    sh.getRange(row, 4).setFormula(`=IFERROR(${ad(spdCol)},0)`).setNumberFormat(fmtKMWon);
    sh.getRange(row, 5).setFormula(`=COUNTIFS('문의접수'!A:A,">="&$N$16,'문의접수'!A:A,"<="&$O$16,'문의접수'!D:D,"${inq}")`).setNumberFormat('#,##0"건"');

    if (!ga4) {
      sh.getRange(row, 6, 1, 6).setValues([['-','-','-','-','-','-']]);
      sh.getRange(row, 12).setValue('GA4 무관');
    } else {
      const ev = (e) => sources.map(s =>
        `SUMIFS('GA4_자동'!F:F,'GA4_자동'!B:B,"${s}",'GA4_자동'!E:E,"${e}",${ga4D})`).join('+');
      const sess = sources.map(s =>
        `SUMIFS('GA4_자동'!G:G,'GA4_자동'!B:B,"${s}",'GA4_자동'!E:E,"session_start",${ga4D})`).join('+');
      sh.getRange(row, 6).setFormula(`=IFERROR(${sess},0)`).setNumberFormat(fmtKM);
      sh.getRange(row, 7).setFormula(`=IFERROR(${ev('kakao_chat_click')},0)`);
      sh.getRange(row, 8).setFormula(`=IFERROR(${ev('phone_click')},0)`);
      sh.getRange(row, 9).setFormula(`=IFERROR(${ev('citymarket_click')},0)`);
      sh.getRange(row, 10).setFormula(`=IFERROR(IF(F${row}=0,0,G${row}/F${row}),0)`).setNumberFormat('0.00%');
      sh.getRange(row, 11).setFormula(`=IFERROR(IF(G${row}=0,"-",D${row}/G${row}),"-")`).setNumberFormat('#,##0"원"');
      sh.getRange(row, 12).setFormula(`=IF(D${row}=0,"-",IF(G${row}=0,"🔴 카톡클릭 0",IF(K${row}<50000,"🟢 효율","🔴 비효율")))`);
    }
  });

  // 행 23: 전체 합계
  sh.getRange('A23').setValue('전체 (attribution 무관)').setFontWeight('bold').setBackground('#FFF2CC');
  sh.getRange('B23:E23').setBackground('#FFF2CC');
  sh.getRange('F23').setFormula(`=IFERROR(SUMIFS('GA4_자동'!G:G,'GA4_자동'!E:E,"session_start",${ga4D}),0)`).setNumberFormat(fmtKM);
  sh.getRange('G23').setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,'GA4_자동'!E:E,"kakao_chat_click",${ga4D}),0)`);
  sh.getRange('H23').setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,'GA4_자동'!E:E,"phone_click",${ga4D}),0)`);
  sh.getRange('I23').setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,'GA4_자동'!E:E,"citymarket_click",${ga4D}),0)`);
  sh.getRange('F23:L23').setBackground('#FFF2CC').setFontWeight('bold');

  sh.getRange('A17:L23').setHorizontalAlignment('center');

  SpreadsheetApp.getUi().alert('✅ 채널 매트릭스 갱신 완료\n· 메타/네이버 = 통합 시트 (광고그룹 단위 자동 합산)\n· 구글/카카오/당근 = 기존 수동 입력 시트\n· 당근 GA4 수집 활성화 (daangn + danggn)');
}

// ──[일상]── 추세 시트 — 30일 일별 광고비/카톡클릭 차트 재생성
function addTimeSeriesChart() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName('추세');
  if (!sh) sh = ss.insertSheet('추세');
  sh.clear();
  sh.getCharts().forEach(c => sh.removeChart(c));

  sh.getRange('A1:G1').merge().setValue('■ 시계열 추세 (최근 30일 일별 광고비)')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(12);

  // ★ 패치: 채널별 시트/지출 컬럼 매핑
  const trendChannels = [
    {disp:'메타',   sheet:'메타+',   spdCol:'H'},
    {disp:'구글',   sheet:'구글',        spdCol:'G'},
    {disp:'네이버', sheet:'네이버+', spdCol:'H'},
    {disp:'카카오', sheet:'카카오',      spdCol:'G'},
    // 당근 추세: 옛 당근 시트 G열. 전환 시 {disp:'당근', sheet:'당근+', spdCol:'F'} 로 교체
    {disp:'당근',   sheet:'당근',        spdCol:'G'},
  ];

  sh.getRange('A3').setValue('날짜');
  trendChannels.forEach((c, i) => sh.getRange(3, 2 + i).setValue(c.disp));
  sh.getRange(3, 7).setValue('일합계');
  sh.getRange('A3:G3').setBackground('#D9E1F2').setFontWeight('bold')
    .setBorder(true,true,true,true,true,true).setHorizontalAlignment('center');

  for (let i = 0; i < 30; i++) {
    const r = 4 + i;
    sh.getRange(r, 1).setFormula(`=TODAY()-${29 - i}`).setNumberFormat('M/d (ddd)');
    trendChannels.forEach((c, idx) => {
      sh.getRange(r, 2 + idx).setFormula(
        `=IFERROR(SUMIFS('${c.sheet}'!${c.spdCol}:${c.spdCol},'${c.sheet}'!A:A,A${r}),0)`
      ).setNumberFormat('#,##0');
    });
    sh.getRange(r, 7).setFormula(`=SUM(B${r}:F${r})`).setNumberFormat('#,##0').setFontWeight('bold');
  }

  const chart = sh.newChart()
    .setChartType(Charts.ChartType.LINE)
    .addRange(sh.getRange('A3:F33'))
    .setOption('title', '채널별 일별 광고비 (최근 30일)')
    .setOption('height', 400).setOption('width', 1000)
    .setOption('legend', {position: 'bottom'})
    .setOption('hAxis', {title: '날짜'})
    .setOption('vAxis', {title: '광고비 (원)', format: '#,##0'})
    .setPosition(2, 9, 0, 0)
    .build();
  sh.insertChart(chart);

  sh.getRange('A36:G36').merge().setValue('■ 카톡 채팅 클릭 추세 (GA4)')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(12);

  sh.getRange('A38').setValue('날짜');
  trendChannels.forEach((c, i) => sh.getRange(38, 2 + i).setValue(c.disp));
  sh.getRange(38, 7).setValue('일합계');
  sh.getRange('A38:G38').setBackground('#D9E1F2').setFontWeight('bold').setBorder(true,true,true,true,true,true);

  const ga4SourceMap = ['meta','google','naver','kakao','daangn'];
  for (let i = 0; i < 30; i++) {
    const r = 39 + i;
    sh.getRange(r, 1).setFormula(`=TODAY()-${29 - i}`).setNumberFormat('M/d (ddd)');
    ga4SourceMap.forEach((src, c) => {
      sh.getRange(r, 2 + c).setFormula(
        `=IFERROR(SUMIFS('GA4_자동'!F:F,'GA4_자동'!A:A,TEXT(A${r},"yyyymmdd"),'GA4_자동'!B:B,"${src}",'GA4_자동'!E:E,"kakao_chat_click"),0)`
      ).setNumberFormat('#,##0');
    });
    sh.getRange(r, 7).setFormula(`=SUM(B${r}:F${r})`).setFontWeight('bold');
  }

  const chart2 = sh.newChart()
    .setChartType(Charts.ChartType.LINE)
    .addRange(sh.getRange('A38:F68'))
    .setOption('title', '채널별 일별 카톡 채팅 클릭 (최근 30일)')
    .setOption('height', 400).setOption('width', 1000)
    .setOption('legend', {position: 'bottom'})
    .setOption('hAxis', {title: '날짜'})
    .setOption('vAxis', {title: '카톡 클릭 수'})
    .setPosition(37, 9, 0, 0)
    .build();
  sh.insertChart(chart2);

  sh.setColumnWidth(1, 110);
  for (let c = 2; c <= 7; c++) sh.setColumnWidth(c, 90);

  Logger.log('시계열 차트 2개 생성 완료');
}

// ──[일상]── SNS 채널 운영 보고 (E28 자체 드롭다운으로 기간 별도 설정)
function updateSNSReport(opts) {
  opts = opts || {};
  const forceRebuild = opts.forceRebuild !== false;
  const showAlert = opts.showAlert !== false;

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('통합대시보드');

  if (!forceRebuild && sh.getRange('A28').getValue() === '★ SNS 채널 운영') {
    return;
  }

  sh.getRange('A28:Z35').breakApart();
  sh.getRange('A28:Z35').clearContent().clearFormat();

  sh.getRange('A28:C28').merge().setValue('★ SNS 채널 운영')
    .setBackground('#1F4E78').setFontColor('#FFFFFF')
    .setFontWeight('bold').setFontSize(13);
  sh.getRange('D28').setValue('📅 기간:').setFontWeight('bold').setHorizontalAlignment('right');
  sh.getRange('E28').setBackground('#FFF59D').setFontWeight('bold').setHorizontalAlignment('center')
    .setDataValidation(SpreadsheetApp.newDataValidation()
      .requireValueInList(['어제','최근 3일','최근 7일','최근 30일'], true).setAllowInvalid(false).build());
  if (sh.getRange('E28').getValue() === '') sh.getRange('E28').setValue('최근 30일');

  sh.getRange('M28').setValue('기간▶').setFontColor('#BBBBBB').setFontSize(8).setHorizontalAlignment('right');
  sh.getRange('N28').setFormula('=IF($E$28="어제",TODAY()-1,IF($E$28="최근 3일",TODAY()-2,IF($E$28="최근 7일",TODAY()-6,TODAY()-29)))')
    .setNumberFormat('m/d').setFontColor('#BBBBBB');
  sh.getRange('O28').setFormula('=IF($E$28="어제",TODAY()-1,TODAY())')
    .setNumberFormat('m/d').setFontColor('#BBBBBB');

  const h = ['채널','포스트수','총 조회수','평균','최고','팔로워','시트'];
  sh.getRange(29, 1, 1, 7).setValues([h])
    .setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center');

  const sns = [
    {row: 30, name: '스레드', sheet: '스레드'},
    {row: 31, name: '인스타', sheet: '인스타'},
    {row: 32, name: '유튜브', sheet: '유튜브'},
    {row: 33, name: '틱톡',   sheet: '틱톡'},
  ];

  sns.forEach(({row, name, sheet}) => {
    sh.getRange(row, 1).setValue(name).setFontWeight('bold');
    sh.getRange(row, 2).setFormula(
      `=COUNTIFS('${sheet}'!A:A,">="&$N$28,'${sheet}'!A:A,"<="&$O$28)`
    ).setNumberFormat('#,##0');
    sh.getRange(row, 3).setFormula(
      `=SUMIFS('${sheet}'!E:E,'${sheet}'!A:A,">="&$N$28,'${sheet}'!A:A,"<="&$O$28)`
    ).setNumberFormat('#,##0');
    sh.getRange(row, 4).setFormula(
      `=IFERROR(IF(B${row}=0,0,C${row}/B${row}),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(row, 5).setFormula(
      `=IFERROR(MAXIFS('${sheet}'!E:E,'${sheet}'!A:A,">="&$N$28,'${sheet}'!A:A,"<="&$O$28),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(row, 6).setFormula(
      `=IFERROR(LOOKUP(2,1/(('${sheet}'!G:G<>"")*('${sheet}'!A:A<=$O$28)),'${sheet}'!G:G),"-")`
    );

    const tgt = ss.getSheetByName(sheet);
    if (tgt) {
      sh.getRange(row, 7).setFormula(
        `=HYPERLINK("#gid=${tgt.getSheetId()}","→ ${name}")`
      ).setFontColor('#0066CC').setFontWeight('bold');
    }
  });

  sh.getRange('A28:G33').setBorder(true,true,true,true,true,true);
  sh.getRange('B29:F33').setHorizontalAlignment('center');

  if (showAlert) SpreadsheetApp.getUi().alert('✅ SNS 보고표 갱신 — E28 드롭다운으로 기간 별도 설정 (채널 매트릭스와 분리)');
}

// ──[수동/일상]── 각 SNS 시트 우측 K:P 월별 합계표 수식 복구
function repairSNSMonthlySummaries(showAlert) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const snsSheets = ['스레드', '인스타', '유튜브', '틱톡'];
  const missingSheets = [];

  snsSheets.forEach(sheetName => {
    const sh = ss.getSheetByName(sheetName);
    if (!sh) {
      missingSheets.push(sheetName);
      return;
    }

    sh.getRange('K1:P16').breakApart();
    sh.getRange('K1:P16').clearContent().clearFormat();

    sh.getRange('K1:P1').merge()
      .setValue('📊 월별 합계')
      .setBackground('#1F4E78')
      .setFontColor('#FFFFFF')
      .setFontWeight('bold')
      .setHorizontalAlignment('center');

    sh.getRange('K3:P3').setValues([[
      '월', '포스트수', '총 조회수', '평균 조회수', '최고 조회수', '월말 팔로워'
    ]])
      .setBackground('#D9E1F2')
      .setFontWeight('bold')
      .setHorizontalAlignment('center')
      .setBorder(true, true, true, true, true, true);

    for (let m = 1; m <= 12; m++) {
      const r = 3 + m;
      sh.getRange(r, 11)
        .setFormula(`=DATE(YEAR(TODAY()),${m},1)`)
        .setNumberFormat('yyyy.m');
      sh.getRange(r, 12)
        .setFormula(`=COUNTIFS($A$4:$A$1000,">="&$K${r},$A$4:$A$1000,"<="&EOMONTH($K${r},0))`)
        .setNumberFormat('#,##0');
      sh.getRange(r, 13)
        .setFormula(`=SUMIFS($E$4:$E$1000,$A$4:$A$1000,">="&$K${r},$A$4:$A$1000,"<="&EOMONTH($K${r},0))`)
        .setNumberFormat('#,##0');
      sh.getRange(r, 14)
        .setFormula(`=IFERROR($M${r}/$L${r},"-")`)
        .setNumberFormat('#,##0');
      sh.getRange(r, 15)
        .setFormula(`=IFERROR(MAXIFS($E$4:$E$1000,$A$4:$A$1000,">="&$K${r},$A$4:$A$1000,"<="&EOMONTH($K${r},0)),0)`)
        .setNumberFormat('#,##0');
      sh.getRange(r, 16)
        .setFormula(`=IFERROR(INDEX(SORT(FILTER({$A$4:$A$1000,$G$4:$G$1000},$A$4:$A$1000>=$K${r},$A$4:$A$1000<=EOMONTH($K${r},0),$G$4:$G$1000<>""),1,FALSE),1,2),"-")`)
        .setNumberFormat('#,##0');
    }

    const totalRow = 16;
    sh.getRange(totalRow, 11)
      .setFormula(`=YEAR(TODAY())&" 합계"`)
      .setFontWeight('bold');
    sh.getRange(totalRow, 12)
      .setFormula('=SUM(L4:L15)')
      .setNumberFormat('#,##0')
      .setFontWeight('bold');
    sh.getRange(totalRow, 13)
      .setFormula('=SUM(M4:M15)')
      .setNumberFormat('#,##0')
      .setFontWeight('bold');
    sh.getRange(totalRow, 14)
      .setFormula('=IFERROR(M16/L16,"-")')
      .setNumberFormat('#,##0')
      .setFontWeight('bold');
    sh.getRange(totalRow, 15)
      .setFormula('=MAX(O4:O15)')
      .setNumberFormat('#,##0')
      .setFontWeight('bold');
    sh.getRange(totalRow, 16)
      .setFormula(`=IFERROR(INDEX(SORT(FILTER({$A$4:$A$1000,$G$4:$G$1000},YEAR($A$4:$A$1000)=YEAR(TODAY()),$G$4:$G$1000<>""),1,FALSE),1,2),"-")`)
      .setNumberFormat('#,##0')
      .setFontWeight('bold');

    sh.getRange('K3:P16')
      .setBorder(true, true, true, true, true, true)
      .setHorizontalAlignment('center');

    sh.setColumnWidths(11, 6, 110);
  });

  if (showAlert !== false) {
    const msg = missingSheets.length
      ? `✅ SNS 월별 합계 수식 복구 완료\n단, 없는 시트: ${missingSheets.join(', ')}`
      : '✅ SNS 월별 합계 수식 복구 완료';
    SpreadsheetApp.getUi().alert(msg);
  }
}

// ════════════════════════════════════════════════════════════
//  [일상] 카톡 리포트 × 문의접수 입력률 관리 — 문의접수 시트 내장형
// ════════════════════════════════════════════════════════════

function getInquirySheet_() {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(INQUIRY_SHEET);
  if (!sh) throw new Error(`'${INQUIRY_SHEET}' 시트를 찾을 수 없습니다.`);
  return sh;
}

function normalizeYmd_(value, defaultYear) {
  const TZ = 'Asia/Seoul';
  const year = defaultYear || new Date().getFullYear();
  if (value instanceof Date && !isNaN(value.getTime())) {
    return Utilities.formatDate(value, TZ, 'yyyy-MM-dd');
  }
  if (typeof value === 'number' && !isNaN(value)) {
    const d = new Date(Math.round((value - 25569) * 86400 * 1000));
    if (!isNaN(d.getTime())) return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
  }
  const s = String(value || '').trim();
  if (!s) return '';
  let m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/);
  if (m) {
    return `${m[1]}-${String(m[2]).padStart(2, '0')}-${String(m[3]).padStart(2, '0')}`;
  }
  m = s.match(/^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일/);
  if (m) {
    return `${m[1]}-${String(m[2]).padStart(2, '0')}-${String(m[3]).padStart(2, '0')}`;
  }
  m = s.match(/^(\d{1,2})월\s*(\d{1,2})일/);
  if (m) {
    return `${year}-${String(m[1]).padStart(2, '0')}-${String(m[2]).padStart(2, '0')}`;
  }
  const d = new Date(s);
  if (!isNaN(d.getTime())) return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');
  return '';
}

function toNumber_(value) {
  if (typeof value === 'number') return value;
  const n = Number(String(value || '').replace(/[^0-9.-]/g, ''));
  return isNaN(n) ? 0 : n;
}

function kakaoReportCol_(offset) {
  return KAKAO_REPORT_START_COL + offset;
}

function setupKakaoDailyReport() {
  const sh = getInquirySheet_();
  const startCol = KAKAO_REPORT_START_COL;
  const numCols = KAKAO_REPORT_NUM_COLS;

  sh.getRange(1, startCol, 4, numCols).breakApart();
  sh.getRange(1, startCol, 4, numCols).clearContent().clearFormat();

  sh.getRange(1, startCol, 1, numCols).merge()
    .setValue('■ 카톡 리포트 입력/검증 — H:K 5행부터 원본 붙여넣기')
    .setBackground('#1F4E78').setFontColor('#FFFFFF')
    .setFontWeight('bold').setFontSize(12)
    .setHorizontalAlignment('center');

  const desc = [[
    '카카오 리포트의 일자',
    '해당일 기준 채널 전체 친구수',
    '해당일 새로 추가된 친구수',
    '카카오 공식 채팅 요청 친구수',
    '문의접수 A:E에 수기 입력된 건수',
    '관리대장 입력건 ÷ 채팅 요청 친구수',
    '채팅 요청 친구수 - 관리대장 입력건',
    '문의접수에서 개통으로 표시된 건수',
    '개통수 ÷ 관리대장 입력건',
    '입력률 기준 자동 진단'
  ]];

  sh.getRange(2, startCol, 1, numCols).setValues(desc)
    .setBackground('#F3F6FA')
    .setFontColor('#555555')
    .setFontSize(9)
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle')
    .setWrap(true)
    .setBorder(true,true,true,true,true,true);
  sh.setRowHeight(2, 48);

  const groups = [
    {col: startCol,     cols: 4, label: '① 카카오 공식 리포트', bg: '#D9EAF7'},
    {col: startCol + 4, cols: 3, label: '② 관리대장 입력 검증', bg: '#FFF2CC'},
    {col: startCol + 7, cols: 2, label: '③ 개통 성과', bg: '#E2F0D9'},
    {col: startCol + 9, cols: 1, label: '④ 관리 상태', bg: '#F4CCCC'},
  ];

  groups.forEach(g => {
    const range = sh.getRange(3, g.col, 1, g.cols);
    if (g.cols > 1) range.merge();
    range.setValue(g.label)
      .setBackground(g.bg)
      .setFontWeight('bold')
      .setHorizontalAlignment('center')
      .setVerticalAlignment('middle')
      .setBorder(true,true,true,true,true,true);
  });
  sh.setRowHeight(3, 26);

  const headers = ['날짜','친구수','채널 추가수 합계','채팅 요청 친구수','관리대장 입력건','입력률','누락추정','개통수','개통률','상태'];
  const notes = [[
    '카카오 비즈니스 리포트에서 복사한 날짜입니다. H5부터 붙여넣습니다.',
    '카카오 채널의 해당일 전체 친구수입니다. 원본 리포트 값입니다.',
    '해당일 채널을 새로 추가한 친구 수입니다. 원본 리포트 값입니다.',
    '카카오가 집계한 해당일 채팅 요청 친구수입니다. 문의 총량의 기준값입니다.',
    '같은 날짜에 문의접수 A:E 관리대장에 입력된 고객 행 수입니다.',
    '관리대장 입력건 / 채팅 요청 친구수입니다. 상담원 기록 누락 여부를 보는 핵심 지표입니다.',
    '채팅 요청 친구수에서 관리대장 입력건을 뺀 값입니다. 0보다 크면 누락 가능성이 있습니다.',
    '같은 날짜 문의접수 C열에 개통으로 표시된 건수입니다.',
    '개통수 / 관리대장 입력건입니다. 입력된 문의 기준 전환율입니다.',
    '입력률 기준 자동 판정입니다. 정상/일부누락/관리불안정/대량누락/수기>리포트로 표시됩니다.'
  ]];

  sh.getRange(KAKAO_REPORT_HEADER_ROW, startCol, 1, headers.length).setValues([headers])
    .setBackground('#D9E1F2').setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle')
    .setBorder(true,true,true,true,true,true)
    .setNotes(notes);
  sh.setRowHeight(KAKAO_REPORT_HEADER_ROW, 24);

  sh.setColumnWidths(startCol, 1, 115);
  sh.setColumnWidths(startCol + 1, 3, 120);
  sh.setColumnWidths(startCol + 4, 6, 110);

  sh.getRange(1, startCol, 4, numCols).setWrap(true);

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 1).setNumberFormat('yyyy-mm-dd');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 1, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 4).setNumberFormat('#,##0');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 5, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 1).setNumberFormat('0.0%');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 6, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 2).setNumberFormat('#,##0');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 8, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 1).setNumberFormat('0.0%');

  SpreadsheetApp.getUi().alert('✅ 문의접수 시트 우측에 카톡 리포트 영역 정비 완료\nH:K 5행부터 카카오 리포트를 붙여넣은 뒤 입력률 갱신을 실행하세요.');
}

function setupKakaoDailyReportHeadersOnly_(sh) {
  const startCol = KAKAO_REPORT_START_COL;
  const headers = ['날짜','친구수','채널 추가수 합계','채팅 요청 친구수','관리대장 입력건','입력률','누락추정','개통수','개통률','상태'];
  const current = sh.getRange(KAKAO_REPORT_HEADER_ROW, startCol, 1, headers.length).getValues()[0].join('');
  if (current.indexOf('채팅 요청 친구수') === -1 || current.indexOf('입력률') === -1) {
    setupKakaoDailyReport();
  }
}

function updateKakaoInquiryCoverage(showAlert) {
  const sh = getInquirySheet_();
  setupKakaoDailyReportHeadersOnly_(sh);

  const defaultYear = new Date().getFullYear();
  const sheetLastRow = Math.max(sh.getLastRow(), KAKAO_REPORT_DATA_ROW);

  const inqValues = sheetLastRow >= 2 ? sh.getRange(2, 1, sheetLastRow - 1, 3).getValues() : [];
  const inputByDate = {};
  const openedByDate = {};

  inqValues.forEach(row => {
    const ymd = normalizeYmd_(row[0], defaultYear);
    const name = String(row[1] || '').trim();
    const status = String(row[2] || '').trim();
    if (!ymd || !name) return;
    inputByDate[ymd] = (inputByDate[ymd] || 0) + 1;
    if (status === '개통') openedByDate[ymd] = (openedByDate[ymd] || 0) + 1;
  });

  const startCol = KAKAO_REPORT_START_COL;
  const rawNumRows = Math.max(sheetLastRow - KAKAO_REPORT_DATA_ROW + 1, 1);
  const rawValues = sh.getRange(KAKAO_REPORT_DATA_ROW, startCol, rawNumRows, 4).getValues();

  let lastDataIndex = -1;
  rawValues.forEach((row, i) => {
    if (row.some(v => String(v || '').trim() !== '')) lastDataIndex = i;
  });

  if (lastDataIndex < 0) {
    if (showAlert !== false) SpreadsheetApp.getUi().alert('문의접수 시트 H:K 5행부터 카톡 리포트를 먼저 붙여넣어야 합니다.');
    return;
  }

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 4, rawNumRows, 6).clearContent();

  const reportValues = rawValues.slice(0, lastDataIndex + 1);
  const normalizedDates = [];
  const out = [];

  reportValues.forEach(row => {
    const ymd = normalizeYmd_(row[0], defaultYear);
    const chatReq = toNumber_(row[3]);
    const input = ymd ? (inputByDate[ymd] || 0) : 0;
    const opened = ymd ? (openedByDate[ymd] || 0) : 0;
    const inputRate = chatReq > 0 ? input / chatReq : '';
    const missing = chatReq - input;
    const openRate = input > 0 ? opened / input : '';
    let status = '';
    if (!ymd) status = '날짜 확인';
    else if (chatReq === 0 && input === 0) status = '-';
    else if (missing < 0) status = '수기>리포트';
    else if (inputRate === '') status = '-';
    else if (inputRate >= 0.9) status = '정상';
    else if (inputRate >= 0.7) status = '일부누락';
    else if (inputRate >= 0.5) status = '관리불안정';
    else status = '대량누락';
    normalizedDates.push([ymd ? new Date(ymd + 'T12:00:00Z')  /* 정오 UTC = 모든 시간대에서 같은 날짜 표시 */ : row[0]]);
    out.push([input, inputRate, missing, opened, openRate, status]);
  });

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol, normalizedDates.length, 1)
    .setValues(normalizedDates).setNumberFormat('yyyy-mm-dd');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 4, out.length, 6).setValues(out);
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 1, out.length, 4).setNumberFormat('#,##0');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 4, out.length, 1).setNumberFormat('#,##0');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 5, out.length, 1).setNumberFormat('0.0%');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 6, out.length, 2).setNumberFormat('#,##0');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 8, out.length, 1).setNumberFormat('0.0%');
  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 9, out.length, 1).setHorizontalAlignment('center');

  updateKakaoReportDashboard(false);

  if (showAlert !== false) {
    SpreadsheetApp.getUi().alert('✅ 문의접수 입력률 갱신 완료');
  }
}

function updateKakaoReportDashboard(showAlert) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const dash = ss.getSheetByName('통합대시보드');
  const inquiry = ss.getSheetByName(INQUIRY_SHEET);
  if (!dash || !inquiry) return;

  dash.getRange('A36:Z44').breakApart();
  dash.getRange('A36:Z44').clearContent().clearFormat();

  dash.getRange('A36:C36').merge().setValue('★ 카톡 문의 입력률 리포트')
    .setBackground('#1F4E78').setFontColor('#FFFFFF')
    .setFontWeight('bold').setFontSize(13);
  dash.getRange('D36').setValue('📅 기간:').setFontWeight('bold').setHorizontalAlignment('right');
  dash.getRange('E36').setBackground('#FFF59D').setFontWeight('bold').setHorizontalAlignment('center')
    .setDataValidation(SpreadsheetApp.newDataValidation()
      .requireValueInList(['어제','최근 3일','최근 7일','최근 30일'], true).setAllowInvalid(false).build());
  if (dash.getRange('E36').getValue() === '') dash.getRange('E36').setValue('최근 30일');

  dash.getRange('M36').setValue('기간▶').setFontColor('#BBBBBB').setFontSize(8).setHorizontalAlignment('right');
  dash.getRange('N36').setFormula('=IF($E$36="어제",TODAY()-1,IF($E$36="최근 3일",TODAY()-2,IF($E$36="최근 7일",TODAY()-6,TODAY()-29)))')
    .setNumberFormat('m/d').setFontColor('#BBBBBB');
  dash.getRange('O36').setFormula('=IF($E$36="어제",TODAY()-1,TODAY())')
    .setNumberFormat('m/d').setFontColor('#BBBBBB');

  const headers = ['카톡 채팅요청','관리대장 입력','입력률','누락추정','개통','개통률','친구증가','판단'];
  dash.getRange(37, 1, 1, headers.length).setValues([headers])
    .setBackground('#D9E1F2').setFontWeight('bold')
    .setHorizontalAlignment('center').setBorder(true,true,true,true,true,true);

  const d = `'${INQUIRY_SHEET}'!H:H,">="&$N$36,'${INQUIRY_SHEET}'!H:H,"<="&$O$36`;
  dash.getRange('A38').setFormula(`=IFERROR(SUMIFS('${INQUIRY_SHEET}'!K:K,${d}),0)`).setNumberFormat('#,##0"건"');
  dash.getRange('B38').setFormula(`=IFERROR(SUMIFS('${INQUIRY_SHEET}'!L:L,${d}),0)`).setNumberFormat('#,##0"건"');
  dash.getRange('C38').setFormula('=IFERROR(B38/A38,"-")').setNumberFormat('0.0%');
  dash.getRange('D38').setFormula('=A38-B38').setNumberFormat('#,##0"건"');
  dash.getRange('E38').setFormula(`=IFERROR(SUMIFS('${INQUIRY_SHEET}'!O:O,${d}),0)`).setNumberFormat('#,##0"건"');
  dash.getRange('F38').setFormula('=IFERROR(E38/B38,"-")').setNumberFormat('0.0%');
  dash.getRange('G38').setFormula(`=IFERROR(SUMIFS('${INQUIRY_SHEET}'!J:J,${d}),0)`).setNumberFormat('#,##0"명"');
  dash.getRange('H38').setFormula('=IF(C38="-","-",IF(C38>=0.9,"🟢 정상",IF(C38>=0.7,"🟡 일부누락",IF(C38>=0.5,"🟠 관리불안정","🔴 대량누락"))))');

  dash.getRange('A37:H38').setBorder(true,true,true,true,true,true).setHorizontalAlignment('center');

  dash.getRange('A40').setFormula(`=HYPERLINK("#gid=${inquiry.getSheetId()}","→ 문의접수 H:Q 카톡 리포트 영역")`)
    .setFontColor('#0066CC').setFontWeight('bold');
  dash.getRange('B40:H40').merge()
    .setValue('※ 문의 총량은 문의접수 H:K의 카톡 공식 리포트, 고객별 상태/개통/유입채널은 문의접수 A:E 관리대장 기준')
    .setFontColor('#666666').setFontStyle('italic');

  if (showAlert !== false) SpreadsheetApp.getUi().alert('✅ 카톡 문의 입력률 대시보드 갱신 완료');
}

function inspectAdCreativeLayout() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('광고소재');
  if (!sh) {
    var names = ss.getSheets().map(function(s){return s.getName();});
    SpreadsheetApp.getUi().alert("'광고소재' 시트 없음.\n전체 시트 목록:\n" + names.join('\n'));
    return;
  }
  var lastRow = sh.getLastRow(), lastCol = sh.getLastColumn();
  var out = '시트=광고소재  마지막행=' + lastRow + '  마지막열=' + lastCol + '\n\n';
  var top = sh.getRange(1, 1, Math.min(3,lastRow), Math.min(11,lastCol)).getDisplayValues();
  for (var r=0;r<top.length;r++){
    out += '행' + (r+1) + ': ' + top[r].map(function(v){return v===''?'·':v;}).join(' | ') + '\n';
  }
  out += '\n[K열 내용 있는 행]\n';
  var kvals = sh.getRange(1, 11, lastRow, 1).getValues();
  for (var i=0;i<kvals.length;i++){
    var v = String(kvals[i][0]||'').trim();
    if (v) out += 'K' + (i+1) + ': ' + v.substring(0,40) + '\n';
  }
  SpreadsheetApp.getUi().alert(out);
  Logger.log(out);
}

// ──[Web App]── generator.html 호스팅 + API 라우팅 (2026-06-09 C-4: createTemplateFromFile)
function doGet(e) {
  // 권한 체크: Owner Execute일 때 빈 문자열 통과
  const allowed = ['313jongmin@gmail.com', 'mazision@gmail.com'];
  let user = '';
  try { user = Session.getActiveUser().getEmail(); } catch (err) {}
  if (user && allowed.indexOf(user) === -1) {
    return HtmlService.createHtmlOutput(
      '<h1>🔒 접근 권한 없음</h1><p>접속 계정: ' + user + '</p>'
    );
  }

  // API 라우팅: ?api=meta_creatives
  if (e && e.parameter && e.parameter.api === 'meta_creatives') {
    return getMetaCreativesAsJSON_();
  }

  // 페이지 라우팅: ?page=generator (default) / ?page=index
  const page = (e && e.parameter && e.parameter.page) || 'generator';
  if (page === 'generator') {
    return HtmlService.createTemplateFromFile('generator')
      .evaluate()
      .setTitle('폰스팟 광고 생성기')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }
  if (page === 'index') {
    return HtmlService.createTemplateFromFile('index')
      .evaluate()
      .setTitle('폰스팟 인덱스')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
  }
  return HtmlService.createHtmlOutput('<h1>404</h1>');
}

// ──[Web App utility]── HTML 파일 include 함수 (2026-06-09 C-4)
// styles.html 등 공통 자원을 generator.html에서 <?!= include('styles') ?>로 호출
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

// ============ ★ 야간 전체 새로고침 트리거 (2026-06-18) ============
// 개별 채널 sync(01:30~02:30) 다음 02:45에 refreshAll 자동 = 대시보드/인사이트/추세/스탬프 매일 최신.
function setupRefreshAllTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'refreshAll') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('refreshAll').timeBased().atHour(2).nearMinute(45).everyDays(1).create();
  SpreadsheetApp.getUi().alert('✅ 전체 새로고침 야간 트리거 등록 (매일 02:45).');
}


// ============ ★ UTM named range (컬럼 시프트 내성, 2026-06-18) ============
// UTM_CH=A열(채널), UTM_KEYVAL=B:C(광고그룹명·utm_campaign). 컬럼 삽입/이동 시
// 명명 범위가 자동 추적 → SUMIFS/FILTER가 안 깨짐(2026-06-17 마이그레이션 시프트 사고 방지).
// idempotent — 있으면 범위 갱신, 없으면 생성. sync/refreshAll 시작 시 호출됨.
function ensureUtmNamedRanges_() {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName('UTM');
  if (!sh) return;
  const want = { 'UTM_CH': 'A:A', 'UTM_KEYVAL': 'B:C' };
  const existing = {};
  ss.getNamedRanges().forEach(function (nr) { existing[nr.getName()] = nr; });
  Object.keys(want).forEach(function (name) {
    const rng = sh.getRange(want[name]);
    if (existing[name]) existing[name].setRange(rng);
    else ss.setNamedRange(name, rng);
  });
}

function setupUtmNamedRanges() {
  ensureUtmNamedRanges_();
  SpreadsheetApp.getUi().alert('✅ UTM named range 셋업 완료 (UTM_CH=A열, UTM_KEYVAL=B:C).\n컬럼 삽입/이동 시 자동 추적 → 수식 안 깨짐.');
}



// ============ ★ UTM 슬러그 드롭다운 (GA4 실측 utm_campaign 기준, 2026-06-18) ============
// UTM C열에 GA4_자동의 실제 utm_campaign 목록을 채널별 드롭다운으로 적용.
// region vs region_keyword 같은 슬러그 불일치/오타를 입력 단계에서 차단.
function refreshUtmSlugDropdowns() {
  const ss = SpreadsheetApp.getActive();
  const ui = SpreadsheetApp.getUi();
  const ga4 = ss.getSheetByName(GA4_AUTO_SHEET);
  const utm = ss.getSheetByName('UTM');
  if (!ga4 || !utm) { ui.alert('GA4_자동 또는 UTM 시트 없음.'); return; }
  const CH2SRC = { '페북': 'meta', '네이버': 'naver', '당근': 'daangn', '구글': 'google', '카카오': 'kakao' };
  const SKIP = { '(organic)': 1, '(direct)': 1, '(not set)': 1, '(data not available)': 1, '': 1 };
  const last = ga4.getLastRow();
  const data = last > 1 ? ga4.getRange(2, 2, last - 1, 3).getValues() : []; // B(src), C, D(campaign)
  const bySrc = {};
  data.forEach(function (r) {
    const src = String(r[0]).trim();
    const camp = String(r[2]).trim();
    if (!src || SKIP[camp]) return;
    (bySrc[src] = bySrc[src] || {})[camp] = 1;
  });
  const uLast = utm.getLastRow();
  if (uLast < 2) { ui.alert('UTM 데이터 없음.'); return; }
  const chans = utm.getRange(2, 1, uLast - 1, 1).getValues();
  let applied = 0;
  for (let i = 0; i < chans.length; i++) {
    const ch = String(chans[i][0]).trim();
    const src = CH2SRC[ch];
    if (!src || !bySrc[src]) continue;
    const listv = Object.keys(bySrc[src]).sort();
    if (!listv.length) continue;
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(listv, true).setAllowInvalid(true).build();
    utm.getRange(i + 2, 3).setDataValidation(rule);
    applied++;
  }
  const msg = 'UTM C열 드롭다운 적용 ' + applied + '행 (GA4 실측 utm_campaign 기준)';
  Logger.log(msg);
  if (typeof logSync_ === 'function') logSync_('refreshUtmSlugDropdowns', msg);
  ui.alert('✅ 완료', msg + '\n\n채널별 GA4 실제 값만 선택 가능 → region/region_keyword 같은 불일치 차단.', ui.ButtonSet.OK);
}

// ──[E, 2026-06-22]── 야간 대시보드 재빌드 (refreshAll 6분초과 미작동 대체)
// 데이터 sync는 개별 트리거가 담당. 이건 대시보드 UI/수식 재빌드만(빠름, API 호출 없음).
// 개별 sync(1:35~2:35) 끝난 뒤 03:00 실행 권장. UI alert는 트리거 컨텍스트에서 throw하므로 각자 try.
function nightlyDashboard() {
  try { buildDashboardV2(); } catch (e) { Logger.log('DashV2: ' + e.message); }
  try { if (typeof addTimeSeriesChart === 'function') addTimeSeriesChart(); } catch (e) { Logger.log('Chart: ' + e.message); }
  if (typeof logSync_ === 'function') logSync_('nightlyDashboard', '대시보드 재빌드 완료');
}

function setupNightlyDashboardTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'nightlyDashboard') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('nightlyDashboard').timeBased().atHour(3).nearMinute(0).everyDays(1).create();
  try { SpreadsheetApp.getUi().alert('✅ 야간 대시보드 재빌드 트리거 등록 (매일 03:00).\n\n※ 기존 refreshAll 트리거는 6분 초과로 미작동 → 삭제 권장.'); } catch (e) {}
}

// ──[2026-06-22]── 리틀리 유입 + 실비용 대조 섹션 (통합대시보드 45~59, 옛 여백 활용)
function updateLitlyAndPaymentSections_() {
  const ss = SpreadsheetApp.getActive();
  const dash = ss.getSheetByName('통합대시보드');
  if (!dash) return;
  try { dash.showRows(45, 15); } catch (e) {}
  try { dash.getRange('A45:I59').breakApart(); } catch (e) {}
  dash.getRange('A45:I59').clearContent().clearFormat();

  // ===== 리틀리(링크인바이오) 유입 =====
  dash.getRange('A45:I45').merge().setValue('★ 리틀리(링크인바이오) 유입')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(13).setHorizontalAlignment('center');
  dash.getRange(46, 1, 1, 4).setValues([['기간', '방문자수', '클릭수', 'CTR']])
    .setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center').setBorder(true, true, true, true, true, true);
  dash.getRange('F46').setValue('최신 유입경로비율').setFontWeight('bold').setFontColor('#1F4E78');
  const LP = [['어제', 'TODAY()-1', 'TODAY()-1'], ['최근 7일', 'TODAY()-6', 'TODAY()'], ['최근 30일', 'TODAY()-29', 'TODAY()']];
  LP.forEach(function (p, i) {
    const r = 47 + i;
    const base = "'리틀리'!A:A,\">=\"&" + p[1] + ",'리틀리'!A:A,\"<=\"&" + p[2];
    dash.getRange(r, 1).setValue(p[0]).setFontWeight('bold');
    dash.getRange(r, 2).setFormula("=IFERROR(SUMIFS('리틀리'!B:B," + base + "),0)").setNumberFormat('#,##0"명"');
    dash.getRange(r, 3).setFormula("=IFERROR(SUMIFS('리틀리'!C:C," + base + "),0)").setNumberFormat('#,##0');
    dash.getRange(r, 4).setFormula("=IFERROR(C" + r + "/B" + r + ",\"-\")").setNumberFormat('0.0%');
    dash.getRange(r, 1, 1, 4).setBorder(true, true, true, true, true, true).setHorizontalAlignment('center');
  });
  dash.getRange('F47:I49').merge().setVerticalAlignment('top').setWrap(true).setHorizontalAlignment('left')
    .setFormula('=IFERROR(INDEX(FILTER(\'리틀리\'!G4:G1000,\'리틀리\'!G4:G1000<>""),ROWS(FILTER(\'리틀리\'!G4:G1000,\'리틀리\'!G4:G1000<>""))),"(유입경로 입력 없음)")')
    .setBorder(true, true, true, true, true, true);

  // ===== 실비용 대조 (이번달 카드결제 vs API 광고비) =====
  dash.getRange('A51:I51').merge().setValue('★ 실비용 대조 — 이번달 카드결제 vs API 광고비')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(13).setHorizontalAlignment('center');
  dash.getRange(52, 1, 1, 4).setValues([['채널', '카드결제(실비용)', 'API 광고비', '차이']])
    .setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center').setBorder(true, true, true, true, true, true);
  const M = 'DATE(YEAR(TODAY()),MONTH(TODAY()),1)';
  const PAY = [['메타', '메타+', 'H'], ['네이버', '네이버+', 'H'], ['구글', '구글', 'G'], ['카카오', '카카오', 'G'], ['당근', '당근', 'G']];
  PAY.forEach(function (c, i) {
    const r = 53 + i;
    dash.getRange(r, 1).setValue(c[0]).setFontWeight('bold');
    dash.getRange(r, 2).setFormula("=IFERROR(SUMIFS('결제내역'!D:D,'결제내역'!B:B,\"" + c[0] + "\",'결제내역'!A:A,\">=\"&" + M + ",'결제내역'!A:A,\"<=\"&TODAY()),0)").setNumberFormat('#,##0"원"');
    dash.getRange(r, 3).setFormula("=IFERROR(SUMIFS('" + c[1] + "'!" + c[2] + ":" + c[2] + ",'" + c[1] + "'!A:A,\">=\"&" + M + ",'" + c[1] + "'!A:A,\"<=\"&TODAY()),0)").setNumberFormat('#,##0"원"');
    dash.getRange(r, 4).setFormula("=B" + r + "-C" + r).setNumberFormat('#,##0"원"');
    dash.getRange(r, 1, 1, 4).setBorder(true, true, true, true, true, true).setHorizontalAlignment('center');
  });
  dash.getRange(58, 1).setValue('합계').setFontWeight('bold');
  dash.getRange(58, 2).setFormula('=SUM(B53:B57)').setNumberFormat('#,##0"원"').setFontWeight('bold');
  dash.getRange(58, 3).setFormula('=SUM(C53:C57)').setNumberFormat('#,##0"원"').setFontWeight('bold');
  dash.getRange(58, 4).setFormula('=B58-C58').setNumberFormat('#,##0"원"').setFontWeight('bold');
  dash.getRange(58, 1, 1, 4).setBackground('#FFF2CC').setBorder(true, true, true, true, true, true).setHorizontalAlignment('center');
  dash.getRange('A59:I59').merge().setValue('※ 카드결제=결제내역 실청구액 / API=플랫폼 보고 광고비. 차이는 결제 타이밍·환불·미반영분.')
    .setFontStyle('italic').setFontColor('#888888').setFontSize(9);
}

// buildDashboardV2() — 통합대시보드 2열(가로) 라이트톤 레이아웃 (2026-06-22).
//   좌(A~F): 기간별핵심/채널별효율/리틀리  ·  우(H~M): 실비용대조/SNS  ·  스트립 1~2행 고정.
//   수식은 기존 update* 함수에서 추출 재사용. 추이(60행~)는 미변경 + A60 비면 자동복구.
function buildDashboardV2() {
  const ss = SpreadsheetApp.getActive();
  const dash = ss.getSheetByName('통합대시보드');
  if (!dash) return;
  var savedMargin = dash.getRange('C3').getValue();   // 개통 1건 마진 입력값 보존(클리어 전)

  // ── 라이트톤 색 토큰 ──
  const C_SEC_BG   = '#1F4E78';  // 네이비 (광고그룹 추이 헤더와 통일)
  const C_SEC_FG   = '#FFFFFF';  // 흰 폰트
  const C_COL_BG   = '#F7F7F8';
  const C_COL_FG   = '#5F5F5F';
  const C_ROW_BD   = '#ECECEC';
  const C_TOTAL_BG = '#FBF7E8';
  const C_LABEL    = '#888888';
  const F_WON = '#,##0"원"';
  const F_INT = '#,##0';
  const F_PCT = '0.0%';
  const fmtKM = '[>=1000000]0.00,,"M";[>=1000]0.0,"K";#,##0';

  const LCOL = 1;   // A
  const RCOL = 8;   // H (우측 시작; G=좌우 간격칸)
  const colL = function (n) { return String.fromCharCode(64 + n); };  // 열번호→문자 (RCOL 이동 시 수식 안전)

  // ── 0) 초기화 (1~59행만) ──
  dash.getRange('A1:Z59').clearDataValidations();
  dash.getRange('A1:Z59').breakApart();
  dash.getRange('A1:Z59').clearContent().clearFormat();
  try { dash.showRows(1, 59); } catch (e) {}
  try { dash.setRowHeights(1, 59, 22); } catch (e) {}

  function sectionHeader(row, title, startCol, width) {
    const sc = startCol || LCOL;
    const w = width || 6;
    dash.getRange(row, sc, 1, w).merge().setValue(title)
      .setBackground(C_SEC_BG).setFontColor(C_SEC_FG).setFontWeight('bold').setFontSize(11)
      .setHorizontalAlignment('center')
      .setBorder(null, null, true, null, null, null, '#D5DAE2', SpreadsheetApp.BorderStyle.SOLID);
  }
  function colHeader(row, labels, startCol) {
    const sc = startCol || LCOL;
    dash.getRange(row, sc, 1, labels.length).setValues([labels])
      .setBackground(C_COL_BG).setFontColor(C_COL_FG).setFontWeight('bold')
      .setHorizontalAlignment('center');
  }
  function dataBox(r1, nRows, nCols, startCol) {
    const sc = startCol || LCOL;
    const rng = dash.getRange(r1, sc, nRows, nCols);
    rng.setBorder(true, true, true, true, true, true, C_ROW_BD, SpreadsheetApp.BorderStyle.SOLID);
    rng.setHorizontalAlignment('center');                      // 데이터 전체 중앙정렬
    dash.getRange(r1, sc, nRows, 1).setFontWeight('bold');     // 라벨열 굵게
    for (var zi = 0; zi < nRows; zi++) {           // 제브라(홀짝 행 옅은 칠)로 가독성
      if (zi % 2 === 1) dash.getRange(r1 + zi, sc, 1, nCols).setBackground('#FAFAFB');
    }
  }

  const ADS = [
    {sh:'메타+',   spd:'H'},
    {sh:'구글',        spd:'G'},
    {sh:'네이버+', spd:'H'},
    {sh:'카카오',      spd:'G'},
    {sh:'당근',        spd:'G'},
  ];
  const sumPaidFx = (st, en) => ADS.map(a =>
    `SUMIFS('${a.sh}'!${a.spd}:${a.spd},'${a.sh}'!A:A,">="&${st},'${a.sh}'!A:A,"<="&${en})`
  ).join('+');
  const countInqFx = (st, en, extra='') =>
    `COUNTIFS('문의접수'!A:A,">="&${st},'문의접수'!A:A,"<="&${en}${extra})`;

  // 1) 요약 스트립 (1~2행, 고정) [전폭]
  const monthStart = 'DATE(YEAR(TODAY()),MONTH(TODAY()),1)';
  const GS = '$N$2', GE = '$O$2';   // 전역 기간(L2 드롭다운 기준)
  dash.getRange('K2').setValue('📅 기간:').setFontColor(C_LABEL).setFontSize(9).setFontWeight('bold').setHorizontalAlignment('right');
  const gdd = dash.getRange('L2');
  gdd.setBackground('#FFF59D').setFontWeight('bold').setHorizontalAlignment('center')
    .setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(['어제', '최근 3일', '최근 7일', '최근 30일'], true).setAllowInvalid(false).build());
  if (gdd.getValue() === '') gdd.setValue('최근 30일');
  dash.getRange('N2').setFormula('=IF($L$2="어제",TODAY()-1,IF($L$2="최근 3일",TODAY()-2,IF($L$2="최근 7일",TODAY()-6,TODAY()-29)))').setNumberFormat('m/d').setFontColor('#BBBBBB');
  dash.getRange('O2').setFormula('=IF($L$2="어제",TODAY()-1,TODAY())').setNumberFormat('m/d').setFontColor('#BBBBBB');

  const trackedInqG = `(${countInqFx(GS, GE)}-${countInqFx(GS, GE, ",'문의접수'!D:D,\"불확실\"")}-${countInqFx(GS, GE, ",'문의접수'!D:D,\"\"")})`;
  const inqG = countInqFx(GS, GE);

  const stripLabels = ['광고비', 'CPL', '개통률', '문의', '출처미상%'];
  const stripCols = ['A', 'C', 'E', 'G', 'I'];
  stripLabels.forEach(function (lbl, i) {
    const c = stripCols[i];
    const c2 = String.fromCharCode(c.charCodeAt(0) + 1);
    dash.getRange(c + '1:' + c2 + '1').merge().setValue(lbl)
      .setFontColor(C_LABEL).setFontSize(9).setHorizontalAlignment('center');
    dash.getRange(c + '2:' + c2 + '2').merge()
      .setFontWeight('bold').setFontSize(18).setHorizontalAlignment('center');
  });
  dash.getRange('A2').setFormula(`=${sumPaidFx(GS, GE)}`).setNumberFormat(F_WON);
  dash.getRange('C2').setFormula(`=IFERROR((${sumPaidFx(GS, GE)})/${trackedInqG},"-")`).setNumberFormat(F_WON);
  dash.getRange('E2').setFormula(`=IFERROR(${countInqFx(GS, GE, ",'문의접수'!C:C,\"개통\"")}/${trackedInqG},"-")`).setNumberFormat(F_PCT);
  dash.getRange('G2').setFormula(`=${inqG}`).setNumberFormat('#,##0"건"');
  dash.getRange('I2').setFormula(`=IFERROR((${inqG}-${trackedInqG})/${inqG},"-")`).setNumberFormat(F_PCT);

  dash.setFrozenRows(2);

  // 행3: 개통 1건 마진 입력(값 보존) + 선택기간 순이익(=개통×마진-광고비)
  dash.getRange('A3:B3').merge().setValue('💰 개통 1건당 마진(원)')
    .setFontColor(C_LABEL).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('right');
  dash.getRange('C3').setBackground('#FFF59D').setFontWeight('bold').setHorizontalAlignment('center').setNumberFormat('#,##0"원"');
  if (savedMargin !== '' && savedMargin !== null && savedMargin !== undefined) dash.getRange('C3').setValue(savedMargin);
  dash.getRange('E3').setValue('→ 순이익(기간)').setFontColor(C_LABEL).setFontWeight('bold').setFontSize(10).setHorizontalAlignment('right');
  dash.getRange('F3').setFormula(`=IF($C$3="","-",${countInqFx(GS, GE, ",'문의접수'!C:C,\"개통\"")}*$C$3-(${sumPaidFx(GS, GE)}))`).setNumberFormat(F_WON).setFontWeight('bold').setHorizontalAlignment('center');

  // 행3 우측: 광고 생성기(generator.html 웹앱) 바로가기 버튼 — 웹앱 배포 URL을 동적 취득(하드코딩 X)
  var genUrl = '';
  try { genUrl = ScriptApp.getService().getUrl() || ''; } catch (e) {}
  dash.getRange('H3:K3').breakApart();
  dash.getRange('H3:K3').merge();
  if (genUrl) {
    dash.getRange('H3').setFormula('=HYPERLINK("' + genUrl + '","🎨 광고 생성기 열기")')
      .setBackground('#1A73E8').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(11).setHorizontalAlignment('center');
  } else {
    dash.getRange('H3').setValue('🎨 광고 생성기 (웹앱 미배포 — 배포 후 재빌드)')
      .setFontColor('#AAAAAA').setFontStyle('italic').setHorizontalAlignment('center');
  }

  // ── 좌측 열 (A~F) ──

  // 2L) 기간별 핵심 — 헤더 A4:F4 / 컬럼헤더 5 / 데이터 6~8
  sectionHeader(4, '기간별 핵심', LCOL);
  colHeader(5, ['기간', '광고비', '문의', '개통', 'CPL', '순이익'], LCOL);
  const kpiPeriods = [
    ['어제',      'TODAY()-1',  'TODAY()-1'],
    ['최근 7일',  'TODAY()-6',  'TODAY()'],
    ['최근 30일', 'TODAY()-29', 'TODAY()'],
  ];
  const kpiStart = 6;
  kpiPeriods.forEach(function (p, i) {
    const r = kpiStart + i;
    const st = p[1], en = p[2];
    const trackedInq = `(${countInqFx(st, en)}-${countInqFx(st, en, ",'문의접수'!D:D,\"불확실\"")}-${countInqFx(st, en, ",'문의접수'!D:D,\"\"")})`;
    dash.getRange(r, 1).setValue(p[0]);
    dash.getRange(r, 2).setFormula(`=${sumPaidFx(st, en)}`).setNumberFormat(F_WON);
    dash.getRange(r, 3).setFormula(`=${countInqFx(st, en)}`).setNumberFormat('#,##0"건"');
    dash.getRange(r, 4).setFormula(`=${countInqFx(st, en, ",'문의접수'!C:C,\"개통\"")}`).setNumberFormat('#,##0"건"');
    dash.getRange(r, 5).setFormula(`=IFERROR(B${r}/${trackedInq},"-")`).setNumberFormat(F_WON);
    dash.getRange(r, 6).setFormula(`=IF($C$3="","-",D${r}*$C$3-B${r})`).setNumberFormat(F_WON);  // 순이익=개통×마진-광고비
  });
  dataBox(kpiStart, kpiPeriods.length, 6, LCOL);   // 6~8

  // 3L) 채널별 효율 — 전역 상단 기간(L2) 따라감 / 컬럼헤더 11 / 데이터 12~16
  const chHeaderRow = 10;
  sectionHeader(chHeaderRow, '채널별 효율', LCOL);   // 전역 상단 기간(L2) 따라감
  const ABS_N = '$N$2';
  const ABS_O = '$O$2';
  colHeader(11, ['채널', '노출', '클릭', '소진금액', '문의', '문의당비용'], LCOL);

  const ga4D = `'GA4_자동'!A:A,">="&TEXT(${ABS_N},"yyyymmdd"),'GA4_자동'!A:A,"<="&TEXT(${ABS_O},"yyyymmdd")`;
  // 채널 순서 = 실비용 대조와 동일. 소진금액=결제내역(카드결제) / 문의=GA4 카톡클릭(당근만 카톡문의+앱문의 별도식)
  const channels = [
    {name:'메타',   adSheet:'메타+',   impCol:'F', clkCol:'G', sources:['meta','facebook.com','m.facebook.com','l.facebook.com']},
    {name:'네이버', adSheet:'네이버+', impCol:'F', clkCol:'G', sources:['naver','naver_blog','ad.search.naver.com','m.ad.search.naver.com','m.search.naver.com']},
    {name:'구글',   adSheet:'구글',    impCol:'E', clkCol:'F', sources:['google']},
    {name:'카카오', adSheet:'카카오',  impCol:'E', clkCol:'F', sources:['kakao']},
    {name:'당근',   adSheet:'당근+',  impCol:'D', clkCol:'E', sources:['daangn','danggn'], danggn:true},  // 노출/클릭 = 당근+ 일별(옛 당근 시트는 운영일지라 누락)
  ];
  const chStart = 12;
  channels.forEach(function (c, i) {
    const r = chStart + i;
    const ad = (col) => `SUMIFS('${c.adSheet}'!${col}:${col},'${c.adSheet}'!A:A,">="&${ABS_N},'${c.adSheet}'!A:A,"<="&${ABS_O})`;
    const ev = (e) => c.sources.map(s =>
      `SUMIFS('GA4_자동'!F:F,'GA4_자동'!B:B,"${s}",'GA4_자동'!E:E,"${e}",${ga4D})`).join('+');
    const spend = `SUMIFS('결제내역'!D:D,'결제내역'!B:B,"${c.name}",'결제내역'!A:A,">="&${ABS_N},'결제내역'!A:A,"<="&${ABS_O})`;
    const inq = c.danggn
      ? `SUMIFS('당근+'!P:P,'당근+'!A:A,">="&${ABS_N},'당근+'!A:A,"<="&${ABS_O})+SUMIFS('당근+'!Q:Q,'당근+'!A:A,">="&${ABS_N},'당근+'!A:A,"<="&${ABS_O})`
      : ev('kakao_chat_click');
    dash.getRange(r, 1).setValue(c.name);
    dash.getRange(r, 2).setFormula(`=IFERROR(${ad(c.impCol)},0)`).setNumberFormat(fmtKM);
    dash.getRange(r, 3).setFormula(`=IFERROR(${ad(c.clkCol)},0)`).setNumberFormat(fmtKM);
    dash.getRange(r, 4).setFormula(`=IFERROR(${spend},0)`).setNumberFormat(F_WON);          // 소진금액=결제내역
    dash.getRange(r, 5).setFormula(`=IFERROR(${inq},0)`).setNumberFormat(F_INT);            // 문의
    dash.getRange(r, 6).setFormula(`=IFERROR(IF(E${r}=0,"-",D${r}/E${r}),"-")`).setNumberFormat(F_WON);  // 문의당비용=소진/문의
  });
  dataBox(chStart, channels.length, 6, LCOL);   // 12~16

  // 4L) 리틀리 유입 — 한 칸 내림(카톡 현황과 줄맞춤). 헤더 A19:G19 / 컬럼헤더 20 / 데이터 21~23 / E20:F23 박스
  sectionHeader(19, '리틀리 유입', LCOL);
  colHeader(20, ['기간', '방문자수', '클릭수', 'CTR'], LCOL);
  dash.getRange(20, 5).setValue('최신 유입경로비율')
    .setBackground(C_COL_BG).setFontColor(C_COL_FG).setFontWeight('bold').setFontSize(9)
    .setHorizontalAlignment('center');
  dash.getRange(20, 6).setBackground(C_COL_BG);
  const liStart = 21;
  const liPeriods = [['어제', 'TODAY()-1', 'TODAY()-1'], ['최근 7일', 'TODAY()-6', 'TODAY()'], ['최근 30일', 'TODAY()-29', 'TODAY()']];
  liPeriods.forEach(function (p, i) {
    const r = liStart + i;
    const base = "'리틀리'!A:A,\">=\"&" + p[1] + ",'리틀리'!A:A,\"<=\"&" + p[2];
    dash.getRange(r, 1).setValue(p[0]);
    dash.getRange(r, 2).setFormula("=IFERROR(SUMIFS('리틀리'!B:B," + base + "),0)").setNumberFormat('#,##0"명"');
    dash.getRange(r, 3).setFormula("=IFERROR(SUMIFS('리틀리'!C:C," + base + "),0)").setNumberFormat(F_INT);
    dash.getRange(r, 4).setFormula("=IFERROR(C" + r + "/B" + r + ",\"-\")").setNumberFormat(F_PCT);
  });
  dataBox(liStart, liPeriods.length, 4, LCOL);   // 20~22
  dash.getRange(liStart, 5, liPeriods.length, 2).merge()   // E20:F22
    .setVerticalAlignment('top').setWrap(true).setHorizontalAlignment('left')
    .setFormula('=IFERROR(INDEX(FILTER(\'리틀리\'!G4:G1000,\'리틀리\'!G4:G1000<>""),ROWS(FILTER(\'리틀리\'!G4:G1000,\'리틀리\'!G4:G1000<>""))),"(유입경로 입력 없음)")')
    .setBorder(true, true, true, true, true, true, C_ROW_BD, SpreadsheetApp.BorderStyle.SOLID);

  // ── 우측 열 (H~M) ──

  // 5R) 실비용 대조 — 헤더 H4:M4 / 컬럼헤더 5(H·I·J·K) / 데이터 6~10 / 합계 11 / 주석 12
  sectionHeader(10, '실비용 대조 (이번달 카드결제 vs API 광고비)', RCOL);
  colHeader(11, ['채널', '카드결제', 'API광고비', '차이'], RCOL);
  const payStart = 12;
  const PAY = [['메타', '메타+', 'H'], ['네이버', '네이버+', 'H'], ['구글', '구글', 'G'], ['카카오', '카카오', 'G'], ['당근', '당근', 'G']];
  PAY.forEach(function (c, i) {
    const r = payStart + i;
    dash.getRange(r, RCOL).setValue(c[0]);                                  // H
    dash.getRange(r, RCOL + 1).setFormula("=IFERROR(SUMIFS('결제내역'!D:D,'결제내역'!B:B,\"" + c[0] + "\",'결제내역'!A:A,\">=\"&" + monthStart + ",'결제내역'!A:A,\"<=\"&TODAY()),0)").setNumberFormat(F_WON);  // I
    dash.getRange(r, RCOL + 2).setFormula("=IFERROR(SUMIFS('" + c[1] + "'!" + c[2] + ":" + c[2] + ",'" + c[1] + "'!A:A,\">=\"&" + monthStart + ",'" + c[1] + "'!A:A,\"<=\"&TODAY()),0)").setNumberFormat(F_WON);  // J
    dash.getRange(r, RCOL + 3).setFormula("=" + colL(RCOL+1) + r + "-" + colL(RCOL+2) + r).setNumberFormat(F_WON);  // 차이=카드결제-API (RCOL상대)
  });
  dataBox(payStart, PAY.length, 4, RCOL);   // 6~10
  const payTotal = payStart + PAY.length;   // 11
  dash.getRange(payTotal, RCOL).setValue('합계').setFontWeight('bold');                                      // H11
  dash.getRange(payTotal, RCOL + 1).setFormula(`=SUM(${colL(RCOL+1)}${payStart}:${colL(RCOL+1)}${payTotal - 1})`).setNumberFormat(F_WON).setFontWeight('bold');  // I11
  dash.getRange(payTotal, RCOL + 2).setFormula(`=SUM(${colL(RCOL+2)}${payStart}:${colL(RCOL+2)}${payTotal - 1})`).setNumberFormat(F_WON).setFontWeight('bold');  // J11
  dash.getRange(payTotal, RCOL + 3).setFormula(`=${colL(RCOL+1)}${payTotal}-${colL(RCOL+2)}${payTotal}`).setNumberFormat(F_WON).setFontWeight('bold');           // K11
  dash.getRange(payTotal, RCOL, 1, 4).setBackground(C_TOTAL_BG)
    .setBorder(true, true, true, true, true, true, C_ROW_BD, SpreadsheetApp.BorderStyle.SOLID)
    .setHorizontalAlignment('right');
  dash.getRange(payTotal, RCOL).setHorizontalAlignment('left');
  dash.getRange(18, RCOL, 1, 6).merge()
    .setValue('· 차이(+) = 카드결제가 API 집계보다 큼 (수수료·부가세·미집계분 등)')
    .setFontColor('#AAAAAA').setFontStyle('italic').setFontSize(9).setHorizontalAlignment('left');

  // 6R) SNS 채널 운영 — 헤더 H14:M14 / 컬럼헤더 15(H·I·J·K·L) / 데이터 16~19
  sectionHeader(4, 'SNS 채널 운영', RCOL);
  colHeader(5, ['채널', '포스트수', '총조회수', '평균', '팔로워'], RCOL);
  const snsStart = 6;
  const sns = [
    {name: '유튜브', sheet: '유튜브'},
    {name: '인스타', sheet: '인스타'},
    {name: '스레드', sheet: '스레드'},
    {name: '틱톡',   sheet: '틱톡'},
  ];
  const snsSt = '$N$2', snsEn = '$O$2';   // 전역 상단 기간(L2)
  sns.forEach(function (s, i) {
    const r = snsStart + i;
    dash.getRange(r, RCOL).setValue(s.name);                                                            // H
    dash.getRange(r, RCOL + 1).setFormula(`=COUNTIFS('${s.sheet}'!A:A,">="&${snsSt},'${s.sheet}'!A:A,"<="&${snsEn})`).setNumberFormat(F_INT);  // I
    dash.getRange(r, RCOL + 2).setFormula(`=SUMIFS('${s.sheet}'!E:E,'${s.sheet}'!A:A,">="&${snsSt},'${s.sheet}'!A:A,"<="&${snsEn})`).setNumberFormat(F_INT);  // J
    dash.getRange(r, RCOL + 3).setFormula(`=IFERROR(IF(I${r}=0,0,J${r}/I${r}),0)`).setNumberFormat(F_INT);  // K = J/I
    var folF = "FILTER('" + s.sheet + "'!G4:G1000,'" + s.sheet + "'!G4:G1000<>\"\",'" + s.sheet + "'!A4:A1000<=" + snsEn + ")";
    dash.getRange(r, RCOL + 4).setFormula("=IFERROR(INDEX(" + folF + ",ROWS(" + folF + ")),\"-\")").setNumberFormat(F_INT);  // L 팔로워=기간내 최신 비공백
  });
  dataBox(snsStart, sns.length, 5, RCOL);   // 6~9

  // 7R) 카톡 현황 — 헤더 H19:M19 / 컬럼헤더 20 / 데이터 21~23 (어제/7일/30일, 리틀리 우측)
  sectionHeader(19, '카톡 현황', RCOL);
  colHeader(20, ['기간', '광고비', '카톡클릭', '카톡당비용'], RCOL);
  const kkPeriods = [
    ['어제',      'TODAY()-1',  'TODAY()-1'],
    ['최근 7일',  'TODAY()-6',  'TODAY()'],
    ['최근 30일', 'TODAY()-29', 'TODAY()'],
  ];
  const kkStart = 21;
  kkPeriods.forEach(function (p, i) {
    const r = kkStart + i;
    const st = p[1], en = p[2];
    const kClick = `SUMIFS('GA4_자동'!F:F,'GA4_자동'!E:E,"kakao_chat_click",'GA4_자동'!A:A,">="&TEXT(${st},"yyyymmdd"),'GA4_자동'!A:A,"<="&TEXT(${en},"yyyymmdd"))`;
    dash.getRange(r, RCOL).setValue(p[0]);                                                     // H 기간
    dash.getRange(r, RCOL + 1).setFormula(`=${sumPaidFx(st, en)}`).setNumberFormat(F_WON);     // I 광고비
    dash.getRange(r, RCOL + 2).setFormula(`=IFERROR(${kClick},0)`).setNumberFormat(F_INT);     // J 카톡클릭
    dash.getRange(r, RCOL + 3).setFormula(`=IFERROR(IF(${colL(RCOL+2)}${r}=0,"-",${colL(RCOL+1)}${r}/${colL(RCOL+2)}${r}),"-")`).setNumberFormat(F_WON);  // K 카톡당비용
  });
  dataBox(kkStart, kkPeriods.length, 4, RCOL);   // 21~23

  // ── 푸터 — 24행 (A24:F24 병합) ──
  const footerRow = 24;
  const stamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  dash.getRange(footerRow, 1, 1, 6).merge()
    .setValue('🕐 마지막 업데이트: ' + stamp + '  ·  기간 변경 = 상단 L2 드롭다운(전체 반영)')
    .setFontColor('#AAAAAA').setFontStyle('italic').setFontSize(9).setHorizontalAlignment('left');

  const hideFrom = footerRow + 1;   // 24
  if (hideFrom <= 59) { try { dash.hideRows(hideFrom, 59 - hideFrom + 1); } catch (e) {} }

  // 광고그룹 추이 자동복구 가드
  try {
    if (typeof setupAdgroupTrendChart === 'function' && String(dash.getRange('A60').getValue() || '').trim() === '') {
      setupAdgroupTrendChart();
    }
  } catch (e) { Logger.log('adgroup 복구 실패: ' + e.message); }

  // 폭/정렬 마무리
  dash.setColumnWidth(1, 100);                              // A (라벨) 고정
  for (let c = 2; c <= 6; c++) dash.setColumnWidth(c, 80);  // B~F = 80 고정
  dash.setColumnWidth(7, 60);                               // G = 좌우 간격칸 고정
  dash.setColumnWidth(8, 100);                              // H (우측 라벨) 고정
  for (let c = 9; c <= 13; c++) dash.setColumnWidth(c, 108);// I~M
  try { dash.setRowHeight(1, 18); dash.setRowHeight(2, 34); } catch (e) {}

  // 조건부 색: 출처미상(I2) 위험 / 실비용 차이(K12:K17) 음수 — 매번 내 규칙만 갱신
  try {
    var keep = dash.getConditionalFormatRules().filter(function (rule) {
      var rs = rule.getRanges().map(function (rg) { return rg.getA1Notation(); }).join(',');
      return rs.indexOf('I2') < 0 && rs.indexOf('K12') < 0 && rs.indexOf('F3') < 0 && rs.indexOf('F6') < 0;
    });
    keep.push(SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThanOrEqualTo(0.7)
      .setFontColor('#9F1A1A').setBackground('#FCEBEB').setRanges([dash.getRange('I2')]).build());
    keep.push(SpreadsheetApp.newConditionalFormatRule().whenNumberBetween(0.5, 0.6999)
      .setFontColor('#8A5A00').setBackground('#FAEEDA').setRanges([dash.getRange('I2')]).build());
    keep.push(SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0)
      .setFontColor('#9F1A1A').setRanges([dash.getRange('K12:K17')]).build());
    keep.push(SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0)
      .setFontColor('#9F1A1A').setRanges([dash.getRange('F3'), dash.getRange('F6:F8')]).build());
    keep.push(SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0)
      .setFontColor('#1D7A4D').setRanges([dash.getRange('F3'), dash.getRange('F6:F8')]).build());
    dash.setConditionalFormatRules(keep);
  } catch (e) { Logger.log('조건부서식: ' + e.message); }

  try {
    SpreadsheetApp.getUi().alert('✅ 통합대시보드 V2 빌드 완료 (2열 가로 레이아웃)\n· 1~2행 요약 스트립(고정)\n· 좌: 기간별 핵심 / 채널별 효율 / 리틀리\n· 우: SNS / 실비용 대조 / 카톡 현황\n· 60행 이후 = 광고그룹 추이 영역(미변경)');
  } catch (e) {}

  if (typeof logSync_ === 'function') { try { logSync_('buildDashboardV2', '대시보드 V2 빌드 (2열)'); } catch (e) {} }
}

// ============ 일회용: 시트 탭 이름 단축 (_통합 → +, UTM_매핑 → UTM), 2026-06-23 ============
// 코드 문자열은 이미 새 이름으로 치환됨. 이 함수로 실제 탭을 리네임하면 정합.
// 시트 안 수식은 탭 리네임 시 구글시트가 자동 갱신. 당근_UTM_매핑은 유지(건드리지 않음).
function renameTabsToPlus() {
  const ss = SpreadsheetApp.getActive();
  const MAP = [
    ['메타_통합', '메타+'],
    ['네이버_통합', '네이버+'],
    ['당근_통합', '당근+'],
    ['구글_통합', '구글+'],
    ['UTM_매핑', 'UTM'],
  ];
  const done = [], skip = [];
  MAP.forEach(function (m) {
    const oldN = m[0], newN = m[1];
    const sh = ss.getSheetByName(oldN);
    if (!sh) { skip.push(oldN + '(없음)'); return; }
    if (ss.getSheetByName(newN)) { skip.push(newN + '(이미존재)'); return; }
    sh.setName(newN);
    done.push(oldN + '→' + newN);
  });
  const msg = '탭 리네임 완료\n\n적용: ' + (done.join(', ') || '없음') +
    '\n건너뜀: ' + (skip.join(', ') || '없음') +
    '\n\n다음: 통합대시보드 새로고침(또는 buildDashboardV2) 1회 권장.';
  Logger.log(msg);
  try { SpreadsheetApp.getUi().alert(msg); } catch (e) {}
  return { done: done, skip: skip };
}


// ============ 브랜드 프로필 시트 백업/복원 (generator.html 브랜드 프로필) ============
const SHEET_BRAND_PROFILES = '브랜드_설정';
function getBrandProfilesSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_BRAND_PROFILES);
  if (!sh) {
    sh = ss.insertSheet(SHEET_BRAND_PROFILES);
    sh.getRange('A1').setNote('generator.html 브랜드 프로필 JSON (자동 관리 — 수기 편집 비권장)');
  }
  return sh;
}
function pushBrandProfilesToSheet(profilesJson) {
  try {
    const sh = getBrandProfilesSheet_();
    const s = (typeof profilesJson === 'string') ? profilesJson : JSON.stringify(profilesJson);
    sh.getRange('A1').setValue(s);
    sh.getRange('B1').setValue(new Date());
    return { ok: true };
  } catch (e) { return { ok: false, error: String(e) }; }
}
function getBrandProfilesFromSheet() {
  try {
    const sh = getBrandProfilesSheet_();
    const v = sh.getRange('A1').getValue();
    return { ok: true, profiles: v ? String(v) : '{}' };
  } catch (e) { return { ok: false, error: String(e) }; }
}
