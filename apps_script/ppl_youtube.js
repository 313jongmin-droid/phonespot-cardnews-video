/**
 * ppl_youtube.js — 유튜브 PPL 협찬 발굴 (카테고리 분류 + 설정 탭 + 재실행형 보강)
 * 정본 가이드: _docs/PPL_YOUTUBE_OUTREACH_GUIDE.md
 *
 * ★ 사실 한계: YouTube/Apify는 타 채널 시청자 연령·성별 미제공(채널 주인만 조회).
 *   → 30~50 남성은 직접 필터 불가. 카테고리로 근사 + 회신율 집계로 정밀화.
 *
 * 편집 탭 2개 (코드 push 없이 종민이 조정):
 *   PPL_설정      — 정렬/기간/길이/구독자범위/최소조건/건수/배치 등 전체 옵션
 *   PPL_카테고리  — 카테고리·검색키워드·가중치·사용
 *
 * 실행 흐름 (Apps Script 6분 제한 때문에 2단계 분리, 각 단계 1 Apify 호출):
 *   1) ⚡ 빠른 발굴 / 🔍 카테고리 지정  → Pass1 검색 → 후보를 PPL_후보 탭에 적재(상태=대기)
 *   2) 🔄 보강 이어서 진행            → 대기 후보를 배치로 Pass2 보강 → 필터/점수 → 유튜브_협찬발굴 기록
 *      남은 게 있으면 다시 클릭(재실행 가능). 3) ✍️ 초안 재생성 4) 📊 카테고리별 집계
 *
 * Apify: streamers/youtube-scraper, 비동기 폴링. 토큰 APIFY_TOKEN(getApifyToken_). $0.005/결과.
 * 발송은 수동(유튜브 ToS). 자동 DM 금지.
 */

var PPL_ACTOR_PATH  = 'streamers~youtube-scraper';
var PPL_SHEET       = '유튜브_협찬발굴';
var PPL_CAT_SHEET   = 'PPL_카테고리';
var PPL_CFG_SHEET   = 'PPL_설정';
var PPL_STAGE_SHEET = 'PPL_후보';
var PPL_SUM_SHEET   = 'PPL_카테고리_집계';
var PPL_GEMINI_MODEL = 'gemini-2.5-flash';
var PPL_BUDGET = 240;   // Apify 폴링 예산(초). 단계당 1회 호출이라 6분 내 여유.

// PPL_설정 기본값 — (키, 값, 설명). 탭 없으면 이걸로 생성.
var PPL_SEED_CONFIG = [
  ['정렬', 'date', 'relevance(대형편향) / date(최신·소형 유리, 권장) / views / rating'],
  ['기간필터', 'month', '빈칸(전체) / week / month / year — 활성 채널만 잡음'],
  ['영상길이', '', '빈칸(전체) / under4 / between420 / plus20 — 숏츠 양산 채널 배제하려면 plus20'],
  ['키워드당_영상수', 20, 'Pass1 검색 시 키워드당 수집 영상 수 (많을수록 후보↑, 비용↑)'],
  ['최대_검색키워드수', 12, '1회 발굴에 쓸 키워드 상한'],
  ['구독자_최소', 5000, '이 미만 제외'],
  ['구독자_최대', 300000, '이 이상 제외'],
  ['보강_배치크기', 30, '🔄 보강 1회 클릭당 처리할 후보 수 (6분 제한 방어)'],
  ['보강_총상한', 100, '한 발굴 사이클에서 보강할 최대 후보 수'],
  ['최종_건수', 30, '시트에 남길 최대 채널 수 (점수 상위)'],
  ['최근업로드_N일이내', 0, '0=미적용. 예:60 → 최근 60일 내 업로드만'],
  ['최소_평균조회수', 0, '0=미적용'],
  ['최소_영상수', 0, '0=미적용'],
  ['이메일있는것만', 'N', 'Y면 설명란 이메일 파싱된 채널만 남김'],
  ['크리에이터만', 'Y', 'Y면 판매점/쇼핑몰·기관 채널 제외'],
  ['국내채널만', 'Y', 'Y면 한글/한국 채널만']
];

var PPL_SEED_TAXONOMY = [
  ['자동차',       '자동차 리뷰,신차 시승기,국산차 리뷰,수입차 리뷰,중고차 구매', 2, 'Y'],
  ['IT·가젯',      'IT 리뷰,스마트폰 리뷰,노트북 리뷰,가젯 리뷰,PC 견적',        2, 'Y'],
  ['자급제·통신',   '자급제 휴대폰,통신비 절약,알뜰폰 요금제',                     1, 'Y'],
  ['경제·재테크',   '재테크,주식 투자,부동산 투자,경제 뉴스,자산관리',            2, 'Y'],
  ['시사·지식',    '시사 브리핑,뉴스 해설,역사 이야기,과학 지식',                1, 'Y'],
  ['취미·아웃도어', '낚시,캠핑 차박,골프 레슨,등산,밀리터리',                     2, 'Y'],
  ['스포츠',       '축구 분석,야구 하이라이트,격투기,헬스 운동',                 1, 'Y']
];

