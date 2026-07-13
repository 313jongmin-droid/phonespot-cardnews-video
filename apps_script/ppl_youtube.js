/**
 * ppl_youtube.js — 유튜브 PPL 협찬 대상 발굴 + 제안 메일 초안 (L2, Apps Script 상주화)
 * 정본 가이드: _docs/PPL_YOUTUBE_OUTREACH_GUIDE.md
 *
 * 발굴 소스: Apify actor `streamers/youtube-scraper` (h7sDV53CddomktSi5).
 *   - MCP YouTube Data와 무관 (MCP는 공유 프로젝트 Search 쿼터 소진 이슈). Apify는 쿼터 없음.
 *   - 토큰: PropertiesService → APIFY_TOKEN (meta-sync.js의 getApifyToken_ 재사용).
 *   - 단가: $0.005 / 결과(영상 1건 또는 채널 1건). 2패스 = Pass1 검색 + Pass2 채널보강.
 *
 * 2패스 로직:
 *   Pass1 (발굴): searchQueries=[키워드], maxResults=키워드당 N → 영상 결과에서 channelUrl 유니크 수집.
 *                 (검색 결과 아이템은 channelName/channelUrl/viewCount만 있고 구독자·설명 없음.)
 *   Pass2 (보강): startUrls=[채널 /videos URL], sortVideosBy=NEWEST, maxResults=1
 *                 → 아이템에 채널 필드(numberOfSubscribers, channelDescription, channelLocation,
 *                   channelTotalVideos, channelTotalViews, channelJoinedDate, 최신영상 date) 포함.
 *   → 규모 필터(마이크로 1만~10만 기본) → 적합도 점수 0~10 → 등급 → 시트 + Gemini 초안.
 *
 * 이메일: channelDescription 정규식 파싱만(가이드 3-a, 수집률 낮음). Data API엔 이메일 필드 없음.
 * 발송: 시트 O열 초안 검토 후 수동 발송(이메일). 자동 DM ❌(유튜브 ToS).
 *
 * 멀티브랜드: push → GitHub Actions clasp --force → 폰스팟 + KT 양쪽 자동 배포.
 */

var PPL_ACTOR_PATH = 'streamers~youtube-scraper';      // api.apify.com actor path
var PPL_SHEET = '유튜브_협찬발굴';
var PPL_GEMINI_MODEL = 'gemini-2.5-flash';

// 기본 키워드 — 30~50 남성 시청층 스큐 + 폰스팟 협찬 도메인. (시트 프롬프트에서 콤마로 덮어쓰기 가능)
var PPL_DEFAULT_KEYWORDS = [
  '자급제 휴대폰', '통신비 절약', '알뜰폰 요금제', '휴대폰 성지 시세',
  '갤럭시 리뷰', '아이폰 리뷰', '스마트폰 개통', 'IT 가젯 리뷰'
];

// 규모 프리셋 (구독자 범위)
var PPL_SCALE = {
  'micro': { min: 10000,  max: 100000,  label: '마이크로' },
  'mid':   { min: 100000, max: 500000,  label: '중형' },
  'all':   { min: 0,      max: 1e12,    label: '무관' }
};

// 폰스팟 협찬 조건 템플릿 (과장·허위 금지 — 실제 조건만. 필요 시 여기만 수정)
var PPL_OFFER_TEMPLATE =
  '안녕하세요, 지역 휴대폰 성지 \'폰스팟\'입니다.\n' +
  '채널을 잘 보고 있어 협찬을 제안드립니다.\n\n' +
  '[협찬 조건]\n' +
  '· 제품/기기 협찬 또는 원고료 (영상 규모·형식에 따라 협의)\n' +
  '· 매장 개통/시세 관련 콘텐츠 소재 제공\n' +
  '· 진행 기간·횟수 협의\n\n' +
  '조건·단가는 채널 상황에 맞춰 조율 가능합니다. 관심 있으시면 회신 부탁드립니다.\n' +
  '— 폰스팟 드림';

