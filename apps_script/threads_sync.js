/**
 * threads_sync.gs — 폰스팟 스레드 성과 자동 수집
 * 대상 시트: "폰스팟 광고운영 관리대장" > 스레드 탭
 * 계정: @kr_phonespot
 *
 * 최초 1회 setThreadsToken_() 실행해서 토큰 저장 → 이후 syncThreads()를 트리거로.
 *
 * 토큰 발급: 앱 대시보드 > 이용 사례 > Threads API > 설정 > "사용자 토큰 생성기"에서
 *   kr_phonespot 옆 [액세스 토큰 생성하기] 클릭.
 *   여기서 나오는 것이 이미 60일짜리 장기 토큰이므로 단기→장기 교환이 필요 없고,
 *   앱 시크릿도 쓰지 않는다. (갱신 엔드포인트도 access_token만 받는다)
 *   ★ 권한(threads_manage_insights 등)을 먼저 추가한 뒤에 토큰을 생성할 것.
 *     토큰은 발급 시점의 권한만 담는다.
 *
 * ⚠️ 검증 안 된 부분 (실행 후 로그 보고 조정 필요)
 *  - insights metric 이름: 문서상 views/likes/replies/reposts/quotes.
 *    계정 상태에 따라 일부가 거부될 수 있어서, 개별 호출 실패 시 건너뛰도록 짜뒀음.
 *  - 오래된 게시물은 insights가 안 나올 수 있음 (API 도입 이전 게시물).
 *    그런 행은 조용히 넘어가고 로그에만 남김.
 */

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────
var TH = {
  SHEET: '스레드',
  HEADER_ROW: 3,        // 3행이 헤더, 데이터는 4행부터
  FIRST_ROW: 4,
  COL: {
    DATE:      1,  // A 날짜
    KIND:      2,  // B 구분
    TOPIC:     3,  // C 주제
    LINK:      4,  // D 링크
    VIEWS:     5,  // E 조회수
    LIKES:     6,  // F 좋아요
    FOLLOWERS: 7,  // G 팔로워 수
    MEMO:      8,  // H 운영 메모
    NOTE:      9,  // I 비고
    REPLIES:  10   // J 답글 — 비어있던 열. K열부터 월별 합계 블록이라 건드리지 않는다.
  },
  MAX_RUNTIME_MS: 3.5 * 60 * 1000,  // 6분 제한. 뒤에 훅 스냅샷이 붙어서 여유를 더 뒀다
  IMPORT_FROM: '2026-09-07',        // 이 날짜부터 올린 글은 시트에 자동 편입
  IMPORT_MAX: 60,                   // 한 번에 편입할 최대 행 수
  LOG_SHEET: '동기화_로그',
  API: 'https://graph.threads.net/v1.0',
  PROP_TOKEN: 'THREADS_LONG_TOKEN',
  PROP_ISSUED: 'THREADS_TOKEN_ISSUED_AT'
};

// ─────────────────────────────────────────────
// 최초 셋업 — 이 두 개만 손으로 1회 실행
// ─────────────────────────────────────────────

/**
 * 대시보드에서 받은 장기 토큰을 저장한다. 1회만 실행.
 *
 * 사용법 — 아래 한 줄을 편집기에 임시로 만들어 실행하고, 실행 후 그 줄은 지운다.
 *   function _once(){ setThreadsToken_('여기에_토큰_붙여넣기'); }
 * (코드 본문에 토큰을 남기지 않기 위해서다. 저장은 스크립트 속성으로 들어간다.)
 *
 * 저장 직후 검증까지 해서, 토큰이 실제로 동작하는지와 계정이 맞는지 로그에 찍는다.
 */
