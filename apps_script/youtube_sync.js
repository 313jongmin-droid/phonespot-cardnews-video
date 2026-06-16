/**
 * YouTube Data + Analytics → '유튜브' 시트 sync + 학습 MD 생성.
 *
 * 시트 갱신:
 *   - '유튜브' A:I 만 건드림 (K~P 자동 수식 영역 X)
 *   - A 날짜 / B 포맷 / C 주제 / D 링크 / E 조회수 / F 좋아요 / G 팔로워 / H 운영메모 / I 비고
 *   - video_id dedup. 기존 행 A~G, I 갱신 (H 유지). 새 영상은 append.
 *   - sync 끝나면 A열 날짜 오름차순 정렬 (아래로 갈수록 최신)
 *
 * 자동 학습 (2026-06-05):
 *   - generateYouTubeInsightsMarkdown() 매일 03:40 자동
 *   - Gemini API로 시트 분석 → Markdown 생성
 *   - Drive 폴더 "phonespot_cardnews_state" 에 youtube_insights.md 저장 (덮어쓰기)
 *   - Drive desktop sync → 로컬 cardnews/shorts task가 빌드 시 Read
 *
 * Advanced Services 필요:
 *   - YouTube Data API v3   (identifier: YouTube)
 *   - YouTube Analytics API  (identifier: YouTubeAnalytics)
 *
 * PropertiesService (선택):
 *   - GEMINI_API_KEY: 미설정 시 폴백 (단순 분리)
 */

var YT_SHEET_TAB = '유튜브';
var SHEET_DATA_START_ROW = 4;
var SHEET_ID = '1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI';
var GEMINI_MODEL = 'gemini-2.5-flash';
var INSIGHTS_DRIVE_FOLDER = 'phonespot_cardnews_state';
var INSIGHTS_FILE = 'youtube_insights.md';


// ============== 메인 — 데이터 수집 ==============

