// ══════════════════════════════════════════════════════════════
//  페이지별 퍼널 — 리틀리 vs 시티마켓 분리측정 (2026-07-20 신설, GA4 전담 task / 종민 지시)
//  세션 "시작 위치(landingPage)" 기준으로 유입을 가른다:
//    · 리틀리에서 시작한 세션      → 리틀리 성과 (시티마켓 경유 도착·카톡 포함)
//    · 시티마켓에서 직접 시작한 세션 → 시티마켓 직접 성과
//  근거: citymarket_arrival이 원 광고소스(meta 57.5% 등)를 유지 → source로는 경유/직접 구분 불가.
//        세션 시작 페이지(landingPage)로만 깔끔히 분리됨.
//
//  ★ 격리 원칙(무회귀): 기존 GA4_자동 / SUMIFS 소비수식 / 통합대시보드 / 리틀리 탭은 절대 수정 안 함.
//     신규 탭 2개(GA4_페이지별, 페이지별_퍼널)만 insertSheet로 생성. insertColumnBefore 미사용.
//  ★ 시티마켓 카톡/전화 클릭은 GTM 이벤트 태그(kakao_chat_click / phone_click)가 있어야 집계됨.
//  ★ 멀티브랜드: 폰스팟 기본값 하드코딩. KT 등 랜딩 경로가 다르면 _설정 시트에 PF_* 키로 덮어쓰기.
//
//  성능(2026-07-21): 6분 한도 초과 방지 —
//    (1) 랜딩 차원 = landingPage(경로만, 쿼리 제거) → 원천 행 수 급감. 실패 시 landingPagePlusQueryString 폴백.
//    (2) 시트 쓰기는 탭당 setValues 1회(배치). 행별 setValues/setNote 금지.
//    (3) 마지막 날 누락 버그(날짜 타임스탬프 비교)를 날짜 문자열 비교로 수정.
// ══════════════════════════════════════════════════════════════

var PF_DETAIL_SHEET = 'GA4_페이지별';   // 날짜×유입×이벤트 집계(투명성/차팅용)
var PF_FUNNEL_SHEET = '페이지별_퍼널';  // 요약 퍼널 + 랜딩경로 진단
var PF_LOOKBACK_DAYS = 30;

// ── 유입 버킷 분류 (landingPage 경로 프리픽스). 브랜드별로 _설정에서 덮어쓸 수 있음. ──
function pf_buckets_() {
  return {
    a: { name: String(getBrandConfig_('PF_A_NAME', '리틀리')),
         paths: pf_splitPaths_(getBrandConfig_('PF_A_PATHS', '/phonespot')) },
    b: { name: String(getBrandConfig_('PF_B_NAME', '시티마켓')),
         paths: pf_splitPaths_(getBrandConfig_('PF_B_PATHS', '/pb,/poni,/pspot,/b2b')) },
    // 랜딩페이지 (not set)/빈값 = GA4가 랜딩을 못 잡은 세션. 어느 버킷으로 볼지 _설정에서 조정.
    // 기본 '기타'(정직). '시티마켓'으로 두면 랜딩 소실된 시티마켓 유입을 시티마켓 성과로 귀속(추정).
    notset: String(getBrandConfig_('PF_NOTSET_BUCKET', '기타'))
  };
}
function pf_splitPaths_(s) {
  return String(s || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean);
}
function pf_classify_(landingPath, bk) {
  var p = String(landingPath || '');
  var q = p.indexOf('?'); if (q >= 0) p = p.slice(0, q);   // 쿼리스트링 제거
  if (p === '' || p === '(not set)') return bk.notset;      // 랜딩 소실 세션
  var i;
  for (i = 0; i < bk.a.paths.length; i++) if (p.indexOf(bk.a.paths[i]) === 0) return bk.a.name;
  for (i = 0; i < bk.b.paths.length; i++) if (p.indexOf(bk.b.paths[i]) === 0) return bk.b.name;
  return '기타';
}