var PPL_SHOP_TERMS = ['대리점','가맹점','판매왕','판매점','판매 전문','판매전문','공식몰','쇼핑몰','스토어','최저가로','도매','좌표','개통문의','개통 문의'];
var PPL_ORG_TERMS  = ['위원회','협회','공식 유튜브','공식유튜브','방송통신','진흥원','공단','정부기관'];

var PPL_OFFER_TEMPLATE =
  '안녕하세요, 지역 휴대폰 성지 \'폰스팟\'입니다.\n' +
  '채널을 잘 보고 있어 협찬을 제안드립니다.\n\n' +
  '[협찬 조건]\n' +
  '· 제품/기기 협찬 또는 원고료 (영상 규모·형식에 따라 협의)\n' +
  '· 매장 개통/시세 관련 콘텐츠 소재 제공\n' +
  '· 진행 기간·횟수 협의\n\n' +
  '조건·단가는 채널 상황에 맞춰 조율 가능합니다. 관심 있으시면 회신 부탁드립니다.\n' +
  '— 폰스팟 드림';

function pplUi_() { try { return SpreadsheetApp.getUi(); } catch (e) { return null; } }
function pplAlert_(m) { var u = pplUi_(); if (u) u.alert(m); }

// ───────────────────────── 메뉴 ─────────────────────────
function buildPplYoutubeMenu_(ui) {
  ui.createMenu('🎯 유튜브 협찬발굴')
    .addItem('⚡ 1단계: 빠른 발굴 (전체 카테고리)', 'pplRunDefault')
    .addItem('🔍 1단계: 카테고리 지정 발굴', 'pplPromptDiscovery')
    .addItem('🔄 2단계: 보강 이어서 진행', 'pplEnrichNext')
    .addSeparator()
    .addItem('✍️ 3단계: 초안만 재생성', 'pplRegenerateDrafts')
    .addItem('📊 카테고리별 집계', 'pplCategorySummary')
    .addSeparator()
    .addItem('⚙️ 설정 탭 열기', 'pplOpenConfig')
    .addItem('🗂 카테고리 탭 열기', 'pplOpenTaxonomy')
    .addItem('📂 발굴 시트 열기', 'pplOpenSheet')
    .addToUi();
}

// ───────────────────────── 설정 탭 ─────────────────────────
function pplCreateConfigSheet_() {
  var ss = SpreadsheetApp.getActive(), sh = ss.insertSheet(PPL_CFG_SHEET);
  sh.appendRow(['PPL 발굴 설정 — 값(B열)만 고치면 다음 실행에 즉시 반영']);
  sh.appendRow(['설정 키', '값', '설명']);
  sh.getRange(2, 1, 1, 3).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
  PPL_SEED_CONFIG.forEach(function (r) { sh.appendRow(r); });
  sh.setColumnWidth(1, 180); sh.setColumnWidth(2, 110); sh.setColumnWidth(3, 520); sh.setFrozenRows(2);
  return sh;
}
function pplGetConfig_() {
  var sh = SpreadsheetApp.getActive().getSheetByName(PPL_CFG_SHEET);
  if (!sh) sh = pplCreateConfigSheet_();
  var cfg = {};
  PPL_SEED_CONFIG.forEach(function (r) { cfg[r[0]] = r[1]; });   // 기본값
  if (sh.getLastRow() >= 3) {
    sh.getRange(3, 1, sh.getLastRow() - 2, 2).getValues().forEach(function (r) {
      var k = String(r[0] || '').trim(); if (k) cfg[k] = r[1];
    });
  }
  return cfg;
}
function pplNum_(v, d) { var n = Number(v); return isNaN(n) ? d : n; }
function pplYes_(v) { return String(v || '').trim().toUpperCase() === 'Y'; }
function pplOpenConfig() { var sh = SpreadsheetApp.getActive().getSheetByName(PPL_CFG_SHEET) || pplCreateConfigSheet_(); SpreadsheetApp.getActive().setActiveSheet(sh); }