function setThreadsToken_(longLivedToken) {
  if (!longLivedToken || longLivedToken.length < 20) {
    throw new Error('토큰이 비었거나 너무 짧다.');
  }

  var props = PropertiesService.getScriptProperties();
  props.setProperty(TH.PROP_TOKEN, longLivedToken);
  props.setProperty(TH.PROP_ISSUED, String(Date.now()));

  // 바로 검증 — 잘못된 토큰을 저장해두고 며칠 뒤에 깨닫는 일을 막는다.
  var me = thFetch_('/me', { fields: 'id,username' });
  Logger.log('토큰 저장 완료. 계정: @' + me.username + ' (id ' + me.id + ')');

  if (me.username !== 'kr_phonespot') {
    Logger.log('⚠️ 예상과 다른 계정이다. 확인 필요.');
  }
}

/** 지금 토큰으로 뭐가 되는지 점검. 아무 때나 실행해도 안전(읽기만 한다). */
function checkThreadsAccess() {
  var me = thFetch_('/me', { fields: 'id,username' });
  Logger.log('계정: @' + me.username);

  var posts = thFetch_('/me/threads', { fields: 'id,permalink,timestamp', limit: 5 });
  Logger.log('최근 게시물 ' + ((posts.data || []).length) + '건 조회됨');

  if (posts.data && posts.data[0]) {
    var ins = fetchMediaInsights_(posts.data[0].id);
    Logger.log('지표 샘플: ' + (ins ? JSON.stringify(ins) : '조회 실패 — insights 권한 확인'));
  }

  var f = fetchFollowerCount_();
  Logger.log('팔로워: ' + (f == null ? '조회 실패' : f));
}

/** 트리거 등록 — 1회 실행 */
/**
 * 트리거 1개만 쓴다. 앱스크립트는 사용자당 스크립트당 20개가 한도인데
 * 이 프로젝트엔 이미 20개 넘게 있어서, 새 트리거를 아껴야 한다.
 *
 * 토큰 갱신은 별도 트리거 없이 syncThreads 안에서 같이 돈다 —
 * refreshThreadsToken 은 만료 7일 전이 아니면 바로 빠져나오므로 비용이 없다.
 *
 * 두 번 실행해도 안전하다. 자기 트리거를 먼저 지우고 다시 건다.
 */
function installThreadsTriggers() {
  if (!threadsGuard_('installThreadsTriggers')) return;
  var removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var f = t.getHandlerFunction();
    if (f === 'syncThreads' || f === 'refreshThreadsToken') {
      ScriptApp.deleteTrigger(t); removed++;
    }
  });
  ScriptApp.newTrigger('syncThreads').timeBased().everyDays(1).atHour(3).create();
  Logger.log('트리거 등록: syncThreads 03시 (토큰 갱신 포함). 이전 %s개 정리.', removed);
  Logger.log('현재 내 트리거 %s개 / 한도 20개', ScriptApp.getProjectTriggers().length);
}

/** 내가 만들 수 있는 트리거가 몇 개 남았는지, 무엇이 걸려 있는지 */
function listTriggers() {
  var ts = ScriptApp.getProjectTriggers();
  Logger.log('내 계정 트리거 %s개 / 한도 20개  (남은 자리 %s)', ts.length, Math.max(0, 20 - ts.length));
  var byFn = {};
  ts.forEach(function (t) {
    var f = t.getHandlerFunction();
    (byFn[f] = byFn[f] || []).push(t);
  });
  Object.keys(byFn).sort().forEach(function (f) {
    var n = byFn[f].length;
    Logger.log('  %s%s', f, n > 1 ? '   ⚠️ ' + n + '개 중복' : '');
  });
}

/**
 * 같은 함수에 걸린 중복 트리거를 정리한다.
 * 기본은 미리보기다. 실제로 지우려면 pruneDuplicateTriggers(true).
 *
 * ⚠️ 한 함수를 일부러 여러 시각에 돌리고 있다면 그것도 '중복'으로 잡힌다.
 *    미리보기 결과를 먼저 확인할 것.
 */
