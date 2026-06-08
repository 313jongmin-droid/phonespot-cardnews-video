// ════════════════════════════════════════════════════════════

//  폰스팟 광고운영 관리대장 — Apps Script (메뉴 정리본: 2026-05-29)

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

// ──[일상]── 시트 열 때 커스텀 메뉴 생성

function onOpen() {

  SpreadsheetApp.getUi()

    .createMenu('🛠 폰스팟 운영')

    .addItem('⚡ 전체 새로고침', 'refreshAll')

    .addSeparator()

    .addItem('🔄 GA4 최신 데이터 가져오기 (어제)', 'fetchGA4Daily')

    .addItem('📥 GA4 30일 다시 가져오기 (백필)', 'fetchGA4Backfill')

    .addSeparator()

    .addItem('📊 SNS 월별 합계 수식 복구', 'repairSNSMonthlySummaries')

    .addItem('📉 문의접수 입력률 갱신', 'updateKakaoInquiryCoverage')

    .addToUi();

  // 📡 메타 자동화 메뉴 (meta-sync.gs) — 같은 프로젝트의 다른 파일 함수

  try { buildMetaSyncMenu_(SpreadsheetApp.getUi()); } catch (e) {}

  // 🎬 YouTube 메뉴 (youtube_sync.gs) — 별도 설치 스크립트. onOpen에서 호출돼야 버튼이 뜸

  try { addYouTubeMenuItem(); } catch (e) {}

}

// ──[일상]── 전체 새로고침: GA4 수집 + KPI + 매트릭스 + 차트

function refreshAll() {

  const ui = SpreadsheetApp.getUi();

  try {

    fetchGA4Daily();

    updateKPISummary();

    updateChannelMatrixWithGA4();

    updateSNSReport({ forceRebuild: false, showAlert: false }); // 이미 만들어졌으면 재생성 생략(속도↑). 수식은 자동 재계산

    repairSNSMonthlySummaries(false);

    updateKakaoInquiryCoverage(false);

    addTimeSeriesChart();

    const stamp = recordLastRefresh_(); // 최근 업데이트 날짜/시간 기록

    ui.alert('✅ 전체 새로고침 완료\n🕐 ' + stamp);

  } catch (e) {

    ui.alert('❌ 오류: ' + e.message);

  }

}

// ──[유틸]── 최근 전체 업데이트 시각 기록 (통합대시보드 A46) — refreshAll이 호출

function recordLastRefresh_() {

  const stamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');

  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('통합대시보드');

  if (sh) {

    sh.getRange('A46:F46').breakApart();

    sh.getRange('A46').setValue('🕐 마지막 전체 업데이트: ' + stamp)

      .setFontColor('#666666').setFontStyle('italic').setFontWeight('bold');

  }

  return stamp;

}

// ──[일상]── 어제 GA4 데이터 수집 (매일 새벽 트리거가 호출)