// ── GA4 runReport (landing 차원 지정). 유효하지 않은 차원명이면 throw → 폴백에서 처리. ──
function pf_fetch_(landingDim, start, end, propId) {
  var TZ = 'Asia/Seoul';
  var req = {
    dateRanges: [{ startDate: Utilities.formatDate(start, TZ, 'yyyy-MM-dd'),
                   endDate: Utilities.formatDate(end, TZ, 'yyyy-MM-dd') }],
    dimensions: [{ name: 'date' }, { name: landingDim }, { name: 'eventName' }],
    metrics: [{ name: 'eventCount' }, { name: 'sessions' }],
    orderBys: [{ dimension: { dimensionName: 'date' }, desc: true }],
    limit: 100000
  };
  return AnalyticsData.Properties.runReport(req, 'properties/' + propId);
}

// ──[일상/수동]── GA4 → 랜딩페이지 차원 수집 → 유입별 집계 → 두 신규 탭 재작성 ──
function fetchPageFunnel() {
  var ss = SpreadsheetApp.getActive();
  var end = new Date(); end.setDate(end.getDate() - 1);
  var start = new Date(); start.setDate(start.getDate() - PF_LOOKBACK_DAYS);
  var propId = getBrandConfig_('GA4_PROP_ID', GA4_PROP_ID);

  // 경로만(landingPage)로 먼저 시도(행 수 급감) → 안 되면 쿼리포함 폴백
  var resp, dimUsed = 'landingPage';
  try {
    resp = pf_fetch_('landingPage', start, end, propId);
  } catch (e1) {
    dimUsed = 'landingPagePlusQueryString';
    resp = pf_fetch_('landingPagePlusQueryString', start, end, propId);
  }
  var rows = (resp && resp.rows) ? resp.rows : [];

  var bk = pf_buckets_();
  var agg = {};    // agg[yyyymmdd][bucket][event] = {ec, ss}
  var land = {};   // 랜딩경로(쿼리제거) -> {bucket, ev:{event:ec}} (분류 점검용)
  rows.forEach(function (r) {
    var d = r.dimensionValues[0].value;
    var lp = r.dimensionValues[1].value;
    var ev = (typeof normalizeGA4Event_ === 'function') ? normalizeGA4Event_(r.dimensionValues[2].value) : r.dimensionValues[2].value;
    var ec = parseInt(r.metricValues[0].value, 10) || 0;
    var ssn = parseInt(r.metricValues[1].value, 10) || 0;
    var bkt = pf_classify_(lp, bk);
    (agg[d] = agg[d] || {});
    (agg[d][bkt] = agg[d][bkt] || {});
    var cell = (agg[d][bkt][ev] = agg[d][bkt][ev] || { ec: 0, ss: 0 });
    cell.ec += ec; cell.ss += ssn;
    var lpath = String(lp || ''); var qq = lpath.indexOf('?'); if (qq >= 0) lpath = lpath.slice(0, qq);
    var L = (land[lpath] = land[lpath] || { bucket: bkt, ev: {} });
    L.ev[ev] = (L.ev[ev] || 0) + ec;
  });

  pf_writeDetail_(ss, agg, bk);
  pf_writeFunnel_(ss, agg, bk, start, end, land);

  if (typeof logSync_ === 'function') {
    try { logSync_('fetchPageFunnel', Object.keys(agg).length + '일 / 원천 ' + rows.length + '행 (' + dimUsed + ')'); } catch (e) {}
  }
  // ★ 논블로킹 토스트 (getUi().alert는 확인 클릭 대기 → '무한로딩'처럼 보임. toast로 교체 2026-07-21)
  try {
    ss.toast(rows.length + '행 · ' + bk.a.name + '/' + bk.b.name + ' 분리 완료. 시티마켓 카톡·전화는 GTM 태그 필요.',
      '✅ 페이지별 퍼널 갱신 (' + PF_LOOKBACK_DAYS + '일)', 8);
  } catch (e) {}
}