function pruneDuplicateTriggers(reallyDelete) {
  var byFn = {};
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var f = t.getHandlerFunction();
    (byFn[f] = byFn[f] || []).push(t);
  });
  var victims = [];
  Object.keys(byFn).forEach(function (f) {
    byFn[f].slice(1).forEach(function (t) { victims.push(f); if (reallyDelete) ScriptApp.deleteTrigger(t); });
  });
  if (!victims.length) { Logger.log('중복 트리거 없음'); return; }
  Logger.log('%s %s개: %s', reallyDelete ? '삭제함' : '삭제 후보(미리보기)', victims.length, victims.join(', '));
  if (!reallyDelete) Logger.log('실제로 지우려면 pruneDuplicateTriggers(true)');
  else Logger.log('현재 내 트리거 %s개', ScriptApp.getProjectTriggers().length);
}

// ─────────────────────────────────────────────
// 토큰
// ─────────────────────────────────────────────

function getThreadsToken_() {
  var t = PropertiesService.getScriptProperties().getProperty(TH.PROP_TOKEN);
  if (!t) throw new Error('토큰 없음. setThreadsToken_() 먼저 실행할 것.');
  return t;
}

/**
 * 장기 토큰 갱신. 60일 만료라 매일 확인해서 만료 7일 전부터 갱신.
 * 갱신 조건: 발급 후 24시간 경과 + 아직 만료 전. 앱 시크릿은 필요 없다.
 */
function refreshThreadsToken() {
  if (!threadsGuard_('refreshThreadsToken')) return;
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty(TH.PROP_TOKEN);
  var issued = Number(props.getProperty(TH.PROP_ISSUED) || 0);
  if (!token) { thLog_('refreshThreadsToken', 'SKIP', '토큰 없음'); return; }

  var ageDays = (Date.now() - issued) / 86400000;
  if (ageDays < 1) { return; }          // 24시간 안 지나면 갱신 불가
  if (ageDays < 53) { return; }         // 만료 7일 전부터만

  var url = 'https://graph.threads.net/refresh_access_token'
    + '?grant_type=th_refresh_token'
    + '&access_token=' + encodeURIComponent(token);

  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  var body = JSON.parse(res.getContentText());

  if (body.access_token) {
    props.setProperty(TH.PROP_TOKEN, body.access_token);
    props.setProperty(TH.PROP_ISSUED, String(Date.now()));
    thLog_('refreshThreadsToken', 'OK', '갱신 완료, ' + Math.round(body.expires_in / 86400) + '일 남음');
  } else {
    // 여기서 실패하면 방치 시 60일 뒤 파이프라인이 조용히 죽는다. 반드시 알림.
    thLog_('refreshThreadsToken', 'FAIL', res.getContentText());
    thAlert_('⚠️ 스레드 토큰 갱신 실패\n' + res.getContentText().slice(0, 300));
  }
}

// ─────────────────────────────────────────────
// API
// ─────────────────────────────────────────────

function thFetch_(path, params) {
  var qs = Object.keys(params || {}).map(function (k) {
    return k + '=' + encodeURIComponent(params[k]);
  }).join('&');

  var url = TH.API + path + '?access_token=' + encodeURIComponent(getThreadsToken_())
    + (qs ? '&' + qs : '');

  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  var code = res.getResponseCode();
  var body = JSON.parse(res.getContentText());

  if (code !== 200) {
    var e = new Error('API ' + code + ' ' + path + ' : ' + res.getContentText().slice(0, 200));
    e.httpCode = code;
    throw e;
  }
  return body;
}

/**
 * 내 게시물 + 내 답글을 전부 가져와 shortcode -> {id, permalink, ...} 맵으로.
 *
 * ★ /me/threads 는 답글을 돌려주지 않는다. 답글은 /me/replies 로 따로 받아야 한다.
 *   폰스팟 시트는 구분이 '댓글/스하리댓글/일반댓글'인 행이 162건이라, 이걸 빼면 절반을 놓친다.
 *   (2026-08-25 1차 백필에서 323행 중 184행 매칭실패로 확인)
 */
