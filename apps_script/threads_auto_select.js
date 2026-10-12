/**
 * auto_select.gs — 미승인 초안 자동 선정·발행 + 훅 성과 학습 (5단계)
 *
 *   09시   snapshotHookScores()   D+5 지난 글의 조회수를 훅_성과 탭에 고정 기록
 *   10분마다 autoPublishPending() 생성 60분 지나도록 손 안 댄 배치를 자동 선정 → '승인'
 *
 * 자동 선정된 행은 기존 publishApproved() 가 그대로 집어간다.
 * 가격 재검증·중복 방어·간격 제한이 전부 그대로 걸린다. 우회로를 만들지 않는다.
 *
 * ──────────────────────────────────────────────────────
 * 왜 "제일 성과 좋은 훅"을 그냥 고르지 않는가
 *
 * 표본이 적을 때 최고 평균은 대부분 노이즈다. 그걸 매번 고르면 나머지 훅은
 * 영영 표본이 안 쌓이고, 처음 몇 번의 우연이 코드로 굳는다. 학습이 아니라 고착이다.
 *
 * 그래서 UCB1 을 쓴다. 점수 = 평균 + √(2·lnN / n).
 * 적게 써본 훅에 자동으로 가산점이 붙어 탐색이 저절로 일어나고,
 * 표본이 쌓이면 가산점이 줄어 실력대로 수렴한다. 튜닝할 상수가 사실상 없다.
 *
 * 평균은 두 번 보정한다.
 *   ① 로그 변환 — 조회수는 롱테일이다(폰스팟 실측: 상위 4건이 전체의 60.7%).
 *      생평균을 쓰면 대박 하나가 그 훅을 영구 1위로 만든다.
 *   ② 같은 시기 중앙값으로 나눔 — 도달이 시기별로 17배까지 흔들렸다
 *      (4월 373 → 6월 22). 보정 없이는 "4월에 쓴 훅"이 무조건 이긴다.
 *
 *   상대성과 = ln(1+조회수) − ln(1+같은주 중앙값)
 *
 * 학습 단위는 **표현축**(TEASE/NUM/EXC/RANK/QUES)뿐이다.
 * 사건축(PB/DROP/RANK/SCARCE)은 그날 시세가 정하는 것이라 고를 수 있는 게 아니다.
 * 3안은 같은 사건에 표현만 다르므로, 비교 대상도 표현축이어야 한다.
 * ──────────────────────────────────────────────────────
 */

var AS = {
  SHEET_DRAFT: '시세_초안',
  SHEET_THREADS: '스레드',
  SHEET_PERF: '훅_성과',
  LOG_SHEET: '동기화_로그',

  AUTO_PUBLISH: true,       // ★ 자동 발행 전체 스위치. false 면 선정만 하고 안 올린다.
  AUTO_AFTER_MIN: 60,       // 생성 후 이만큼 지나도 손 안 댔으면 자동 선정
  SNAP_DAYS: 5,             // 발행 후 며칠 시점의 조회수를 성과로 볼지
  SNAP_TOL_H: 18,           // 그 시점 ±허용 시간
  WINDOW_DAYS: 7,           // 상대성과 계산용 비교 창(±일)
  UCB_C: 0.8,               // 탐색 강도. 크면 더 골고루, 작으면 더 빨리 수렴
  MIN_N_TRUST: 5,           // 이보다 표본이 적은 훅은 '탐색중'으로 표시

  PERF_HEAD: ['발행일','발행시각','슬롯','종류','사건','표현','선정','수정','조회수','기준중앙값','상대성과','링크'],

  PROP_TG_TOKEN: 'TELEGRAM_BOT_TOKEN',
  PROP_TG_CHAT:  'TELEGRAM_CHAT_ID'
};

// 초안에 절대 나가면 안 되는 말. 자동 발행은 사람이 안 읽으므로 여기서 막는다.
var AS_BANNED = ['역대급','대란','다시 없','마감 임박','수량이 적','남은 것들','재고 소진','최저가 보장'];

// ─────────────────────────────────────────────
// 진입점
// ─────────────────────────────────────────────

