/**
 * ppl_youtube.js — 유튜브 PPL 협찬 대상 발굴 + 카테고리 분류 + 제안 초안 (L2)
 * 정본 가이드: _docs/PPL_YOUTUBE_OUTREACH_GUIDE.md
 *
 * 목표(2026-07-13 종민): 폰 무관. "30~50 남성 시청층 스큐" 채널을 카테고리로 근사 발굴 →
 *   카테고리 태깅 → 카테고리별 집계(회신율)로 분류·타겟팅을 점점 정밀화(피드백 루프).
 *
 * ★ 사실 한계: YouTube/Apify는 타 채널의 시청자 연령·성별을 제공하지 않음(채널 주인만 조회).
 *   → 성별/연령 직접 필터 불가. '카테고리(자동차·IT·재테크·시사·취미…)'로 근사한다.
 *
 * 분류 체계 = 편집 가능한 시트 탭 'PPL_카테고리'(카테고리·키워드·가중치·사용). 코드가 매 실행 시 읽음.
 *   → 종민이 탭만 고쳐 키워드 추가/가중치 조정 → 코드 push 없이 정밀화.
 *
 * 발굴 소스: Apify actor streamers/youtube-scraper (비동기 폴링, 6분 제한 방어).
 *   토큰: PropertiesService APIFY_TOKEN (getApifyToken_ 재사용). 단가 $0.005/결과.
 *   2패스: Pass1 키워드검색→채널수집(+카테고리 태깅) / Pass2 채널URL 보강(구독자·설명·이메일).
 *
 * 발송은 수동(유튜브 ToS). 자동 DM 금지.
 */

var PPL_ACTOR_PATH = 'streamers~youtube-scraper';
var PPL_SHEET      = '유튜브_협찬발굴';
var PPL_CAT_SHEET  = 'PPL_카테고리';
var PPL_SUM_SHEET  = 'PPL_카테고리_집계';
var PPL_GEMINI_MODEL = 'gemini-2.5-flash';

var PPL_MAX_ENRICH = 35;      // Pass2 채널 상한 (6분 제한 방어)
var PPL_MAX_KW     = 12;      // 1회 발굴 검색 키워드 상한 (6분 제한 방어)
var PPL_BUDGET_P1  = 120;     // Pass1 폴링 예산(초)
var PPL_BUDGET_P2  = 180;     // Pass2 폴링 예산(초)

// PPL_카테고리 탭 없을 때 자동 시드. (카테고리, 키워드콤마, 가중치0~2, 사용Y/N)
var PPL_SEED_TAXONOMY = [
  ['자동차',       '자동차 리뷰,신차 시승기,국산차 리뷰,수입차 리뷰,중고차 구매', 2, 'Y'],
  ['IT·가젯',      'IT 리뷰,스마트폰 리뷰,노트북 리뷰,가젯 리뷰,PC 견적',        2, 'Y'],
  ['자급제·통신',   '자급제 휴대폰,통신비 절약,알뜰폰 요금제',                     1, 'Y'],
  ['경제·재테크',   '재테크,주식 투자,부동산 투자,경제 뉴스,자산관리',            2, 'Y'],
  ['시사·지식',    '시사 브리핑,뉴스 해설,역사 이야기,과학 지식',                1, 'Y'],
  ['취미·아웃도어', '낚시,캠핑 차박,골프 레슨,등산,밀리터리',                     2, 'Y'],
  ['스포츠',       '축구 분석,야구 하이라이트,격투기,헬스 운동',                 1, 'Y']
];

var PPL_SCALE = {
  'micro': { min: 10000,  max: 100000,  label: '마이크로' },
  'mid':   { min: 100000, max: 500000,  label: '중형' },
  'all':   { min: 0,      max: 1e12,    label: '무관' }
};

// 크리에이터가 아닌 채널(판매점/쇼핑몰·기관) 제외 — 협찬 대상 아님. 기본 제외.
var PPL_EXCLUDE_NONCREATOR = true;
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