// ───────────────────────── 카테고리 탭 ─────────────────────────
function pplCreateTaxonomySheet_() {
  var ss = SpreadsheetApp.getActive(), sh = ss.insertSheet(PPL_CAT_SHEET);
  sh.appendRow(['PPL 카테고리 분류 — 여기 고치면 발굴에 즉시 반영']);
  sh.appendRow(['카테고리', '검색 키워드(콤마 구분)', '남성30-50 가중치(0~2)', '사용(Y/N)']);
  sh.getRange(2, 1, 1, 4).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
  PPL_SEED_TAXONOMY.forEach(function (r) { sh.appendRow(r); });
  sh.setColumnWidth(1, 130); sh.setColumnWidth(2, 460); sh.setColumnWidth(3, 160); sh.setFrozenRows(2);
  return sh;
}
function pplGetTaxonomy_() {
  var sh = SpreadsheetApp.getActive().getSheetByName(PPL_CAT_SHEET); if (!sh) sh = pplCreateTaxonomySheet_();
  if (sh.getLastRow() < 3) return [];
  var out = [];
  sh.getRange(3, 1, sh.getLastRow() - 2, 4).getValues().forEach(function (r) {
    var cat = String(r[0] || '').trim(); if (!cat) return;
    if (String(r[3] || 'Y').trim().toUpperCase() === 'N') return;
    var kws = String(r[1] || '').split(',').map(function (x) { return x.trim(); }).filter(String);
    var w = parseFloat(r[2]); if (isNaN(w)) w = 1;
    if (kws.length) out.push({ category: cat, keywords: kws, weight: w });
  });
  return out;
}
function pplOpenTaxonomy() { var sh = SpreadsheetApp.getActive().getSheetByName(PPL_CAT_SHEET) || pplCreateTaxonomySheet_(); SpreadsheetApp.getActive().setActiveSheet(sh); }

// ───────────────────────── 1단계: 검색 → 후보 적재 ─────────────────────────
function pplRunDefault() {
  var tax = pplGetTaxonomy_(); if (!tax.length) { pplAlert_('PPL_카테고리 탭에 사용(Y) 카테고리가 없습니다.'); return; }
  var pairs = [];
  tax.forEach(function (c) { c.keywords.slice(0, 2).forEach(function (k) { pairs.push({ kw: k, category: c.category, weight: c.weight }); }); });
  pplDiscoverToStaging_(pairs);
}
function pplPromptDiscovery() {
  var ui = SpreadsheetApp.getUi(), tax = pplGetTaxonomy_();
  var r1 = ui.prompt('🔍 카테고리 지정 발굴', '카테고리명 하나 입력(전체=빈칸):\n' + tax.map(function (c) { return c.category; }).join(' / ') +
    '\n\n※ 정렬·기간·구독자범위 등 조건은 PPL_설정 탭에서 조정', ui.ButtonSet.OK_CANCEL);
  if (r1.getSelectedButton() !== ui.Button.OK) return;
  var pick = (r1.getResponseText() || '').trim(), pairs = [];
  if (pick) {
    var c = null; for (var i = 0; i < tax.length; i++) if (tax[i].category.indexOf(pick) >= 0 || pick.indexOf(tax[i].category) >= 0) { c = tax[i]; break; }
    if (!c) { ui.alert('일치 카테고리 없음: ' + pick); return; }
    c.keywords.forEach(function (k) { pairs.push({ kw: k, category: c.category, weight: c.weight }); });
  } else {
    tax.forEach(function (cc) { cc.keywords.slice(0, 2).forEach(function (k) { pairs.push({ kw: k, category: cc.category, weight: cc.weight }); }); });
  }
  pplDiscoverToStaging_(pairs);
}