/** 10분마다. 손 안 댄 배치를 자동 선정해 '승인'으로 바꾼다. */
function autoPublishPending() {
  if (!threadsGuard_('autoPublishPending')) return;
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(AS.SHEET_DRAFT);
  if (!sh || sh.getLastRow() < 2) return;

  var last = sh.getLastRow();
  var v = sh.getRange(2, 1, last - 1, PT.NCOL).getValues();

  // 배치별로 묶는다. 사람이 하나라도 손댄 배치는 건드리지 않는다.
  var groups = {};
  for (var i = 0; i < v.length; i++) {
    var b = String(v[i][PT.COL.BATCH - 1] || '');
    if (!b) continue;
    var st = String(v[i][PT.COL.STATUS - 1]).trim();
    var g = groups[b] || (groups[b] = { rows: [], touched: false });
    if (st === '대기') g.rows.push({ row: i + 2, data: v[i] });
    else g.touched = true;          // 승인·보류·미선택·발행완료·만료 = 사람이 판단한 것
  }

  var scores = null;

  Object.keys(groups).forEach(function (b) {
    var g = groups[b];
    if (g.touched || !g.rows.length) return;

    var age = minutesSince_(g.rows[0].data[PT.COL.STAMP - 1]);
    if (age == null || age < AS.AUTO_AFTER_MIN) return;
    // 수명이 지난 초안은 자동으로도 올리지 않는다. 만료가 우선이다.
    if (age >= PT.TTL_MIN) return;

    if (!AS.AUTO_PUBLISH) {
      asLog_('SKIP', b + ' 자동발행 꺼짐');
      return;
    }

    if (scores === null) scores = hookScores_();
    var chosen = pickBest_(g.rows, scores);
    if (!chosen) {
      asLog_('WARN', b + ' 자동 선정 실패 — 전부 금지어에 걸림');
      g.rows.forEach(function (r) { sh.getRange(r.row, PT.COL.STATUS).setValue('보류'); });
      asAlert_('⚠️ ' + b + ' 자동 선정 불가\n시안 전부가 금지어 검사에 걸렸습니다. 확인이 필요합니다.');
      return;
    }

    // 사람 선택과 구분되게 표시한다. 섞이면 선택 편향 보정이 불가능해진다.
    var meta = String(chosen.row_.data[PT.COL.META - 1] || '');
    sh.getRange(chosen.row_.row, PT.COL.META).setValue(meta + ';선정=자동');
    sh.getRange(chosen.row_.row, PT.COL.STATUS).setValue('승인');
    g.rows.forEach(function (r) {
      if (r.row !== chosen.row_.row) sh.getRange(r.row, PT.COL.STATUS).setValue('미선택');
    });

    asLog_('OK', b + ' 자동 선정 ' + chosen.expr + ' (' + chosen.why + ')');
    asAlert_('🤖 ' + b + ' — 승인이 없어 자동으로 골랐습니다\n'
      + '고른 안: ' + chosen.row_.data[PT.COL.VARIANT - 1] + ' ' + chosen.row_.data[PT.COL.TAG - 1] + '\n'
      + '근거: ' + chosen.why + '\n\n'
      + String(chosen.row_.data[PT.COL.POST1 - 1]).split('\n')[0] + '\n\n'
      + '※ 곧 발행됩니다. 취소하려면 지금 상태를 「보류」로 바꾸세요.');
  });
}

/** 09시. D+5 지난 글의 조회수를 훅_성과 탭에 고정 기록한다. */
function snapshotHookScores() {
  if (!threadsGuard_('snapshotHookScores')) return;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var src = ss.getSheetByName(AS.SHEET_THREADS);
  if (!src || src.getLastRow() < TH.FIRST_ROW) { Logger.log('스레드 탭 비어있음'); return; }

  var perf = ss.getSheetByName(AS.SHEET_PERF);
  if (!perf) {
    perf = ss.insertSheet(AS.SHEET_PERF);
    perf.setFrozenRows(1);
  }
  // 헤더는 매번 맞춰 쓴다. 시트를 만든 뒤 열이 추가되면 옛 헤더가 남아
  // 값이 한 칸씩 밀려 보인다 ('수정' 열을 넣었을 때 실제로 그랬다).
  var head = perf.getRange(1, 1, 1, AS.PERF_HEAD.length).getValues()[0];
  if (head.join('|') !== AS.PERF_HEAD.join('|')) {
    perf.getRange(1, 1, 1, AS.PERF_HEAD.length).setValues([AS.PERF_HEAD]).setFontWeight('bold');
  }

  // 이미 기록한 링크는 건너뛴다. 같은 글을 두 번 세면 그 훅이 부당하게 무거워진다.
  var done = {};
  if (perf.getLastRow() > 1) {
    perf.getRange(2, 12, perf.getLastRow() - 1, 1).getValues()
      .forEach(function (r) { if (r[0]) done[String(r[0])] = 1; });
  }

  var postMap;
  try { postMap = fetchMyThreads_(); }
  catch (err) { Logger.log('API 실패: %s', String(err).slice(0, 200)); return; }

  var n = src.getLastRow() - TH.FIRST_ROW + 1;
  var v = src.getRange(TH.FIRST_ROW, 1, n, 10).getValues();

  // 상대성과의 분모 — 발행일 기준 ±WINDOW_DAYS 안의 조회수 중앙값
  var pool = [];
  v.forEach(function (r) {
    var url = String(r[3] || '').trim(); if (!url) return;
    var code = shortcodeFromUrl_(url); var p = code ? postMap[code] : null;
    if (!p || !p.timestamp) return;
    var views = Number(r[4]); if (!r[4] && r[4] !== 0) return;
    pool.push({ t: new Date(p.timestamp).getTime(), views: views });
  });

  var lo = AS.SNAP_DAYS * 86400000 - AS.SNAP_TOL_H * 3600000;
  var hi = AS.SNAP_DAYS * 86400000 + AS.SNAP_TOL_H * 3600000;
  var now = Date.now();
  var out = [];

  for (var i = 0; i < n; i++) {
    var url = String(v[i][3] || '').trim();
    if (!url || done[url]) continue;
    if (v[i][4] === '' || v[i][4] == null) continue;

    var code = shortcodeFromUrl_(url);
    var post = code ? postMap[code] : null;
    if (!post || !post.timestamp) continue;

    var t = new Date(post.timestamp).getTime();
    var age = now - t;
    if (age < lo || age > hi) continue;             // D+5 창 밖

    var tag = parseTag_(String(v[i][2] || ''));     // C열 '[RANK/NUM] 첫줄'
    if (!tag) continue;                              // 태그 없는 옛 글은 학습에 못 쓴다

    var meta = String(v[i][8] || '');
    var slot = (meta.match(/슬롯=(\d+)/) || [])[1] || '';
    var stage = (meta.match(/단계=(\d)/) || [])[1] || '';
    if (stage === '2') continue;                     // 2/2는 훅이 없다. 1/2만 센다.
    var pick = /선정=자동/.test(meta) ? '자동' : '수동';
    var edited = /수정=Y/.test(meta) ? 'Y' : '';   // 스레드에서 사장님이 고친 글

    var views = Number(v[i][4]);
    var med = medianAround_(pool, t, AS.WINDOW_DAYS);
    var rel = Math.log(1 + views) - Math.log(1 + med);

    out.push([
      Utilities.formatDate(new Date(t), 'Asia/Seoul', 'yyyy-MM-dd'),
      Utilities.formatDate(new Date(t), 'Asia/Seoul', 'HH:mm'),
      slot, v[i][1], tag.event, tag.expr, pick, edited,
      views, med, Math.round(rel * 1000) / 1000, url
    ]);
  }

  if (!out.length) { Logger.log('오늘 기록할 D+%s 글 없음', AS.SNAP_DAYS); return; }
  perf.getRange(perf.getLastRow() + 1, 1, out.length, AS.PERF_HEAD.length).setValues(out);
  Logger.log('훅_성과 %s행 추가', out.length);
  asLog_('OK', '훅_성과 ' + out.length + '행 추가');

  // 성적이 새로 들어왔으니 요인 추정도 다시 한다. 트리거는 안 늘린다.
  try { buildFactorTable(); } catch (e) { asLog_('WARN', '요인 모형 실패: ' + String(e).slice(0, 150)); }
}