function fetchYouTubeAnalyticsDaily() {
  var startTime = new Date();
  Logger.log('=== YouTube sync 시작 ' + startTime.toLocaleString('ko-KR') + ' ===');

  var chResp = YouTube.Channels.list('id,snippet,statistics,contentDetails', {mine: true});
  if (!chResp.items || chResp.items.length === 0) throw new Error('채널 없음');
  var channel = chResp.items[0];
  var channelId = channel.id;
  var channelTitle = channel.snippet.title;
  var subscribers = parseInt(channel.statistics.subscriberCount || 0, 10);
  var uploadsPlaylistId = channel.contentDetails.relatedPlaylists.uploads;
  Logger.log('채널: ' + channelTitle + ' (구독자 ' + subscribers + ')');

  var videoIds = [];
  var pageToken = null;
  do {
    var r = YouTube.PlaylistItems.list('contentDetails', {
      playlistId: uploadsPlaylistId,
      maxResults: 50,
      pageToken: pageToken
    });
    (r.items || []).forEach(function(it) { videoIds.push(it.contentDetails.videoId); });
    pageToken = r.nextPageToken;
  } while (pageToken && videoIds.length < 500);
  Logger.log('영상 ' + videoIds.length + '개');
  if (videoIds.length === 0) return {updates: 0, appends: 0};

  var stats = {};
  for (var i = 0; i < videoIds.length; i += 50) {
    var batch = videoIds.slice(i, i + 50);
    var resp = YouTube.Videos.list('snippet,statistics,contentDetails', { id: batch.join(',') });
    (resp.items || []).forEach(function(v) {
      stats[v.id] = {
        title: v.snippet.title || '',
        publishedAt: v.snippet.publishedAt || '',
        durationIso: v.contentDetails.duration || '',
        views: parseInt(v.statistics.viewCount || 0, 10),
        likes: parseInt(v.statistics.likeCount || 0, 10),
        comments: parseInt(v.statistics.commentCount || 0, 10)
      };
    });
  }

  var today = new Date();
  var start = new Date(today); start.setDate(start.getDate() - 30);
  var tz = 'Asia/Seoul';
  var startStr = Utilities.formatDate(start, tz, 'yyyy-MM-dd');
  var endStr = Utilities.formatDate(today, tz, 'yyyy-MM-dd');

  for (var j = 0; j < videoIds.length; j += 50) {
    var batch2 = videoIds.slice(j, j + 50);
    try {
      var ar = YouTubeAnalytics.Reports.query({
        ids: 'channel==' + channelId,
        startDate: startStr, endDate: endStr,
        metrics: 'views,averageViewDuration,averageViewPercentage',
        dimensions: 'video',
        filters: 'video==' + batch2.join(',')
      });
      (ar.rows || []).forEach(function(row) {
        var vid = row[0];
        if (stats[vid]) {
          stats[vid].analyticsViews = row[1];
          stats[vid].avgViewDuration = row[2];
          stats[vid].avgViewPercentage = row[3];
        }
      });
    } catch (e) { Logger.log('[WARN] Analytics batch ' + (j / 50) + ': ' + e); }
  }

  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(YT_SHEET_TAB);
  if (!sheet) throw new Error('탭 "' + YT_SHEET_TAB + '" 없음');
  var lastRow = sheet.getLastRow();
  var existing = {};
  if (lastRow >= SHEET_DATA_START_ROW) {
    var n = lastRow - SHEET_DATA_START_ROW + 1;
    var rngVals = sheet.getRange(SHEET_DATA_START_ROW, 1, n, 9).getValues();
    for (var k = 0; k < rngVals.length; k++) {
      var link = String(rngVals[k][3] || '');
      var m = link.match(/youtu\.be\/([A-Za-z0-9_\-]{8,})/);
      if (m) existing[m[1]] = SHEET_DATA_START_ROW + k;
    }
  }

  var updates = [];
  var appendsBuffer = [];
  videoIds.forEach(function(vid) {
    var v = stats[vid];
    if (!v) return;
    var durSec = parseISO8601DurationSeconds(v.durationIso);
    var isShort = durSec > 0 && durSec <= 60;
    var aDate = v.publishedAt ? v.publishedAt.substring(0, 10) : '';
    var bFormat = isShort ? '네이티브_쇼츠' : '네이티브_피드';
    var cTopic = (v.title || '').substring(0, 80);
    var dLink = 'https://youtu.be/' + vid;
    var iNote = '';
    if (v.avgViewPercentage || v.avgViewDuration) {
      iNote = Math.round(v.avgViewPercentage || 0) + '% retention - '
            + Math.round(v.avgViewDuration || 0) + 's - cmt' + (v.comments || 0);
    }
    var cells = [aDate, bFormat, cTopic, dLink, v.views, v.likes, subscribers, iNote];
    if (existing[vid]) updates.push([existing[vid], cells]);
    else appendsBuffer.push({ publishedAt: v.publishedAt, cells: cells });
  });

  appendsBuffer.sort(function(a, b) { return (a.publishedAt || '').localeCompare(b.publishedAt || ''); });
  var appends = appendsBuffer.map(function(item) { return item.cells; });

  updates.forEach(function(pair) {
    sheet.getRange(pair[0], 1, 1, 7).setValues([pair[1].slice(0, 7)]);
    sheet.getRange(pair[0], 9, 1, 1).setValues([[pair[1][7]]]);
  });
  if (appends.length > 0) {
    var rows = appends.map(function(c) { return c.slice(0, 7).concat(['', c[7]]); });
    sheet.getRange(lastRow + 1, 1, rows.length, 9).setValues(rows);
  }

  var newLastRow = sheet.getLastRow();
  if (newLastRow > SHEET_DATA_START_ROW) {
    sheet.getRange(SHEET_DATA_START_ROW, 1, newLastRow - SHEET_DATA_START_ROW + 1, 9)
      .sort({column: 1, ascending: true});
  }

  Logger.log('=== sync 완료 (' + Math.round((new Date() - startTime) / 1000) + 's) ' +
    'updates=' + updates.length + ' appends=' + appends.length + ' ===');
  return { videosProcessed: videoIds.length, updates: updates.length, appends: appends.length };
}


// ============== ★ 자동 학습 — Markdown 생성 + Drive 저장 ==============