function pplDiscoverToStaging_(kwPairs) {
  var cfg = pplGetConfig_();
  try {
    kwPairs = kwPairs.slice(0, pplNum_(cfg['최대_검색키워드수'], 12));
    var keywords = kwPairs.map(function (p) { return p.kw; });
    var kwMeta = {}; kwPairs.forEach(function (p) { kwMeta[p.kw] = p; });

    var input = {
      searchQueries: keywords,
      maxResults: pplNum_(cfg['키워드당_영상수'], 20),
      maxResultsShorts: 0, maxResultStreams: 0,
      sortingOrder: String(cfg['정렬'] || 'date')
    };
    var df = String(cfg['기간필터'] || '').trim(); if (df) input.dateFilter = df;
    var lf = String(cfg['영상길이'] || '').trim(); if (lf) input.lengthFilter = lf;

    var items = pplFetchApify_(input, PPL_BUDGET);
    var map = {};
    (items || []).forEach(function (it) {
      if (!it || it.error || !it.channelUrl) return;
      var key = pplUrlKey_(it.channelUrl);
      if (!map[key]) map[key] = { url: it.channelUrl, name: it.channelName || '', kws: {}, cats: {} };
      var kw = pplKeywordFromSearchUrl_(it.fromYTUrl);
      if (kw && kwMeta[kw]) { map[key].kws[kw] = 1; map[key].cats[kwMeta[kw].category] = (map[key].cats[kwMeta[kw].category] || 0) + 1; }
    });

    // 이미 본선 시트에 있는 채널 제외
    var done = pplExistingChannelKeys_();
    var stage = pplGetOrCreateStage_();
    var already = {};
    if (stage.getLastRow() >= 3) stage.getRange(3, 1, stage.getLastRow() - 2, 1).getValues().forEach(function (r) { if (r[0]) already[pplUrlKey_(r[0])] = 1; });

    var rows = [], cap = pplNum_(cfg['보강_총상한'], 100);
    Object.keys(map).forEach(function (k) {
      if (rows.length >= cap) return;
      if (already[k] || done[k]) return;
      var m = map[k];
      var cat = pplPrimaryCategory_(m.cats);
      var w = 1, ks = Object.keys(kwMeta);
      for (var i = 0; i < ks.length; i++) if (kwMeta[ks[i]].category === cat) { w = kwMeta[ks[i]].weight; break; }
      rows.push([m.url, m.name, Object.keys(m.kws).join(', '), cat, w, '대기', '']);
    });
    if (rows.length) stage.getRange(stage.getLastRow() + 1, 1, rows.length, 7).setValues(rows);

    pplAlert_('✅ 1단계 발굴 완료\n\n' +
      '검색 키워드: ' + keywords.length + '개 (정렬=' + input.sortingOrder + (df ? ', 기간=' + df : '') + (lf ? ', 길이=' + lf : '') + ')\n' +
      '수집 영상에서 유니크 채널: ' + Object.keys(map).length + '\n' +
      '신규 후보 적재: ' + rows.length + ' (PPL_후보 탭)\n\n' +
      '다음: 🔄 2단계 보강 이어서 진행 클릭 (배치 ' + pplNum_(cfg['보강_배치크기'], 30) + '개씩, 남으면 반복 클릭)');
    try { logSync_('pplDiscover', keywords.join('|') + ' -> stage ' + rows.length); } catch (e) {}
  } catch (e) {
    pplAlert_('❌ 1단계 실패: ' + e.message);
    throw e;
  }
}

