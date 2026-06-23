/**
 * 알림/모니터링 (텔레그램) — 2026-06-18 신설 (STEP3)
 *
 * 사전: Script Property TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 등록
 *       (GitHub Actions Secret과 동일 값. 미등록 시 조용히 스킵 + 로그만.)
 *
 * 구성: tgSend_ 발송 / runHealthCheck_ 침묵실패 포착 / checkAdTargets_ 목표경고 / sendMorningBriefing 아침 브리핑
 * 트리거: refreshAll(02:45) 끝에 runHealthCheck_ 호출 + sendMorningBriefing(09:00) 별도 트리거.
 */

// ============ 텔레그램 발송 ============
function tgSend_(text) {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('TELEGRAM_BOT_TOKEN');
  const chat = props.getProperty('TELEGRAM_CHAT_ID');
  if (!token || !chat) { Logger.log('[tg] 토큰 미등록 — 스킵: ' + String(text).slice(0, 80)); return false; }
  try {
    UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
      method: 'post',
      payload: { chat_id: chat, text: text, disable_web_page_preview: 'true' },
      muteHttpExceptions: true
    });
    return true;
  } catch (e) { Logger.log('[tg] 전송 실패: ' + e.message); return false; }
}

function _ymd(n) {
  const d = new Date(); d.setDate(d.getDate() - n);
  return Utilities.formatDate(d, 'Asia/Seoul', 'yyyy-MM-dd');
}

// ============ 헬스체크 — 침묵 실패 포착 (P2-2) ============
// IFERROR이 0으로 숨기는 매칭 깨짐 + 채널 데이터 끊김을 자동 감지.
function runHealthCheck_() {
  const ss = SpreadsheetApp.getActive();
  const warns = [];
  // (표시명, 시트, 날짜열idx, GA4세션열idx)  ※ idx는 0기반
  const CFG = [
    { name: '메타', sheet: '메타+', dcol: 0, gcol: 10 },
    { name: '네이버', sheet: '네이버+', dcol: 0, gcol: 10 },
    { name: '당근', sheet: '당근+', dcol: 0, gcol: 8 }
  ];
  CFG.forEach(function (c) {
    const sh = ss.getSheetByName(c.sheet);
    if (!sh || sh.getLastRow() < 2) { warns.push('⚠️ ' + c.name + '_통합 비어있음/없음'); return; }
    const n = sh.getLastRow() - 1;
    const dates = sh.getRange(2, c.dcol + 1, n, 1).getDisplayValues()
      .map(function (r) { return String(r[0]).slice(0, 10); })
      .filter(function (x) { return /^\d{4}-\d{2}-\d{2}/.test(x); });
    const maxDate = dates.sort().pop() || '(없음)';
    if (maxDate < _ymd(2)) {
      warns.push('⚠️ ' + c.name + ' 최신 데이터 ' + maxDate + ' (어제 ' + _ymd(1) + ' 없음 — 집행중단/동기화 점검)');
    }
    const gv = sh.getRange(2, c.gcol + 1, n, 1).getValues();
    const nz = gv.filter(function (r) { return (Number(r[0]) || 0) > 0; }).length;
    if (nz === 0) warns.push('⚠️ ' + c.name + ' GA4세션 전 행 0 (매칭 깨짐 의심 — 슬러그/수식 점검)');
  });
  const stamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'MM-dd HH:mm');
  if (warns.length) {
    tgSend_('🚨 폰스팟 광고 헬스체크 (' + stamp + ')\n\n' + warns.join('\n'));
    if (typeof logSync_ === 'function') logSync_('healthCheck', '경고 ' + warns.length + '건');
  } else {
    if (typeof logSync_ === 'function') logSync_('healthCheck', 'OK (이상 없음)');
  }
  return warns;
}

function runHealthCheckMenu() {
  const w = runHealthCheck_();
  SpreadsheetApp.getUi().alert(w.length ? ('⚠️ 경고 ' + w.length + '건\n\n' + w.join('\n')) : '✅ 이상 없음');
}

