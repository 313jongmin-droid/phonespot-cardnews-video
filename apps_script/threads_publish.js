/**
 * publish_threads.gs — 승인된 초안을 스레드에 발행하고 시트에 기록 (3단계)
 *
 * 흐름:
 *   시세_초안 탭 「상태」를 '승인' 으로 바꾼다 (휴대폰 구글시트 앱에서도 가능)
 *     → 5분마다 도는 publishApproved() 가 집어서 발행
 *     → 1/2 발행 → 2/2 를 1/2의 답글로 발행 (체인)
 *     → 상태 '발행완료' + permalink 기록
 *     → 스레드 탭에 2행 자동 추가 (성과 추적용)
 *
 * 텔레그램 웹훅을 안 쓰는 이유: 웹앱 배포·setWebhook 설정이 필요한데
 * 시트 드롭다운 하나로 같은 일이 되고 실패 지점이 적다.
 *
 * ⚠️ 이 스크립트는 실제로 계정에 글을 올린다. 먼저 dryRunPublish() 로 확인할 것.
 */

var PT = {
  API: 'https://graph.threads.net/v1.0',
  SHEET_DRAFT: '시세_초안',
  SHEET_THREADS: '스레드',
  LOG_SHEET: '동기화_로그',

  COL: { STAMP:1, BATCH:2, VARIANT:3, KIND:4, TAG:5, CARRIER:6,
         POST1:7, POST2:8, META:9, STATUS:10, LINK:11 },
  NCOL: 11,
  TH_FIRST_ROW: 4,          // 스레드 탭 데이터 시작 행
  TH_COL: { DATE:1, KIND:2, TOPIC:3, LINK:4, VIEWS:5, LIKES:6, FOLLOWERS:7, MEMO:8, NOTE:9, REPLIES:10 },

  SHEET_NOW: '시세_현재',

  WAIT_MS: 2500,            // 컨테이너 생성 → 발행 사이 대기
  MAX_PER_RUN: 1,           // 한 번에 1건. 몰아서 승인해도 연속 발행되지 않는다.

  // ── 사람이 실수할 수 있는 지점들의 방어값
  TTL_MIN: 240,             // 초안 수명 4시간. 넘으면 승인해도 안 올라간다.
  REMIND_MIN: 20,           // 이만큼 지나도 대기면 한 번 알려준다(자동선정 60분보다 앞서야 한다).
  MIN_GAP_MIN: 30,          // 직전 발행과 최소 간격. 연속 발행 = 도달 손해.
  STUCK_MIN: 10,            // '발행중'이 이보다 오래 머물면 사람이 봐야 한다.
  PRICE_TOL: 0,             // 가격 허용 오차(원). 0 = 1원이라도 다르면 중단.

  PROP_TOKEN: 'THREADS_LONG_TOKEN',
  PROP_TG_TOKEN: 'TELEGRAM_BOT_TOKEN',
  PROP_TG_CHAT:  'TELEGRAM_CHAT_ID',
  PROP_LAST_PUB: 'PT_LAST_PUBLISHED_AT',
  PROP_REMINDED: 'PT_REMINDED_BATCHES'
};

// ─────────────────────────────────────────────
// 진입점
// ─────────────────────────────────────────────

/**
 * 5분마다 트리거. 순서가 중요하다 —
 *   ① 멈춘 것 확인 → ② 낡은 것 만료 → ③ 안 고른 것 알림 → ④ 발행
 * 승인이 없으면 아무 일도 안 일어난다. 그게 정상 동작이다.
 */