function fetchMyThreads_() {
  var map = {};

  ['/me/threads', '/me/replies'].forEach(function (path) {
    var after = null;
    var pages = 0;

    do {
      var params = { fields: 'id,permalink,timestamp,media_type,text', limit: 100 };
      if (after) params.after = after;

      var body;
      try {
        body = thFetch_(path, params);
      } catch (err) {
        thLog_('syncThreads', 'WARN', path + ' 조회 실패: ' + String(err).slice(0, 150));
        break;
      }

      (body.data || []).forEach(function (post) {
        var code = shortcodeFromUrl_(post.permalink);
        if (!code) return;
        post._isReply = (path === '/me/replies');
        map[code] = post;
      });

      after = body.paging && body.paging.cursors ? body.paging.cursors.after : null;
      if (!body.paging || !body.paging.next) after = null;
      pages++;
    } while (after && pages < 40);   // 안전장치
  });

  return map;
}

/** 게시물 하나의 지표. 실패하면 null 반환하고 넘어간다. */
function fetchMediaInsights_(mediaId) {
  try {
    var body = thFetch_('/' + mediaId + '/insights', { metric: 'views,likes,replies,reposts,quotes' });
    var out = {};
    (body.data || []).forEach(function (m) {
      var v = m.values && m.values[0] ? m.values[0].value : null;
      if (v === null && typeof m.total_value === 'object') v = m.total_value.value;
      out[m.name] = v;
    });
    return out;
  } catch (err) {
    return null;   // API 도입 이전 게시물 등
  }
}

/** 계정 팔로워 수 */
function fetchFollowerCount_() {
  try {
    var body = thFetch_('/me/threads_insights', { metric: 'followers_count' });
    var row = (body.data || [])[0];
    if (!row) return null;
    if (row.total_value) return row.total_value.value;
    return row.values && row.values[0] ? row.values[0].value : null;
  } catch (err) {
    return null;
  }
}

// ─────────────────────────────────────────────
// 메인
// ─────────────────────────────────────────────

/**
 * 최근 게시물 성과만 갱신 (매일 트리거용).
 * 이미 값이 있는 행도 덮어쓴다 — 조회수는 시간이 지나며 올라가므로 최신값이 맞다.
 * 단 최근 60일 행만 건드려서 불필요한 API 호출을 줄인다.
 */
function syncThreads() {
  if (!threadsGuard_('syncThreads')) return;
  // 토큰 갱신을 여기서 같이 한다. 트리거 자리를 아끼려고 —
  // 만료 7일 전이 아니면 refreshThreadsToken 은 즉시 빠져나온다.
  try { refreshThreadsToken(); } catch (e) { thLog_('refreshThreadsToken', 'WARN', String(e).slice(0, 200)); }

  // 손으로 올린 글·댓글이 시트에 없으면 성과가 집계되지 않는다.
  // 실패해도 본 동기화는 계속한다.
  try { importNewPosts(); } catch (e) { thLog_('importNewPosts', 'WARN', String(e).slice(0, 200)); }
  runThreadsSync_(60, false);

  // 훅 성과 스냅샷도 여기서 같이 돈다. 트리거 한도(사용자당 20개)를 아끼려는 것이고,
  // 조회수를 채운 직후에 D+5 스냅샷을 뜨므로 순서로도 이게 맞다.
  try { if (typeof snapshotHookScores === 'function') snapshotHookScores(); }
  catch (e) { thLog_('snapshotHookScores', 'WARN', String(e).slice(0, 200)); }
}

/**
 * 스레드 계정에는 있는데 시트에는 없는 글을 자동으로 행 추가한다.
 *
 * 왜 필요한가 — 목표가 "그 달에 올린 글들의 조회수 합"인데,
 * 시트에 행이 없는 글은 syncThreads 가 조회수를 채울 대상 자체가 없어서
 * 아무리 올려도 집계에 안 잡힌다. 하루 8건씩 댓글을 달면서 그걸 손으로
 * 8줄 입력하는 건 오래 못 간다. 그래서 편입을 자동화한다.
 *
 * TH.IMPORT_FROM 이후 글만 넣는다. 과거 글까지 끌어오면
 * 이미 정리된 297행에 중복·미분류가 섞인다.
 */
