/**
 * threads_00_guard.js — 스레드 자동화 공통 가드  (2026-10-12)
 *
 * ★ 이 저장소의 threads_*.js 7개는 폰스팟 스레드(@kr_phonespot) 자동화다.
 *   시세 수집 → 초안 생성 → 스레드 발행 → 조회수 수집 → 훅·요인 학습까지 매일 자동으로 돈다.
 *   트리거: syncPrices(매시) · publishApproved(5분) · syncThreads(03시) · generateSlot8/12/18/21
 *
 * ★ 에디터에서 직접 고치지 말 것. 이 저장소로만 수정한다.
 *   배포가 `clasp push --force` 라서 저장소에 없는 파일은 지워진다.
 *   2026-10-08 18:28 패널 작업 커밋(e0828d8)에 alerts.js 가 섞여 배포되면서,
 *   에디터에만 있던 스레드 파일 7개가 삭제되어 4일간 발행이 멈춘 사고가 있었다.
 *
 * ★ 같은 코드가 KT폰샵 프로젝트에도 배포된다. 스레드는 폰스팟 본점 시트에서만 돌아야 하므로
 *   모든 진입 함수가 threadsGuard_() 를 먼저 통과한다. 다른 시트에서는 아무것도 하지 않는다.
 *
 * ★ 텔레그램: alerts.js 의 TELEGRAM_ALL_OFF 를 그대로 따른다(현재 true → 스레드 알림도 발송 안 함, 로그만).
 */

var THREADS_HOME_SHEET_ID = '1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI';   // 폰스팟 광고운영 관리대장

/** 폰스팟 본점 시트에 붙은 프로젝트인가 */
function threadsHere_() {
  try { return SpreadsheetApp.getActiveSpreadsheet().getId() === THREADS_HOME_SHEET_ID; }
  catch (e) { return false; }
}

/** 진입 함수 첫 줄에서 호출. false 면 즉시 return 한다. */
function threadsGuard_(name) {
  if (threadsHere_()) return true;
  Logger.log('[threads] 폰스팟 본점 시트가 아니라 %s 를 실행하지 않습니다.', name);
  return false;
}

/** 스레드 알림을 보내지 않아야 하는가. alerts.js 의 전체 종료 스위치를 따른다. */
function threadsMuted_() {
  try { if (typeof TELEGRAM_ALL_OFF !== 'undefined' && TELEGRAM_ALL_OFF) return true; } catch (e) { /* noop */ }
  try { return String(PropertiesService.getScriptProperties().getProperty('TELEGRAM_MUTE') || '').trim() === '1'; }
  catch (e) { return false; }
}

/** 알림 대신 동기화_로그에 남긴다 — 무엇이 안 나갔는지는 남겨야 한다. */
function threadsMuteLog_(src, text) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('동기화_로그');
    if (sh) sh.appendRow([new Date(), src, '뮤트', String(text).replace(/\n/g, ' / ').slice(0, 200)]);
  } catch (e) { /* noop */ }
}