// ───────────────────────── 2단계: 보강(배치, 재실행 가능) ─────────────────────────
function pplEnrichNext() {
  var cfg = pplGetConfig_();
  var stage = pplGetOrCreateStage_();
  if (stage.getLastRow() < 3) { pplAlert_('후보가 없습니다. 먼저 1단계 발굴을 실행하세요.'); return; }
  var n = stage.getLastRow() - 2;
  var vals = stage.getRange(3, 1, n, 7).getValues();
  var batchSize = pplNum_(cfg['보강_배치크기'], 30);
  var idxs = [];
  for (var i = 0; i < vals.length && idxs.length < batchSize; i++) if (String(vals[i][5]) === '대기') idxs.push(i);
  if (!idxs.length) { pplAlert_('대기 중인 후보가 없습니다. (모두 처리됨)\n새로 발굴하려면 1단계를 실행하세요.'); return; }

  try {
    var urls = idxs.map(function (i) { return vals[i][0]; });
    var enriched = pplEnrichChannels_(urls);
    var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
    var subMin = pplNum_(cfg['구독자_최소'], 5000), subMax = pplNum_(cfg['구독자_최대'], 300000);
    var minAvg = pplNum_(cfg['최소_평균조회수'], 0), minVid = pplNum_(cfg['최소_영상수'], 0);
    var recentDays = pplNum_(cfg['최근업로드_N일이내'], 0);
    var emailOnly = pplYes_(cfg['이메일있는것만']), creatorOnly = pplYes_(cfg['크리에이터만']), krOnly = pplYes_(cfg['국내채널만']);

    var rows = [], reasons = { 보강실패: 0, 구독자: 0, 크리에이터: 0, 국내: 0, 활성: 0, 조회수: 0, 영상수: 0, 이메일: 0 };
    idxs.forEach(function (i) {
      var url = vals[i][0], info = enriched[pplUrlKey_(url)];
      var mark = '완료';
      if (!info) { reasons.보강실패++; vals[i][5] = '보강실패'; vals[i][6] = today; return; }
      var subs = info.numberOfSubscribers || 0;
      var tv = pplToNum_(info.channelTotalViews), nv = info.channelTotalVideos || 0;
      var avg = nv ? Math.round(tv / nv) : 0;
      var email = pplParseEmail_(info.channelDescription);

      if (subs < subMin || subs > subMax) { reasons.구독자++; mark = '제외:구독자'; }
      else if (creatorOnly && pplChannelType_(info) !== 'creator') { reasons.크리에이터++; mark = '제외:비크리에이터'; }
      else if (krOnly && !pplIsKorean_(info)) { reasons.국내++; mark = '제외:해외'; }
      else if (recentDays > 0 && !pplRecentWithin_(info.lastUploadRaw, recentDays)) { reasons.활성++; mark = '제외:비활성'; }
      else if (minAvg > 0 && avg < minAvg) { reasons.조회수++; mark = '제외:평균조회수'; }
      else if (minVid > 0 && nv < minVid) { reasons.영상수++; mark = '제외:영상수'; }
      else if (emailOnly && !email) { reasons.이메일++; mark = '제외:이메일없음'; }

      vals[i][5] = mark; vals[i][6] = today;
      if (mark !== '완료') return;

      var kwList = String(vals[i][2] || '').split(',').map(function (x) { return x.trim(); }).filter(String);
      var sc = pplScoreChannel_(info, kwList);
      sc.score = Math.min(10, sc.score + Math.round(pplNum_(vals[i][4], 1)));
      if (pplWantsSponsor_(info)) sc.score = Math.min(10, sc.score + 2);
      rows.push({
        channelId: pplChannelId_(url, info), channelName: info.channelName || vals[i][1] || '',
        subs: subs, totalViews: tv, totalVideos: nv, avgViews: avg,
        matchedKw: vals[i][2], lastUpload: info.lastUploadRaw || '',
        descExcerpt: (info.channelDescription || '').slice(0, 200),
        externalLink: info.channelUrl || url, email: email,
        scaleLabel: pplScaleLabelForSubs_(subs), score: sc.score,
        grade: sc.score >= 7 ? '★★★' : (sc.score >= 4 ? '★★' : '★'),
        draft: '', status: '발굴', foundDate: today, category: vals[i][3] || '(미분류)'
      });
    });

    stage.getRange(3, 1, n, 7).setValues(vals);
    rows.sort(function (a, b) { return b.score - a.score; });
    var limit = pplNum_(cfg['최종_건수'], 30);
    var cur = pplCurrentRowCount_();
    if (cur + rows.length > limit) rows = rows.slice(0, Math.max(0, limit - cur));
    var res = pplWriteSheet_(rows);

    var remain = 0; vals.forEach(function (r) { if (String(r[5]) === '대기') remain++; });
    pplAlert_('🔄 2단계 보강 완료 (이번 배치 ' + idxs.length + '개)\n\n' +
      '시트 추가: ' + res.added + ' (중복 ' + res.skipped + ')\n' +
      '탈락 사유 — 구독자범위 ' + reasons.구독자 + ' / 비크리에이터 ' + reasons.크리에이터 + ' / 해외 ' + reasons.국내 +
      ' / 비활성 ' + reasons.활성 + ' / 평균조회수 ' + reasons.조회수 + ' / 영상수 ' + reasons.영상수 +
      ' / 이메일없음 ' + reasons.이메일 + ' / 보강실패 ' + reasons.보강실패 + '\n' +
      '남은 대기 후보: ' + remain + (remain ? '\n\n→ 🔄 보강 이어서 진행 다시 클릭' : '\n\n→ ✍️ 초안만 재생성으로 진행') +
      '\n\n※ 탈락이 많으면 PPL_설정 탭에서 구독자 범위·조건을 완화하세요.');
    try { logSync_('pplEnrichNext', 'batch ' + idxs.length + ' -> ' + res.added); } catch (e) {}
  } catch (e) {
    pplAlert_('❌ 2단계 실패: ' + e.message);
    throw e;
  }
}

// ───────────────────────── 후보(스테이징) 탭 ─────────────────────────
function pplGetOrCreateStage_() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName(PPL_STAGE_SHEET);
  if (!sh) {
    sh = ss.insertSheet(PPL_STAGE_SHEET);
    sh.appendRow(['PPL 후보 (1단계 검색 결과 → 2단계에서 배치 보강)']);
    sh.appendRow(['채널URL', '채널명', '매칭 키워드', '카테고리', '가중치', '상태', '처리일']);
    sh.getRange(2, 1, 1, 7).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
    sh.setColumnWidth(1, 320); sh.setColumnWidth(3, 220); sh.setFrozenRows(2);
  }
  return sh;
}
function pplExistingChannelKeys_() {
  var sh = SpreadsheetApp.getActive().getSheetByName(PPL_SHEET), out = {};
  if (!sh || sh.getLastRow() < 3) return out;
  sh.getRange(3, 1, sh.getLastRow() - 2, 10).getValues().forEach(function (r) {
    if (r[9]) out[pplUrlKey_(String(r[9]))] = 1;
    if (r[0]) out['ch:' + String(r[0]).toLowerCase()] = 1;
  });
  return out;
}
function pplCurrentRowCount_() { var sh = SpreadsheetApp.getActive().getSheetByName(PPL_SHEET); return (!sh || sh.getLastRow() < 3) ? 0 : sh.getLastRow() - 2; }