function importNewPosts() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TH.SHEET);
  if (!sh) { Logger.log('스레드 탭 없음'); return; }

  var have = {};
  var lastRow = sh.getLastRow();
  if (lastRow >= TH.FIRST_ROW) {
    sh.getRange(TH.FIRST_ROW, TH.COL.LINK, lastRow - TH.FIRST_ROW + 1, 1).getValues()
      .forEach(function (r) {
        var c = shortcodeFromUrl_(String(r[0] || ''));
        if (c) have[c] = 1;
      });
  }

  var postMap = fetchMyThreads_();
  var from = new Date(TH.IMPORT_FROM + 'T00:00:00+09:00').getTime();

  var add = [];
  Object.keys(postMap).forEach(function (code) {
    if (have[code]) return;
    var p = postMap[code];
    if (!p.timestamp) return;
    var t = new Date(p.timestamp).getTime();
    if (t < from) return;
    add.push({ t: t, p: p });
  });
  if (!add.length) { Logger.log('편입할 새 글 없음'); return; }

  add.sort(function (a, b) { return a.t - b.t; });
  if (add.length > TH.IMPORT_MAX) add = add.slice(0, TH.IMPORT_MAX);

  var rows = add.map(function (x) {
    var head = String(x.p.text || '').split('\n')[0].slice(0, 60);
    var hh = Utilities.formatDate(new Date(x.t), 'Asia/Seoul', 'HH');
    return [
      Utilities.formatDate(new Date(x.t), 'Asia/Seoul', 'yyyy-MM-dd'),
      x.p._isReply ? '댓글' : '일반',       // 나중에 손으로 세분해도 된다
      hh + ' / ' + head,                   // 몇 시에 올린 글인지 맨 앞에
      x.p.permalink, '', '', '', '', '자동편입', ''
    ];
  });

  var start = Math.max(sh.getLastRow() + 1, TH.FIRST_ROW);
  sh.getRange(start, 1, rows.length, 10).setValues(rows);
  Logger.log('새 글 %s행 편입 (%s 이후)', rows.length, TH.IMPORT_FROM);
  thLog_('importNewPosts', 'OK', rows.length + '행 편입');
}

/**
 * 과거 전체 소급 복구.
 * 이미 조회수가 채워진 행은 건너뛰므로, 6분 제한에 걸려 중단돼도
 * 그냥 다시 실행하면 멈춘 지점부터 이어진다. 로그에 '중단됨'이 없을 때까지 반복.
 */
function backfillThreads() {
  runThreadsSync_(99999, true);
}

/**
 * @param windowDays 최근 며칠치 행만 대상으로 할지
 * @param skipFilled true면 이미 조회수가 있는 행은 건너뛴다 (백필 재실행용)
 */