// ───────────────────────── 유틸(공통) ─────────────────────────
function pplUi_() { try { return SpreadsheetApp.getUi(); } catch (e) { return null; } }
function pplAlert_(m) { var u = pplUi_(); if (u) u.alert(m); }

// ───────────────────────── 메뉴 (youtube_sync 하위메뉴에서 호출) ─────────────────────────
// 함수명은 youtube_sync.js addYouTubeMenuItem 서브메뉴가 참조. 유지할 것.
function buildPplYoutubeMenu_(ui) {
  ui.createMenu('🎯 유튜브 협찬발굴')
    .addItem('⚡ 빠른 발굴 (전체 카테고리)', 'pplRunDefault')
    .addItem('🔍 카테고리 지정 발굴', 'pplPromptDiscovery')
    .addSeparator()
    .addItem('✍️ 초안만 재생성 (빈 O열)', 'pplRegenerateDrafts')
    .addItem('📊 카테고리별 집계', 'pplCategorySummary')
    .addItem('⚙️ 카테고리 탭 열기', 'pplOpenTaxonomy')
    .addItem('📂 발굴 시트 열기', 'pplOpenSheet')
    .addToUi();
}

function pplRunDefault() {
  var tax = pplGetTaxonomy_();
  if (!tax.length) { pplAlert_('PPL_카테고리 탭에 사용(Y) 카테고리가 없습니다. ⚙️ 카테고리 탭 열기로 확인하세요.'); return; }
  var pairs = [];
  tax.forEach(function (c) { c.keywords.slice(0, 2).forEach(function (k) { pairs.push({ kw: k, category: c.category, weight: c.weight }); }); });
  pairs = pairs.slice(0, PPL_MAX_KW);
  pplRunDiscovery_(pairs, 'micro', 30, 6);
}

function pplPromptDiscovery() {
  var ui = SpreadsheetApp.getUi();
  var tax = pplGetTaxonomy_();
  var names = tax.map(function (c) { return c.category; });
  var r1 = ui.prompt('🎯 카테고리 지정 발굴', '카테고리명 하나 입력(전체=빈칸):\n' + names.join(' / '), ui.ButtonSet.OK_CANCEL);
  if (r1.getSelectedButton() !== ui.Button.OK) return;
  var pick = (r1.getResponseText() || '').trim();
  var pairs = [];
  if (pick) {
    var c = null; for (var i = 0; i < tax.length; i++) if (tax[i].category.indexOf(pick) >= 0 || pick.indexOf(tax[i].category) >= 0) { c = tax[i]; break; }
    if (!c) { ui.alert('일치 카테고리 없음: ' + pick); return; }
    c.keywords.forEach(function (k) { pairs.push({ kw: k, category: c.category, weight: c.weight }); });
  } else {
    tax.forEach(function (cc) { cc.keywords.slice(0, 2).forEach(function (k) { pairs.push({ kw: k, category: cc.category, weight: cc.weight }); }); });
  }
  pairs = pairs.slice(0, PPL_MAX_KW);

  var r2 = ui.prompt('규모', '마이크로 / 중형 / 무관 (기본 마이크로)', ui.ButtonSet.OK_CANCEL);
  if (r2.getSelectedButton() !== ui.Button.OK) return;
  var st = (r2.getResponseText() || '').trim();
  var scaleKey = st.indexOf('중형') >= 0 ? 'mid' : (st.indexOf('무관') >= 0 ? 'all' : 'micro');

  var r3 = ui.prompt('최종 건수', '시트에 채울 최종 채널 수 (기본 30)', ui.ButtonSet.OK_CANCEL);
  if (r3.getSelectedButton() !== ui.Button.OK) return;
  var targetN = parseInt((r3.getResponseText() || '').trim(), 10) || 30;

  pplRunDiscovery_(pairs, scaleKey, targetN, 8);
}