function publishApproved() {
  if (!threadsGuard_('publishApproved')) return;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(PT.SHEET_DRAFT);
  if (!sh || sh.getLastRow() < 2) return;

  unstick_(sh);        // ① '발행중'에서 멈춘 행
  expireStale_(sh);    // ② 수명 지난 초안 — 낡은 가격 발행을 막는 1차 방어
  remindPending_(sh);  // ③ 승인이 안 들어온 배치 알림

  var last = sh.getLastRow();
  var v = sh.getRange(2, 1, last - 1, PT.NCOL).getValues();

  // 승인 행 수집. 같은 배치에서 두 개를 고른 실수는 위쪽 하나만 살린다.
  var picked = null, dupBatch = [];
  for (var i = 0; i < v.length; i++) {
    if (String(v[i][PT.COL.STATUS - 1]).trim() !== '승인') continue;
    var row = i + 2;
    if (!picked) { picked = { row: row, batch: v[i][PT.COL.BATCH - 1] }; continue; }
    if (v[i][PT.COL.BATCH - 1] === picked.batch) dupBatch.push(row);
  }
  if (!picked) return;

  if (dupBatch.length) {
    dupBatch.forEach(function (r) { sh.getRange(r, PT.COL.STATUS).setValue('미선택'); });
    ptLog_('WARN', '배치 ' + picked.batch + ' 중복 승인 ' + (dupBatch.length + 1) + '건 → 첫 행만 발행');
    ptAlert_('⚠️ 같은 배치에서 ' + (dupBatch.length + 1) + '개가 승인돼 있었습니다.\n'
           + '맨 위 1건만 올리고 나머지는 미선택으로 되돌렸습니다.');
  }

  // 직전 발행과 너무 붙으면 미룬다. 승인은 그대로 두므로 다음 사이클에 다시 온다.
  var gap = minutesSince_(PropertiesService.getScriptProperties().getProperty(PT.PROP_LAST_PUB));
  if (gap != null && gap < PT.MIN_GAP_MIN) {
    ptLog_('SKIP', '직전 발행 ' + Math.round(gap) + '분 전 — ' + PT.MIN_GAP_MIN + '분 간격 대기');
    return;
  }

  publishRow_(sh, picked.row);
}

/** 실제로 올리지 않고 무엇이 올라갈지만 로그로 확인 */
function dryRunPublish() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PT.SHEET_DRAFT);
  if (!sh || sh.getLastRow() < 2) { Logger.log('초안 없음'); return; }
  var last = sh.getLastRow();
  var v = sh.getRange(2, 1, last - 1, PT.NCOL).getValues();
  var n = 0;
  v.forEach(function (r, i) {
    if (String(r[PT.COL.STATUS - 1]).trim() !== '승인') return;
    n++;
    var age = minutesSince_(r[PT.COL.STAMP - 1]);
    var drift = priceDrift_(r[PT.COL.META - 1]);
    Logger.log('   수명 %s / 가격 %s',
      age == null ? '?' : Math.round(age) + '분 (만료까지 ' + Math.round(PT.TTL_MIN - age) + '분)',
      drift ? '❌ 변동됨 — 발행되지 않습니다\n' + drift : '✅ 유효');
    Logger.log('행 %s %s %s [%s] %s\n──1/2 (%s자)\n%s\n──2/2 (%s자)\n%s',
      i + 2, r[PT.COL.BATCH - 1], r[PT.COL.VARIANT - 1], r[PT.COL.KIND - 1], r[PT.COL.TAG - 1],
      String(r[PT.COL.POST1 - 1]).length, r[PT.COL.POST1 - 1],
      String(r[PT.COL.POST2 - 1]).length, r[PT.COL.POST2 - 1]);
  });
  Logger.log('승인 대기 %s건. 실제 발행은 publishApproved() 가 합니다.', n);
}

/**
 * 지금 초안이 어떤 상태인지 한눈에. 시트를 안 건드린다.
 * "왜 안 올라갔지?" 싶을 때 제일 먼저 실행할 함수.
 */