/** 지금 훅별 점수가 어떤지. 시트를 안 건드린다. */
function checkHookScores() {
  var s = hookScores_();
  if (!s.total) {
    Logger.log('아직 성과 데이터가 없습니다. D+%s 이후부터 쌓입니다.', AS.SNAP_DAYS);
    Logger.log('그동안 자동 선정은 균등 무작위로 돕니다 — 그게 맞는 시작입니다.');
    return;
  }
  Logger.log('표본 %s건 · 기준일 %s일', s.total, AS.SNAP_DAYS);
  Logger.log('%s  %s  %s  %s', pad2_('표현', 8), pad2_('n', 5), pad2_('평균상대', 10), 'UCB점수');
  s.list.forEach(function (h) {
    Logger.log('%s  %s  %s  %s %s',
      pad2_(h.expr, 8), pad2_(String(h.n), 5),
      pad2_(fx_(h.mean), 10), fx_(h.ucb),
      h.n < AS.MIN_N_TRUST ? '(탐색중)' : '');
  });
  Logger.log('상대성과 0 = 같은 시기 중앙값과 동일. +0.69 = 2배, −0.69 = 절반.');
  if (AS._skipped) {
    Logger.log('※ 스레드에서 고친 글 %s건은 학습에서 제외했습니다.', AS._skipped);
    Logger.log('  훅_성과 탭의 「수정」=Y 행입니다. 새 훅 후보를 찾을 때 그 문구들을 보세요.');
  }
}

function installAutoTriggers() {
  if (!threadsGuard_('installAutoTriggers')) return;
  var removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var f = t.getHandlerFunction();
    if (f === 'autoPublishPending' || f === 'snapshotHookScores') {
      ScriptApp.deleteTrigger(t); removed++;
    }
  });
  if (removed) Logger.log('기존 트리거 %s개 정리', removed);
  // 1안 직행 모드(DG_VARIANTS=1 + DG_AUTO_APPROVE)에서는 autoPublishPending 이 할 일이 없다.
  // 초안이 생성과 동시에 '승인'으로 붙으므로, 배치가 전부 '대기'인 상태가 아예 생기지 않는다.
  // 트리거 한도(사용자당 20개)가 꽉 차 있어서, 아무 일도 안 하는 트리거에 자리를 내줄 수 없다.
  var oneShot = (typeof DG_VARIANTS === 'number' && DG_VARIANTS === 1
              && typeof DG_AUTO_APPROVE !== 'undefined' && DG_AUTO_APPROVE);
  if (oneShot) {
    Logger.log('1안 직행 모드 — autoPublishPending 트리거는 만들지 않습니다.');
    Logger.log('3안 승인 방식으로 되돌릴 때(DG_VARIANTS=3) 다시 실행하세요.');
  } else {
    ScriptApp.newTrigger('autoPublishPending').timeBased().everyMinutes(10).create();
    Logger.log('자동 선정 10분마다');
  }
  // snapshotHookScores 는 별도 트리거를 만들지 않는다.
  // syncThreads 끝에서 같이 돌린다 — 같은 이유다.
  Logger.log('성과 스냅샷은 syncThreads 안에서 함께 돕니다.');
  Logger.log('자동 발행 스위치: %s', AS.AUTO_PUBLISH ? 'ON' : 'OFF');
}