// ============ 목표 CPA/CPL 경고 (P3-2) ============
// 목표는 Script Property TARGET_CPL(문의당 광고비 상한, 기본 50000원). 어제분만 점검.
function checkAdTargets_() {
  const props = PropertiesService.getScriptProperties();
  const targetCPL = Number(props.getProperty('TARGET_CPL') || 50000);
  const ss = SpreadsheetApp.getActive();
  const warns = [];
  const y1 = _ymd(1);
  // 메타/네이버 통합: 날짜0, 광고그룹4, 지출7, 문의수17 (0기반)
  [['메타', '메타+'], ['네이버', '네이버+']].forEach(function (ch) {
    const sh = ss.getSheetByName(ch[1]);
    if (!sh || sh.getLastRow() < 2) return;
    const n = sh.getLastRow() - 1;
    const v = sh.getRange(2, 1, n, 18).getValues();
    v.forEach(function (r) {
      const d = String(r[0]).slice(0, 10);
      if (d < y1) return; // 어제분만
      const spend = Number(r[7]) || 0, inq = Number(r[17]) || 0;
      if (spend >= 30000 && inq === 0) {
        warns.push('⚠️ ' + ch[0] + ' ' + r[4] + ' 어제 지출 ' + spend.toLocaleString() + '원 / 문의 0');
      } else if (inq > 0 && spend / inq > targetCPL) {
        warns.push('⚠️ ' + ch[0] + ' ' + r[4] + ' CPL ' + Math.round(spend / inq).toLocaleString() + '원 (목표 ' + targetCPL.toLocaleString() + ' 초과)');
      }
    });
  });
  if (warns.length) tgSend_('🎯 광고 목표 경고 (어제 기준, 목표 CPL ' + targetCPL.toLocaleString() + '원)\n\n' + warns.slice(0, 15).join('\n'));
  if (typeof logSync_ === 'function') logSync_('checkAdTargets', warns.length ? ('경고 ' + warns.length + '건') : 'OK');
  return warns;
}

// ============ 아침 브리핑 (P3-11, 매일 09:00) ============
// 통합대시보드 KPI 셀 기준. 셀 위치가 바뀌면 아래 A6/B11/B12/B13/B14 조정.
function sendMorningBriefing() {
  const ss = SpreadsheetApp.getActive();
  const d = ss.getSheetByName('통합대시보드');
  if (!d) return;
  const today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'MM/dd');

  // 1) 기간별 종합 — 기간별 핵심표(A6:F8) 기준 (어제/최근7일/최근30일)
  //    컬럼: A기간 B광고비 C문의 D개통 E CPL F순이익  (buildDashboardV2 레이아웃)
  let periodLines = [];
  try {
    const vals = d.getRange(6, 1, 3, 6).getDisplayValues();
    vals.forEach(function (r) {
      const label = String(r[0] || '').trim();
      if (!label) return;
      periodLines.push('▪ ' + label + '\n   광고비 ' + (r[1] || '-') + ' · 문의 ' + (r[2] || '-') +
        ' · 개통 ' + (r[3] || '-') + ' · CPL ' + (r[4] || '-') + ' · 순이익 ' + (r[5] || '-'));
    });
  } catch (e) {}

  // 2) 어제 채널별 노출/클릭/지출 (API/매칭 수집분)
  const y = new Date(); y.setDate(y.getDate() - 1);
  const ymd = Utilities.formatDate(y, 'Asia/Seoul', 'yyyy-MM-dd');
  // [표시명, 시트, 노출col, 클릭col, 지출col] (1-based)
  const CH = [
    ['메타', '메타+', 6, 7, 8],
    ['네이버', '네이버+', 6, 7, 8],
    ['당근', '당근+', 4, 5, 6],
    ['구글', '구글+', 4, 5, 6]
  ];
  let chLines = [];
  CH.forEach(function (c) {
    const sh = ss.getSheetByName(c[1]);
    if (!sh || sh.getLastRow() < 2) return;
    const n = sh.getLastRow() - 1;
    const maxc = Math.max(c[2], c[3], c[4]);
    const data = sh.getRange(2, 1, n, maxc).getValues();
    let imp = 0, clk = 0, spd = 0, hit = false;
    data.forEach(function (row) {
      const dt = row[0];
      const dts = (dt instanceof Date) ? Utilities.formatDate(dt, 'Asia/Seoul', 'yyyy-MM-dd')
                                       : String(dt).slice(0, 10).replace(/\./g, '-').replace(/\s/g, '');
      if (dts !== ymd) return;
      hit = true;
      imp += Number(row[c[2] - 1]) || 0;
      clk += Number(row[c[3] - 1]) || 0;
      spd += Number(row[c[4] - 1]) || 0;
    });
    if (hit) chLines.push('· ' + c[0] + ': 노출 ' + imp.toLocaleString() + ' / 클릭 ' + clk.toLocaleString() +
      ' / 지출 ' + Math.round(spd).toLocaleString() + '원');
  });

  let txt = '☀️ 폰스팟 광고 아침 브리핑 ' + today + '\n\n[기간별 종합]\n'
    + (periodLines.join('\n') || '(KPI표 비어있음 — 전체 새로고침 필요)');
  if (chLines.length) txt += '\n\n[어제 채널별 노출/클릭/지출]\n' + chLines.join('\n');
  txt += '\n\n(상세 = 통합대시보드)';
  tgSend_(txt);
}

function setupMorningBriefingTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'sendMorningBriefing') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('sendMorningBriefing').timeBased().atHour(9).nearMinute(0).everyDays(1).create();
  SpreadsheetApp.getUi().alert('✅ 아침 브리핑 트리거 등록 (매일 09:00).\n\n사전 필수: Script Property TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 등록 (GitHub Secret과 동일 값).');
}

// 텔레그램 연결 테스트
function testTelegram() {
  const ok = tgSend_('✅ 폰스팟 광고 텔레그램 연결 테스트 ' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'MM-dd HH:mm'));
  SpreadsheetApp.getUi().alert(ok ? '✅ 전송 성공 (텔레그램 확인)' : '⚠️ 미전송 — TELEGRAM_BOT_TOKEN/CHAT_ID Script Property 등록 확인');
}

// ============ 토큰 만료/유효성 점검 (D, 2026-06-22) ============
// 메타 토큰(만료 가능)·구글Ads refresh_token(승인 후, 테스트모드면 7일 만료)·네이버키·텔레그램 점검.
// 문제 있을 때만 텔레그램 경고. 매일 08:30 트리거 권장.
function checkTokensDaily() {
  const props = PropertiesService.getScriptProperties();
  const problems = [];

  // 1) 메타 access token — 가벼운 /me 호출로 검증
  const metaTok = props.getProperty('META_TOKEN');
  if (!metaTok) problems.push('· 메타: META_TOKEN 미등록');
  else {
    try { if (typeof metaFetch === 'function') metaFetch('/me', { fields: 'id' }); }
    catch (e) { problems.push('· 메타 토큰 실패: ' + String(e.message).slice(0, 120)); }
  }

  // 2) 구글 Ads refresh_token — 등록돼 있으면 access token 교환 시도
  if (props.getProperty('GOOGLE_ADS_REFRESH_TOKEN')) {
    try { if (typeof _gadsAccessToken_ === 'function') _gadsAccessToken_(); }
    catch (e) { problems.push('· 구글Ads 토큰 실패: ' + String(e.message).slice(0, 120)); }
  }

  // 3) 네이버 키 (API키=만료없음, 존재만 확인)
  if (!props.getProperty('NAVER_SECRET_KEY') || !props.getProperty('NAVER_CUSTOMER_ID'))
    problems.push('· 네이버: 키 누락(NAVER_SECRET_KEY/NAVER_CUSTOMER_ID)');

  // 4) 텔레그램 자체
  if (!props.getProperty('TELEGRAM_BOT_TOKEN') || !props.getProperty('TELEGRAM_CHAT_ID'))
    problems.push('· 텔레그램: BOT_TOKEN/CHAT_ID 누락');

  const stamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'MM-dd HH:mm');
  if (problems.length) {
    tgSend_('🔑 토큰 점검 경고 (' + stamp + ')\n\n' + problems.join('\n') +
      '\n\n→ 갱신 필요: Apps Script 프로젝트설정 → 스크립트 속성. (인수인계 시 여기만 확인)');
  }
  if (typeof logSync_ === 'function') logSync_('checkTokensDaily', problems.length ? ('문제 ' + problems.length + '건') : 'OK');
  return problems;
}

function checkTokensMenu() {
  const p = checkTokensDaily();
  SpreadsheetApp.getUi().alert(p.length ? ('⚠️ 토큰 문제 ' + p.length + '건\n\n' + p.join('\n')) : '✅ 토큰 모두 정상 (메타/구글Ads/네이버/텔레그램)');
}

function setupTokenCheckTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'checkTokensDaily') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('checkTokensDaily').timeBased().atHour(8).nearMinute(30).everyDays(1).create();
  SpreadsheetApp.getUi().alert('✅ 토큰 점검 트리거 등록 (매일 08:30). 문제 있을 때만 텔레그램 경고.');
}