// ───────────────────────── Apify ─────────────────────────
function pplFetchApify_(input, budgetSec) {
  var token = getApifyToken_();
  var startRes = UrlFetchApp.fetch('https://api.apify.com/v2/acts/' + PPL_ACTOR_PATH + '/runs?token=' + token, {
    method: 'post', contentType: 'application/json', payload: JSON.stringify(input), muteHttpExceptions: true
  });
  var sc = startRes.getResponseCode();
  if (sc !== 200 && sc !== 201) throw new Error('Apify 시작 실패 ' + sc + ': ' + startRes.getContentText().slice(0, 300));
  var run = JSON.parse(startRes.getContentText()).data;
  var runId = run.id, dsId = run.defaultDatasetId, status = run.status;
  var budget = (budgetSec || 200) * 1000, waited = 0, step = 5000;
  while (waited < budget && status !== 'SUCCEEDED') {
    if (status === 'FAILED' || status === 'ABORTED' || status === 'TIMED-OUT') throw new Error('Apify 실행 ' + status + ' (runId ' + runId + ')');
    Utilities.sleep(step); waited += step;
    var pr = UrlFetchApp.fetch('https://api.apify.com/v2/actor-runs/' + runId + '?token=' + token, { muteHttpExceptions: true });
    if (pr.getResponseCode() === 200) { var d = JSON.parse(pr.getContentText()).data; status = d.status; dsId = d.defaultDatasetId || dsId; }
  }
  if (status !== 'SUCCEEDED') throw new Error('Apify 시간초과(' + Math.round(budget / 1000) + 's, status=' + status + '). PPL_설정에서 키워드당_영상수/배치크기를 줄이세요.');
  var itRes = UrlFetchApp.fetch('https://api.apify.com/v2/datasets/' + dsId + '/items?clean=true&token=' + token, { muteHttpExceptions: true });
  if (itRes.getResponseCode() !== 200) throw new Error('Apify 데이터셋 실패 ' + itRes.getResponseCode());
  return JSON.parse(itRes.getContentText());
}
function pplEnrichChannels_(channelUrls) {
  var items = pplFetchApify_({
    startUrls: channelUrls.map(function (u) { return { url: pplChannelVideosUrl_(u) }; }),
    maxResults: 1, maxResultsShorts: 0, maxResultStreams: 0, sortVideosBy: 'NEWEST'
  }, PPL_BUDGET);
  var out = {};
  (items || []).forEach(function (it) {
    if (!it || it.error) return;
    var key = pplUrlKey_(it.inputChannelUrl || it.channelUrl || '');
    if (!key || out[key]) return;
    out[key] = {
      channelName: it.channelName || '', channelUrl: it.channelUrl || it.inputChannelUrl || '',
      numberOfSubscribers: it.numberOfSubscribers || 0, channelDescription: it.channelDescription || '',
      channelLocation: it.channelLocation || '', channelTotalVideos: it.channelTotalVideos || 0,
      channelTotalViews: it.channelTotalViews || 0, lastUploadRaw: it.date || ''
    };
  });
  return out;
}

