/**
 * timeslot_stats.gs — 발행 시각별 성과 분석 (4단계)
 *
 * 스레드 탭에는 날짜만 있고 시각이 없다. 그런데 시각은 시트에 없을 뿐
 * 스레드 API 가 게시물마다 timestamp 로 들고 있다. 그래서 과거 글까지
 * 소급해서 시간대를 붙일 수 있다 — 지금까지 쌓인 300행이 그대로 표본이 된다.
 *
 * 스레드 탭은 건드리지 않는다(K열부터 월별 합계 블록이 있어서 열을 못 늘린다).
 * 대신 성과_시간대 탭을 매번 새로 만든다. 이 탭은 읽기 전용 산출물이다.
 *
 *   buildTimeslotStats()  스레드 탭 + API → 성과_시간대 탭 생성
 *   reportTimeslot()      집계 결과를 로그로 (시트 안 건드림)
 *
 * ※ 평균과 중앙값을 같이 본다. 조회수는 한 건이 터지면 평균이 통째로 끌려가서
 *   평균만 보면 "그 시간대가 좋다"가 아니라 "그날 그 글이 터졌다"를 읽게 된다.
 */

var TS = {
  SHEET: '성과_시간대',
  SRC: '스레드',
  FIRST_ROW: 4,
  LOG_SHEET: '동기화_로그',
  MIN_N: 5,          // 표본이 이보다 적으면 결론 내지 않는다
  HEAD: ['날짜','시','시간대','요일','구분','단계','슬롯','주제','조회수','좋아요','답글','링크']
};

// 3시간 묶음. 과거 글은 아무 때나 올라가 있어서 시(hour) 단위로는 표본이 흩어진다.
var TS_BANDS = [
  [0, 5, '새벽 0-5'], [6, 8, '아침 6-8'], [9, 11, '오전 9-11'],
  [12, 14, '점심 12-14'], [15, 17, '오후 15-17'], [18, 20, '저녁 18-20'], [21, 23, '밤 21-23']
];
var TS_DOW = ['일', '월', '화', '수', '목', '금', '토'];

// ─────────────────────────────────────────────
// 진입점
// ─────────────────────────────────────────────

/** 스레드 탭 전체에 발행 시각을 붙여 성과_시간대 탭을 다시 만든다. */
function buildTimeslotStats() {
  var rows = collectTimeslotRows_();
  if (!rows.length) { Logger.log('분석할 행이 없습니다. 먼저 syncThreads 를 돌리세요.'); return; }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(TS.SHEET);
  if (!sh) sh = ss.insertSheet(TS.SHEET);
  sh.clear();
  sh.getRange(1, 1, 1, TS.HEAD.length).setValues([TS.HEAD]).setFontWeight('bold');
  sh.setFrozenRows(1);
  sh.getRange(2, 1, rows.length, TS.HEAD.length).setValues(rows);
  sh.setColumnWidth(8, 300);

  Logger.log('성과_시간대 %s행 생성', rows.length);
  tsSummary_(rows).forEach(function (line) { Logger.log(line); });
  tsLog_('OK', '성과_시간대 ' + rows.length + '행');
}

/** 시트를 안 건드리고 집계만 로그로 본다 */
function reportTimeslot() {
  var rows = collectTimeslotRows_();
  if (!rows.length) { Logger.log('분석할 행이 없습니다.'); return; }
  tsSummary_(rows).forEach(function (line) { Logger.log(line); });
}

// ─────────────────────────────────────────────
// 수집
// ─────────────────────────────────────────────

function collectTimeslotRows_() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TS.SRC);
  if (!sh) { Logger.log('스레드 탭 없음'); return []; }
  var last = sh.getLastRow();
  if (last < TS.FIRST_ROW) return [];

  var n = last - TS.FIRST_ROW + 1;
  var v = sh.getRange(TS.FIRST_ROW, 1, n, 10).getValues();   // A~J

  var postMap;
  try { postMap = fetchMyThreads_(); }        // threads_sync.gs 재사용
  catch (err) { Logger.log('API 조회 실패: %s', String(err).slice(0, 200)); return []; }

  var out = [], noTime = 0;
  for (var i = 0; i < n; i++) {
    var url = String(v[i][3] || '').trim();
    if (!url) continue;
    var views = v[i][4];
    if (views === '' || views == null) continue;      // 성과가 안 채워진 행은 분석 대상이 아니다

    var code = shortcodeFromUrl_(url);
    var post = code ? postMap[code] : null;
    if (!post || !post.timestamp) { noTime++; continue; }

    var d = new Date(post.timestamp);                 // ISO8601 (+0000)
    var kst = Utilities.formatDate(d, 'Asia/Seoul', 'yyyy-MM-dd|HH|u').split('|');
    var hour = parseInt(kst[1], 10);
    var dow = TS_DOW[parseInt(kst[2], 10) % 7];       // u: 1=월 … 7=일

    var meta = String(v[i][8] || '');
    var stage = (meta.match(/단계=(\d)/) || [])[1] || '';
    var slot  = (meta.match(/슬롯=(\d+)/) || [])[1] || '';

    out.push([kst[0], hour, bandOf_(hour), dow, v[i][1], stage, slot,
              String(v[i][2] || '').slice(0, 60), views, v[i][5], v[i][9], url]);
  }
  if (noTime) Logger.log('시각을 못 붙인 행 %s개 (삭제됐거나 다른 계정 글)', noTime);
  return out;
}