// ───────────────────────── 메인 오케스트레이션 ─────────────────────────
function pplRunDiscovery_(kwPairs, scaleKey, targetN, perKeyword) {
  var ui = pplUi_();
  var scale = PPL_SCALE[scaleKey] || PPL_SCALE['micro'];
  try {
    var keywords = kwPairs.map(function (p) { return p.kw; });
    var kwMeta = {}; kwPairs.forEach(function (p) { kwMeta[p.kw] = p; });

    var discovered = pplDiscoverChannels_(keywords, perKeyword, kwMeta);  // [{channelUrl,channelName,cats:{},kws:{}}]
    if (!discovered.length) throw new Error('Pass1 결과 0건 (키워드/Apify 잔액 확인).');

    var urls = discovered.map(function (d) { return d.channelUrl; });
    var enriched = pplEnrichChannels_(urls);

    var rows = [];
    var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
    discovered.forEach(function (d) {
      var info = enriched[pplUrlKey_(d.channelUrl)];
      if (!info) return;
      var subs = info.numberOfSubscribers || 0;
      if (subs < scale.min || subs >= scale.max) return;                 // 규모 필터
      if (PPL_EXCLUDE_NONCREATOR && pplChannelType_(info) !== 'creator') return;  // 판매점/기관 제외

      var kwList = Object.keys(d.kws);
      var primaryCat = pplPrimaryCategory_(d.cats);
      var catWeight = pplCategoryWeight_(primaryCat, kwMeta, d.cats);

      var scoreObj = pplScoreChannel_(info, kwList, keywords);
      scoreObj.score = Math.min(10, scoreObj.score + Math.round(catWeight));   // 카테고리 가중치
      if (pplWantsSponsor_(info)) scoreObj.score = Math.min(10, scoreObj.score + 2);
      scoreObj.grade = scoreObj.score >= 7 ? '★★★' : (scoreObj.score >= 4 ? '★★' : '★');

      var totalViews = pplToNum_(info.channelTotalViews);
      var totalVideos = info.channelTotalVideos || 0;
      rows.push({
        channelId: pplChannelId_(d.channelUrl, info),
        channelName: info.channelName || d.channelName || '',
        subs: subs,
        totalViews: totalViews,
        totalVideos: totalVideos,
        avgViews: totalVideos ? Math.round(totalViews / totalVideos) : 0,
        matchedKw: kwList.join(', '),
        lastUpload: info.lastUploadRaw || '',
        descExcerpt: (info.channelDescription || '').slice(0, 200),
        externalLink: info.channelUrl || d.channelUrl,
        email: pplParseEmail_(info.channelDescription),
        scaleLabel: pplScaleLabelForSubs_(subs),
        score: scoreObj.score,
        grade: scoreObj.grade,
        draft: '',
        status: '발굴',
        foundDate: today,
        category: primaryCat
      });
    });

    rows.sort(function (a, b) { return b.score - a.score; });
    rows = rows.slice(0, targetN);

    var res = pplWriteSheet_(rows);
    pplAlert_('✅ 발굴 완료 (초안 제외)\n\n' +
      '검색 키워드: ' + keywords.length + '개\n' +
      'Pass1 채널: ' + discovered.length + ' → 규모(' + scale.label + ')·크리에이터 통과 후 상위: ' + rows.length + '\n' +
      '시트 신규 추가: ' + res.added + ' (중복 제외: ' + res.skipped + ')\n' +
      '다음: ✍️ 초안만 재생성 → O열 채움 (재실행 가능) / 📊 카테고리별 집계');
    try { logSync_('pplRunDiscovery', keywords.join('|') + ' -> ' + res.added + ' new'); } catch (e) {}
    return res;
  } catch (e) {
    pplAlert_('❌ 발굴 실패: ' + e.message);
    try { logSync_('pplRunDiscovery', 'FAIL: ' + e.message); } catch (ee) {}
    throw e;
  }
}