// ───────────────────────── 메뉴 ─────────────────────────
// Code.js onOpen에서 try{ buildPplYoutubeMenu_(SpreadsheetApp.getUi()); }catch(e){} 로 호출.
function buildPplYoutubeMenu_(ui) {
  ui.createMenu('🎯 유튜브 협찬발굴')
    .addItem('🔍 발굴 실행 (키워드·규모·건수 입력)', 'pplPromptDiscovery')
    .addItem('⚡ 기본 발굴 (마이크로 30건)', 'pplRunDefault')
    .addSeparator()
    .addItem('✍️ 초안만 재생성 (빈 O열 채우기)', 'pplRegenerateDrafts')
    .addItem('📂 발굴 시트 열기', 'pplOpenSheet')
    .addToUi();
}

function pplRunDefault() {
  pplRunDiscovery_(PPL_DEFAULT_KEYWORDS, 'micro', 30, 20);
}

function pplPromptDiscovery() {
  var ui = SpreadsheetApp.getUi();
  var kwRes = ui.prompt('🎯 유튜브 협찬발굴 — 키워드',
    '검색 키워드(콤마 구분). 비우면 기본값:\n' + PPL_DEFAULT_KEYWORDS.join(', '),
    ui.ButtonSet.OK_CANCEL);
  if (kwRes.getSelectedButton() !== ui.Button.OK) return;
  var kwText = (kwRes.getResponseText() || '').trim();
  var keywords = kwText ? kwText.split(',').map(function (s) { return s.trim(); }).filter(String)
                        : PPL_DEFAULT_KEYWORDS;

  var scRes = ui.prompt('규모', '마이크로 / 중형 / 무관 중 하나 (기본 마이크로)', ui.ButtonSet.OK_CANCEL);
  if (scRes.getSelectedButton() !== ui.Button.OK) return;
  var scText = (scRes.getResponseText() || '').trim();
  var scaleKey = scText.indexOf('중형') >= 0 ? 'mid' : (scText.indexOf('무관') >= 0 ? 'all' : 'micro');

  var cntRes = ui.prompt('최종 건수', '시트에 채울 최종 채널 수 (기본 30)', ui.ButtonSet.OK_CANCEL);
  if (cntRes.getSelectedButton() !== ui.Button.OK) return;
  var targetN = parseInt((cntRes.getResponseText() || '').trim(), 10) || 30;

  pplRunDiscovery_(keywords, scaleKey, targetN, 20);
}