function checkPending() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PT.SHEET_DRAFT);
  if (!sh || sh.getLastRow() < 2) { Logger.log('초안 없음'); return; }
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, PT.NCOL).getValues();

  var count = {}, live = [];
  v.forEach(function (r, i) {
    var st = String(r[PT.COL.STATUS - 1]).trim() || '(빈칸)';
    count[st] = (count[st] || 0) + 1;
    if (st !== '대기' && st !== '승인' && st !== '발행중' && st !== '점검필요') return;
    var age = minutesSince_(r[PT.COL.STAMP - 1]);
    live.push('  행' + (i + 2) + '  ' + st + '  ' + r[PT.COL.BATCH - 1] + '  '
      + r[PT.COL.VARIANT - 1] + '  '
      + (age == null ? '시각불명' : Math.round(age) + '분 경과 / 만료까지 '
          + Math.max(0, Math.round(PT.TTL_MIN - age)) + '분'));
  });

  Logger.log('상태 집계: %s', JSON.stringify(count));
  if (live.length) { Logger.log('아직 살아있는 행:'); live.forEach(function (l) { Logger.log(l); }); }
  else Logger.log('처리 대기 중인 행 없음 — 다음 초안 시간까지 아무 일도 안 일어납니다.');

  var gap = minutesSince_(PropertiesService.getScriptProperties().getProperty(PT.PROP_LAST_PUB));
  Logger.log('마지막 발행: %s', gap == null ? '기록 없음' : Math.round(gap) + '분 전');

  // 승인된 게 있으면 가격이 아직 유효한지도 같이 본다
  v.forEach(function (r, i) {
    if (String(r[PT.COL.STATUS - 1]).trim() !== '승인') return;
    var drift = priceDrift_(r[PT.COL.META - 1]);
    Logger.log('행%s 가격검증: %s', i + 2, drift ? '❌ 변동\n' + drift : '✅ 유효');
  });
}

/**
 * 알림이 어디로 가는지 지금 확인한다.
 * 텔레그램 속성이 있으면 텔레그램으로, 없으면 계정 메일로 간다.
 */
function testAlert() {
  var p = PropertiesService.getScriptProperties();
  var tok = p.getProperty(PT.PROP_TG_TOKEN), chat = p.getProperty(PT.PROP_TG_CHAT);
  Logger.log('TELEGRAM_BOT_TOKEN : %s', tok ? '설정됨' : '❌ 없음');
  Logger.log('TELEGRAM_CHAT_ID   : %s', chat ? chat : '❌ 없음');
  ptAlert_('🔔 폰스팟 스레드 알림 테스트\n'
    + '이 메시지가 보이면 발행 알림도 같은 곳으로 옵니다.\n'
    + '발행 알림에는 본문 첫 줄 · 링크 · 수정 마감 시각이 함께 옵니다.');
  Logger.log('보냈습니다. 텔레그램이 안 오면 %s 메일함을 확인하세요.',
    Session.getEffectiveUser().getEmail());
}

/** 트리거 등록 — 1회. 313jongmin 계정에서 실행할 것. */
function installPublishTrigger() {
  if (!threadsGuard_('installPublishTrigger')) return;
  ScriptApp.newTrigger('publishApproved').timeBased().everyMinutes(5).create();
  Logger.log('발행 트리거 등록: 5분마다 승인 확인');
}

// ─────────────────────────────────────────────
// 발행
// ─────────────────────────────────────────────