function bandOf_(hour) {
  for (var i = 0; i < TS_BANDS.length; i++) {
    if (hour >= TS_BANDS[i][0] && hour <= TS_BANDS[i][1]) return TS_BANDS[i][2];
  }
  return '기타';
}

// ─────────────────────────────────────────────
// 집계
// ─────────────────────────────────────────────

function tsSummary_(rows) {
  var out = [];
  out.push('──────── 시간대별 조회수 (' + rows.length + '행) ────────');
  out = out.concat(groupLines_(rows, 2));      // 시간대
  out.push('──────── 요일별 ────────');
  out = out.concat(groupLines_(rows, 3));
  out.push('──────── 구분별 ────────');
  out = out.concat(groupLines_(rows, 4));
  out.push('※ 표본 ' + TS.MIN_N + '개 미만은 (참고) 표시. 중앙값을 먼저 보세요.');
  return out;
}

function groupLines_(rows, colIdx) {
  var g = {};
  rows.forEach(function (r) {
    var k = String(r[colIdx] || '(없음)');
    (g[k] = g[k] || []).push(Number(r[8]) || 0);
  });
  return Object.keys(g).sort().map(function (k) {
    var a = g[k].slice().sort(function (x, y) { return x - y; });
    var sum = a.reduce(function (s, x) { return s + x; }, 0);
    var mid = a.length % 2 ? a[(a.length - 1) / 2]
                           : Math.round((a[a.length / 2 - 1] + a[a.length / 2]) / 2);
    return '  ' + pad_(k, 12) + ' n=' + pad_(String(a.length), 4)
         + '중앙 ' + pad_(String(mid), 8)
         + '평균 ' + pad_(String(Math.round(sum / a.length)), 8)
         + (a.length < TS.MIN_N ? '(참고)' : '');
  });
}

function pad_(s, w) { s = String(s); while (s.length < w) s += ' '; return s; }

function tsLog_(result, message) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TS.LOG_SHEET);
    if (sh) sh.appendRow([new Date(), 'timeslotStats', result, message]);
  } catch (e) { /* noop */ }
}

// ─────────────────────────────────────────────
// 목표 추적 — 월 조회수 100,000
// ─────────────────────────────────────────────

var TS_GOAL = 100000;

/**
 * 월별 조회수 집계와 목표 대비.
 *
 * ⚠️ 해석 주의. 스레드 탭 조회수는 syncThreads 가 매번 최신값으로 덮으므로
 * "그 달에 발생한 조회"가 아니라 "그 달에 올린 글의 지금까지 누적 조회"다.
 * 최근 달일수록 아직 덜 쌓인 상태라 과소평가된다.
 * 프로필의 '최근 조회수'(계정 단위 30일 지표)와도 다른 값이다.
 */