// ───────────────────────── 메인 오케스트레이션 ─────────────────────────
function pplRunDiscovery_(keywords, scaleKey, targetN, perKeyword) {
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) {}
  var scale = PPL_SCALE[scaleKey] || PPL_SCALE['micro'];
  try {
    // Pass1: 발굴
    var discovered = pplDiscoverChannels_(keywords, perKeyword);   // [{channelUrl, channelName, topicTags}]
    if (!discovered.length) throw new Error('Pass1 결과 0건 (키워드/Apify 잔액 확인).');

    // Pass2: 보강 (Apify는 startUrls 대량 처리 가능. 한번에 보강.)
    var urls = discovered.map(function (d) { return d.channelUrl; });
    var enriched = pplEnrichChannels_(urls);   // { channelUrlKey -> channelInfo }

    // 병합 + 필터 + 점수
    var rows = [];
    var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
    discovered.forEach(function (d) {
      var info = enriched[pplUrlKey_(d.channelUrl)];
      if (!info) return;
      var subs = info.numberOfSubscribers || 0;
      if (subs < scale.min || subs >= scale.max) return;           // 규모 필터
      var scoreObj = pplScoreChannel_(info, d.topicTags, keywords);
      var totalViews = pplToNum_(info.channelTotalViews);
      var totalVideos = info.channelTotalVideos || 0;
      var avgViews = totalVideos ? Math.round(totalViews / totalVideos) : 0;
      var email = pplParseEmail_(info.channelDescription);
      rows.push({
        channelId: pplChannelId_(d.channelUrl, info),
        channelName: info.channelName || d.channelName || '',
        subs: subs,
        totalViews: totalViews,
        totalVideos: totalVideos,
        avgViews: avgViews,
        topicTags: d.topicTags.join(', '),
        lastUpload: info.lastUploadRaw || '',
        descExcerpt: (info.channelDescription || '').slice(0, 200),
        externalLink: info.channelUrl || d.channelUrl,
        email: email,
        scaleLabel: pplScaleLabelForSubs_(subs),
        score: scoreObj.score,
        grade: scoreObj.grade,
        draft: '',       // 아래에서 채움
        status: '발굴',
        foundDate: today,
        _info: info
      });
    });

    // 점수 내림차순 → 상위 targetN
    rows.sort(function (a, b) { return b.score - a.score; });
    rows = rows.slice(0, targetN);

    // 초안 생성 (상위 N만)
    rows.forEach(function (r) {
      r.draft = pplGenerateDraft_(r);
    });

    var res = pplWriteSheet_(rows);
    var msg = '✅ 발굴 완료\n\n' +
      '키워드: ' + keywords.length + '개\n' +
      'Pass1 채널: ' + discovered.length + ' → 규모(' + scale.label + ') 통과 후 상위: ' + rows.length + '\n' +
      '시트 신규 추가: ' + res.added + ' (중복 제외: ' + res.skipped + ')\n' +
      '초안 생성: ' + rows.length + '건 (O열)';
    if (ui) ui.alert(msg);
    try { logSync_('pplRunDiscovery', keywords.join('|') + ' → ' + res.added + ' new'); } catch (e) {}
    return res;
  } catch (e) {
    if (ui) ui.alert('❌ 발굴 실패: ' + e.message);
    try { logSync_('pplRunDiscovery', 'FAIL: ' + e.message); } catch (ee) {}
    throw e;
  }
}

// ───────────────────────── Apify 호출 ─────────────────────────
function pplFetchApify_(input) {
  var token = getApifyToken_();   // meta-sync.js 정의 재사용
  var apiUrl = 'https://api.apify.com/v2/acts/' + PPL_ACTOR_PATH +
               '/run-sync-get-dataset-items?token=' + token;
  var res = UrlFetchApp.fetch(apiUrl, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(input),
    muteHttpExceptions: true
  });
  var code = res.getResponseCode();
  if (code !== 200 && code !== 201) {
    throw new Error('Apify 호출 실패 ' + code + ': ' + res.getContentText().slice(0, 400));
  }
  return JSON.parse(res.getContentText());
}

// Pass1: 키워드 검색 → 유니크 채널
function pplDiscoverChannels_(keywords, perKeyword) {
  var input = {
    searchQueries: keywords,
    maxResults: perKeyword || 20,
    maxResultsShorts: 0,
    maxResultStreams: 0,
    sortingOrder: 'relevance'
  };
  var items = pplFetchApify_(input);
  var map = {};   // urlKey -> {channelUrl, channelName, topicTags:Set}
  (items || []).forEach(function (it) {
    if (it && it.error) return;
    var url = it.channelUrl;
    if (!url) return;
    var key = pplUrlKey_(url);
    if (!map[key]) map[key] = { channelUrl: url, channelName: it.channelName || '', topicTags: {} };
    // 어떤 키워드/검색에서 걸렸는지 태그 (fromYTUrl에 search_query 포함)
    var kw = pplKeywordFromSearchUrl_(it.fromYTUrl);
    if (kw) map[key].topicTags[kw] = 1;
  });
  return Object.keys(map).map(function (k) {
    var m = map[k];
    return { channelUrl: m.channelUrl, channelName: m.channelName, topicTags: Object.keys(m.topicTags) };
  });
}