function publishRow_(sh, row) {
  // 여기 오기까지 몇 초가 걸린다. 그 사이 사람이 취소했을 수 있으니 다시 읽는다.
  if (String(sh.getRange(row, PT.COL.STATUS).getValue()).trim() !== '승인') return;

  var v = sh.getRange(row, 1, 1, PT.NCOL).getValues()[0];
  var kind = v[PT.COL.KIND - 1];
  var tag  = v[PT.COL.TAG - 1];
  var p1   = String(v[PT.COL.POST1 - 1]);
  var p2   = String(v[PT.COL.POST2 - 1]);
  var meta = String(v[PT.COL.META - 1]);

  if (!p1) { sh.getRange(row, PT.COL.STATUS).setValue('보류'); return; }
  if (p1.length > 500 || p2.length > 500) {
    sh.getRange(row, PT.COL.STATUS).setValue('보류');
    ptLog_('FAIL', '행 ' + row + ' 500자 초과 (' + p1.length + '/' + p2.length + ')');
    ptAlert_('⚠️ 발행 중단 — 500자 초과\n1/2 ' + p1.length + '자 / 2/2 ' + p2.length + '자');
    return;
  }

  // ★ 가장 중요한 방어 — 초안에 적힌 가격이 지금도 유효한가.
  //   시세는 2시간마다 갱신된다. 4시간 전 초안을 승인하면 없는 가격이 올라간다.
  var stale = priceDrift_(meta);
  if (stale) {
    sh.getRange(row, PT.COL.STATUS).setValue('만료');
    ptLog_('SKIP', '행 ' + row + ' 가격 변동으로 발행 취소 — ' + stale);
    ptAlert_('🛑 발행 취소 — 가격이 바뀌었습니다\n' + stale
           + '\n\n초안을 새로 뽑아 다시 골라주세요.');
    return;
  }

  // 두 번 올라가는 사고를 막는다. 발행 전에 먼저 상태를 잠근다.
  sh.getRange(row, PT.COL.STATUS).setValue('발행중');
  SpreadsheetApp.flush();

  var id1, id2;
  try {
    id1 = postText_(p1, null);
    if (p2) id2 = postText_(p2, id1);
  } catch (err) {
    sh.getRange(row, PT.COL.STATUS).setValue('실패');
    ptLog_('FAIL', '행 ' + row + ' ' + String(err).slice(0, 250));
    ptAlert_('⚠️ 스레드 발행 실패\n' + String(err).slice(0, 300)
           + (id1 ? '\n\n※ 1/2는 올라갔습니다. 계정에서 확인하세요.' : ''));
    return;
  }

  var link1 = permalink_(id1) || '';
  var link2 = id2 ? (permalink_(id2) || '') : '';

  sh.getRange(row, PT.COL.STATUS).setValue('발행완료');
  sh.getRange(row, PT.COL.LINK).setValue(link1);
  PropertiesService.getScriptProperties()
    .setProperty(PT.PROP_LAST_PUB, String(Date.now()));
  voidSiblings_(sh, row, v[PT.COL.BATCH - 1]);

  appendThreadRows_(kind, tag, p1, p2, link1, link2, meta);

  ptLog_('OK', '행 ' + row + ' 발행완료 ' + tag + ' ' + link1);

  // 스레드 편집은 발행 후 5분까지다. 알림에 마감 시각과 본문 첫 줄을 같이 넣어
  // 링크를 열지 않고도 바로 판단할 수 있게 한다.
  var until = Utilities.formatDate(new Date(Date.now() + 5 * 60000), 'Asia/Seoul', 'HH:mm');
  var whyM = meta.match(/근거=([^;]+)/);          // 훅을 왜 골랐는지
  ptAlert_('✅ 스레드 발행됨  ' + kind + ' ' + tag + '\n\n'
    + p1.split('\n')[0] + '\n\n'
    + '1/2 ' + link1 + (link2 ? '\n2/2 ' + link2 : '') + '\n\n'
    + (whyM ? '훅 근거 ' + whyM[1] + '\n' : '')
    + '✏️ 수정은 ' + until + '까지 (발행 후 5분)\n'
    + '그 뒤엔 삭제 후 재발행만 됩니다.');
}

/**
 * 텍스트 게시물 하나를 올린다. parentId 가 있으면 그 글의 답글로 붙는다(=체인).
 * 컨테이너 생성 → 잠깐 대기 → 발행. 2단계다.
 */