function fetchGA4Daily() {

  const TZ = 'Asia/Seoul';

  const y = new Date();

  y.setDate(y.getDate() - 1);

  const ymd = Utilities.formatDate(y, TZ, 'yyyy-MM-dd');

  importGA4(ymd, ymd, false);

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

  const response = AnalyticsData.Properties.runReport(request, 'properties/' + GA4_PROP_ID);

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

function updateKPISummary() {

  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const sh = ss.getSheetByName('통합대시보드');

  // A9:I14 클리어

  sh.getRange('A9:I14').clearContent().clearFormat();

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

    ['최근 7일',   'TODAY()-6',  'TODAY()'],

    ['최근 14일',  'TODAY()-13', 'TODAY()'],

    ['최근 30일',  'TODAY()-29', 'TODAY()'],

  ];

  const CH = ['메타','구글','네이버','카카오','당근'];

  periods.forEach(([lbl, st, en], i) => {

    const r = 11 + i;

    const sumPaid = CH.map(ch => `SUMIFS('${ch}'!G:G,'${ch}'!A:A,">="&${st},'${ch}'!A:A,"<="&${en})`).join('+');

    const countInq = (extra='') => `COUNTIFS('문의접수'!A:A,">="&${st},'문의접수'!A:A,"<="&${en}${extra})`;

    const sumLi = (col) => `SUMIFS('리틀리'!${col}:${col},'리틀리'!A:A,">="&${st},'리틀리'!A:A,"<="&${en})`;

    sh.getRange(r, 1).setValue(lbl).setFontWeight('bold');

    // B: 광고소진

    sh.getRange(r, 2).setFormula(`=${sumPaid}`).setNumberFormat('#,##0"원"');

    // C: 문의 (전체)

    sh.getRange(r, 3).setFormula(`=${countInq()}`).setNumberFormat('#,##0"건"');

    // D: 출처확인 = 문의 - 불확실 - 빈값

    sh.getRange(r, 4).setFormula(`=${countInq()}-${countInq(",'문의접수'!D:D,\"불확실\"")}-${countInq(",'문의접수'!D:D,\"\"")}`).setNumberFormat('#,##0"건"');

    // E: 개통

    sh.getRange(r, 5).setFormula(`=${countInq(",'문의접수'!C:C,\"개통\"")}`).setNumberFormat('#,##0"건"');

    // F: 개통률 = 개통 / 출처확인

    sh.getRange(r, 6).setFormula(`=IFERROR(E${r}/D${r},"-")`).setNumberFormat('0.0%');

    // G: 리틀리CTR

    sh.getRange(r, 7).setFormula(`=IFERROR(${sumLi('C')}/${sumLi('B')},"-")`).setNumberFormat('0.0%');

    // H: CPL(추적) = 광고소진 / 출처확인

    sh.getRange(r, 8).setFormula(`=IFERROR(B${r}/D${r},"-")`).setNumberFormat('#,##0"원"');

    // I: CPL(전체) = 광고소진 / 전체 문의  (출처 확인 안 된 것도 포함)

    sh.getRange(r, 9).setFormula(`=IFERROR(B${r}/C${r},"-")`).setNumberFormat('#,##0"원"');

    sh.getRange(r, 1, 1, 9).setBorder(true,true,true,true,true,true).setHorizontalAlignment('center');

  });

  SpreadsheetApp.getUi().alert('✅ 핵심 KPI 갱신 완료\n· CPL(추적): 출처확인된 문의 기준\n· CPL(전체): 모든 문의 기준 (신규)');

}