// ───────────────────────── Apify (비동기 폴링) ─────────────────────────
function pplFetchApify_(input, budgetSec) {
  var token = getApifyToken_();
  var startRes = UrlFetchApp.fetch('https://api.apify.com/v2/acts/' + PPL_ACTOR_PATH + '/runs?token=' + token, {
    method: 'post', contentType: 'application/json', payload: JSON.stringify(input), muteHttpExceptions: true
  });
  var sc = startRes.getResponseCode();
  if (sc !== 200 && sc !== 201) throw new Error('Apify 시작 실패 ' + sc + ': ' + startRes.getContentText().slice(0, 300));
  var run = JSON.parse(startRes.getContentText()).data;
  var runId = run.id, dsId = run.defaultDatasetId, status = run.status;
  var budget = (budgetSec || 150) * 1000, waited = 0, step = 5000;
  while (waited < budget && status !== 'SUCCEEDED') {
    if (status === 'FAILED' || status === 'ABORTED' || status === 'TIMED-OUT') throw new Error('Apify 실행 ' + status + ' (runId ' + runId + ')');
    Utilities.sleep(step); waited += step;
    var pr = UrlFetchApp.fetch('https://api.apify.com/v2/actor-runs/' + runId + '?token=' + token, { muteHttpExceptions: true });
    if (pr.getResponseCode() === 200) { var d = JSON.parse(pr.getContentText()).data; status = d.status; dsId = d.defaultDatasetId || dsId; }
  }
  if (status !== 'SUCCEEDED') throw new Error('Apify 시간초과(' + Math.round(budget / 1000) + 's, status=' + status + '). 키워드/건수 줄여 재시도.');
  var itRes = UrlFetchApp.fetch('https://api.apify.com/v2/datasets/' + dsId + '/items?clean=true&token=' + token, { muteHttpExceptions: true });
  if (itRes.getResponseCode() !== 200) throw new Error('Apify 데이터셋 실패 ' + itRes.getResponseCode());
  return JSON.parse(itRes.getContentText());
}

// Pass1: 키워드 검색 → 유니크 채널 (+카테고리/키워드 태깅)
function pplDiscoverChannels_(keywords, perKeyword, kwMeta) {
  var items = pplFetchApify_({
    searchQueries: keywords, maxResults: perKeyword || 8, maxResultsShorts: 0, maxResultStreams: 0, sortingOrder: 'relevance'
  }, PPL_BUDGET_P1);
  var map = {};
  (items || []).forEach(function (it) {
    if (!it || it.error || !it.channelUrl) return;
    var key = pplUrlKey_(it.channelUrl);
    if (!map[key]) map[key] = { channelUrl: it.channelUrl, channelName: it.channelName || '', cats: {}, kws: {} };
    var kw = pplKeywordFromSearchUrl_(it.fromYTUrl);
    if (kw && kwMeta[kw]) { map[key].kws[kw] = 1; map[key].cats[kwMeta[kw].category] = (map[key].cats[kwMeta[kw].category] || 0) + 1; }
  });
  return Object.keys(map).map(function (k) { return map[k]; });
}

// Pass2: 채널 URL 보강
function pplEnrichChannels_(channelUrls) {
  channelUrls = channelUrls.slice(0, PPL_MAX_ENRICH);
  var startUrls = channelUrls.map(function (u) { return { url: pplChannelVideosUrl_(u) }; });
  var items = pplFetchApify_({ startUrls: startUrls, maxResults: 1, maxResultsShorts: 0, maxResultStreams: 0, sortVideosBy: 'NEWEST' }, PPL_BUDGET_P2);
  var out = {};
  (items || []).forEach(function (it) {
    if (!it || it.error) return;
    var key = pplUrlKey_(it.inputChannelUrl || it.channelUrl || '');
    if (!key || out[key]) return;
    out[key] = {
      channelName: it.channelName || '', channelUrl: it.channelUrl || it.inputChannelUrl || '',
      numberOfSubscribers: it.numberOfSubscribers || 0, channelDescription: it.channelDescription || '',
      channelLocation: it.channelLocation || '', channelTotalVideos: it.channelTotalVideos || 0,
      channelTotalViews: it.channelTotalViews || 0, channelJoinedDate: it.channelJoinedDate || '', lastUploadRaw: it.date || ''
    };
  });
  return out;
}