function postText_(text, parentId) {
  var token = PropertiesService.getScriptProperties().getProperty(PT.PROP_TOKEN);
  if (!token) throw new Error('THREADS_LONG_TOKEN 없음');

  var payload = { media_type: 'TEXT', text: text, access_token: token };
  if (parentId) payload.reply_to_id = parentId;

  var created = ptFetch_('/me/threads', payload);
  if (!created.id) throw new Error('컨테이너 생성 실패: ' + JSON.stringify(created).slice(0, 200));

  Utilities.sleep(PT.WAIT_MS);

  var published = ptFetch_('/me/threads_publish', { creation_id: created.id, access_token: token });
  if (!published.id) throw new Error('발행 실패: ' + JSON.stringify(published).slice(0, 200));
  return published.id;
}

function permalink_(id) {
  try {
    var token = PropertiesService.getScriptProperties().getProperty(PT.PROP_TOKEN);
    var res = UrlFetchApp.fetch(PT.API + '/' + id + '?fields=permalink&access_token='
      + encodeURIComponent(token), { muteHttpExceptions: true });
    return JSON.parse(res.getContentText()).permalink || '';
  } catch (e) { return ''; }
}

function ptFetch_(path, payload) {
  var res = UrlFetchApp.fetch(PT.API + path, {
    method: 'post', payload: payload, muteHttpExceptions: true
  });
  var body = res.getContentText();
  if (res.getResponseCode() !== 200) {
    throw new Error('API ' + res.getResponseCode() + ' ' + path + ' : ' + body.slice(0, 250));
  }
  return JSON.parse(body);
}

// ─────────────────────────────────────────────
// 휴먼에러 방어
// ─────────────────────────────────────────────

/**
 * 초안 메타의 검증 태그와 시세_현재를 대조한다.
 * 다르면 바뀐 내용을 문자열로, 같으면 null 을 준다.
 *
 * 검증 태그가 없는(옛 버전으로 만든) 초안은 통과시킨다 —
 * 여기서 막아버리면 이유 없이 아무것도 안 올라간다.
 */
function priceDrift_(meta) {
  var m = String(meta || '').match(/검증=([^;]+)/);
  if (!m) return null;

  var now = nowPriceMap_();
  if (!now) return null;                    // 시세_현재를 못 읽으면 판단 보류

  var bad = [];
  m[1].split(',').forEach(function (part) {
    var kv = part.split('@');
    if (kv.length !== 2) return;
    var key = kv[0].replace(/~/g, '|');
    var was = Number(kv[1]);
    var is  = now[key];
    if (is === undefined) { bad.push(key.split('|')[1] + ' 오늘 목록에서 빠짐'); return; }
    if (Math.abs(is - was) > PT.PRICE_TOL) {
      bad.push(key.split('|')[1] + ' ' + ptWon_(was) + ' → ' + ptWon_(is));
    }
  });
  return bad.length ? bad.join('\n') : null;
}

function nowPriceMap_() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PT.SHEET_NOW);
  if (!sh || sh.getLastRow() < 2) return null;
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 16).getValues();
  var map = {};
  v.forEach(function (r) { if (r[15]) map[r[15]] = Number(r[13]); });
  return map;
}

/**
 * 수명이 지난 초안을 만료시킨다.
 * 승인 상태도 만료 대상이다 — 승인해두고 자리를 뜬 사이 시세가 바뀌었을 수 있다.
 * (가격 재검증이 2차 방어지만, 시간으로 먼저 자르는 편이 확실하다)
 */
function expireStale_(sh) {
  var last = sh.getLastRow();
  if (last < 2) return;
  var v = sh.getRange(2, 1, last - 1, PT.NCOL).getValues();
  var expired = {};

  for (var i = 0; i < v.length; i++) {
    var st = String(v[i][PT.COL.STATUS - 1]).trim();
    if (st !== '대기' && st !== '승인') continue;
    var age = minutesSince_(v[i][PT.COL.STAMP - 1]);
    if (age == null || age < PT.TTL_MIN) continue;
    sh.getRange(i + 2, PT.COL.STATUS).setValue('만료');
    var b = String(v[i][PT.COL.BATCH - 1]);
    expired[b] = (expired[b] || 0) + 1;
  }

  var batches = Object.keys(expired);
  if (!batches.length) return;
  ptLog_('OK', '만료 처리 ' + batches.join(', '));
  ptAlert_('⏳ 안 고르신 초안이 만료됐습니다\n' + batches.join('\n')
         + '\n\n올라간 글은 없습니다. 다음 시간대에 새로 올라옵니다.');
}