// ─────────────────────────────────────────────
// 선정
// ─────────────────────────────────────────────

/**
 * 시안들 중 하나를 고른다.
 * 금지어에 걸린 안은 후보에서 뺀다 — 자동 발행은 사람이 안 읽는다.
 */
function pickBest_(rows, scores) {
  var cands = rows.filter(function (r) {
    return !bannedIn_(String(r.data[PT.COL.POST1 - 1]) + '\n' + String(r.data[PT.COL.POST2 - 1]));
  });
  if (!cands.length) return null;

  var best = null;
  cands.forEach(function (r) {
    var tag = parseTag_(String(r.data[PT.COL.TAG - 1] || ''));
    var expr = tag ? tag.expr : '?';
    var s = scores.map[expr];
    // 한 번도 안 써본 표현은 무조건 먼저. UCB 의 표준 초기화다.
    var score = s ? s.ucb : Infinity;
    var tie = Math.random();          // 동점(특히 전부 미탐색)이면 무작위
    if (!best || score > best.score || (score === best.score && tie > best.tie)) {
      best = { row_: r, expr: expr, score: score, tie: tie,
               why: s ? (s.n < AS.MIN_N_TRUST
                          ? expr + ' 탐색중 (n=' + s.n + ')'
                          : expr + ' 상대성과 ' + fx_(s.mean) + ' (n=' + s.n + ')')
                      : expr + ' 아직 표본 없음 → 우선 시도' };
    }
  });
  return best;
}

/** 훅_성과 탭 → 표현축별 UCB1 점수 */
function hookScores_() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(AS.SHEET_PERF);
  var empty = { total: 0, map: {}, list: [] };
  if (!sh || sh.getLastRow() < 2) return empty;

  var v = sh.getRange(2, 1, sh.getLastRow() - 1, AS.PERF_HEAD.length).getValues();
  var g = {}, total = 0, skipped = 0;
  v.forEach(function (r) {
    var expr = String(r[5] || '').trim();
    if (!expr) return;
    // 사장님이 스레드에서 고친 글은 뺀다. 태그는 원래 훅을 가리키는데
    // 실제로 나간 문구는 다른 것이라, 그대로 세면 엉뚱한 표현에 점수가 붙는다.
    if (String(r[7] || '').trim() === 'Y') { skipped++; return; }
    var rel = Number(r[10]);
    if (isNaN(rel)) return;
    (g[expr] = g[expr] || []).push(rel);
    total++;
  });
  if (skipped) AS._skipped = skipped;
  if (!total) return empty;

  var lnN = Math.log(total);
  var list = Object.keys(g).map(function (expr) {
    var a = g[expr];
    var mean = a.reduce(function (s, x) { return s + x; }, 0) / a.length;
    return { expr: expr, n: a.length, mean: mean,
             ucb: mean + AS.UCB_C * Math.sqrt(2 * lnN / a.length) };
  }).sort(function (x, y) { return y.ucb - x.ucb; });

  var map = {};
  list.forEach(function (h) { map[h.expr] = h; });
  return { total: total, map: map, list: list };
}

// ─────────────────────────────────────────────
// 보조
// ─────────────────────────────────────────────

/** '[RANK/NUM] 오늘 가성비 TOP 3' → {event:'RANK', expr:'NUM'} */
function parseTag_(s) {
  var m = String(s).match(/\[([A-Z_]+)\/([A-Z_]+)\]/);
  return m ? { event: m[1], expr: m[2] } : null;
}

function bannedIn_(text) {
  var t = String(text);
  for (var i = 0; i < AS_BANNED.length; i++) if (t.indexOf(AS_BANNED[i]) >= 0) return AS_BANNED[i];
  return null;
}

/** t 를 중심으로 ±days 안의 조회수 중앙값. 도달 드리프트 보정용 분모. */
function medianAround_(pool, t, days) {
  var w = days * 86400000;
  var a = pool.filter(function (p) { return Math.abs(p.t - t) <= w; })
              .map(function (p) { return p.views; })
              .sort(function (x, y) { return x - y; });
  if (!a.length) return 0;
  return a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2;
}

function fx_(n) { var v = Math.round(Number(n) * 100) / 100; return (v > 0 ? '+' : '') + v.toFixed(2); }
function pad2_(s, w) { s = String(s); while (s.length < w) s += ' '; return s; }

function asLog_(result, message) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(AS.LOG_SHEET);
    if (sh) sh.appendRow([new Date(), 'autoSelect', result, message]);
  } catch (e) { /* noop */ }
}

function asAlert_(text) { ptAlert_(text); }

// ─────────────────────────────────────────────
// 문구 틀(템플릿) 단위 점수 — draft_gen.pickHookScored_ 가 쓴다
// ─────────────────────────────────────────────