// ── 일별 상세 탭 (날짜|유입|이벤트|이벤트수|세션) — setValues 1회 배치 ──
function pf_writeDetail_(ss, agg, bk) {
  var sh = ss.getSheetByName(PF_DETAIL_SHEET);
  if (!sh) sh = ss.insertSheet(PF_DETAIL_SHEET);
  sh.clearContents();
  var grid = [['날짜', '유입', '이벤트', '이벤트수', '세션']];
  var order = [bk.a.name, bk.b.name, '기타'];
  Object.keys(agg).sort().reverse().forEach(function (d) {
    order.forEach(function (bkt) {
      var evs = agg[d][bkt];
      if (!evs) return;
      Object.keys(evs).sort().forEach(function (ev) {
        grid.push([d, bkt, ev, evs[ev].ec, evs[ev].ss]);
      });
    });
  });
  sh.getRange(1, 1, grid.length, 5).setValues(grid);
  sh.getRange(1, 1, 1, 5).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
  if (grid.length > 1) {
    sh.getRange(2, 1, grid.length - 1, 1).setNumberFormat('@');       // yyyymmdd 문자열
    sh.getRange(2, 4, grid.length - 1, 2).setNumberFormat('#,##0');
  }
  sh.setColumnWidths(1, 5, 120);
}

// ── 요약 퍼널 탭 (기간 × 유입버킷) + 랜딩경로 진단 — setValues 1회 배치 ──
function pf_writeFunnel_(ss, agg, bk, start, end, land) {
  var sh = ss.getSheetByName(PF_FUNNEL_SHEET);
  if (!sh) sh = ss.insertSheet(PF_FUNNEL_SHEET);
  sh.clear();

  var buckets = [bk.a.name, bk.b.name, '기타'];
  var EVENTS = ['session_start', 'citymarket_arrival', 'kakao_chat_click', 'phone_click', 'click'];
  var yKey = Utilities.formatDate(end, 'Asia/Seoul', 'yyyyMMdd');
  var ySet = {}; ySet[yKey] = 1;
  var d7s = new Date(end.getTime()); d7s.setDate(d7s.getDate() - 6);
  var periods = [['어제 (' + yKey + ')', ySet],
                 ['최근 7일', pf_dateSet_(d7s, end)],
                 ['최근 30일', pf_dateSet_(start, end)]];

  var title = '■ 페이지별 퍼널 — ' + bk.a.name + ' vs ' + bk.b.name + ' (세션 시작 위치 기준 분리, GA4)';
  var note = '※ ' + bk.a.name + '=세션이 ' + bk.a.name + '에서 시작 / ' + bk.b.name + '=' + bk.b.name +
    '에서 직접 시작. ' + bk.a.name + ' 경유로 ' + bk.b.name + ' 도착·카톡한 건은 ' + bk.a.name +
    ' 성과로 집계. ⚠️ ' + bk.b.name + ' 카톡·전화는 GTM 이벤트 태그(kakao_chat_click/phone_click)가 있어야 잡힘.';

  var grid = [];
  grid.push([title, '', '', '', '', '', '']);
  grid.push([note, '', '', '', '', '', '']);
  grid.push(['', '', '', '', '', '', '']);
  var headerRows = [];   // 1-index 저장(배경 칠)
  periods.forEach(function (p) {
    headerRows.push(grid.length + 1);
    grid.push(['── ' + p[0] + ' ──', '방문(세션)', '가격확인도착', '카톡클릭', '전화클릭', '링크클릭', '카톡전환율']);
    buckets.forEach(function (bkt) {
      var v = {};
      EVENTS.forEach(function (e) { v[e] = pf_sum_(agg, p[1], bkt, e); });
      var rate = v.session_start > 0 ? v.kakao_chat_click / v.session_start : '';
      grid.push([bkt, v.session_start, v.citymarket_arrival, v.kakao_chat_click, v.phone_click, v.click, rate]);
    });
    grid.push(['', '', '', '', '', '', '']);
  });

  // 랜딩경로 진단 (기타가 크면 실제 경로 확인 → _설정 PF_A_PATHS/PF_B_PATHS 보정)
  var diagHeaderRow = grid.length + 1;
  grid.push(['── 랜딩경로 상위 (분류 점검용, 30일) ──', '유입', '방문(session_start)', '가격확인도착', '카톡클릭', '', '']);
  var arr = Object.keys(land).map(function (p) {
    var e = land[p].ev;
    return { p: p, b: land[p].bucket, ss: e['session_start'] || 0, ca: e['citymarket_arrival'] || 0, kk: e['kakao_chat_click'] || 0 };
  });
  arr.sort(function (a, b) { return (b.ss + b.ca) - (a.ss + a.ca); });
  arr.slice(0, 25).forEach(function (x) {
    grid.push([x.p, x.b, x.ss, x.ca, x.kk, '', '']);
  });

  // ── 단일 배치 쓰기 ──
  sh.getRange(1, 1, grid.length, 7).setValues(grid);
  // 서식(범위 단위 몇 번만)
  sh.getRange(1, 1, 1, 7).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(12);
  sh.getRange(2, 1, 1, 7).setFontStyle('italic').setFontColor('#666').setWrap(true);
  sh.getRange(4, 2, grid.length - 3, 5).setNumberFormat('#,##0');   // 숫자 열
  sh.getRange(4, 7, grid.length - 3, 1).setNumberFormat('0.0%');    // 전환율 열
  headerRows.forEach(function (r) { sh.getRange(r, 1, 1, 7).setBackground('#D9E1F2').setFontWeight('bold'); });
  sh.getRange(diagHeaderRow, 1, 1, 5).setBackground('#FCE4D6').setFontWeight('bold');
  sh.setColumnWidths(1, 7, 110);
  sh.setColumnWidth(1, 320);
  sh.setFrozenRows(3);
}