function monthlyViews() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TS.SRC);
  if (!sh || sh.getLastRow() < TS.FIRST_ROW) { Logger.log('스레드 탭 비어있음'); return; }

  var n = sh.getLastRow() - TS.FIRST_ROW + 1;
  var v = sh.getRange(TS.FIRST_ROW, 1, n, 10).getValues();

  var g = {};
  v.forEach(function (r) {
    var d = r[0];
    if (!(d instanceof Date)) return;
    if (r[4] === '' || r[4] == null) return;
    var k = Utilities.formatDate(d, 'Asia/Seoul', 'yyyy-MM');
    var b = g[k] || (g[k] = { n: 0, sum: 0, arr: [], kinds: {} });
    var views = Number(r[4]) || 0;
    b.n++; b.sum += views; b.arr.push(views);
    var kind = String(r[1] || '미분류');
    var kk = b.kinds[kind] || (b.kinds[kind] = { n: 0, sum: 0 });
    kk.n++; kk.sum += views;
  });

  var keys = Object.keys(g).sort();
  if (!keys.length) { Logger.log('집계할 데이터 없음'); return; }

  Logger.log('목표 월 %s 조회', tsNum_(TS_GOAL));
  Logger.log('%s %s %s %s %s', pad_('월', 9), pad_('건수', 6), pad_('총조회', 10), pad_('중앙값', 8), '목표대비');
  keys.forEach(function (k) {
    var b = g[k];
    var a = b.arr.slice().sort(function (x, y) { return x - y; });
    var mid = a.length % 2 ? a[(a.length - 1) / 2]
                           : Math.round((a[a.length / 2 - 1] + a[a.length / 2]) / 2);
    Logger.log('%s %s %s %s %s%%', pad_(k, 9), pad_(String(b.n), 6),
      pad_(tsNum_(b.sum), 10), pad_(tsNum_(mid), 8),
      (100 * b.sum / TS_GOAL).toFixed(1));
  });

  // 가장 최근 달의 구성
  var last = keys[keys.length - 1], lb = g[last];
  Logger.log('\n── %s 구성 ──', last);
  Object.keys(lb.kinds).sort(function (a, b2) { return lb.kinds[b2].sum - lb.kinds[a].sum; })
    .forEach(function (kind) {
      var kk = lb.kinds[kind];
      Logger.log('  %s %s건  %s  (%s%%)  건당 %s',
        pad_(kind, 10), pad_(String(kk.n), 4), pad_(tsNum_(kk.sum), 9),
        pad_((100 * kk.sum / lb.sum).toFixed(1), 5), tsNum_(Math.round(kk.sum / kk.n)));
    });

  var gap = TS_GOAL - lb.sum;
  Logger.log('\n부족분 %s. 현재 건당 %s 기준 추가 %s건 필요.',
    tsNum_(Math.max(0, gap)), tsNum_(Math.round(lb.sum / lb.n)),
    gap > 0 ? tsNum_(Math.ceil(gap / (lb.sum / lb.n))) : '0');
  Logger.log('※ 이 수치는 누적 조회수다. 계정 단위 「최근 조회수」와는 다르다.');
}

/**
 * 뭐가 터졌는지 본다.
 * 조회수는 상위 소수가 전부를 만든다(폰스팟 실측: 상위 4건이 60.7%).
 * 그 4건이 무엇이었는지가 시세글 최적화보다 중요한 정보다.
 */
function topPosts(howMany) {
  var top = howMany || 15;
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TS.SRC);
  if (!sh || sh.getLastRow() < TS.FIRST_ROW) { Logger.log('스레드 탭 비어있음'); return; }

  var n = sh.getLastRow() - TS.FIRST_ROW + 1;
  var v = sh.getRange(TS.FIRST_ROW, 1, n, 10).getValues();

  var rows = [], total = 0;
  v.forEach(function (r, i) {
    if (r[4] === '' || r[4] == null) return;
    var views = Number(r[4]) || 0;
    total += views;
    rows.push({ row: TS.FIRST_ROW + i, date: r[0], kind: r[1],
                topic: String(r[2] || ''), views: views,
                likes: r[5], replies: r[9], link: r[3] });
  });
  if (!rows.length) { Logger.log('조회수가 채워진 행이 없음'); return; }

  rows.sort(function (a, b) { return b.views - a.views; });
  var cum = 0;
  Logger.log('전체 %s건 / 총조회 %s', rows.length, tsNum_(total));
  Logger.log('%s %s %s %s %s %s', pad_('순', 4), pad_('날짜', 11), pad_('구분', 9),
    pad_('조회', 9), pad_('누적%', 7), '주제');
  rows.slice(0, top).forEach(function (r, i) {
    cum += r.views;
    Logger.log('%s %s %s %s %s %s', pad_(String(i + 1), 4),
      pad_(r.date instanceof Date ? Utilities.formatDate(r.date, 'Asia/Seoul', 'yyyy-MM-dd') : '?', 11),
      pad_(String(r.kind || ''), 9), pad_(tsNum_(r.views), 9),
      pad_((100 * cum / total).toFixed(1) + '%', 7), r.topic.slice(0, 44));
  });

  // 상위 몇 건이 절반을 만드는가
  var half = 0, k = 0;
  while (half < total / 2 && k < rows.length) { half += rows[k].views; k++; }
  Logger.log('\n전체 조회의 절반을 상위 %s건(%s%%)이 만든다.',
    k, (100 * k / rows.length).toFixed(1));
  Logger.log('→ 목표는 평균을 올려서가 아니라 이런 건의 빈도로 채워진다.');
}