// ───────────────────────── 분류/점수/파싱 ─────────────────────────
function pplPrimaryCategory_(cats) {
  var best = '', n = -1;
  Object.keys(cats || {}).forEach(function (c) { if (cats[c] > n) { n = cats[c]; best = c; } });
  return best || '(미분류)';
}
function pplCategoryWeight_(cat, kwMeta, cats) {
  // 대표 카테고리의 가중치 = 그 카테고리 키워드의 weight (kwMeta 중 해당 카테고리 첫 값)
  var w = 1, keys = Object.keys(kwMeta);
  for (var i = 0; i < keys.length; i++) if (kwMeta[keys[i]].category === cat) { w = kwMeta[keys[i]].weight; break; }
  return isNaN(w) ? 1 : w;
}

function pplChannelType_(info) {
  var raw = (info.channelName || '') + ' ' + (info.channelDescription || '');
  for (var i = 0; i < PPL_SHOP_TERMS.length; i++) if (raw.indexOf(PPL_SHOP_TERMS[i]) >= 0) return 'shop';
  for (var j = 0; j < PPL_ORG_TERMS.length; j++) if (raw.indexOf(PPL_ORG_TERMS[j]) >= 0) return 'org';
  return 'creator';
}
function pplWantsSponsor_(info) {
  var raw = ((info.channelName || '') + ' ' + (info.channelDescription || '')).toLowerCase();
  var terms = ['협찬', '광고문의', '광고 문의', '비즈니스문의', '비즈니스 문의', '제휴', 'sponsor', 'business'];
  for (var i = 0; i < terms.length; i++) if (raw.indexOf(terms[i].toLowerCase()) >= 0) return true;
  return !!pplParseEmail_(info.channelDescription);
}

function pplScoreChannel_(info, kwList, keywords) {
  var score = 0;
  var desc = (info.channelDescription || '') + ' ' + (info.channelName || '');
  var kwHit = 0;
  (keywords || []).forEach(function (kw) { var head = kw.split(' ')[0]; if (head && desc.indexOf(head) >= 0) kwHit++; });
  score += Math.min(4, (kwList ? kwList.length : 0) + (kwHit > 0 ? 1 : 0));
  score += pplActivityScore_(info.lastUploadRaw);
  var subs = info.numberOfSubscribers || 0, tv = pplToNum_(info.channelTotalViews), nv = info.channelTotalVideos || 0;
  var ratio = (subs && nv) ? (tv / nv) / subs : 0;
  if (ratio >= 0.5) score += 3; else if (ratio >= 0.2) score += 2; else if (ratio >= 0.05) score += 1;
  if (pplIsKorean_(info)) score += 1;
  if (score > 10) score = 10;
  return { score: score, grade: score >= 7 ? '★★★' : (score >= 4 ? '★★' : '★') };
}