/** 승인이 안 들어온 배치를 한 번만 알려준다. 두 번 이상은 잔소리다. */
function remindPending_(sh) {
  var last = sh.getLastRow();
  if (last < 2) return;
  var v = sh.getRange(2, 1, last - 1, PT.NCOL).getValues();

  var props = PropertiesService.getScriptProperties();
  var done = {};
  (props.getProperty(PT.PROP_REMINDED) || '').split('|').forEach(function (b) { if (b) done[b] = 1; });

  var wait = {};
  for (var i = 0; i < v.length; i++) {
    if (String(v[i][PT.COL.STATUS - 1]).trim() !== '대기') continue;
    var age = minutesSince_(v[i][PT.COL.STAMP - 1]);
    if (age == null || age < PT.REMIND_MIN || age >= PT.TTL_MIN) continue;
    var b = String(v[i][PT.COL.BATCH - 1]);
    if (done[b]) continue;
    wait[b] = Math.round(age);
  }

  var batches = Object.keys(wait);
  if (!batches.length) return;

  ptAlert_('🔔 아직 안 고르신 초안이 있습니다\n'
    + batches.map(function (b) {
        return '· ' + b + ' (' + wait[b] + '분 경과, ' + (PT.TTL_MIN - wait[b]) + '분 뒤 만료)';
      }).join('\n')
    + '\n\n시세_초안 탭에서 하나를 「승인」으로 바꾸시면 올라갑니다.');

  batches.forEach(function (b) { done[b] = 1; });
  // 목록이 무한히 길어지지 않게 뒤에서 40개만 남긴다
  var keep = Object.keys(done).slice(-40);
  props.setProperty(PT.PROP_REMINDED, keep.join('|'));
}

/**
 * '발행중'에서 멈춘 행. 자동으로 되돌리지 않는다 —
 * 이미 올라갔는데 상태만 못 쓴 경우가 있어서, 되돌리면 같은 글이 두 번 올라간다.
 * 사람이 계정을 보고 판단해야 한다.
 */
function unstick_(sh) {
  var last = sh.getLastRow();
  if (last < 2) return;
  var v = sh.getRange(2, 1, last - 1, PT.NCOL).getValues();
  for (var i = 0; i < v.length; i++) {
    if (String(v[i][PT.COL.STATUS - 1]).trim() !== '발행중') continue;
    var age = minutesSince_(v[i][PT.COL.STAMP - 1]);
    if (age == null || age < PT.STUCK_MIN) continue;
    sh.getRange(i + 2, PT.COL.STATUS).setValue('점검필요');
    ptLog_('FAIL', '행 ' + (i + 2) + ' 발행중 상태로 ' + Math.round(age) + '분 정체');
    ptAlert_('⚠️ 발행이 중간에 멈췄습니다 (행 ' + (i + 2) + ')\n\n'
      + '스레드 계정을 먼저 열어보세요.\n'
      + '· 이미 올라가 있으면 → 상태를 「발행완료」로\n'
      + '· 안 올라갔으면 → 상태를 「승인」으로 되돌리면 다시 시도합니다');
  }
}

/** 시각 값(문자열 또는 Date)이 몇 분 전인지. 못 읽으면 null. */
function minutesSince_(val) {
  if (val == null || val === '') return null;
  var t;
  if (val instanceof Date) t = val.getTime();
  else if (typeof val === 'number') t = val > 1e11 ? val : null;      // epoch ms
  else {
    var s = String(val).trim();
    if (/^\d+$/.test(s)) t = Number(s);
    else {
      // 'yyyy-MM-dd HH:mm' — KST 로 적힌 값이다
      var m = s.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
      if (!m) return null;
      t = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4] - 9, +m[5]);
    }
  }
  if (!t) return null;
  return (Date.now() - t) / 60000;
}

