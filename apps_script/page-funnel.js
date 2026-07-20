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
//     버튼은 있는데 태그가 없으면 시티마켓 카톡 칸은 0으로 나옴(사이트/GTM 작업 = 종민/사이트팀).
//  ★ 멀티브랜드: 폰스팟 기본값 하드코딩. KT 등 랜딩 경로가 다르면 _설정 시트에 PF_* 키로 덮어쓰기.
// ══════════════════════════════════════════════════════════════

var PF_DETAIL_SHEET = 'GA4_페이지별';   // 날짜×유입×이벤트 집계(투명성/차팅용)
var PF_FUNNEL_SHEET = '페이지별_퍼널';  // 요약 퍼널(어제/최근7일/최근30일)
var PF_LOOKBACK_DAYS = 30;

// ── 유입 버킷 분류 (landingPage 경로 프리픽스). 브랜드별로 _설정에서 덮어쓸 수 있음. ──
function pf_buckets_() {
  return {
    a: { name: String(getBrandConfig_('PF_A_NAME', '리틀리')),
         paths: pf_splitPaths_(getBrandConfig_('PF_A_PATHS', '/phonespot')) },
    b: { name: String(getBrandConfig_('PF_B_NAME', '시티마켓')),
         paths: pf_splitPaths_(getBrandConfig_('PF_B_PATHS', '/pb,/poni,/pspot,/b2b')) }
  };
}
function pf_splitPaths_(s) {
  return String(s || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean);
}
function pf_classify_(landingPath, bk) {
  var p = String(landingPath || '');
  var q = p.indexOf('?'); if (q >= 0) p = p.slice(0, q);   // 쿼리스트링 제거
  var i;
  for (i = 0; i < bk.a.paths.length; i++) if (p.indexOf(bk.a.paths[i]) === 0) return bk.a.name;
  for (i = 0; i < bk.b.paths.length; i++) if (p.indexOf(bk.b.paths[i]) === 0) return bk.b.name;
  return '기타';
}

// ──[일상/수동]── GA4 Data API → 랜딩페이지 차원으로 수집 → 유입별 집계 → 두 신규 탭 재작성
function fetchPageFunnel() {
  var ss = SpreadsheetApp.getActive();
  var TZ = 'Asia/Seoul';
  var end = new Date(); end.setDate(end.getDate() - 1);
  var start = new Date(); start.setDate(start.getDate() - PF_LOOKBACK_DAYS);

  var req = {
    dateRanges: [{ startDate: Utilities.formatDate(start, TZ, 'yyyy-MM-dd'),
                   endDate: Utilities.formatDate(end, TZ, 'yyyy-MM-dd') }],
    dimensions: [{ name: 'date' }, { name: 'landingPagePlusQueryString' }, { name: 'eventName' }],
    metrics: [{ name: 'eventCount' }, { name: 'sessions' }],
    orderBys: [{ dimension: { dimensionName: 'date' }, desc: true }],
    limit: 100000
  };
  var resp = AnalyticsData.Properties.runReport(req, 'properties/' + getBrandConfig_('GA4_PROP_ID', GA4_PROP_ID));
  var rows = (resp && resp.rows) ? resp.rows : [];

  var bk = pf_buckets_();
  // agg[yyyymmdd][bucket][event] = {ec, ss}
  var agg = {};
  rows.forEach(function (r) {
    var d = r.dimensionValues[0].value;               // yyyymmdd
    var lp = r.dimensionValues[1].value;
    var ev = r.dimensionValues[2].value;
    var ec = parseInt(r.metricValues[0].value, 10) || 0;
    var ssn = parseInt(r.metricValues[1].value, 10) || 0;
    var bkt = pf_classify_(lp, bk);
    (agg[d] = agg[d] || {});
    (agg[d][bkt] = agg[d][bkt] || {});
    var cell = (agg[d][bkt][ev] = agg[d][bkt][ev] || { ec: 0, ss: 0 });
    cell.ec += ec; cell.ss += ssn;
  });

  pf_writeDetail_(ss, agg, bk);
  pf_writeFunnel_(ss, agg, bk, start, end);

  if (typeof logSync_ === 'function') {
    try { logSync_('fetchPageFunnel', Object.keys(agg).length + '일 / 원천 ' + rows.length + '행 집계'); } catch (e) {}
  }
  try {
    SpreadsheetApp.getUi().alert('✅ 페이지별 퍼널 갱신 (' + PF_LOOKBACK_DAYS + '일)\n' +
      '· ' + bk.a.name + ' / ' + bk.b.name + ' 분리 (세션 시작 위치 기준)\n' +
      '· 탭: ' + PF_FUNNEL_SHEET + ' (요약) + ' + PF_DETAIL_SHEET + ' (일별 상세)\n' +
      '⚠️ 시티마켓 카톡·전화는 GTM 이벤트 태그가 있어야 0이 아님.');
  } catch (e) {}
}