function pplActivityScore_(raw) {
  if (!raw) return 0;
  var s = String(raw).toLowerCase();
  if (/hour|minute|today|시간 전|분 전|오늘/.test(s)) return 2;
  if (/(\d+)\s*day|일 전/.test(s)) { var d = parseInt((s.match(/(\d+)\s*day/) || s.match(/(\d+)\s*일/) || [])[1] || '0', 10); return d <= 30 ? 2 : 1; }
  if (/week|주 전/.test(s)) { var w = parseInt((s.match(/(\d+)\s*week/) || s.match(/(\d+)\s*주/) || [])[1] || '1', 10); return w <= 4 ? 2 : 1; }
  if (/month|개월|달 전/.test(s)) { var m = parseInt((s.match(/(\d+)\s*month/) || s.match(/(\d+)\s*개월/) || [])[1] || '1', 10); return m <= 2 ? 1 : 0; }
  var md = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (md) { var days = (Date.now() - new Date(md[1], md[2] - 1, md[3]).getTime()) / 86400000; if (days <= 30) return 2; if (days <= 60) return 1; return 0; }
  return 0;
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
  var mCh = s.match(/\/channel\/(uc[\w-]+)/); if (mCh) return 'ch:' + mCh[1];
  var mH = s.match(/@([\w.\-가-힣]+)/); if (mH) return 'h:' + mH[1];
  return s;
}
function pplChannelId_(url, info) {
  var mCh = String(url).match(/\/channel\/(UC[\w-]+)/i); if (mCh) return mCh[1];
  var mCh2 = String(info && info.channelUrl || '').match(/\/channel\/(UC[\w-]+)/i); if (mCh2) return mCh2[1];
  var mH = String(url).match(/@([\w.\-가-힣]+)/); return mH ? '@' + mH[1] : url;
}
function pplChannelVideosUrl_(url) { return String(url).replace(/\/about$/, '').replace(/\/videos$/, '').replace(/\/$/, '') + '/videos'; }
function pplKeywordFromSearchUrl_(u) {
  if (!u) return ''; var m = String(u).match(/search_query=([^&]+)/); if (!m) return '';
  try { return decodeURIComponent(m[1].replace(/\+/g, ' ')); } catch (e) { return ''; }
}
function pplScaleLabelForSubs_(subs) { if (subs >= 500000) return '대형'; if (subs >= 100000) return '중형'; if (subs >= 10000) return '마이크로'; return '나노'; }

// ───────────────────────── Gemini 초안 ─────────────────────────
function pplGenerateDraft_(row) { return pplGeminiPersonalize_(row) + '\n\n' + PPL_OFFER_TEMPLATE; }
function pplGeminiPersonalize_(row) {
  var key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  var fallback = '\'' + (row.channelName || '채널') + '\' 채널의 ' + (row.category || row.matchedKw || '') + ' 콘텐츠를 관심 있게 보고 있습니다.';
  if (!key) return fallback;
  try {
    var prompt = '너는 지역 휴대폰 매장 \'폰스팟\'의 협찬 담당자다. 아래 유튜브 채널에 보낼 협찬 제안 메일의 "첫 인사 1문단"만 한국어로 써라. ' +
      '최대 2~3문장. 과장·허위 금지, 확인된 것만. 이모지 금지. 채널명과 주제를 자연스럽게 언급하되 아부 배제.\n\n' +
      '채널명: ' + (row.channelName || '') + '\n카테고리: ' + (row.category || '') + '\n매칭키워드: ' + (row.matchedKw || '') +
      '\n구독자: ' + row.subs + '\n설명: ' + (row.descExcerpt || '').slice(0, 160);
    var res = UrlFetchApp.fetch('https://generativelanguage.googleapis.com/v1beta/models/' + PPL_GEMINI_MODEL + ':generateContent?key=' + key, {
      method: 'post', contentType: 'application/json', payload: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }), muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) return fallback;
    var j = JSON.parse(res.getContentText());
    var t = j && j.candidates && j.candidates[0] && j.candidates[0].content && j.candidates[0].content.parts && j.candidates[0].content.parts[0].text;
    return (t && t.trim()) ? t.trim() : fallback;
  } catch (e) { return fallback; }
}