// ──[일상]── 채널 매트릭스 재구성 (E16 드롭다운으로 기간 변경: 어제/7일/30일)

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

      .requireValueInList(['어제','최근 7일','최근 30일'], true).setAllowInvalid(false).build());

  if (sh.getRange('E16').getValue() === '') sh.getRange('E16').setValue('최근 30일');

  sh.getRange('M16').setValue('기간▶').setFontColor('#BBBBBB').setFontSize(8).setHorizontalAlignment('right');

  sh.getRange('N16').setFormula('=IF($E$16="어제",TODAY()-1,IF($E$16="최근 7일",TODAY()-6,TODAY()-29))')

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

  // 채널 정의 — 메타/구글/네이버/카카오/당근. 당근도 GA4 수집 활성화 (sources: daangn + danggn)

  const channels = [

    {row:18, name:'메타',   sheet:'메타',   inq:'메타',   ga4:true,  sources:['meta','facebook.com','m.facebook.com','l.facebook.com']},

    {row:19, name:'구글',   sheet:'구글',   inq:'구글',   ga4:true,  sources:['google']},

    {row:20, name:'네이버', sheet:'네이버', inq:'네이버', ga4:true,  sources:['naver','naver_blog','ad.search.naver.com','m.ad.search.naver.com','m.search.naver.com']},

    {row:21, name:'카카오', sheet:'카카오', inq:'카카오', ga4:true,  sources:['kakao']},

    {row:22, name:'당근',   sheet:'당근',   inq:'당근',   ga4:true,  sources:['daangn','danggn']},

  ];

  const fmtKM = '[>=1000000]0.00,,"M";[>=1000]0.0,"K";#,##0';

  const fmtKMWon = '[>=1000000]0.00,,"M원";[>=1000]0.0,"K원";#,##0"원"';

  const ga4D = `'GA4_자동'!A:A,">="&TEXT($N$16,"yyyymmdd"),'GA4_자동'!A:A,"<="&TEXT($O$16,"yyyymmdd")`;

  channels.forEach(({row, name, sheet, inq, ga4, sources}) => {

    sh.getRange(row, 1).setValue(name).setFontWeight('bold');

    const ad = (col) => `SUMIFS('${sheet}'!${col}:${col},'${sheet}'!A:A,">="&$N$16,'${sheet}'!A:A,"<="&$O$16)`;

    sh.getRange(row, 2).setFormula(`=IFERROR(${ad('E')},0)`).setNumberFormat(fmtKM);

    sh.getRange(row, 3).setFormula(`=IFERROR(${ad('F')},0)`).setNumberFormat(fmtKM);

    sh.getRange(row, 4).setFormula(`=IFERROR(${ad('G')},0)`).setNumberFormat(fmtKMWon);

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

  SpreadsheetApp.getUi().alert('✅ 채널 매트릭스 갱신 완료\n· 당근 GA4 수집 활성화 (daangn + danggn)');

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

  const sheetNames = ['메타','구글','네이버','카카오','당근'];

  const dispNames  = ['메타','구글','네이버','카카오','당근'];

  sh.getRange('A3').setValue('날짜');

  dispNames.forEach((nm, i) => sh.getRange(3, 2 + i).setValue(nm));

  sh.getRange(3, 7).setValue('일합계');

  sh.getRange('A3:G3').setBackground('#D9E1F2').setFontWeight('bold')

    .setBorder(true,true,true,true,true,true).setHorizontalAlignment('center');

  for (let i = 0; i < 30; i++) {

    const r = 4 + i;

    sh.getRange(r, 1).setFormula(`=TODAY()-${29 - i}`).setNumberFormat('M/d (ddd)');

    sheetNames.forEach((ch, c) => {

      sh.getRange(r, 2 + c).setFormula(`=IFERROR(SUMIFS('${ch}'!G:G,'${ch}'!A:A,A${r}),0)`)

        .setNumberFormat('#,##0');

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

  dispNames.forEach((nm, i) => sh.getRange(38, 2 + i).setValue(nm));

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

// ──[수동]── 통합대시보드 행27 네비게이션 링크 복구

// ──[수동]── 통합대시보드 H1에 새로고침 안내문구

// ──[수동]── UTM_생성기 드롭다운 5종 설정

// ──[유틸]── 숨긴 시트 전부 다시 표시

// ──[유틸]── 전체 시트 이름/GID 로그 출력

// ──[일상]── SNS 채널 운영 보고 (E28 자체 드롭다운으로 기간 별도 설정)

function updateSNSReport(opts) {

  opts = opts || {};

  const forceRebuild = opts.forceRebuild !== false; // 기본 true (메뉴/수동 실행 시 재생성)

  const showAlert = opts.showAlert !== false;       // 기본 true

  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const sh = ss.getSheetByName('통합대시보드');

  // 이미 표가 만들어져 있고 강제 재생성이 아니면 → 재생성 생략. 수식이 자동 재계산되므로 데이터는 최신 유지

  if (!forceRebuild && sh.getRange('A28').getValue() === '★ SNS 채널 운영') {

    return;

  }

  sh.getRange('A28:Z35').breakApart();

  sh.getRange('A28:Z35').clearContent().clearFormat();

  // ── 행 28: 섹션 헤더 + SNS 전용 기간 드롭다운 ──

  sh.getRange('A28:C28').merge().setValue('★ SNS 채널 운영')

    .setBackground('#1F4E78').setFontColor('#FFFFFF')

    .setFontWeight('bold').setFontSize(13);

  sh.getRange('D28').setValue('📅 기간:').setFontWeight('bold').setHorizontalAlignment('right');

  sh.getRange('E28').setBackground('#FFF59D').setFontWeight('bold').setHorizontalAlignment('center')

    .setDataValidation(SpreadsheetApp.newDataValidation()

      .requireValueInList(['어제','최근 7일','최근 30일'], true).setAllowInvalid(false).build());

  if (sh.getRange('E28').getValue() === '') sh.getRange('E28').setValue('최근 30일');

  // 보조 셀 N28(시작) / O28(종료) — 채널 매트릭스의 N16/O16과 완전 분리

  sh.getRange('M28').setValue('기간▶').setFontColor('#BBBBBB').setFontSize(8).setHorizontalAlignment('right');

  sh.getRange('N28').setFormula('=IF($E$28="어제",TODAY()-1,IF($E$28="최근 7일",TODAY()-6,TODAY()-29))')

    .setNumberFormat('m/d').setFontColor('#BBBBBB');

  sh.getRange('O28').setFormula('=IF($E$28="어제",TODAY()-1,TODAY())')

    .setNumberFormat('m/d').setFontColor('#BBBBBB');

  // 행 29: 컬럼 헤더

  const h = ['채널','포스트수','총 조회수','평균','최고','팔로워','시트'];

  sh.getRange(29, 1, 1, 7).setValues([h])

    .setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center');

  // 행 30~33: SNS 채널 4개

  const sns = [

    {row: 30, name: '스레드', sheet: '스레드'},

    {row: 31, name: '인스타', sheet: '인스타'},

    {row: 32, name: '유튜브', sheet: '유튜브'},

    {row: 33, name: '틱톡',   sheet: '틱톡'},

  ];

  sns.forEach(({row, name, sheet}) => {

    sh.getRange(row, 1).setValue(name).setFontWeight('bold');

    // 기간 = $N$28 ~ $O$28 (SNS 전용 드롭다운)

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

// A열 날짜 / E열 조회수 / G열 팔로워 수 / K열 월 기준

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

    // 월별 합계표 영역만 정비한다. 원본 운영일지 A:I는 건드리지 않는다.

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

      // K열 월 값은 실제 날짜값(해당 월 1일)으로 넣고, 표시는 yyyy.m 형태로 처리

      sh.getRange(r, 11)

        .setFormula(`=DATE(YEAR('통합대시보드'!$B$2),${m},1)`)

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

      // 최종 테스트 통과한 방식: 해당 월의 날짜+팔로워만 FILTER → 날짜 최신순 SORT → 첫 행의 팔로워 반환

      sh.getRange(r, 16)

        .setFormula(`=IFERROR(INDEX(SORT(FILTER({$A$4:$A$1000,$G$4:$G$1000},$A$4:$A$1000>=$K${r},$A$4:$A$1000<=EOMONTH($K${r},0),$G$4:$G$1000<>""),1,FALSE),1,2),"-")`)

        .setNumberFormat('#,##0');

    }

    const totalRow = 16;

    sh.getRange(totalRow, 11)

      .setFormula(`=YEAR('통합대시보드'!$B$2)&" 합계"`)

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

      .setFormula(`=IFERROR(INDEX(SORT(FILTER({$A$4:$A$1000,$G$4:$G$1000},YEAR($A$4:$A$1000)=YEAR('통합대시보드'!$B$2),$G$4:$G$1000<>""),1,FALSE),1,2),"-")`)

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

//  목적: 별도 시트를 만들지 않고, 문의접수 시트 우측 H:Q 영역에

//        카카오 공식 리포트 입력/검증 영역을 추가한다.

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

    // Google Sheets serial date 대응. 1899-12-30 기준.

    const d = new Date(Math.round((value - 25569) * 86400 * 1000));

    if (!isNaN(d.getTime())) return Utilities.formatDate(d, TZ, 'yyyy-MM-dd');

  }

  const s = String(value || '').trim();

  if (!s) return '';

  // 2026-05-27 / 2026.05.27 / 2026/05/27

  let m = s.match(/^(\d{4})[-./](\d{1,2})[-./](\d{1,2})/);

  if (m) {

    return `${m[1]}-${String(m[2]).padStart(2, '0')}-${String(m[3]).padStart(2, '0')}`;

  }

  // 2025년 12월 31일

  m = s.match(/^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일/);

  if (m) {

    return `${m[1]}-${String(m[2]).padStart(2, '0')}-${String(m[3]).padStart(2, '0')}`;

  }

  // 5월 27일 → 기본 연도 적용

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

// ──[수동/일상]── 문의접수 시트 우측 H:Q에 카톡 리포트 입력 영역 생성/정비

function setupKakaoDailyReport() {

  const sh = getInquirySheet_();

  const startCol = KAKAO_REPORT_START_COL;

  const numCols = KAKAO_REPORT_NUM_COLS;

  // 상단 안내/헤더만 정비한다. H5:K 이하 사용자가 붙여넣은 원본 데이터는 삭제하지 않는다.

  // H1:Q4 안의 기존 병합 셀을 먼저 해제해야 재실행해도 오류가 나지 않는다.

  sh.getRange(1, startCol, 4, numCols).breakApart();

  sh.getRange(1, startCol, 4, numCols).clearContent().clearFormat();

  sh.getRange(1, startCol, 1, numCols).merge()

    .setValue('■ 카톡 리포트 입력/검증 — H:K 5행부터 원본 붙여넣기')

    .setBackground('#1F4E78').setFontColor('#FFFFFF')

    .setFontWeight('bold').setFontSize(12)

    .setHorizontalAlignment('center');

  // 행 2: 컬럼별 설명. 처음 보는 사람도 각 지표 의미를 알 수 있게 개별 설명을 노출한다.

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

  // 행 3: 영역 구분 헤더 — 원본 리포트 / 수기 검증 / 성과 / 판단을 시각적으로 분리

  const groups = [

    {col: startCol,     cols: 4, label: '① 카카오 공식 리포트', bg: '#D9EAF7'}, // H:K

    {col: startCol + 4, cols: 3, label: '② 관리대장 입력 검증', bg: '#FFF2CC'}, // L:N

    {col: startCol + 7, cols: 2, label: '③ 개통 성과', bg: '#E2F0D9'}, // O:P

    {col: startCol + 9, cols: 1, label: '④ 관리 상태', bg: '#F4CCCC'}, // Q

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

  sh.setColumnWidths(startCol, 1, 115);      // H 날짜

  sh.setColumnWidths(startCol + 1, 3, 120);  // I:K 원본 리포트

  sh.setColumnWidths(startCol + 4, 6, 110);  // L:Q 계산값

  sh.getRange(1, startCol, 4, numCols).setWrap(true);

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 1).setNumberFormat('yyyy-mm-dd');

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 1, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 4).setNumberFormat('#,##0');

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 5, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 1).setNumberFormat('0.0%');

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 6, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 2).setNumberFormat('#,##0');

  sh.getRange(KAKAO_REPORT_DATA_ROW, startCol + 8, sh.getMaxRows() - KAKAO_REPORT_DATA_ROW + 1, 1).setNumberFormat('0.0%');

  SpreadsheetApp.getUi().alert('✅ 문의접수 시트 우측에 카톡 리포트 영역 정비 완료\nH:K 5행부터 카카오 리포트를 붙여넣은 뒤 입력률 갱신을 실행하세요.\n각 컬럼 설명은 2행과 헤더 메모에 표시됩니다.');

}

function setupKakaoDailyReportHeadersOnly_(sh) {

  const startCol = KAKAO_REPORT_START_COL;

  const headers = ['날짜','친구수','채널 추가수 합계','채팅 요청 친구수','관리대장 입력건','입력률','누락추정','개통수','개통률','상태'];

  const current = sh.getRange(KAKAO_REPORT_HEADER_ROW, startCol, 1, headers.length).getValues()[0].join('');

  if (current.indexOf('채팅 요청 친구수') === -1 || current.indexOf('입력률') === -1) {

    setupKakaoDailyReport();

  }

}

// ──[일상]── H:K 카톡 공식 리포트와 A:E 문의접수 관리대장을 비교

function updateKakaoInquiryCoverage(showAlert) {

  const sh = getInquirySheet_();

  setupKakaoDailyReportHeadersOnly_(sh);

  const defaultYear = new Date().getFullYear();

  const sheetLastRow = Math.max(sh.getLastRow(), KAKAO_REPORT_DATA_ROW);

  // A:C 기존 문의접수 영역 집계. H:Q 리포트 영역은 A:C가 비어 있으므로 집계에 섞이지 않는다.

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

  // H:K에서 실제 데이터가 있는 마지막 행까지만 계산한다.

  let lastDataIndex = -1;

  rawValues.forEach((row, i) => {

    if (row.some(v => String(v || '').trim() !== '')) lastDataIndex = i;

  });

  if (lastDataIndex < 0) {

    if (showAlert !== false) SpreadsheetApp.getUi().alert('문의접수 시트 H:K 5행부터 카톡 리포트를 먼저 붙여넣어야 합니다.');

    return;

  }

  // 기존 계산값 L:Q는 지우되, 원본 H:K는 보존한다.

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

    normalizedDates.push([ymd ? new Date(ymd + 'T00:00:00+09:00') : row[0]]);

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

    SpreadsheetApp.getUi().alert('✅ 문의접수 입력률 갱신 완료\n· H:K 카톡 공식 리포트 대비 A:E 관리대장 입력률 산출\n· 누락추정/개통수/개통률 반영');

  }

}

// ──[일상]── 통합대시보드 A36:H40에 카톡 문의 입력률 요약 표시

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

      .requireValueInList(['어제','최근 7일','최근 30일'], true).setAllowInvalid(false).build());

  if (dash.getRange('E36').getValue() === '') dash.getRange('E36').setValue('최근 30일');

  dash.getRange('M36').setValue('기간▶').setFontColor('#BBBBBB').setFontSize(8).setHorizontalAlignment('right');

  dash.getRange('N36').setFormula('=IF($E$36="어제",TODAY()-1,IF($E$36="최근 7일",TODAY()-6,TODAY()-29))')

    .setNumberFormat('m/d').setFontColor('#BBBBBB');

  dash.getRange('O36').setFormula('=IF($E$36="어제",TODAY()-1,TODAY())')

    .setNumberFormat('m/d').setFontColor('#BBBBBB');

  const headers = ['카톡 채팅요청','관리대장 입력','입력률','누락추정','개통','개통률','친구증가','판단'];

  dash.getRange(37, 1, 1, headers.length).setValues([headers])

    .setBackground('#D9E1F2').setFontWeight('bold')

    .setHorizontalAlignment('center').setBorder(true,true,true,true,true,true);

  // 문의접수 내장 리포트 영역: H 날짜 / J 채널추가 / K 채팅요청 / L 관리대장입력 / O 개통

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