function runThreadsSync_(windowDays, skipFilled) {
  var t0 = Date.now();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(TH.SHEET);
  if (!sh) { thLog_('syncThreads', 'FAIL', '스레드 탭 없음'); return; }

  var lastRow = sh.getLastRow();
  if (lastRow < TH.FIRST_ROW) { thLog_('syncThreads', 'SKIP', '데이터 없음'); return; }

  // J열 헤더가 없으면 만든다. 기존 K~P 월별 블록은 손대지 않는다.
  var jHead = sh.getRange(TH.HEADER_ROW, TH.COL.REPLIES);
  if (!String(jHead.getValue()).trim()) jHead.setValue('답글');

  var n = lastRow - TH.FIRST_ROW + 1;
  var dates   = sh.getRange(TH.FIRST_ROW, TH.COL.DATE,    n, 1).getValues();
  var links   = sh.getRange(TH.FIRST_ROW, TH.COL.LINK,    n, 1).getValues();
  var views   = sh.getRange(TH.FIRST_ROW, TH.COL.VIEWS,   n, 1).getValues();
  var likes   = sh.getRange(TH.FIRST_ROW, TH.COL.LIKES,   n, 1).getValues();
  var replies = sh.getRange(TH.FIRST_ROW, TH.COL.REPLIES, n, 1).getValues();
  var topics  = sh.getRange(TH.FIRST_ROW, TH.COL.TOPIC,   n, 1).getValues();
  var notes   = sh.getRange(TH.FIRST_ROW, TH.COL.NOTE,    n, 1).getValues();
  var importFrom = new Date(TH.IMPORT_FROM + 'T00:00:00+09:00').getTime();
  var edited = 0;

  var postMap;
  try {
    postMap = fetchMyThreads_();
  } catch (err) {
    thLog_('syncThreads', 'FAIL', String(err).slice(0, 300));
    thAlert_('⚠️ 스레드 동기화 실패\n' + String(err).slice(0, 300));
    return;
  }

  var cutoff = Date.now() - windowDays * 86400000;
  var updated = 0, missed = 0, noInsight = 0, skipped = 0;
  var halted = false;
  var missedSamples = [];   // 왜 안 맞는지 진단용 — 앞의 몇 개만 남긴다

  for (var i = 0; i < n; i++) {
    // 시간이 다 되면 여기까지 한 걸 저장하고 빠진다. 남은 건 다음 실행에서.
    if (Date.now() - t0 > TH.MAX_RUNTIME_MS) { halted = true; break; }

    var url = String(links[i][0] || '').trim();
    if (!url) continue;

    var d = dates[i][0];
    if (d instanceof Date && d.getTime() < cutoff) continue;

    // 조회수와 답글이 "둘 다" 채워진 행만 건너뛴다.
    // 조회수만 보고 건너뛰면, J열(답글)을 추가하기 전에 채워진 행들이 영영 답글 없이 남는다.
    // (2026-08-25 실제로 발생: 166행이 조회수만 있고 답글이 빈 채로 남았음)
    var vFilled = views[i][0] !== '' && views[i][0] != null;
    var rFilled = replies[i][0] !== '' && replies[i][0] != null;
    if (skipFilled && vFilled && rFilled) { skipped++; continue; }

    var code = shortcodeFromUrl_(url);
    if (!code) {
      missed++;
      if (missedSamples.length < 5) missedSamples.push('행' + (TH.FIRST_ROW + i) + ' 링크형식:' + url.slice(0, 60));
      continue;
    }

    var post = postMap[code];
    if (!post) {   // 삭제됐거나 다른 계정 글
      missed++;
      if (missedSamples.length < 5) missedSamples.push('행' + (TH.FIRST_ROW + i) + ' 미발견:' + code);
      continue;
    }

    // ── 실제로 올라간 문구를 되가져오고, 발행 시각을 맨 앞에 붙인다.
    //
    // 주제 열 형식:  08 / [RANK/TEASE] 오늘 가성비 TOP 3
    //               └시각  └훅 태그      └본문 첫 줄
    //
    // 사장님이 스레드에서 5분 안에 고치면 시트의 문구와 달라지는데,
    // 성과가 붙는 건 '고쳐진 글'이다. 원본 기준으로 학습하면 엉뚱한 걸 배운다.
    // 시각은 API timestamp 에서 가져오므로, 접두어가 없던 옛 행도 여기서 채워진다.
    if (post.text != null && d instanceof Date && d.getTime() >= importFrom) {
      var live = String(post.text).split('\n')[0].slice(0, 120);
      var cur  = String(topics[i][0] || '');
      // 앞머리를 시각 접두어 / 훅 태그 두 조각으로 뜯는다. 둘 다 없을 수 있다.
      var m    = cur.match(/^((?:\d{1,2}\s*\/\s*)?)((?:\[[A-Z_]+\/[A-Z_]+\]\s*)?)/);
      var tag  = m[2] || '';
      var body = cur.slice(m[0].length);
      var hh   = post.timestamp
               ? Utilities.formatDate(new Date(post.timestamp), 'Asia/Seoul', 'HH') + ' / '
               : (m[1] || '');

      if (live) {
        var bodyChanged = body.trim() !== live.trim();
        var next = hh + tag + live;
        if (next !== cur) {
          topics[i][0] = next;
          edited++;
        }
        // '수정=Y' 는 본문이 실제로 달라졌을 때만. 시각 접두어를 붙인 건 수정이 아니다.
        if (bodyChanged && body.trim()) {
          var note = String(notes[i][0] || '');
          if (note.indexOf('수정=Y') < 0) {
            notes[i][0] = note + (note ? ';' : '') + '수정=Y;원본=' + body.slice(0, 40);
          }
        }
      }
    }

    var ins = fetchMediaInsights_(post.id);
    if (!ins) { noInsight++; continue; }

    if (ins.views   != null) views[i][0]   = ins.views;
    if (ins.likes   != null) likes[i][0]   = ins.likes;
    if (ins.replies != null) replies[i][0] = ins.replies;
    updated++;

    Utilities.sleep(120);   // 예의상 간격
  }

  sh.getRange(TH.FIRST_ROW, TH.COL.VIEWS,   n, 1).setValues(views);
  sh.getRange(TH.FIRST_ROW, TH.COL.LIKES,   n, 1).setValues(likes);
  sh.getRange(TH.FIRST_ROW, TH.COL.REPLIES, n, 1).setValues(replies);
  if (edited) {
    sh.getRange(TH.FIRST_ROW, TH.COL.TOPIC, n, 1).setValues(topics);
    sh.getRange(TH.FIRST_ROW, TH.COL.NOTE,  n, 1).setValues(notes);
    thLog_('syncThreads', 'OK', '스레드에서 수정된 문구 ' + edited + '건 반영');
  }

  // 팔로워는 오늘 날짜의 마지막 행에만 기록 (계정 단위 지표라 행마다 넣을 필요 없음)
  var followers = fetchFollowerCount_();
  if (followers != null) {
    sh.getRange(lastRow, TH.COL.FOLLOWERS).setValue(followers);
  }

  var msg = '갱신 ' + updated + '행' + (edited ? ' / 문구수정 ' + edited : '')
    + (skipped ? ' / 이미채워짐 ' + skipped : '')
    + ' / 매칭실패 ' + missed
    + ' / 지표없음 ' + noInsight
    + (followers != null ? ' / 팔로워 ' + followers : '')
    + ' / ' + Math.round((Date.now() - t0) / 1000) + '초'
    + (halted ? '  ★ 시간초과로 중단됨 — 다시 실행하면 이어서 진행' : '');

  thLog_('syncThreads', halted ? 'PARTIAL' : 'OK', msg);
  Logger.log(msg);
  Logger.log('API에서 받은 게시물+답글 총 ' + Object.keys(postMap).length + '건');
  if (missedSamples.length) Logger.log('매칭실패 샘플: ' + missedSamples.join(' | '));
}