// Pass2: 채널 URL 보강 (구독자·설명·위치·최신업로드)
function pplEnrichChannels_(channelUrls) {
  var startUrls = channelUrls.map(function (u) { return { url: pplChannelVideosUrl_(u) }; });
  var input = {
    startUrls: startUrls,
    maxResults: 1,               // 채널당 최신영상 1건 → 아이템에 채널 필드 포함
    maxResultsShorts: 0,
    maxResultStreams: 0,
    sortVideosBy: 'NEWEST'
  };
  var items = pplFetchApify_(input);
  var out = {};
  (items || []).forEach(function (it) {
    if (!it || it.error) return;
    // inputChannelUrl(=우리가 넣은 URL) 또는 channelUrl 기준 매칭
    var key = pplUrlKey_(it.inputChannelUrl || it.channelUrl || '');
    if (!key) return;
    if (!out[key]) {
      out[key] = {
        channelName: it.channelName || '',
        channelUrl: it.channelUrl || it.inputChannelUrl || '',
        numberOfSubscribers: it.numberOfSubscribers || 0,
        channelDescription: it.channelDescription || '',
        channelLocation: it.channelLocation || '',
        channelTotalVideos: it.channelTotalVideos || 0,
        channelTotalViews: it.channelTotalViews || 0,
        channelJoinedDate: it.channelJoinedDate || '',
        lastUploadRaw: it.date || ''       // 최신 영상 업로드(상대/절대 문자열)
      };
    }
  });
  return out;
}

// ───────────────────────── 점수·파싱 유틸 ─────────────────────────
function pplScoreChannel_(info, topicTags, keywords) {
  var score = 0;
  // 1) 주제 적합도 (검색에서 걸린 태그 수 + 설명 키워드 매칭)  최대 4
  var topicHits = (topicTags && topicTags.length) ? topicTags.length : 0;
  var desc = (info.channelDescription || '') + ' ' + (info.channelName || '');
  var kwHit = 0;
  (keywords || []).forEach(function (kw) {
    var head = kw.split(' ')[0];
    if (head && desc.indexOf(head) >= 0) kwHit++;
  });
  score += Math.min(4, topicHits + (kwHit > 0 ? 1 : 0));
  // 2) 활성도 (최신 업로드) 최대 2
  score += pplActivityScore_(info.lastUploadRaw);
  // 3) 참여도 (평균조회수/구독자) 최대 3
  var subs = info.numberOfSubscribers || 0;
  var totalViews = pplToNum_(info.channelTotalViews);
  var totalVideos = info.channelTotalVideos || 0;
  var avg = totalVideos ? totalViews / totalVideos : 0;
  var ratio = subs ? avg / subs : 0;
  if (ratio >= 0.5) score += 3; else if (ratio >= 0.2) score += 2; else if (ratio >= 0.05) score += 1;
  // 4) 한국 채널 +1
  if (pplIsKorean_(info)) score += 1;
  if (score > 10) score = 10;
  var grade = score >= 7 ? '★★★' : (score >= 4 ? '★★' : '★');
  return { score: score, grade: grade };
}

function pplActivityScore_(raw) {
  if (!raw) return 0;
  var s = String(raw).toLowerCase();
  // 상대 표기
  if (/hour|minute|today|시간 전|분 전|오늘/.test(s)) return 2;
  if (/(\d+)\s*day|일 전/.test(s)) { var d = parseInt((s.match(/(\d+)\s*day/) || s.match(/(\d+)\s*일/) || [])[1] || '0', 10); return d <= 30 ? 2 : 1; }
  if (/week|주 전/.test(s)) { var w = parseInt((s.match(/(\d+)\s*week/) || s.match(/(\d+)\s*주/) || [])[1] || '1', 10); return w <= 4 ? 2 : 1; }
  if (/month|개월|달 전/.test(s)) { var m = parseInt((s.match(/(\d+)\s*month/) || s.match(/(\d+)\s*개월/) || [])[1] || '1', 10); return m <= 2 ? 1 : 0; }
  // 절대 날짜 (yyyy-mm-dd)
  var md = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (md) {
    var days = (Date.now() - new Date(md[1], md[2] - 1, md[3]).getTime()) / 86400000;
    if (days <= 30) return 2; if (days <= 60) return 1; return 0;
  }
  return 0;
}

function pplParseEmail_(desc) {
  if (!desc) return '';
  var m = String(desc).match(/[\w.+-]+@[\w-]+\.[\w.-]+/);
  return m ? m[0] : '';
}

