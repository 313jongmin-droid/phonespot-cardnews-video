/**
 * 자연어 데이터 질의 (STEP5, P3-12) — 2026-06-18 신설
 * 시트 메뉴에서 질문 입력 → 통합대시보드+채널통합+소재성과를 컨텍스트로 Gemini 답변.
 * 사전: Script Property GEMINI_API_KEY (이미 등록되어 있음 — 메타 인사이트가 사용 중).
 * 추측 금지 프롬프트. generator.html 미접촉.
 */

var NLQ_MODEL = 'gemini-2.5-flash';

function _geminiAsk_(prompt) {
  const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) return null;
  const url = 'https://generativelanguage.googleapis.com/v1beta/models/' + NLQ_MODEL + ':generateContent?key=' + key;
  const payload = { contents: [{ parts: [{ text: prompt }] }] };
  try {
    const res = UrlFetchApp.fetch(url, {
      method: 'post', contentType: 'application/json',
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) { Logger.log('gemini ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 300)); return null; }
    const j = JSON.parse(res.getContentText());
    return j.candidates[0].content.parts[0].text;
  } catch (e) { Logger.log('gemini 호출 실패: ' + e.message); return null; }
}

function _buildSheetContext_(ss) {
  const parts = [];
  const dash = ss.getSheetByName('통합대시보드');
  if (dash) {
    const v = dash.getRange(1, 1, Math.min(57, dash.getLastRow()), Math.min(12, dash.getLastColumn())).getDisplayValues();
    parts.push('[통합대시보드]\n' + v.map(function (r) { return r.filter(String).join(' | '); }).filter(String).join('\n'));
  }
  [['메타', '메타+'], ['네이버', '네이버+'], ['당근', '당근+']].forEach(function (c) {
    const sh = ss.getSheetByName(c[1]); if (!sh || sh.getLastRow() < 2) return;
    const last = sh.getLastRow(); const start = Math.max(2, last - 6);
    const v = sh.getRange(start, 1, last - start + 1, Math.min(18, sh.getLastColumn())).getDisplayValues();
    parts.push('[' + c[0] + '_통합 최근 7행]\n' + v.map(function (r) { return r.join(' | '); }).join('\n'));
  });
  const perf = ss.getSheetByName('소재_성과');
  if (perf && perf.getLastRow() > 1) {
    const v = perf.getRange(1, 1, Math.min(15, perf.getLastRow()), Math.min(9, perf.getLastColumn())).getDisplayValues();
    parts.push('[소재_성과]\n' + v.map(function (r) { return r.filter(String).join(' | '); }).filter(String).join('\n'));
  }
  return parts.join('\n\n');
}

function askSheetQuestion() {
  const ui = SpreadsheetApp.getUi();
  const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) { ui.alert('GEMINI_API_KEY 미등록 (Apps Script 프로젝트 설정 → 스크립트 속성).'); return; }
  const res = ui.prompt('광고 데이터에 질문', '예: 지난주 네이버 CPL은? / 어제 제일 잘한 소재는? / 이번달 채널별 광고비 비교', ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  const q = String(res.getResponseText() || '').trim();
  if (!q) return;
  const ss = SpreadsheetApp.getActive();
  const ctx = _buildSheetContext_(ss);
  const prompt = '너는 폰스팟 광고운영 분석가다. 아래 시트 데이터만 근거로 질문에 한국어로 간결·정확히 답하라. '
    + '데이터에 없으면 "데이터에 없음"이라고 답하고 추측하지 마라. 숫자는 데이터 그대로 인용하라.\n\n'
    + '=== 시트 데이터 ===\n' + ctx + '\n\n=== 질문 ===\n' + q;
  const ans = _geminiAsk_(prompt);
  ui.alert('질문: ' + q + '\n\n' + (ans || '(응답 실패 — GEMINI_API_KEY/네트워크 확인. 로그 참조.)'));
}

function buildNlQueryMenu_(ui) {
  ui.createMenu('데이터 질문')
    .addItem('💬 광고 데이터에 질문하기', 'askSheetQuestion')
    .addToUi();
}