// ─────────────────────────────────────────────
// 유틸
// ─────────────────────────────────────────────

/**
 * https://www.threads.com/@kr_phonespot/post/DZpJQvvmopv  -> DZpJQvvmopv
 * http://threads.com/@kr_phonespot/post/DZ_-ZE0Grk3       -> DZ_-ZE0Grk3
 * 뒤에 쿼리스트링이나 슬래시가 붙어도 잘라낸다.
 */
function shortcodeFromUrl_(url) {
  if (!url) return null;
  var m = String(url).match(/\/post\/([A-Za-z0-9_-]+)/);
  return m ? m[1] : null;
}

/** 기존 동기화_로그 탭에 같은 형식으로 기록 (시각/함수/결과/메시지) */
function thLog_(fn, result, message) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(TH.LOG_SHEET);
    if (!sh) return;
    sh.appendRow([new Date(), fn, result, message]);
  } catch (e) { /* 로그 실패로 본작업을 죽이지 않는다 */ }
}

/**
 * 텔레그램 알림.
 * 기존 브리핑 파이프라인이 _state/outbox 파일을 로컬 listener가 읽어 보내는 구조라,
 * Apps Script에서는 직접 못 쏜다. 우선 로그+메일로 두고,
 * 필요하면 여기를 outbox 쓰기나 봇 직접 호출로 바꾼다.
 */
function thAlert_(text) {
  try {
    MailApp.sendEmail(Session.getEffectiveUser().getEmail(), '[폰스팟] 스레드 동기화 알림', text);
  } catch (e) { /* noop */ }
}