function pplIsKorean_(info) {
  if ((info.channelLocation || '').indexOf('Korea') >= 0 || (info.channelLocation || '').indexOf('한국') >= 0) return true;
  var text = (info.channelName || '') + (info.channelDescription || '');
  return /[가-힣]/.test(text);
}

function pplToNum_(v) {
  if (typeof v === 'number') return v;
  if (!v) return 0;
  var n = parseInt(String(v).replace(/[^0-9]/g, ''), 10);
  return isNaN(n) ? 0 : n;
}

// 채널 URL 정규화 키 (핸들/채널ID 통일)
function pplUrlKey_(url) {
  if (!url) return '';
  var s = String(url).toLowerCase().replace(/\/about$/, '').replace(/\/videos$/, '').replace(/\/$/, '');
  var mCh = s.match(/\/channel\/(uc[\w-]+)/);
  if (mCh) return 'ch:' + mCh[1];
  var mH = s.match(/@([\w.\-가-힣]+)/);
  if (mH) return 'h:' + mH[1];
  return s;
}

function pplChannelId_(url, info) {
  var mCh = String(url).match(/\/channel\/(UC[\w-]+)/i);
  if (mCh) return mCh[1];
  var mCh2 = String(info && info.channelUrl || '').match(/\/channel\/(UC[\w-]+)/i);
  if (mCh2) return mCh2[1];
  var mH = String(url).match(/@([\w.\-가-힣]+)/);
  return mH ? '@' + mH[1] : url;
}

function pplChannelVideosUrl_(url) {
  var s = String(url).replace(/\/about$/, '').replace(/\/videos$/, '').replace(/\/$/, '');
  return s + '/videos';
}

function pplKeywordFromSearchUrl_(fromYTUrl) {
  if (!fromYTUrl) return '';
  var m = String(fromYTUrl).match(/search_query=([^&]+)/);
  if (!m) return '';
  try { return decodeURIComponent(m[1].replace(/\+/g, ' ')); } catch (e) { return ''; }
}

function pplScaleLabelForSubs_(subs) {
  if (subs >= 500000) return '대형';
  if (subs >= 100000) return '중형';
  if (subs >= 10000) return '마이크로';
  return '나노';
}

// ───────────────────────── Gemini 제안 초안 ─────────────────────────
function pplGenerateDraft_(row) {
  var personalized = pplGeminiPersonalize_(row);   // 실패 시 폴백 문구 반환
  return personalized + '\n\n' + PPL_OFFER_TEMPLATE;
}