// 기간 합계: agg에서 dateSet에 속한 날짜의 특정 버킷·이벤트 eventCount 합
function pf_sum_(agg, dateSet, bucket, event) {
  var t = 0;
  Object.keys(agg).forEach(function (d) {
    if (!dateSet[d]) return;
    var b = agg[d][bucket];
    if (b && b[event]) t += b[event].ec;
  });
  return t;
}

// [start..end] 포함 yyyymmdd 집합.
// ★ 날짜 "문자열(yyyymmdd)"로 비교 — start/end가 서로 다른 new Date()라 ms가 어긋나면
//   타임스탬프 비교 시 마지막 날이 <= 에서 탈락하는 버그가 있었음(2026-07-21 수정).
function pf_dateSet_(start, end) {
  var TZ = 'Asia/Seoul', s = {}, cur = new Date(start.getTime());
  var endK = Utilities.formatDate(end, TZ, 'yyyyMMdd');
  var k = Utilities.formatDate(cur, TZ, 'yyyyMMdd');
  var guard = 0;
  while (k <= endK && guard < 400) {
    s[k] = 1;
    cur.setDate(cur.getDate() + 1);
    k = Utilities.formatDate(cur, TZ, 'yyyyMMdd');
    guard++;
  }
  return s;
}

// ── 메뉴 항목은 Code.js 메인 메뉴('브랜드 통합' > GA4 그룹)에 직접 추가됨
//    (fetchPageFunnel / setupPageFunnelTrigger). 별도 상단 메뉴는 오버플로로 안 보여서 폐기 (2026-07-20).

// ── 전용 시간트리거 (동명 트리거 삭제 후 재생성 = 중복 방지) ──
function setupPageFunnelTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'fetchPageFunnel') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('fetchPageFunnel').timeBased().atHour(3).nearMinute(30).everyDays(1).create();
  try { SpreadsheetApp.getUi().alert('✅ 페이지별 퍼널 트리거 등록 (매일 03:30). 기존 트리거는 건드리지 않음.'); } catch (e) {}
}