/**
 * 훅_성과를 문구 틀별로 묶는다.
 * 어느 틀인지는 스레드 탭 비고의 '훅=' 으로 찾고, 없으면(옛 글) 첫 줄 문구로 되찾는다.
 * 스레드에서 사장님이 고친 글(수정=Y)은 원래 틀을 대표하지 않으므로 뺀다.
 *
 * 반환: { total, byT: {tid:{n,sum,mean}}, byPool: {풀:{n,sum,mean}} }
 */
function hookTemplateScores_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var perf = ss.getSheetByName(AS.SHEET_PERF);
  var out = { total: 0, byT: {}, byPool: {} };
  if (!perf || perf.getLastRow() < 2) return out;

  // 링크 → (주제, 비고)
  var th = ss.getSheetByName(AS.SHEET_THREADS), byLink = {};
  if (th && th.getLastRow() >= TH.FIRST_ROW) {
    th.getRange(TH.FIRST_ROW, 1, th.getLastRow() - TH.FIRST_ROW + 1, 10).getValues()
      .forEach(function (r) { if (r[3]) byLink[String(r[3]).trim()] = { topic: String(r[2]), note: String(r[8]) }; });
  }

  var v = perf.getRange(2, 1, perf.getLastRow() - 1, AS.PERF_HEAD.length).getValues();
  v.forEach(function (r) {
    if (String(r[7] || '').trim() === 'Y') return;            // 수정본 제외
    var rel = Number(r[10]);
    if (r[10] === '' || isNaN(rel)) return;
    var link = String(r[11] || '').trim();
    var src = byLink[link] || {};
    var m = String(src.note || '').match(/훅=([A-Z_]+#\d+)/);
    var tid = m ? m[1] : '';
    if (!tid && src.topic && typeof templateOf_ === 'function') {
      var line = src.topic.replace(/^\d{1,2}\s*\/\s*/, '').replace(/^\[[A-Z_]+\/[A-Z_]+\]\s*/, '');
      tid = templateOf_(line);
    }
    if (!tid) return;
    var pool = tid.split('#')[0];
    var a = out.byT[tid] || (out.byT[tid] = { n: 0, sum: 0 });
    var b = out.byPool[pool] || (out.byPool[pool] = { n: 0, sum: 0 });
    a.n++; a.sum += rel; b.n++; b.sum += rel; out.total++;
  });
  Object.keys(out.byT).forEach(function (k) { out.byT[k].mean = out.byT[k].sum / out.byT[k].n; });
  Object.keys(out.byPool).forEach(function (k) { out.byPool[k].mean = out.byPool[k].sum / out.byPool[k].n; });
  return out;
}

/** 문구 틀별 성적을 로그로. 시트를 안 건드린다. */
function checkHookTemplates() {
  var sc = hookTemplateScores_();
  var used = (typeof recentTemplateUse_ === 'function') ? recentTemplateUse_() : {};
  var ts = (typeof hookTemplates_ === 'function') ? hookTemplates_() : [];
  Logger.log('훅_성과 표본 %s건 (수정본 제외). 상대성과 0=같은 시기 중앙값, +0.69=2배', sc.total);
  var lastPool = '';
  ts.forEach(function (t) {
    if (t.pool !== lastPool) {
      var p = sc.byPool[t.pool];
      Logger.log('── %s  (풀 평균 %s, n=%s)', t.pool, p ? fx_(p.mean) : '-', p ? p.n : 0);
      lastPool = t.pool;
    }
    var s = sc.byT[t.tid], u = used[t.tid];
    Logger.log('   %s  n=%s  평균 %s  최근6일 %s회  "%s"',
      pad2_(t.tid, 12), pad2_(String(s ? s.n : 0), 3), pad2_(s ? fx_(s.mean) : '  -  ', 6),
      u ? u.pend : 0, t.text);
  });
}

// ─────────────────────────────────────────────
// 요인 모형 — 시간대 · 주제 · 훅을 한 번에 추정한다
// ─────────────────────────────────────────────

/**
 * 왜 요인을 따로 재면 안 되는가 (2026-09-21 사고의 일반화)
 *
 * 훅별 평균, 시간대별 평균을 각각 내면 서로의 효과가 섞여 들어온다.
 *   · 전시폰(DP)은 성적이 좋고 QUES 훅을 자주 썼다 → QUES 가 좋아 보인다
 *   · 21시 칸에 변동 컨셉이 자주 걸렸다 → 21시가 좋아 보인다
 * 실제로 9월에 변동 컨셉의 훅을 갈아치웠다가 조회 중앙값이 863 → 103 으로 떨어졌다.
 *
 * 그래서 가산 모형 하나로 동시에 추정한다.
 *   ln(1+조회) − ln(1+같은시기 중앙값) = 절편 + 슬롯효과 + 주제효과 + 훅효과 + 오차
 * 라틴 방격 로테이션(4슬롯 × 4주제)이 균형 설계라서 이 분해가 성립한다.
 * **성과 좋은 슬롯·주제로 몰기 시작하면 균형이 깨져 추정 자체가 불가능해진다.**
 * 그래서 선택(탐색)은 훅에서만 한다. 슬롯·주제는 계속 기계적으로 돈다.
 *
 * 표본이 적은 수준이 3배로 튀는 걸 막으려고 릿지(축소)로 푼다.
 * 훅은 더 세게 당긴다(LAMBDA_HOOK) — 훅 수준이 제일 많고 제일 얕다.
 */
var AS_FM = {
  SHEET: '요인_성과',
  LAMBDA: 1.0,        // 슬롯·주제 축소 강도
  LAMBDA_HOOK: 4.0,   // 훅 축소 강도. 크면 "모르면 풀 평균"에 가깝다
  MIN_N: 8,           // 이보다 표본이 적은 수준은 '탐색중'
  Z: 1.96,
  HEAD: ['갱신', '요인', '수준', '표본', '추정배수', '95%하한', '95%상한', '판정']
};

/** 훅_성과 + 스레드 비고 → 모형에 넣을 행 목록 */
function fmRows_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var perf = ss.getSheetByName(AS.SHEET_PERF);
  var out = [];
  if (!perf || perf.getLastRow() < 2) return out;

  var th = ss.getSheetByName(AS.SHEET_THREADS), byLink = {};
  if (th && th.getLastRow() >= TH.FIRST_ROW) {
    th.getRange(TH.FIRST_ROW, 1, th.getLastRow() - TH.FIRST_ROW + 1, 10).getValues()
      .forEach(function (r) { if (r[3]) byLink[String(r[3]).trim()] = { topic: String(r[2]), note: String(r[8]) }; });
  }

  perf.getRange(2, 1, perf.getLastRow() - 1, AS.PERF_HEAD.length).getValues().forEach(function (r) {
    if (String(r[7] || '').trim() === 'Y') return;          // 사장님이 고친 글은 제외
    var rel = Number(r[10]);
    if (r[10] === '' || isNaN(rel)) return;
    var link = String(r[11] || '').trim();
    var src = byLink[link] || {};
    var note = String(src.note || '');

    var m = note.match(/훅=([A-Z_]+#\d+)/);
    var tid = m ? m[1] : '';
    if (!tid && src.topic && typeof templateOf_ === 'function') {
      tid = templateOf_(String(src.topic).replace(/^\d{1,2}\s*\/\s*/, '')
                                          .replace(/^\[[A-Z_]+\/[A-Z_]+\]\s*/, ''));
    }
    var slot = String(r[2] || (note.match(/슬롯=(\d+)/) || [])[1] || '');
    if (slot === '22') slot = '21';                          // 21:58 발행이 22로 찍히는 경우
    out.push({ rel: rel, slot: slot, kind: fmKind_(note, String(r[4] || '')), tid: tid });
  });
  return out;
}

/** 비고에서 주제를 판정한다. 훅_성과의 '종류'는 시세표/전시폰이라 컨셉이 아니다. */
function fmKind_(note, event) {
  if (/사건=신규폰/.test(note)) return '신규폰';
  if (/변동=/.test(note)) return '변동';
  if (event === 'SCARCE' || /개봉/.test(note)) return 'DP';
  if (/카테고리=플래그십/.test(note)) return '플래그십';
  return '가성비';
}

/**
 * 릿지 회귀. 기준 수준(첫 수준)은 절편에 흡수된다.
 * 반환 { ok, n, resid, terms:[{factor,level,n,est,se}] }
 */
function fmFit_(rows) {
  if (!rows || rows.length < 10) return { ok: false, n: rows ? rows.length : 0 };

  var slots = ['8', '12', '18', '21'], kinds = ['DP', '가성비', '변동', '플래그십', '신규폰'];
  var cnt = { slot: {}, kind: {}, tid: {} };
  rows.forEach(function (r) {
    cnt.slot[r.slot] = (cnt.slot[r.slot] || 0) + 1;
    cnt.kind[r.kind] = (cnt.kind[r.kind] || 0) + 1;
    if (r.tid) cnt.tid[r.tid] = (cnt.tid[r.tid] || 0) + 1;
  });

  var cols = [{ factor: '절편', level: '기준', get: function () { return 1; }, lam: 0, n: rows.length }];
  slots.forEach(function (s, i) {
    if (i === 0 || !cnt.slot[s]) return;                      // 8시가 기준
    cols.push({ factor: '시간대', level: s + '시', lam: AS_FM.LAMBDA, n: cnt.slot[s],
                get: function (r) { return r.slot === s ? 1 : 0; } });
  });
  kinds.forEach(function (k, i) {
    if (i === 0 || !cnt.kind[k]) return;                      // DP가 기준
    cols.push({ factor: '주제', level: k, lam: AS_FM.LAMBDA, n: cnt.kind[k],
                get: function (r) { return r.kind === k ? 1 : 0; } });
  });
  // 훅은 같은 풀 안에서만 비교한다. 풀의 첫 틀이 그 풀의 기준이 된다.
  var byPool = {};
  Object.keys(cnt.tid).sort().forEach(function (tid) {
    var p = tid.split('#')[0];
    (byPool[p] = byPool[p] || []).push(tid);
  });
  Object.keys(byPool).forEach(function (p) {
    byPool[p].forEach(function (tid, i) {
      if (i === 0) return;
      cols.push({ factor: '훅', level: tid, lam: AS_FM.LAMBDA_HOOK, n: cnt.tid[tid],
                  get: function (r) { return r.tid === tid ? 1 : 0; } });
    });
  });

  var p = cols.length, n = rows.length;
  if (n <= p) return { ok: false, n: n, tooFew: true, p: p };

  var X = rows.map(function (r) {
    return cols.map(function (c) { return c.get(r); });
  });
  var y = rows.map(function (r) { return r.rel; });

  // (X'X + λI) b = X'y
  var A = fmZeros_(p, p), b = fmZeros_(p, 1);
  for (var i = 0; i < n; i++) {
    for (var a = 0; a < p; a++) {
      if (!X[i][a]) continue;
      b[a][0] += X[i][a] * y[i];
      for (var c2 = 0; c2 < p; c2++) A[a][c2] += X[i][a] * X[i][c2];
    }
  }
  var R = fmZeros_(p, p);
  for (var k = 0; k < p; k++) R[k][k] = cols[k].lam;
  var Ar = fmAdd_(A, R);
  var Ai = fmInv_(Ar);
  if (!Ai) return { ok: false, n: n, singular: true };
  var beta = fmMul_(Ai, b);

  // 잔차
  var ss = 0;
  for (var i2 = 0; i2 < n; i2++) {
    var f = 0;
    for (var j = 0; j < p; j++) f += X[i2][j] * beta[j][0];
    ss += (y[i2] - f) * (y[i2] - f);
  }
  var dof = Math.max(1, n - p);
  var s2 = ss / dof;

  // 분산 = s² (A+λI)⁻¹ A (A+λI)⁻¹
  var V = fmMul_(fmMul_(Ai, A), Ai);
  var terms = cols.map(function (c, i3) {
    return { factor: c.factor, level: c.level, n: c.n,
             est: beta[i3][0], se: Math.sqrt(Math.max(0, s2 * V[i3][i3])) };
  });

  return { ok: true, n: n, p: p, resid: Math.sqrt(s2), terms: terms };
}

/** 요인 추정 결과를 「요인_성과」 탭에 쓰고 요약을 남긴다. 월요일엔 텔레그램으로도. */
function buildFactorTable() {
  var fit = fmFit_(fmRows_());
  if (!fit.ok) {
    Logger.log('요인 모형: 표본 부족 (n=%s%s). D+%s 성적이 더 쌓여야 합니다.',
      fit.n, fit.p ? ', 추정할 값 ' + fit.p + '개' : '', AS.SNAP_DAYS);
    asLog_('SKIP', '요인 모형 표본 부족 n=' + fit.n);
    return;
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(AS_FM.SHEET);
  if (!sh) { sh = ss.insertSheet(AS_FM.SHEET); sh.setFrozenRows(1); }
  sh.clear();
  sh.getRange(1, 1, 1, AS_FM.HEAD.length).setValues([AS_FM.HEAD]).setFontWeight('bold');

  var stamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  var rows = fit.terms.filter(function (t) { return t.factor !== '절편'; }).map(function (t) {
    var lo = Math.exp(t.est - AS_FM.Z * t.se), hi = Math.exp(t.est + AS_FM.Z * t.se);
    var verdict = (t.n < AS_FM.MIN_N) ? '탐색중(표본 ' + t.n + ')'
                : (lo > 1) ? '기준보다 높음'
                : (hi < 1) ? '기준보다 낮음'
                : '판정보류';
    return [stamp, t.factor, t.level, t.n,
            Math.round(Math.exp(t.est) * 100) / 100,
            Math.round(lo * 100) / 100, Math.round(hi * 100) / 100, verdict];
  });
  // 기준 수준도 표에 남긴다. 없으면 "무엇 대비"인지 시트만 보고 알 수 없다.
  rows.unshift([stamp, '시간대', '8시 (기준)', '', 1, '', '', '기준']);
  rows.splice(4, 0, [stamp, '주제', 'DP (기준)', '', 1, '', '', '기준']);
  sh.getRange(2, 1, rows.length, AS_FM.HEAD.length).setValues(rows);

  // 얼마나 더 모아야 판정이 되는지 — 이게 없으면 표를 과신하게 된다
  var need = function (ratio) {
    var d = Math.log(ratio);
    return Math.ceil(2 * Math.pow(1.96 + 0.8416, 2) * fit.resid * fit.resid / (d * d));
  };
  var note = '표본 ' + fit.n + '건 · 잔차 ' + (Math.round(fit.resid * 100) / 100)
           + ' · 2배 차이 판정에 수준당 ' + need(2) + '건, 1.5배는 ' + need(1.5) + '건';
  sh.getRange(rows.length + 3, 1).setValue(note);
  sh.getRange(rows.length + 4, 1).setValue(
    '추정배수 1.00 = 기준 수준과 같음. 구간이 1을 포함하면 아직 차이를 말할 수 없음.');

  Logger.log('%s', note);
  fit.terms.forEach(function (t) {
    if (t.factor === '절편') return;
    Logger.log('%s %s  n=%s  ×%s  (%s ~ %s)', pad2_(t.factor, 6), pad2_(t.level, 14),
      pad2_(String(t.n), 3), (Math.round(Math.exp(t.est) * 100) / 100).toFixed(2),
      (Math.exp(t.est - AS_FM.Z * t.se)).toFixed(2), (Math.exp(t.est + AS_FM.Z * t.se)).toFixed(2));
  });
  asLog_('OK', '요인_성과 ' + rows.length + '행 · ' + note);

  // 월요일에만 요약을 보낸다. 매일 보내면 표를 안 보게 된다.
  if (new Date().getDay() === 1) {
    var top = fit.terms.filter(function (t) {
      return t.factor !== '절편' && t.n >= AS_FM.MIN_N;
    }).sort(function (a, b) { return b.est - a.est; });
    var line = function (t) {
      return t.factor + ' ' + t.level + ' ×' + (Math.round(Math.exp(t.est) * 100) / 100).toFixed(2)
           + ' (n=' + t.n + ')';
    };
    asAlert_('📊 주간 요인 점검\n' + note + '\n\n'
      + (top.length ? '상위: ' + top.slice(0, 2).map(line).join(' · ') + '\n'
                    + '하위: ' + top.slice(-2).map(line).join(' · ')
                    : '아직 표본 ' + AS_FM.MIN_N + '건을 넘긴 수준이 없습니다.')
      + '\n\n자세한 건 「요인_성과」 탭.');
  }
}

/** 지금 추정치만 로그로 본다. 시트를 안 건드린다. */
function checkFactors() {
  var rows = fmRows_(), fit = fmFit_(rows);
  Logger.log('모형에 들어간 글 %s건 (수정본·태그없는 옛 글 제외)', rows.length);
  if (!fit.ok) { Logger.log('표본 부족 — 추정할 값 %s개', fit.p || '?'); return; }
  Logger.log('잔차 %s · 요인으로 설명되는 몫이 작을수록 이 값이 큽니다', (Math.round(fit.resid * 100) / 100));
  fit.terms.forEach(function (t) {
    if (t.factor === '절편') return;
    Logger.log('%s %s n=%s ×%s (%s~%s)', pad2_(t.factor, 6), pad2_(t.level, 14), pad2_(String(t.n), 3),
      Math.exp(t.est).toFixed(2), Math.exp(t.est - 1.96 * t.se).toFixed(2), Math.exp(t.est + 1.96 * t.se).toFixed(2));
  });
}

/**
 * draft_gen 이 훅을 고를 때 쓰는 값.
 * 슬롯·주제 효과를 뺀 **순수 훅 효과**다. 풀의 기준 틀은 0.
 * 모형이 아직 못 서면 null 을 주고, draft_gen 은 예전 방식(풀 평균)으로 돌아간다.
 */
function hookFactorScores_() {
  var fit = fmFit_(fmRows_());
  if (!fit.ok) return null;
  var out = { total: fit.n, resid: fit.resid, byT: {} };
  fit.terms.forEach(function (t) {
    if (t.factor === '훅') out.byT[t.level] = { est: t.est, se: t.se, n: t.n };
  });
  return out;
}

// ── 작은 행렬 도구 (p ≤ 30 이라 단순 구현으로 충분하다)
function fmZeros_(r, c) {
  var m = [];
  for (var i = 0; i < r; i++) { m.push([]); for (var j = 0; j < c; j++) m[i].push(0); }
  return m;
}
function fmAdd_(A, B) {
  return A.map(function (row, i) { return row.map(function (x, j) { return x + B[i][j]; }); });
}
function fmMul_(A, B) {
  var n = A.length, m = B[0].length, k = B.length, C = fmZeros_(n, m);
  for (var i = 0; i < n; i++) for (var j = 0; j < m; j++) {
    var s = 0; for (var t = 0; t < k; t++) s += A[i][t] * B[t][j];
    C[i][j] = s;
  }
  return C;
}
/** 가우스-조던 역행렬. 특이하면 null. */
function fmInv_(M) {
  var n = M.length, A = M.map(function (r) { return r.slice(); }), I = fmZeros_(n, n);
  for (var i = 0; i < n; i++) I[i][i] = 1;
  for (var c = 0; c < n; c++) {
    var piv = c;
    for (var r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[piv][c])) piv = r;
    if (Math.abs(A[piv][c]) < 1e-10) return null;
    var tmp = A[c]; A[c] = A[piv]; A[piv] = tmp;
    tmp = I[c]; I[c] = I[piv]; I[piv] = tmp;
    var d = A[c][c];
    for (var j = 0; j < n; j++) { A[c][j] /= d; I[c][j] /= d; }
    for (var r2 = 0; r2 < n; r2++) {
      if (r2 === c) continue;
      var f = A[r2][c];
      if (!f) continue;
      for (var j2 = 0; j2 < n; j2++) { A[r2][j2] -= f * A[c][j2]; I[r2][j2] -= f * I[c][j2]; }
    }
  }
  return I;
}