function pplGeminiPersonalize_(row) {
  var key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  var fallback = '\'' + (row.channelName || '채널') + '\' 채널의 ' +
    (row.topicTags || '휴대폰/통신') + ' 콘텐츠를 관심 있게 보고 있습니다.';
  if (!key) return fallback;
  try {
    var prompt =
      '너는 지역 휴대폰 매장 \'폰스팟\'의 협찬 담당자다. 아래 유튜브 채널에 보낼 협찬 제안 메일의 ' +
      '"첫 인사 1문단"만 한국어로 써라. 조건은 최대 2~3문장. 과장·허위 금지, 실제로 확인된 것만. ' +
      '이모지 금지. 채널명과 주제를 자연스럽게 언급하되 아부는 배제.\n\n' +
      '채널명: ' + (row.channelName || '') + '\n' +
      '주제태그: ' + (row.topicTags || '') + '\n' +
      '구독자: ' + row.subs + '\n' +
      '설명발췌: ' + (row.descExcerpt || '').slice(0, 160);
    var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + PPL_GEMINI_MODEL +
              ':generateContent?key=' + key;
    var res = UrlFetchApp.fetch(url, {
      method: 'post', contentType: 'application/json',
      payload: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) return fallback;
    var j = JSON.parse(res.getContentText());
    var t = j && j.candidates && j.candidates[0] && j.candidates[0].content &&
            j.candidates[0].content.parts && j.candidates[0].content.parts[0].text;
    return (t && t.trim()) ? t.trim() : fallback;
  } catch (e) {
    return fallback;
  }
}

// 빈 O열만 채우기 (Gemini 키 등록 후 재실행 등)
function pplRegenerateDrafts() {
  var ui = null; try { ui = SpreadsheetApp.getUi(); } catch (e) {}
  var sheet = SpreadsheetApp.getActive().getSheetByName(PPL_SHEET);
  if (!sheet || sheet.getLastRow() < 3) { if (ui) ui.alert('발굴 데이터가 없습니다.'); return; }
  var n = sheet.getLastRow() - 2;
  var rng = sheet.getRange(3, 1, n, 17);
  var vals = rng.getValues();
  var filled = 0;
  for (var i = 0; i < vals.length; i++) {
    if (vals[i][14]) continue;   // O열(15번째=index14) 이미 있음
    var row = {
      channelName: vals[i][1], subs: vals[i][2], topicTags: vals[i][6],
      descExcerpt: vals[i][8]
    };
    vals[i][14] = pplGenerateDraft_(row);
    filled++;
  }
  rng.setValues(vals);
  if (ui) ui.alert('✍️ 초안 ' + filled + '건 생성/갱신.');
}

// ───────────────────────── 시트 ─────────────────────────
function pplGetOrCreateSheet_() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(PPL_SHEET);
  if (!sheet) {
    sheet = ss.insertSheet(PPL_SHEET);
    sheet.appendRow(['유튜브 PPL 협찬 발굴 (Apify streamers/youtube-scraper)']);
    sheet.appendRow([
      '채널ID', '채널명', '구독자', '총조회수', '영상수', '평균조회수',
      '주제 태그', '최근 업로드', '설명 발췌', '외부 링크', '이메일',
      '규모대', '적합도 점수', '등급', '제안 메일 초안', '상태', '발굴일'
    ]);
    sheet.getRange(2, 1, 1, 17).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
    sheet.setColumnWidths(1, 17, 100);
    sheet.setColumnWidth(2, 160);  // 채널명
    sheet.setColumnWidth(9, 260);  // 설명 발췌
    sheet.setColumnWidth(15, 420); // 제안 초안
    sheet.setFrozenRows(2);
  }
  return sheet;
}

function pplWriteSheet_(rows) {
  var sheet = pplGetOrCreateSheet_();
  // 중복 체크 (A열 채널ID 기준)
  var existing = {};
  if (sheet.getLastRow() >= 3) {
    var ids = sheet.getRange(3, 1, sheet.getLastRow() - 2, 1).getValues();
    ids.forEach(function (r) { if (r[0]) existing[String(r[0])] = 1; });
  }
  var out = [];
  var skipped = 0;
  rows.forEach(function (r) {
    if (existing[String(r.channelId)]) { skipped++; return; }
    out.push([
      r.channelId, r.channelName, r.subs, r.totalViews, r.totalVideos, r.avgViews,
      r.topicTags, r.lastUpload, r.descExcerpt, r.externalLink, r.email,
      r.scaleLabel, r.score, r.grade, r.draft, r.status, r.foundDate
    ]);
  });
  if (out.length) {
    sheet.getRange(sheet.getLastRow() + 1, 1, out.length, 17).setValues(out);
  }
  return { added: out.length, skipped: skipped };
}

function pplOpenSheet() {
  var sheet = pplGetOrCreateSheet_();
  SpreadsheetApp.getActive().setActiveSheet(sheet);
}

// ───────────────────────── 디버그 ─────────────────────────
// 메뉴가 안 뜰 때: 에디터에서 이 함수 직접 실행(▶). try/catch 없이 메뉴를 그려서
// 에러가 있으면 실행 로그에 그대로 노출. 성공하면 시트에 '🎯 유튜브 협찬발굴' 메뉴가 붙음.
function pplTestMenu() {
  buildPplYoutubeMenu_(SpreadsheetApp.getUi());
  return '✅ buildPplYoutubeMenu_ 실행 성공 — 시트 상단에 메뉴가 붙어야 함';
}