function pplRegenerateDrafts() {
  var sh = SpreadsheetApp.getActive().getSheetByName(PPL_SHEET);
  if (!sh || sh.getLastRow() < 3) { pplAlert_('발굴 데이터가 없습니다.'); return; }
  var n = sh.getLastRow() - 2, rng = sh.getRange(3, 1, n, 18), vals = rng.getValues(), filled = 0;
  for (var i = 0; i < vals.length; i++) {
    if (vals[i][14]) continue;   // O열(index14)
    vals[i][14] = pplGenerateDraft_({ channelName: vals[i][1], subs: vals[i][2], matchedKw: vals[i][6], descExcerpt: vals[i][8], category: vals[i][17] });
    filled++;
  }
  rng.setValues(vals);
  pplAlert_('✍️ 초안 ' + filled + '건 생성/갱신.');
}

// ───────────────────────── 시트 (18열: A~R, R=카테고리) ─────────────────────────
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

// ───────────────────────── 카테고리 분류 탭 (편집 가능) ─────────────────────────
function pplGetTaxonomy_() {
  var sh = SpreadsheetApp.getActive().getSheetByName(PPL_CAT_SHEET);
  if (!sh) sh = pplCreateTaxonomySheet_();
  var last = sh.getLastRow(); if (last < 3) return [];
  var vals = sh.getRange(3, 1, last - 2, 4).getValues(), out = [];
  vals.forEach(function (r) {
    var cat = String(r[0] || '').trim(); if (!cat) return;
    if (String(r[3] || 'Y').trim().toUpperCase() === 'N') return;
    var kws = String(r[1] || '').split(',').map(function (x) { return x.trim(); }).filter(String);
    var w = parseFloat(r[2]); if (isNaN(w)) w = 1;
    if (kws.length) out.push({ category: cat, keywords: kws, weight: w });
  });
  return out;
}
function pplCreateTaxonomySheet_() {
  var ss = SpreadsheetApp.getActive(), sh = ss.insertSheet(PPL_CAT_SHEET);
  sh.appendRow(['PPL 카테고리 분류 — 여기 고치면 발굴에 즉시 반영 (키워드 추가/가중치·사용 조정)']);
  sh.appendRow(['카테고리', '검색 키워드(콤마 구분)', '남성30-50 가중치(0~2)', '사용(Y/N)']);
  sh.getRange(2, 1, 1, 4).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
  PPL_SEED_TAXONOMY.forEach(function (r) { sh.appendRow(r); });
  sh.setColumnWidth(1, 130); sh.setColumnWidth(2, 460); sh.setColumnWidth(3, 160); sh.setFrozenRows(2);
  return sh;
}
function pplOpenTaxonomy() { var sh = SpreadsheetApp.getActive().getSheetByName(PPL_CAT_SHEET) || pplCreateTaxonomySheet_(); SpreadsheetApp.getActive().setActiveSheet(sh); }

// ───────────────────────── 카테고리별 집계 (정밀화 피드백) ─────────────────────────
function pplCategorySummary() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName(PPL_SHEET);
  if (!sh || sh.getLastRow() < 3) { pplAlert_('발굴 데이터가 없습니다.'); return; }
  var v = sh.getRange(3, 1, sh.getLastRow() - 2, 18).getValues(), agg = {};
  v.forEach(function (r) {
    var cat = r[17] || '(미분류)', st = String(r[15] || '');
    if (!agg[cat]) agg[cat] = { cnt: 0, score: 0, subs: 0, sent: 0, reply: 0 };
    var a = agg[cat]; a.cnt++; a.score += Number(r[12]) || 0; a.subs += Number(r[2]) || 0;
    if (st.indexOf('발송') >= 0) a.sent++; if (st.indexOf('회신') >= 0) a.reply++;
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
  pplAlert_('📊 카테고리별 집계 갱신 완료. 회신율 높은 카테고리는 PPL_카테고리 탭에서 키워드/가중치 늘려 정밀화하세요.');
}

// ───────────────────────── 디버그 ─────────────────────────
function pplTestMenu() { buildPplYoutubeMenu_(SpreadsheetApp.getUi()); return 'OK'; }