// ── 일별 상세 탭 (날짜|유입|이벤트|이벤트수|세션) ──
function pf_writeDetail_(ss, agg, bk) {
  var sh = ss.getSheetByName(PF_DETAIL_SHEET);
  if (!sh) sh = ss.insertSheet(PF_DETAIL_SHEET);
  sh.clearContents();
  sh.getCharts().forEach(function (c) { sh.removeChart(c); });
  sh.getRange(1, 1, 1, 5).setValues([['날짜', '유입', '이벤트', '이벤트수', '세션']])
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
  var out = [];
  var order = [bk.a.name, bk.b.name, '기타'];
  Object.keys(agg).sort().reverse().forEach(function (d) {
    order.forEach(function (bkt) {
      var evs = agg[d][bkt];
      if (!evs) return;
      Object.keys(evs).sort().forEach(function (ev) {
        out.push([d, bkt, ev, evs[ev].ec, evs[ev].ss]);
      });
    });
  });
  if (out.length) {
    sh.getRange(2, 1, out.length, 5).setValues(out);
    sh.getRange(2, 1, out.length, 1).setNumberFormat('@');   // yyyymmdd 문자열
    sh.getRange(2, 4, out.length, 2).setNumberFormat('#,##0');
  }
  sh.setColumnWidths(1, 5, 120);
}

// ── 요약 퍼널 탭 (기간 × 유입버킷) ──
function pf_writeFunnel_(ss, agg, bk, start, end) {
  var sh = ss.getSheetByName(PF_FUNNEL_SHEET);
  if (!sh) sh = ss.insertSheet(PF_FUNNEL_SHEET);
  sh.clear();

  var buckets = [bk.a.name, bk.b.name, '기타'];
  // 이벤트 라벨 ↔ GA4 eventName (방문=session_start, 가격확인도착=citymarket_arrival ...)
  var EV = [['방문(세션)', 'session_start'], ['가격확인도착', 'citymarket_arrival'],
            ['카톡클릭', 'kakao_chat_click'], ['전화클릭', 'phone_click'], ['링크클릭', 'click']];

  var yKey = Utilities.formatDate(end, 'Asia/Seoul', 'yyyyMMdd');
  var ySet = {}; ySet[yKey] = 1;
  var d7s = new Date(end.getTime()); d7s.setDate(d7s.getDate() - 6);
  var periods = [['어제 (' + yKey + ')', ySet],
                 ['최근 7일', pf_dateSet_(d7s, end)],
                 ['최근 30일', pf_dateSet_(start, end)]];

  sh.getRange('A1:G1').merge()
    .setValue('■ 페이지별 퍼널 — ' + bk.a.name + ' vs ' + bk.b.name + ' (세션 시작 위치 기준 분리, GA4)')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setFontSize(12);
  sh.getRange('A2:G2').merge()
    .setValue('※ ' + bk.a.name + '=세션이 ' + bk.a.name + '에서 시작 / ' + bk.b.name + '=' + bk.b.name +
      '에서 직접 시작. ' + bk.a.name + ' 경유로 ' + bk.b.name + ' 도착·카톡한 건은 ' + bk.a.name +
      ' 성과로 집계. ⚠️ ' + bk.b.name + ' 카톡·전화는 GTM 이벤트 태그(kakao_chat_click/phone_click)가 있어야 잡힘.')
    .setFontStyle('italic').setFontColor('#666').setWrap(true);

  var row = 4;
  periods.forEach(function (p) {
    sh.getRange(row, 1, 1, 7)
      .setValues([['── ' + p[0] + ' ──', '방문(세션)', '가격확인도착', '카톡클릭', '전화클릭', '링크클릭', '카톡전환율']])
      .setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center');
    sh.getRange(row, 1).setHorizontalAlignment('left');
    row++;
    buckets.forEach(function (bkt) {
      var vals = [bkt];
      EV.forEach(function (e) { vals.push(pf_sum_(agg, p[1], bkt, e[1])); });
      var visit = pf_sum_(agg, p[1], bkt, 'session_start');
      var kakao = pf_sum_(agg, p[1], bkt, 'kakao_chat_click');
      vals.push(visit > 0 ? kakao / visit : '');
      sh.getRange(row, 1, 1, 7).setValues([vals]);
      sh.getRange(row, 2, 1, 5).setNumberFormat('#,##0');
      sh.getRange(row, 7, 1, 1).setNumberFormat('0.0%');
      if (bkt === bk.b.name) sh.getRange(row, 4, 1, 2).setNote('GTM 이벤트 태그 없으면 0 (태그 필요)');
      row++;
    });
    row++;
  });
  sh.setColumnWidths(1, 7, 110);
  sh.setColumnWidth(1, 150);
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

// [start..end] 포함 yyyymmdd 집합
function pf_dateSet_(start, end) {
  var TZ = 'Asia/Seoul', s = {}, cur = new Date(start.getTime());
  while (cur.getTime() <= end.getTime()) {
    s[Utilities.formatDate(cur, TZ, 'yyyyMMdd')] = 1;
    cur.setDate(cur.getDate() + 1);
  }
  return s;
}

// ── 메뉴 (Code.js onOpen에서 buildPageFunnelMenu_ 호출) ──
function buildPageFunnelMenu_(ui) {
  ui.createMenu('📑 페이지별(리틀리/시티마켓)')
    .addItem('🧭 페이지별 퍼널 수집·갱신', 'fetchPageFunnel')
    .addItem('⏰ 페이지별 퍼널 트리거 등록 (매일 03:30)', 'setupPageFunnelTrigger')
    .addToUi();
}

// ── 전용 시간트리거 (동명 트리거 삭제 후 재생성 = 중복 방지) ──
function setupPageFunnelTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'fetchPageFunnel') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('fetchPageFunnel').timeBased().atHour(3).nearMinute(30).everyDays(1).create();
  try { SpreadsheetApp.getUi().alert('✅ 페이지별 퍼널 트리거 등록 (매일 03:30). 기존 트리거는 건드리지 않음.'); } catch (e) {}
}