function generateYouTubeInsightsMarkdown() {
  Logger.log('=== generateYouTubeInsightsMarkdown 시작 ===');
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(YT_SHEET_TAB);
  if (!sheet) throw new Error('유튜브 시트 없음');

  var lastRow = sheet.getLastRow();
  if (lastRow < 2) { Logger.log('데이터 없음'); return; }

  var data = sheet.getRange(2, 1, lastRow - 1, 9).getValues();
  var videos = data.map(function(row) {
    var link = String(row[3] || '');
    var m = link.match(/youtu\.be\/([A-Za-z0-9_\-]{8,})/);
    return {
      date: row[0] instanceof Date ? Utilities.formatDate(row[0], 'Asia/Seoul', 'yyyy-MM-dd') : String(row[0] || ''),
      format: row[1] || '',
      title: String(row[2] || ''),
      link: link,
      videoId: m ? m[1] : '',
      views: Number(row[4]) || 0,
      likes: Number(row[5]) || 0,
      retention: parseRetentionFromNote_(String(row[8] || ''))
    };
  }).filter(function(v) { return v.title && v.views > 0; });

  if (videos.length === 0) { Logger.log('유효 영상 없음'); return; }

  var avgViews = Math.round(videos.reduce(function(s, v) { return s + v.views; }, 0) / videos.length);
  var withRet = videos.filter(function(v) { return v.retention > 0; });
  var avgRetention = withRet.length > 0
    ? (withRet.reduce(function(s, v) { return s + v.retention; }, 0) / withRet.length).toFixed(1)
    : '0';

  var topByViews = videos.slice().sort(function(a, b) { return b.views - a.views; }).slice(0, 10);
  var topByRetention = withRet.slice().sort(function(a, b) { return b.retention - a.retention; }).slice(0, 5);
  var outperformers = videos.filter(function(v) { return v.views > avgViews * 2; });
  var underperformers = videos.filter(function(v) { return v.views < avgViews * 0.3 && v.views > 0; });

  var insights = analyzeWithGemini_(topByViews, outperformers, underperformers);

  var stats = {
    topByViews: topByViews, topByRetention: topByRetention,
    outperformers: outperformers, underperformers: underperformers,
    avgViews: avgViews, avgRetention: avgRetention, totalCount: videos.length
  };

  var md = buildMarkdown_(insights, stats);
  saveToDrive_(md);

  Logger.log('=== Markdown 생성 + Drive 저장 완료 ===');
}

function parseRetentionFromNote_(note) {
  var m = note.match(/(\d+)% retention/);
  return m ? parseInt(m[1]) : 0;
}