function ptWon_(n) {
  var v = Math.round(Number(n) || 0);
  var s = String(Math.abs(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return (v < 0 ? '0원 + ' + s + '원 페이백' : s + '원');
}

// ─────────────────────────────────────────────
// 시트 기록
// ─────────────────────────────────────────────

/**
 * 스레드 탭에 2행 추가. syncThreads 가 나중에 조회수·좋아요·답글을 채운다.
 * C열(주제)에 [사건/표현] 태그 + 첫 줄, I열(비고)에 메타 — 후킹 분류표 v1 형식.
 */
function appendThreadRows_(kind, tag, p1, p2, link1, link2, meta) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PT.SHEET_THREADS);
  if (!sh) { ptLog_('WARN', '스레드 탭 없음 — 성과 기록 건너뜀'); return; }

  var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
  var head1 = p1.split('\n')[0];
  var head2 = p2 ? p2.split('\n')[0] : '';
  var 구분 = (kind === 'DP') ? '전시폰' : '시세표';

  // 주제 열 맨 앞에 발행 시각(시)을 붙인다 — 08 / [RANK/TEASE] 첫줄
  // 시트만 훑어도 몇 시 글인지 바로 보인다. syncThreads 가 이 형식을 유지·보정한다.
  var hh = Utilities.formatDate(new Date(), 'Asia/Seoul', 'HH') + ' / ';

  var rows = [[today, 구분, hh + tag + ' ' + head1, link1, '', '', '', '', meta + ';단계=1', '']];
  if (p2) rows.push([today, 구분, hh + tag + ' ' + head2, link2, '', '', '', '', meta + ';단계=2', '']);

  var start = Math.max(sh.getLastRow() + 1, PT.TH_FIRST_ROW);
  sh.getRange(start, 1, rows.length, 10).setValues(rows);
}

// ─────────────────────────────────────────────
// 유틸
// ─────────────────────────────────────────────

function ptLog_(result, message) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PT.LOG_SHEET);
    if (sh) sh.appendRow([new Date(), 'publishThreads', result, message]);
  } catch (e) { /* noop */ }
}

function ptAlert_(text) {
  if (threadsMuted_()) { threadsMuteLog_('publishThreads', text); return; }   // alerts.js TELEGRAM_ALL_OFF 따름
  var p = PropertiesService.getScriptProperties();
  var token = p.getProperty(PT.PROP_TG_TOKEN), chat = p.getProperty(PT.PROP_TG_CHAT);
  if (token && chat) {
    try {
      var res = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
        method: 'post', muteHttpExceptions: true,
        payload: { chat_id: chat, text: text, disable_web_page_preview: 'true' }
      });
      if (res.getResponseCode() === 200) return;
    } catch (e) { /* noop */ }
  }
  try { MailApp.sendEmail(Session.getEffectiveUser().getEmail(), '[폰스팟] 스레드 발행', text); }
  catch (e) { /* noop */ }
}

/**
 * 같은 배치의 나머지 시안을 '미선택'으로 바꾼다.
 * 무엇이 제시됐고 무엇이 안 뽑혔는지가 남아야, 나중에 선택 편향을 보정할 수 있다.
 */
function voidSiblings_(sh, publishedRow, batch) {
  if (!batch) return;
  var last = sh.getLastRow();
  if (last < 2) return;
  var v = sh.getRange(2, PT.COL.BATCH, last - 1, 1).getValues();
  var st = sh.getRange(2, PT.COL.STATUS, last - 1, 1).getValues();
  for (var i = 0; i < v.length; i++) {
    var row = i + 2;
    if (row === publishedRow) continue;
    if (v[i][0] !== batch) continue;
    var cur = String(st[i][0]).trim();
    if (cur === '발행완료' || cur === '미선택') continue;
    sh.getRange(row, PT.COL.STATUS).setValue('미선택');
  }
}