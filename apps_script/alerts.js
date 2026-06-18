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
    { name: '메타', sheet: '메타_통합', dcol: 0, gcol: 10 },
    { name: '네이버', sheet: '네이버_통합', dcol: 0, gcol: 10 },
    { name: '당근', sheet: '당근_통합', dcol: 0, gcol: 8 }
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
  [['메타', '메타_통합'], ['네이버', '네이버_통합']].forEach(function (ch) {
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
  const g = function (a1) { return d.getRange(a1).getDisplayValue(); };
  const txt = '☀️ 폰스팟 광고 아침 브리핑 ' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'MM/dd') + '\n\n'
    + '· 이번달 광고비: ' + g('A6') + '\n'
    + '· 어제: ' + g('B11') + '\n'
    + '· 최근 7일: ' + g('B12') + '\n'
    + '· 최근 30일: ' + g('B14') + '\n'
    + '(상세 = 통합대시보드)';
  tgSend_(txt);
  // 이상치도 함께 점검
  try { runHealthCheck_(); } catch (e) {}
  try { checkAdTargets_(); } catch (e) {}
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

// ============ 알림 메뉴 ============
function buildAlertsMenu_(ui) {
  ui.createMenu('🔔 알림/모니터링')
    .addItem('🩺 헬스체크 지금 실행', 'runHealthCheckMenu')
    .addItem('🎯 목표 경고 지금 점검', 'checkAdTargets_')
    .addItem('☀️ 아침 브리핑 지금 보내기', 'sendMorningBriefing')
    .addSeparator()
    .addItem('⏰ 아침 브리핑 트리거 (09:00)', 'setupMorningBriefingTrigger')
    .addItem('🔑 텔레그램 연결 테스트', 'testTelegram')
    .addToUi();
}