function analyzeWithGemini_(topByViews, outperformers, underperformers) {
  var key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) {
    Logger.log('GEMINI_API_KEY 없음 → 폴백');
    return fallbackAnalyze_(topByViews);
  }
  var topTitles = topByViews.map(function(v) { return '[' + v.views + '회] ' + v.title; }).join('\n');
  var outTitles = outperformers.slice(0, 10).map(function(v) { return '[' + v.views + '회] ' + v.title; }).join('\n');
  var underTitles = underperformers.slice(0, 10).map(function(v) { return '[' + v.views + '회] ' + v.title; }).join('\n');

  var prompt = '폰스팟 (휴대폰 매장) 유튜브 채널 영상 성과 분석:\n\n' +
    '=== 조회수 상위 10개 ===\n' + topTitles + '\n\n' +
    '=== 평균 대비 2배 이상 (우수) ===\n' + (outTitles || '(없음)') + '\n\n' +
    '=== 평균 대비 30% 미만 (저조) ===\n' + (underTitles || '(없음)') + '\n\n' +
    'JSON 형식으로만 응답:\n' +
    '{\n' +
    '  "top_keywords": [{"keyword": "키워드", "count": 빈도, "avg_views": 평균조회수}],\n' +
    '  "hooking_patterns": [{"pattern": "패턴명", "examples": ["예시"]}],\n' +
    '  "outperformer_traits": ["우수 공통점1","공통점2"],\n' +
    '  "underperformer_traits": ["저조 공통점1"],\n' +
    '  "next_script_recommendation": "다음 스크립트 룰 3-4문장"\n' +
    '}\n\n' +
    '키워드: 한국어 명사, 휴대폰/통신 도메인. 조사 제거. 최대 15개.\n' +
    '후킹: 의문/숫자/감탄/시간/가격. 최대 5개.\n' +
    '권장: 카드뉴스/쇼츠 작성자에게 직접 조언.';

  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL + ':generateContent?key=' + key;
  var payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.3, response_mime_type: 'application/json' }
  };
  try {
    var res = UrlFetchApp.fetch(url, {
      method: 'POST', contentType: 'application/json',
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) {
      Logger.log('Gemini ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 500));
      return fallbackAnalyze_(topByViews);
    }
    var data = JSON.parse(res.getContentText());
    return JSON.parse(data.candidates[0].content.parts[0].text);
  } catch (e) {
    Logger.log('Gemini 실패: ' + e.message);
    return fallbackAnalyze_(topByViews);
  }
}

function fallbackAnalyze_(topByViews) {
  var stopwords = ['은','는','이','가','을','를','의','에','와','과','로','으로','도','만','폰스팟','쇼츠'];
  var wordCount = {};
  topByViews.forEach(function(v) {
    var words = v.title.split(/[\s,/!?.~()|]+/).filter(function(w) {
      return w.length >= 2 && stopwords.indexOf(w) === -1;
    });
    words.forEach(function(w) {
      if (!wordCount[w]) wordCount[w] = { count: 0, totalViews: 0 };
      wordCount[w].count++;
      wordCount[w].totalViews += v.views;
    });
  });
  var keywords = Object.keys(wordCount).map(function(k) {
    return { keyword: k, count: wordCount[k].count, avg_views: Math.round(wordCount[k].totalViews / wordCount[k].count) };
  }).sort(function(a, b) { return (b.count * b.avg_views) - (a.count * a.avg_views); }).slice(0, 15);

  return {
    top_keywords: keywords,
    hooking_patterns: [
      { pattern: '숫자 포함', examples: topByViews.filter(function(v) { return /\d/.test(v.title); }).slice(0, 3).map(function(v) { return v.title; }) },
      { pattern: '의문문', examples: topByViews.filter(function(v) { return /\?/.test(v.title); }).slice(0, 3).map(function(v) { return v.title; }) }
    ],
    outperformer_traits: ['(Gemini 비활성)'],
    underperformer_traits: [],
    next_script_recommendation: 'PropertiesService에 GEMINI_API_KEY 저장 시 정확 분석.'
  };
}

function buildMarkdown_(insights, stats) {
  var nowStr = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  var md = '';

  md += '# 폰스팟 유튜브 인사이트 (자동 학습)\n\n';
  md += '> **자동 생성** | 갱신: ' + nowStr + ' | 분석 영상 ' + stats.totalCount + '개 | 평균 조회수 ' + stats.avgViews.toLocaleString() + '회 | 평균 retention ' + stats.avgRetention + '%\n\n';
  md += '카드뉴스/쇼츠/뉴스 수집 시 이 파일 자동 Read → 스크립트·후보 선별에 반영.\n\n';
  md += '---\n\n';

  md += '## 💡 다음 스크립트 권장\n\n';
  md += insights.next_script_recommendation + '\n\n';
  md += '---\n\n';

  md += '## ★ Top 키워드 (스크립트 우선 반영, 후보 점수 +30%)\n\n';
  md += '| 키워드 | 빈도 | 평균 조회수 |\n|---|---|---|\n';
  insights.top_keywords.forEach(function(k) {
    md += '| ' + k.keyword + ' | ' + k.count + ' | ' + k.avg_views.toLocaleString() + ' |\n';
  });
  md += '\n---\n\n';

  md += '## ★ 후킹 패턴 (제목·도입부에 활용, 매치 시 +20%)\n\n';
  insights.hooking_patterns.forEach(function(p) {
    md += '### ' + p.pattern + '\n';
    (p.examples || []).forEach(function(ex) { md += '- ' + ex + '\n'; });
    md += '\n';
  });
  md += '---\n\n';

  md += '## ★ 우수 영상 공통점 (반영)\n\n';
  insights.outperformer_traits.forEach(function(t) { md += '- ✓ ' + t + '\n'; });
  md += '\n---\n\n';

  if (insights.underperformer_traits && insights.underperformer_traits.length > 0) {
    md += '## ★ 회피 패턴 (-40% 감점)\n\n';
    insights.underperformer_traits.forEach(function(t) { md += '- ✗ ' + t + '\n'; });
    md += '\n---\n\n';
  }

  md += '## Top 10 조회수 영상\n\n';
  stats.topByViews.forEach(function(v, i) {
    md += (i+1) + '. **[' + v.views.toLocaleString() + '회]** ' + v.title + ' — ' + v.link + '\n';
  });
  md += '\n---\n\n';

  if (stats.topByRetention.length > 0) {
    md += '## Top 5 시청 지속률 (retention)\n\n';
    stats.topByRetention.forEach(function(v, i) {
      md += (i+1) + '. **[' + v.retention + '%]** ' + v.title + ' (' + v.views.toLocaleString() + '회) — ' + v.link + '\n';
    });
    md += '\n---\n\n';
  }

  md += '## 매장 정합 우선순위 (휴대폰 도메인 보정)\n\n';
  md += '- 모델명 (갤럭시/아이폰 + 숫자) 강조\n';
  md += '- 가격/지원금/공시지원 우선\n';
  md += '- 통신사 (SKT/KT/LG) 키워드 적극\n';
  md += '- 매장 = 안양/광교 등 지역 노출 시 가중치 추가\n';

  return md;
}

function saveToDrive_(content) {
  var folders = DriveApp.getFoldersByName(INSIGHTS_DRIVE_FOLDER);
  var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(INSIGHTS_DRIVE_FOLDER);
  var files = folder.getFilesByName(INSIGHTS_FILE);
  if (files.hasNext()) {
    files.next().setContent(content);
    Logger.log('Drive 갱신: ' + INSIGHTS_DRIVE_FOLDER + '/' + INSIGHTS_FILE);
  } else {
    folder.createFile(INSIGHTS_FILE, content, MimeType.PLAIN_TEXT);
    Logger.log('Drive 생성: ' + INSIGHTS_DRIVE_FOLDER + '/' + INSIGHTS_FILE);
  }
}


// ============== Helper ==============

function parseISO8601DurationSeconds(s) {
  if (!s) return 0;
  var m = s.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!m) return 0;
  return (parseInt(m[1] || 0, 10) * 3600) + (parseInt(m[2] || 0, 10) * 60) + parseInt(m[3] || 0, 10);
}


