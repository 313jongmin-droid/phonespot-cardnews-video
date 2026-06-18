/**
 * 크리에이티브 인사이트 (STEP4) — 2026-06-18 신설
 *  - P3-8 A/B 자동평가: 메타_소재 성과로 승자/손실 소재 랭킹 → '소재_성과' 시트 + 텔레그램
 *  - P3-9 벤치마크 자동확장: syncMetaAdLibrary 를 BENCHMARK_TERMS(Script Property)로 주기 수집
 *  - P3-10 폐루프(데이터측): 소재_성과 시트가 생성기 참고용 고성과 패턴 제공
 *    ※ generator.html 이 이 시트를 직접 읽게 하는 '완전 연결'은 별도 작업(데이터 계약 변경이라 신중)
 *  generator.html 미접촉. 텔레그램은 alerts.js tgSend_ 재사용(없으면 스킵).
 */

var CI_CREATIVES_SHEET = '메타_소재';
var CI_RESULT_SHEET = '소재_성과';

// ============ P3-8 A/B 자동평가 ============
// 메타_소재(노출/클릭/지출/CTR) → CTR 기준 승자/손실 랭킹. 노출 500↑만(노이즈 제거).
function analyzeCreativePerformance() {
  const ss = SpreadsheetApp.getActive();
  const src = ss.getSheetByName(CI_CREATIVES_SHEET);
  const ui = (function () { try { return SpreadsheetApp.getUi(); } catch (e) { return null; } })();
  if (!src || src.getLastRow() < 3) { if (ui) ui.alert('메타_소재 시트 비어있음. 🎨 광고소재 갱신 먼저.'); return; }
  // 데이터 = 3행부터(1=배너, 2=헤더). 컬럼: 2광고명 3상태 4헤드라인 7노출 8클릭 9지출 10CTR 11CPC 16카테고리
  const n = src.getLastRow() - 2;
  const v = src.getRange(3, 1, n, 16).getValues();
  const rows = [];
  v.forEach(function (r) {
    const name = String(r[1] || '').trim();
    const head = String(r[3] || '').trim();
    const imp = Number(r[6]) || 0;
    const clk = Number(r[7]) || 0;
    const spend = Number(r[8]) || 0;
    let ctr = Number(r[9]) || 0;
    if (!name || imp < 500) return;       // 노이즈 제거
    if (!ctr && imp > 0) ctr = clk / imp * 100;
    rows.push({ name: name, head: head, imp: imp, clk: clk, spend: spend, ctr: ctr, cpc: Number(r[10]) || 0 });
  });
  if (!rows.length) { if (ui) ui.alert('평가할 소재 없음(노출 500↑ 기준).'); return; }

  const byCtr = rows.slice().sort(function (a, b) { return b.ctr - a.ctr; });
  const winners = byCtr.slice(0, 5);
  // 손실 = 지출 1만↑ 중 CTR 하위
  const losers = rows.filter(function (r) { return r.spend >= 10000; }).sort(function (a, b) { return a.ctr - b.ctr; }).slice(0, 3);

  // 결과 시트
  let out = ss.getSheetByName(CI_RESULT_SHEET);
  if (!out) out = ss.insertSheet(CI_RESULT_SHEET);
  out.clear();
  out.getRange(1, 1).setValue('🏆 소재 성과 랭킹 (CTR 기준, 노출 500↑) — ' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm'))
    .setFontWeight('bold');
  const header = ['구분', '순위', '광고명', '헤드라인', '노출', '클릭', '지출', 'CTR(%)', 'CPC'];
  out.getRange(3, 1, 1, header.length).setValues([header]).setFontWeight('bold').setBackground('#1F4E78').setFontColor('#FFFFFF');
  let row = 4;
  winners.forEach(function (r, i) {
    out.getRange(row++, 1, 1, header.length).setValues([['🏆 승자', i + 1, r.name, r.head, r.imp, r.clk, r.spend, Math.round(r.ctr * 100) / 100, r.cpc]]);
  });
  row++;
  losers.forEach(function (r, i) {
    out.getRange(row++, 1, 1, header.length).setValues([['⚠️ 손실', i + 1, r.name, r.head, r.imp, r.clk, r.spend, Math.round(r.ctr * 100) / 100, r.cpc]]);
  });
  out.autoResizeColumns(1, header.length);

  // 텔레그램 요약
  const top = winners.slice(0, 3).map(function (r, i) { return (i + 1) + '. ' + r.name + ' (CTR ' + (Math.round(r.ctr * 100) / 100) + '%)'; }).join('\n');
  const bot = losers.slice(0, 2).map(function (r) { return '· ' + r.name + ' (CTR ' + (Math.round(r.ctr * 100) / 100) + '%, 지출 ' + r.spend.toLocaleString() + ')'; }).join('\n');
  if (typeof tgSend_ === 'function') {
    tgSend_('🎨 소재 A/B 평가\n\n[승자 TOP3]\n' + top + (bot ? ('\n\n[손실 의심]\n' + bot) : ''));
  }
  if (typeof logSync_ === 'function') logSync_('analyzeCreativePerformance', '승자 ' + winners.length + ' / 손실 ' + losers.length);
  if (ui) ui.alert('✅ 소재_성과 시트 갱신\n승자 ' + winners.length + ' / 손실 ' + losers.length + '건');
}

// ============ P3-9 벤치마크 자동확장 ============
// Script Property BENCHMARK_TERMS (콤마 구분). 미설정 시 기본 키워드.
function syncBenchmarkScheduled() {
  const props = PropertiesService.getScriptProperties();
  const raw = props.getProperty('BENCHMARK_TERMS') || '휴대폰성지,갤럭시 S26,자급제,핸드폰 싸게';
  const terms = raw.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
  let ok = 0, fail = 0;
  terms.forEach(function (t) {
    try {
      if (typeof syncMetaAdLibrary === 'function') { syncMetaAdLibrary(t, 'BM'); ok++; Utilities.sleep(1500); }
    } catch (e) { fail++; Logger.log('벤치마크 ' + t + ' 실패: ' + e.message); }
  });
  const msg = '벤치마크 자동수집 ' + ok + '개 키워드 (실패 ' + fail + ')';
  if (typeof logSync_ === 'function') logSync_('syncBenchmarkScheduled', msg);
  Logger.log(msg);
}

function setupBenchmarkTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'syncBenchmarkScheduled') ScriptApp.deleteTrigger(t);
  });
  // 주 1회(매주 월 04:00) — Ad Library는 매일 안 바뀜
  ScriptApp.newTrigger('syncBenchmarkScheduled').timeBased().onWeekDay(ScriptApp.WeekDay.MONDAY).atHour(4).create();
  SpreadsheetApp.getUi().alert('✅ 벤치마크 자동수집 트리거 등록 (매주 월 04:00).\n\n검색어 변경 = Script Property BENCHMARK_TERMS (콤마 구분).');
}

// ============ 메뉴 ============
function buildCreativeInsightsMenu_(ui) {
  ui.createMenu('🎨 소재 인사이트')
    .addItem('🏆 소재 A/B 평가 지금 실행', 'analyzeCreativePerformance')
    .addSeparator()
    .addItem('🔍 벤치마크 자동수집 지금 실행', 'syncBenchmarkScheduled')
    .addItem('⏰ 벤치마크 주간 트리거 (월 04:00)', 'setupBenchmarkTrigger')
    .addToUi();
}
