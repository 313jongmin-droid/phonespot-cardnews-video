/**
 * 메타_인사이트 시트 출력 (CLAUDE.md STEP 1 #8 해결).
 *
 * 배경: generateMetaInsightsMarkdown()는 Drive MD로만 저장 → 카드뉴스 세션이
 * "메타_인사이트 시트"를 Read하려면 시트가 필요(STEP 1 #8 "★ 시트 추가 필요").
 *
 * 설계: 기존 85KB meta-sync.js를 안 건드림. clasp 프로젝트의 별도 .js 파일로 추가.
 * Apps Script는 파일 간 전역 스코프 공유 → meta-sync.js의 상수
 * (SHEET_META_CREATIVES, SHEET_META_INTEGRATED, EVAL_*)를 그대로 참조.
 * 상수 미정의 시 typeof 가드로 안전 폴백.
 *
 * 배포: git add apps_script/meta-insights-sheet.js → commit → push
 *   → GitHub Actions clasp push --force 로 자동 배포.
 * 활성화(1회): Apps Script 편집기에서 setupMetaInsightsSheetTrigger() 실행
 *   + writeMetaInsightsSheet() 1회 실행해 시트 즉시 생성.
 *
 * 카드뉴스 활용: 매 캡션 사이클에 '메타_인사이트' 시트 Read → Top 헤드라인 패턴
 *   + 광고그룹 효율을 짧은 채널 후킹 reference로.
 */

var META_INSIGHTS_SHEET = '메타_인사이트';

function _miConst(name, fallback) {
  try { return eval(name); } catch (e) { return fallback; }
}

function writeMetaInsightsSheet() {
  var ss = SpreadsheetApp.getActive();
  var sCreatives = _miConst('SHEET_META_CREATIVES', '메타_소재');
  var sIntegrated = _miConst('SHEET_META_INTEGRATED', '메타_통합');
  var minSpend = _miConst('EVAL_MIN_SPEND', 0);
  var ctrGood = _miConst('EVAL_CTR_GOOD', 7);

  var cSheet = ss.getSheetByName(sCreatives);
  if (!cSheet || cSheet.getLastRow() < 3) {
    Logger.log('메타_소재 데이터 없음 → 종료');
    return;
  }

  // 메타_소재: 3행~, 1~15열 (meta-sync.js generateMetaInsightsMarkdown 동일 매핑)
  var cData = cSheet.getRange(3, 1, cSheet.getLastRow() - 2, 15).getValues();
  var ads = cData.map(function (row) {
    return {
      name: String(row[1] || '').trim(),
      headline: String(row[3] || '').trim(),
      body: String(row[4] || '').trim(),
      spend: Number(row[8]) || 0,
      ctr: Number(row[9]) || 0,
      cpc: Number(row[10]) || 0
    };
  }).filter(function (a) {
    return a.headline && a.headline !== '-' && a.spend >= minSpend;
  });

  if (ads.length === 0) {
    Logger.log('유효 광고 없음 → 종료');
    return;
  }

  var avgCTR = ads.reduce(function (s, a) { return s + a.ctr; }, 0) / ads.length;
  var cpcS = ads.filter(function (a) { return a.cpc > 0; });
  var avgCPC = cpcS.length ? cpcS.reduce(function (s, a) { return s + a.cpc; }, 0) / cpcS.length : 0;
  var topByCTR = ads.slice().sort(function (a, b) { return b.ctr - a.ctr; }).slice(0, 15);

  // 광고그룹 효율 (메타_통합: E광고그룹명 / H지출 / K세션 / L카톡클릭)
  var topCamp = [];
  var iSheet = ss.getSheetByName(sIntegrated);
  if (iSheet && iSheet.getLastRow() >= 2) {
    var iData = iSheet.getRange(2, 1, iSheet.getLastRow() - 1, 16).getValues();
    var byC = {};
    iData.forEach(function (row) {
      var name = String(row[4] || '').trim();
      if (!name) return;
      if (!byC[name]) byC[name] = { name: name, spend: 0, kakao: 0, sess: 0 };
      byC[name].spend += Number(row[7]) || 0;
      byC[name].kakao += Number(row[11]) || 0;
      byC[name].sess += Number(row[10]) || 0;
    });
    topCamp = Object.keys(byC).map(function (k) {
      var c = byC[k];
      return {
        name: c.name, spend: c.spend, kakao: c.kakao,
        convRate: c.sess > 0 ? c.kakao / c.sess : 0,
        costPerKakao: c.kakao > 0 ? c.spend / c.kakao : 0
      };
    }).filter(function (c) { return c.spend > 0 && c.kakao > 0; })
      .sort(function (a, b) { return a.costPerKakao - b.costPerKakao; })
      .slice(0, 10);
  }

  // ---- 시트 작성 ----
  var sh = ss.getSheetByName(META_INSIGHTS_SHEET);
  if (!sh) sh = ss.insertSheet(META_INSIGHTS_SHEET);
  sh.clear();

  var rows = [];
  var now = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  rows.push(['메타 인사이트 (자동 생성)', now, '', '']);
  rows.push(['총 광고수', ads.length, '평균 CTR', avgCTR.toFixed(2) + '%']);
  rows.push(['평균 CPC', Math.round(avgCPC) + '원', '우수 기준 CTR', ctrGood + '%']);
  rows.push(['', '', '', '']);

  rows.push(['▼ Top 헤드라인 (CTR순)', '', '', '']);
  rows.push(['헤드라인', 'CTR%', 'CPC(원)', '지출(원)']);
  topByCTR.forEach(function (a) {
    rows.push([a.headline, a.ctr, Math.round(a.cpc), Math.round(a.spend)]);
  });
  rows.push(['', '', '', '']);

  rows.push(['▼ 광고그룹 효율 (카톡당 비용 낮은순)', '', '', '']);
  rows.push(['광고그룹', '카톡당(원)', '전환율%', '지출(원)']);
  topCamp.forEach(function (c) {
    rows.push([c.name, Math.round(c.costPerKakao), (c.convRate * 100).toFixed(2), Math.round(c.spend)]);
  });

  sh.getRange(1, 1, rows.length, 4).setValues(rows);
  sh.setFrozenRows(1);
  sh.getRange(1, 1, 1, 4).setFontWeight('bold');

  if (typeof logSync_ === 'function') {
    logSync_('writeMetaInsightsSheet', 'OK (' + ads.length + ' ads / ' + topCamp.length + ' 광고그룹)');
  }
  Logger.log('메타_인사이트 시트 작성 완료');
}

/** 매일 01:50 자동 갱신 트리거 등록 (1회 실행). 중복 제거 후 재등록. */
function setupMetaInsightsSheetTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'writeMetaInsightsSheet') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('writeMetaInsightsSheet').timeBased().everyDays(1).atHour(1).nearMinute(50).create();
  Logger.log('트리거 등록: writeMetaInsightsSheet 매일 01:50');
}