// ───────────────────────── 분류/점수/파싱 ─────────────────────────
function pplPrimaryCategory_(cats) { var b = '', n = -1; Object.keys(cats || {}).forEach(function (c) { if (cats[c] > n) { n = cats[c]; b = c; } }); return b || '(미분류)'; }
function pplChannelType_(info) {
  var raw = (info.channelName || '') + ' ' + (info.channelDescription || '');
  for (var i = 0; i < PPL_SHOP_TERMS.length; i++) if (raw.indexOf(PPL_SHOP_TERMS[i]) >= 0) return 'shop';
  for (var j = 0; j < PPL_ORG_TERMS.length; j++) if (raw.indexOf(PPL_ORG_TERMS[j]) >= 0) return 'org';
  return 'creator';
}
function pplWantsSponsor_(info) {
  var raw = ((info.channelName || '') + ' ' + (info.channelDescription || '')).toLowerCase();
  var t = ['협찬', '광고문의', '광고 문의', '비즈니스문의', '비즈니스 문의', '제휴', 'sponsor', 'business'];
  for (var i = 0; i < t.length; i++) if (raw.indexOf(t[i].toLowerCase()) >= 0) return true;
  return !!pplParseEmail_(info.channelDescription);
}
function pplScoreChannel_(info, kwList) {
  var score = Math.min(4, (kwList ? kwList.length : 0) + 1);
  score += pplActivityScore_(info.lastUploadRaw);
  var subs = info.numberOfSubscribers || 0, tv = pplToNum_(info.channelTotalViews), nv = info.channelTotalVideos || 0;
  var ratio = (subs && nv) ? (tv / nv) / subs : 0;
  if (ratio >= 0.5) score += 3; else if (ratio >= 0.2) score += 2; else if (ratio >= 0.05) score += 1;
  if (pplIsKorean_(info)) score += 1;
  if (score > 10) score = 10;
  return { score: score };
}
function pplParseDate_(raw) {
  if (!raw) return null;
  var s = String(raw);
  var iso = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (iso) return new Date(iso[1], iso[2] - 1, iso[3]);
  var now = Date.now(), m;
  if ((m = s.match(/(\d+)\s*(day|일)/))) return new Date(now - m[1] * 86400000);
  if ((m = s.match(/(\d+)\s*(week|주)/))) return new Date(now - m[1] * 7 * 86400000);
  if ((m = s.match(/(\d+)\s*(month|개월|달)/))) return new Date(now - m[1] * 30 * 86400000);
  if ((m = s.match(/(\d+)\s*(year|년)/))) return new Date(now - m[1] * 365 * 86400000);
  if (/hour|minute|시간|분|today|오늘/.test(s)) return new Date(now);
  return null;
}
function pplRecentWithin_(raw, days) { var d = pplParseDate_(raw); if (!d) return true; return (Date.now() - d.getTime()) / 86400000 <= days; }
function pplActivityScore_(raw) {
  var d = pplParseDate_(raw); if (!d) return 0;
  var days = (Date.now() - d.getTime()) / 86400000;
  if (days <= 30) return 2; if (days <= 60) return 1; return 0;
}
function pplParseEmail_(desc) { if (!desc) return ''; var m = String(desc).match(/[\w.+-]+@[\w-]+\.[\w.-]+/); return m ? m[0] : ''; }
function pplIsKorean_(info) {
  if ((info.channelLocation || '').indexOf('Korea') >= 0 || (info.channelLocation || '').indexOf('한국') >= 0) return true;
  return /[가-힣]/.test((info.channelName || '') + (info.channelDescription || ''));
}
function pplToNum_(v) { if (typeof v === 'number') return v; if (!v) return 0; var n = parseInt(String(v).replace(/[^0-9]/g, ''), 10); return isNaN(n) ? 0 : n; }
function pplUrlKey_(url) {
  if (!url) return '';
  var s = String(url).toLowerCase().replace(/\/about$/, '').replace(/\/videos$/, '').replace(/\/$/, '');
  var m1 = s.match(/\/channel\/(uc[\w-]+)/); if (m1) return 'ch:' + m1[1];
  var m2 = s.match(/@([\w.\-가-힣]+)/); if (m2) return 'h:' + m2[1];
  return s;
}
function pplChannelId_(url, info) {
  var m = String(url).match(/\/channel\/(UC[\w-]+)/i); if (m) return m[1];
  var m2 = String(info && info.channelUrl || '').match(/\/channel\/(UC[\w-]+)/i); if (m2) return m2[1];
  var m3 = String(url).match(/@([\w.\-가-힣]+)/); return m3 ? '@' + m3[1] : url;
}
function pplChannelVideosUrl_(url) { return String(url).replace(/\/about$/, '').replace(/\/videos$/, '').replace(/\/$/, '') + '/videos'; }
function pplKeywordFromSearchUrl_(u) {
  if (!u) return ''; var m = String(u).match(/search_query=([^&]+)/); if (!m) return '';
  try { return decodeURIComponent(m[1].replace(/\+/g, ' ')); } catch (e) { return ''; }
}
function pplScaleLabelForSubs_(s) { if (s >= 500000) return '대형'; if (s >= 100000) return '중형'; if (s >= 10000) return '마이크로'; return '나노'; }

// ───────────────────────── 초안 ─────────────────────────
function pplGenerateDraft_(row) { return pplGeminiPersonalize_(row) + '\n\n' + PPL_OFFER_TEMPLATE; }
function pplGeminiPersonalize_(row) {
  var key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  var fb = '\'' + (row.channelName || '채널') + '\' 채널의 ' + (row.category || row.matchedKw || '') + ' 콘텐츠를 관심 있게 보고 있습니다.';
  if (!key) return fb;
  try {
    var prompt = '너는 지역 휴대폰 매장 \'폰스팟\'의 협찬 담당자다. 아래 유튜브 채널에 보낼 협찬 제안 메일의 "첫 인사 1문단"만 한국어로 써라. ' +
      '최대 2~3문장. 과장·허위 금지. 이모지 금지. 아부 배제.\n\n채널명: ' + (row.channelName || '') +
      '\n카테고리: ' + (row.category || '') + '\n매칭키워드: ' + (row.matchedKw || '') + '\n구독자: ' + row.subs +
      '\n설명: ' + (row.descExcerpt || '').slice(0, 160);
    var res = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models/' + PPL_GEMINI_MODEL + ':generateContent?key=' + key, {
      method: 'post', contentType: 'application/json', payload: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }), muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) return fb;
    var j = JSON.parse(res.getContentText());
    var t = j && j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts && j.candidates[0].content.parts[0].text;
    return (t && t.trim()) ? t.trim() : fb;
  } catch (e) { return fb; }
}
function pplRegenerateDrafts() {
  var sh = SpreadsheetApp.getActive().getSheetByName(PPL_SHEET);
  if (!sh || sh.getLastRow() < 3) { pplAlert_('발굴 데이터가 없습니다.'); return; }
  var n = sh.getLastRow() - 2, rng = sh.getRange(3, 1, n, 18), vals = rng.getValues(), filled = 0;
  for (var i = 0; i < vals.length; i++) {
    if (vals[i][14]) continue;
    vals[i][14] = pplGenerateDraft_({ channelName: vals[i][1], subs: vals[i][2], matchedKw: vals[i][6], descExcerpt: vals[i][8], category: vals[i][17] });
    filled++;
  }
  rng.setValues(vals);
  pplAlert_('✍️ 초안 ' + filled + '건 생성/갱신.');
}