// ============== 메뉴 / 트리거 ==============

function addYouTubeMenuItem() {
  SpreadsheetApp.getUi()
    .createMenu('🎥 유튜브 자동화')
    .addItem('🔄 지금 갱신 (데이터)', 'fetchYouTubeAnalyticsDaily')
    .addItem('🧠 인사이트 MD 생성', 'generateYouTubeInsightsMarkdown')
    .addSeparator()
    .addItem('⏰ Daily Trigger 설정', 'setupYouTubeTriggers')
    .addItem('📋 로그 보기', 'showLastLog')
    .addToUi();
}

function showLastLog() {
  SpreadsheetApp.getUi().alert('최근 실행 로그', Logger.getLog() || '(로그 없음)',
                               SpreadsheetApp.getUi().ButtonSet.OK);
}

/**
 * 매일 새벽 자동:
 *   - 03:30 fetchYouTubeAnalyticsDaily (데이터)
 *   - 03:40 generateYouTubeInsightsMarkdown (MD 생성 + Drive 저장)
 */
function setupYouTubeTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    var fn = t.getHandlerFunction();
    if (fn === 'fetchYouTubeAnalyticsDaily'
        || fn === 'generateYouTubeInsightsMarkdown') {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger('fetchYouTubeAnalyticsDaily')
    .timeBased().atHour(3).nearMinute(30).everyDays(1).inTimezone('Asia/Seoul').create();

  ScriptApp.newTrigger('generateYouTubeInsightsMarkdown')
    .timeBased().atHour(3).nearMinute(40).everyDays(1).inTimezone('Asia/Seoul').create();

  SpreadsheetApp.getUi().alert('트리거 2개 등록',
    '03:30 데이터 수집\n03:40 MD 인사이트 생성 + Drive 저장\n매일 새벽 자동.',
    SpreadsheetApp.getUi().ButtonSet.OK);
}

function createTimeDrivenTrigger() { setupYouTubeTriggers(); }