// ============ 주간 성과 리포트 (4, 2026-06-22) — 매주 월 09:10 ============
// 지난 7일(어제까지) 채널별 광고비 + 문의 + CPL을 텔레그램으로.
function sendWeeklyReport() {
  const ss = SpreadsheetApp.getActive();
  const tz = 'Asia/Seoul';
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const start = new Date(today); start.setDate(today.getDate() - 7); // 7일 전
  const end = new Date(today); end.setDate(today.getDate() - 1);     // 어제
  const fmt = function (d) { return Utilities.formatDate(d, tz, 'yyyy-MM-dd'); };
  const sStr = fmt(start), eStr = fmt(end);
  const inWin = function (dt) {
    const k = (dt instanceof Date) ? Utilities.formatDate(dt, tz, 'yyyy-MM-dd')
                                   : String(dt).slice(0, 10).replace(/\./g, '-').replace(/\s/g, '');
    return k >= sStr && k <= eStr;
  };
  // [표시명, 시트, 지출col(1-based)]
  const CH = [['메타', '메타+', 8], ['네이버', '네이버+', 8], ['당근', '당근+', 6], ['구글', '구글+', 6]];
  let lines = [], totalSpend = 0;
  CH.forEach(function (c) {
    const sh = ss.getSheetByName(c[1]);
    if (!sh || sh.getLastRow() < 2) return;
    const n = sh.getLastRow() - 1;
    const v = sh.getRange(2, 1, n, c[2]).getValues();
    let sp = 0;
    v.forEach(function (r) { if (inWin(r[0])) sp += Number(r[c[2] - 1]) || 0; });
    if (sp > 0) { totalSpend += sp; lines.push('· ' + c[0] + ': ' + Math.round(sp).toLocaleString() + '원'); }
  });
  // 문의 (문의접수 A열 날짜 카운트)
  let inq = 0;
  const iq = ss.getSheetByName('문의접수');
  if (iq && iq.getLastRow() > 1) {
    const dv = iq.getRange(2, 1, iq.getLastRow() - 1, 1).getValues();
    dv.forEach(function (r) { if (inWin(r[0])) inq++; });
  }
  const cpl = inq > 0 ? Math.round(totalSpend / inq) : 0;
  const txt = '📅 주간 광고 리포트 (' + sStr + ' ~ ' + eStr + ')\n\n'
    + '[채널별 광고비]\n' + (lines.join('\n') || '(데이터 없음)')
    + '\n\n· 총 광고비: ' + Math.round(totalSpend).toLocaleString() + '원'
    + '\n· 문의: ' + inq + '건'
    + '\n· CPL: ' + (inq > 0 ? cpl.toLocaleString() + '원' : '-')
    + '\n\n(상세 = 통합대시보드)';
  tgSend_(txt);
  if (typeof logSync_ === 'function') logSync_('sendWeeklyReport', 'ok', '주간 리포트 발송 ' + sStr + '~' + eStr);
}

function setupWeeklyReportTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'sendWeeklyReport') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('sendWeeklyReport').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(9).nearMinute(10).create();
  SpreadsheetApp.getUi().alert('✅ 주간 리포트 트리거 등록 (매주 월 09:10).');
}

// ============ 알림 메뉴 ============
function buildAlertsMenu_(ui) {
  ui.createMenu('🔔 알림/모니터링')
    .addItem('🩺 헬스체크 지금 실행', 'runHealthCheckMenu')
    .addItem('🎯 목표 경고 지금 점검', 'checkAdTargets_')
    .addItem('☀️ 아침 브리핑 지금 보내기', 'sendMorningBriefing')
    .addItem('📅 주간 리포트 지금 보내기', 'sendWeeklyReport')
    .addSeparator()
    .addItem('⏰ 아침 브리핑 트리거 (09:00)', 'setupMorningBriefingTrigger')
    .addItem('⏰ 주간 리포트 트리거 (월 09:10)', 'setupWeeklyReportTrigger')
    .addItem('🔑 텔레그램 연결 테스트', 'testTelegram')
    .addSeparator()
    .addItem('🔑 토큰 점검 지금', 'checkTokensMenu')
    .addItem('⏰ 토큰 점검 트리거 (08:30)', 'setupTokenCheckTrigger')
    .addToUi();
}