// ───────────────────────── 본선 시트 (18열) ─────────────────────────
function pplGetOrCreateSheet_() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName(PPL_SHEET);
  if (!sh) {
    sh = ss.insertSheet(PPL_SHEET);
    sh.appendRow(['유튜브 PPL 협찬 발굴 (Apify streamers/youtube-scraper)']);
    sh.appendRow(['채널ID', '채널명', '구독자', '총조회수', '영상수', '평균조회수', '매칭 키워드', '최근 업로드', '설명 발췌',
      '외부 링크', '이메일', '규모대', '적합도 점수', '등급', '제안 메일 초안', '상태', '발굴일', '카테고리']);
    sh.getRange(2, 1, 1, 18).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
    sh.setColumnWidths(1, 18, 100);
    sh.setColumnWidth(2, 160); sh.setColumnWidth(9, 260); sh.setColumnWidth(15, 420); sh.setColumnWidth(18, 120);
    sh.setFrozenRows(2);
  }
  return sh;
}
function pplWriteSheet_(rows) {
  var sh = pplGetOrCreateSheet_(), existing = {};
  if (sh.getLastRow() >= 3) sh.getRange(3, 1, sh.getLastRow() - 2, 1).getValues().forEach(function (r) { if (r[0]) existing[String(r[0])] = 1; });
  var out = [], skipped = 0;
  rows.forEach(function (r) {
    if (existing[String(r.channelId)]) { skipped++; return; }
    out.push([r.channelId, r.channelName, r.subs, r.totalViews, r.totalVideos, r.avgViews, r.matchedKw, r.lastUpload, r.descExcerpt,
      r.externalLink, r.email, r.scaleLabel, r.score, r.grade, r.draft, r.status, r.foundDate, r.category]);
  });
  if (out.length) sh.getRange(sh.getLastRow() + 1, 1, out.length, 18).setValues(out);
  return { added: out.length, skipped: skipped };
}
function pplOpenSheet() { SpreadsheetApp.getActive().setActiveSheet(pplGetOrCreateSheet_()); }

// ───────────────────────── 카테고리별 집계 ─────────────────────────
function pplCategorySummary() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName(PPL_SHEET);
  if (!sh || sh.getLastRow() < 3) { pplAlert_('발굴 데이터가 없습니다.'); return; }
  var v = sh.getRange(3, 1, sh.getLastRow() - 2, 18).getValues(), agg = {};
  v.forEach(function (r) {
    var cat = r[17] || '(미분류)', st = String(r[15] || '');
    if (!agg[cat]) agg[cat] = { cnt: 0, score: 0, subs: 0, sent: 0, reply: 0 };
    var a = agg[cat]; a.cnt++; a.score += Number(r[12]) || 0; a.subs += Number(r[2]) || 0;
    if (st.indexOf('발송') >= 0) a.sent++;
    if (st.indexOf('회신') >= 0) a.reply++;
  });
  var out = ss.getSheetByName(PPL_SUM_SHEET) || ss.insertSheet(PPL_SUM_SHEET);
  out.clear();
  out.appendRow(['카테고리', '채널수', '평균 적합도', '평균 구독자', '발송', '회신', '회신율']);
  out.getRange(1, 1, 1, 7).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
  Object.keys(agg).sort(function (a, b) { return agg[b].cnt - agg[a].cnt; }).forEach(function (c) {
    var a = agg[c];
    out.appendRow([c, a.cnt, (a.score / a.cnt).toFixed(1), Math.round(a.subs / a.cnt), a.sent, a.reply, a.sent ? (a.reply / a.sent * 100).toFixed(0) + '%' : '-']);
  });
  out.setColumnWidth(1, 140); out.setFrozenRows(1);
  ss.setActiveSheet(out);
  pplAlert_('📊 집계 갱신 완료. 회신율 높은 카테고리는 PPL_카테고리 탭에서 키워드/가중치를 늘리세요.');
}

function pplTestMenu() { buildPplYoutubeMenu_(SpreadsheetApp.getUi()); return 'OK'; }