function tsNum_(n) {
  return String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ─────────────────────────────────────────────
// 탭 정리 — 스레드 탭 하나로만 운용
// ─────────────────────────────────────────────

/**
 * 스크립트가 알아서 채우는 작업용 탭들은 숨긴다.
 * 사장님이 눈으로 볼 곳은 「스레드」 하나면 된다.
 *
 * 숨겨도 스크립트는 그대로 읽고 쓴다 — getSheetByName 은 숨김 여부와 무관하다.
 * 다시 보려면 showWorkTabs(), 또는 시트 하단 탭 영역 우클릭 → 숨겨진 시트.
 */
var TS_HIDE = ['시세_현재', '시세_변동', '시세_초안', '시세_설정',
               '훅_성과', '성과_시간대', '동기화_로그'];

function hideWorkTabs() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var done = [], missing = [];
  TS_HIDE.forEach(function (n) {
    var sh = ss.getSheetByName(n);
    if (!sh) { missing.push(n); return; }
    if (!sh.isSheetHidden()) { sh.hideSheet(); done.push(n); }
  });
  Logger.log('숨김 %s개: %s', done.length, done.join(', ') || '(이미 다 숨겨져 있음)');
  if (missing.length) Logger.log('아직 없는 탭: %s', missing.join(', '));
  Logger.log('스크립트는 숨긴 탭도 그대로 읽고 씁니다. 되돌리려면 showWorkTabs().');
}

function showWorkTabs() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var done = [];
  TS_HIDE.forEach(function (n) {
    var sh = ss.getSheetByName(n);
    if (sh && sh.isSheetHidden()) { sh.showSheet(); done.push(n); }
  });
  Logger.log('다시 표시 %s개: %s', done.length, done.join(', ') || '(숨겨진 게 없음)');
}

/**
 * 스레드 탭만 보면 되도록, 오늘 상황을 한 번에 찍어준다.
 * 숨긴 탭을 열어보지 않고도 무슨 일이 있었는지 알 수 있게.
 */
function todayStatus() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tz = 'Asia/Seoul';
  var today = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');
  Logger.log('━━━ %s ━━━', today);

  // 오늘 시간대 배치
  if (typeof kindForSlot_ === 'function') {
    Logger.log('배치  12시 %s / 18시 %s / 21시 %s',
      kindForSlot_(12, new Date()), kindForSlot_(18, new Date()), kindForSlot_(21, new Date()));
  }

  // 시세 수집
  var now = ss.getSheetByName('시세_현재');
  if (now && now.getLastRow() > 1) {
    Logger.log('시세  %s행 · 수집 %s', now.getLastRow() - 1,
      Utilities.formatDate(new Date(now.getRange(2, 1).getValue()), tz, 'MM-dd HH:mm'));
  } else Logger.log('시세  ❌ 없음 — syncPricesNow 필요');

  // 오늘 초안
  var dr = ss.getSheetByName('시세_초안');
  if (dr && dr.getLastRow() > 1) {
    var v = dr.getRange(2, 1, dr.getLastRow() - 1, 11).getValues();
    var mine = v.filter(function (r) { return String(r[0]).indexOf(today) === 0; });
    Logger.log('초안  오늘 %s건', mine.length);
    mine.forEach(function (r) {
      Logger.log('   %s  %s  %s  %s', r[1], r[3], r[9], r[10] || '');
      Logger.log('   %s', String(r[6]).split('\n')[0]);
    });
  } else Logger.log('초안  없음');

  // 오늘 스레드 기록
  var th = ss.getSheetByName('스레드');
  if (th && th.getLastRow() >= 4) {
    var n = th.getLastRow() - 3;
    var rows = th.getRange(4, 1, n, 10).getValues().filter(function (r) {
      return r[0] instanceof Date && Utilities.formatDate(r[0], tz, 'yyyy-MM-dd') === today;
    });
    Logger.log('발행  오늘 %s행', rows.length);
    rows.forEach(function (r) {
      Logger.log('   %s  조회 %s  좋아요 %s  답글 %s  %s',
        String(r[2]).slice(0, 34), r[4] === '' ? '-' : r[4],
        r[5] === '' ? '-' : r[5], r[9] === '' ? '-' : r[9], r[3]);
    });
  }

  // 최근 오류
  var lg = ss.getSheetByName('동기화_로그');
  if (lg && lg.getLastRow() > 1) {
    var last = Math.min(40, lg.getLastRow() - 1);
    var logs = lg.getRange(lg.getLastRow() - last + 1, 1, last, 4).getValues()
      .filter(function (r) { return /FAIL|WARN/.test(String(r[2])); });
    if (logs.length) {
      Logger.log('⚠️ 최근 오류 %s건', logs.length);
      logs.slice(-5).forEach(function (r) {
        Logger.log('   %s %s %s', Utilities.formatDate(new Date(r[0]), tz, 'MM-dd HH:mm'), r[1], String(r[3]).slice(0, 80));
      });
    } else Logger.log('로그  최근 40건에 오류 없음');
  }
}