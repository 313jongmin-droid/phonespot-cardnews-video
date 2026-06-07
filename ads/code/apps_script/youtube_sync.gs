/**
 * YouTube Data + Analytics → '유튜브' 시트 sync.
 * + 자동 학습 (인사이트 생성) — '유튜브_인사이트' 시트
 *
 * 매뉴얼 (ads/MANUAL.md) 정책 따름:
 *   - '유튜브' 시트 A:I 만 건드림 (K~P 자동 수식 영역 X)
 *   - A 날짜 / B 포맷 / C 주제 / D 링크 / E 조회수 / F 좋아요 / G 팔로워 / H 운영메모 / I 비고
 *   - video_id 로 dedup. 기존 행은 A~G, I 갱신 (H 유지). 새 영상은 새 행 append.
 *
 * 자동 학습 (2026-06-05 추가):
 *   - generateYouTubeInsights() 매일 03:40 자동 실행
 *   - 우수 영상 → 키워드/후킹/패턴 추출 (Gemini API)
 *   - "유튜브_인사이트" 시트 자동 갱신
 *   - cardnews/shorts task가 이 시트 읽고 스크립트에 반영
 *
 * Advanced Services 필요 (Apps Script Editor → Services + 버튼):
 *   - YouTube Data API v3   (identifier: YouTube)
 *   - YouTube Analytics API  (identifier: YouTubeAnalytics)
 *
 * PropertiesService 키 (선택):
 *   - GEMINI_API_KEY: 미설정 시 폴백 (단순 공백 분리) 작동
 */

var YT_SHEET_TAB = '유튜브';
var YT_INSIGHTS_TAB = '유튜브_인사이트';
var SHEET_DATA_START_ROW = 2;
var GEMINI_MODEL = 'gemini-2.5-flash';
var SHEET_ID = '1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI';


// ============== 메인 진입점 — 데이터 수집 ==============

function fetchYouTubeAnalyticsDaily() {
  var startTime = new Date();
  Logger.log('=== YouTube sync 시작 ' + startTime.toLocaleString('ko-KR') + ' ===');

  // 1) 채널 정보
  var chResp = YouTube.Channels.list('id,snippet,statistics,contentDetails', {mine: true});
  if (!chResp.items || chResp.items.length === 0) {
    throw new Error('인증된 사용자에 채널이 없습니다');
  }
  var channel = chResp.items[0];
  var channelId = channel.id;
  var channelTitle = channel.snippet.title;
  var subscribers = parseInt(channel.statistics.subscriberCount || 0, 10);
  var uploadsPlaylistId = channel.contentDetails.relatedPlaylists.uploads;

  Logger.log('채널: ' + channelTitle + ' (구독자 ' + subscribers + ')');

  // 2) 전체 영상 ID 수집 (페이지네이션)
  var videoIds = [];
  var pageToken = null;
  do {
    var r = YouTube.PlaylistItems.list('contentDetails', {
      playlistId: uploadsPlaylistId,
      maxResults: 50,
      pageToken: pageToken
    });
    (r.items || []).forEach(function(it) {
      videoIds.push(it.contentDetails.videoId);
    });
    pageToken = r.nextPageToken;
  } while (pageToken && videoIds.length < 500);

  Logger.log('영상 ' + videoIds.length + '개 발견');
  if (videoIds.length === 0) {
    Logger.log('영상 없음 - 종료');
    return {updates: 0, appends: 0};
  }

  // 3) 각 영상 stats (batches of 50)
  var stats = {};
  for (var i = 0; i < videoIds.length; i += 50) {
    var batch = videoIds.slice(i, i + 50);
    var resp = YouTube.Videos.list('snippet,statistics,contentDetails', {
      id: batch.join(',')
    });
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

  // 4) Analytics: 최근 30일 영상별 avgViewDuration / avgViewPercentage
  var today = new Date();
  var start = new Date(today);
  start.setDate(start.getDate() - 30);
  var tz = 'Asia/Seoul';
  var startStr = Utilities.formatDate(start, tz, 'yyyy-MM-dd');
  var endStr = Utilities.formatDate(today, tz, 'yyyy-MM-dd');

  for (var j = 0; j < videoIds.length; j += 50) {
    var batch2 = videoIds.slice(j, j + 50);
    try {
      var ar = YouTubeAnalytics.Reports.query({
        ids: 'channel==' + channelId,
        startDate: startStr,
        endDate: endStr,
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
    } catch (e) {
      Logger.log('[WARN] Analytics batch ' + (j / 50) + ' 실패: ' + e);
    }
  }

  // 5) 시트 기존 행 읽기 + dedup map
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(YT_SHEET_TAB);
  if (!sheet) {
    throw new Error('탭 "' + YT_SHEET_TAB + '" 를 찾을 수 없음');
  }
  var lastRow = sheet.getLastRow();
  var existing = {};
  if (lastRow >= SHEET_DATA_START_ROW) {
    var n = lastRow - SHEET_DATA_START_ROW + 1;
    var rngVals = sheet.getRange(SHEET_DATA_START_ROW, 1, n, 9).getValues();
    for (var k = 0; k < rngVals.length; k++) {
      var link = String(rngVals[k][3] || '');
      var m = link.match(/youtu\.be\/([A-Za-z0-9_\-]{8,})/);
      if (m) {
        existing[m[1]] = SHEET_DATA_START_ROW + k;
      }
    }
  }
  Logger.log('시트 기존 행 ' + lastRow + ' / 매칭 ' + Object.keys(existing).length);

  // 6) updates vs appends 분류
  var updates = [];
  var appends = [];

  videoIds.forEach(function(vid) {
    var v = stats[vid];
    if (!v) return;

    var durSec = parseISO8601DurationSeconds(v.durationIso);
    var isShort = durSec > 0 && durSec <= 60;

    var aDate = v.publishedAt ? v.publishedAt.substring(0, 10) : '';
    var bFormat = isShort ? '네이티브_쇼츠' : '네이티브_피드';
    var cTopic = (v.title || '').substring(0, 80);
    var dLink = 'https://youtu.be/' + vid;
    var eViews = v.views;
    var fLikes = v.likes;
    var gSubs = subscribers;

    var iNote = '';
    if (v.avgViewPercentage || v.avgViewDuration) {
      iNote = Math.round(v.avgViewPercentage || 0) + '% retention - '
            + Math.round(v.avgViewDuration || 0) + 's - cmt' + (v.comments || 0);
    }

    var cells = [aDate, bFormat, cTopic, dLink, eViews, fLikes, gSubs, iNote];

    if (existing[vid]) {
      updates.push([existing[vid], cells]);
    } else {
      appends.push(cells);
    }
  });

  Logger.log('계획: updates=' + updates.length + ' appends=' + appends.length);

  // 7) Updates apply (A:G 와 I 별도 - H 절대 안 건드림)
  updates.forEach(function(pair) {
    var rowNum = pair[0];
    var cells = pair[1];
    sheet.getRange(rowNum, 1, 1, 7).setValues([cells.slice(0, 7)]);
    sheet.getRange(rowNum, 9, 1, 1).setValues([[cells[7]]]);
  });

  // 8) Appends apply (한 번에 batch)
  if (appends.length > 0) {
    var rows = appends.map(function(c) {
      return c.slice(0, 7).concat(['', c[7]]);
    });
    sheet.getRange(lastRow + 1, 1, rows.length, 9).setValues(rows);
  }

  var elapsed = Math.round((new Date() - startTime) / 1000);
  Logger.log('=== 완료 (' + elapsed + 's) updates=' + updates.length
           + ' appends=' + appends.length + ' ===');

  return {
    channelTitle: channelTitle,
    subscribers: subscribers,
    videosProcessed: videoIds.length,
    updates: updates.length,
    appends: appends.length
  };
}


// ============== ★ 자동 학습 — 인사이트 생성 ==============

function generateYouTubeInsights() {
  Logger.log('=== generateYouTubeInsights 시작 ===');
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(YT_SHEET_TAB);
  if (!sheet) throw new Error('유튜브 시트 없음');

  var lastRow = sheet.getLastRow();
  if (lastRow < 2) { Logger.log('데이터 없음'); return; }

  // 1) 데이터 읽기
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

  // 2) 평균 계산
  var avgViews = Math.round(videos.reduce(function(s, v) { return s + v.views; }, 0) / videos.length);
  var withRet = videos.filter(function(v) { return v.retention > 0; });
  var avgRetention = withRet.length > 0
    ? (withRet.reduce(function(s, v) { return s + v.retention; }, 0) / withRet.length).toFixed(1)
    : '0';

  // 3) 우수/저조 선별
  var topByViews = videos.slice().sort(function(a, b) { return b.views - a.views; }).slice(0, 10);
  var topByRetention = withRet.slice().sort(function(a, b) { return b.retention - a.retention; }).slice(0, 5);
  var outperformers = videos.filter(function(v) { return v.views > avgViews * 2; });
  var underperformers = videos.filter(function(v) { return v.views < avgViews * 0.3 && v.views > 0; });

  Logger.log('avgViews=' + avgViews + ' avgRet=' + avgRetention + '% out=' + outperformers.length + ' under=' + underperformers.length);

  // 4) Gemini API 분석
  var insights = analyzeWithGemini_(topByViews, outperformers, underperformers);

  // 5) 인사이트 시트 갱신
  writeInsightsSheet_(insights, {
    topByViews: topByViews,
    topByRetention: topByRetention,
    outperformers: outperformers,
    underperformers: underperformers,
    avgViews: avgViews,
    avgRetention: avgRetention,
    totalCount: videos.length
  });

  Logger.log('=== 인사이트 생성 완료 ===');
}

function parseRetentionFromNote_(note) {
  var m = note.match(/(\d+)% retention/);
  return m ? parseInt(m[1]) : 0;
}

function analyzeWithGemini_(topByViews, outperformers, underperformers) {
  var key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) {
    Logger.log('GEMINI_API_KEY 없음 → 폴백 (단순 분리)');
    return fallbackAnalyze_(topByViews);
  }

  var topTitles = topByViews.map(function(v) { return '[' + v.views + '회] ' + v.title; }).join('\n');
  var outTitles = outperformers.slice(0, 10).map(function(v) { return '[' + v.views + '회] ' + v.title; }).join('\n');
  var underTitles = underperformers.slice(0, 10).map(function(v) { return '[' + v.views + '회] ' + v.title; }).join('\n');

  var prompt = '폰스팟 (휴대폰 매장) 유튜브 채널 영상 성과 분석. 다음 영상들을 보고 한국어로 분석:\n\n' +
    '=== 조회수 상위 10개 ===\n' + topTitles + '\n\n' +
    '=== 평균 대비 2배 이상 (우수) ===\n' + (outTitles || '(없음)') + '\n\n' +
    '=== 평균 대비 30% 미만 (저조) ===\n' + (underTitles || '(없음)') + '\n\n' +
    '다음 JSON 형식으로만 응답 (다른 텍스트 X):\n' +
    '{\n' +
    '  "top_keywords": [{"keyword": "키워드", "count": 빈도, "avg_views": 평균조회수}],\n' +
    '  "hooking_patterns": [{"pattern": "패턴명", "examples": ["예시1","예시2"]}],\n' +
    '  "outperformer_traits": ["우수 공통점1","공통점2","공통점3"],\n' +
    '  "underperformer_traits": ["저조 공통점1","공통점2"],\n' +
    '  "next_script_recommendation": "다음 스크립트에 반영해야 할 룰. 3-4문장."\n' +
    '}\n\n' +
    '키워드: 한국어 명사 위주. 조사/어미 제거. 휴대폰/통신 도메인 우선. 최대 15개.\n' +
    '후킹 패턴: 의문/숫자/감탄/시간/가격 등. 최대 5개.\n' +
    '권장: 카드뉴스/쇼츠 스크립트 작성자에게 줄 직접적 조언.';

  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + GEMINI_MODEL + ':generateContent?key=' + key;
  var payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: {
      temperature: 0.3,
      response_mime_type: 'application/json'
    }
  };

  try {
    var res = UrlFetchApp.fetch(url, {
      method: 'POST',
      contentType: 'application/json',
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });
    var code = res.getResponseCode();
    if (code !== 200) {
      Logger.log('Gemini API ' + code + ': ' + res.getContentText().slice(0, 500));
      return fallbackAnalyze_(topByViews);
    }
    var data = JSON.parse(res.getContentText());
    var text = data.candidates[0].content.parts[0].text;
    return JSON.parse(text);
  } catch (e) {
    Logger.log('Gemini 실패: ' + e.message);
    return fallbackAnalyze_(topByViews);
  }
}

function fallbackAnalyze_(topByViews) {
  var stopwords = ['은','는','이','가','을','를','의','에','와','과','로','으로','도','만','부터','까지','보다','처럼','이런','그런','저런','폰스팟','쇼츠'];
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
    outperformer_traits: ['(Gemini 비활성 — 단순 분석 결과만 표시)'],
    underperformer_traits: [],
    next_script_recommendation: 'PropertiesService에 GEMINI_API_KEY 저장하면 더 정확한 분석 가능 (Apps Script → 프로젝트 설정 → 스크립트 속성).'
  };
}

function writeInsightsSheet_(insights, stats) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ss.getSheetByName(YT_INSIGHTS_TAB);
  if (!sh) {
    sh = ss.insertSheet(YT_INSIGHTS_TAB);
  }
  sh.clear();
  sh.clearConditionalFormatRules();

  var r = 1;

  // 헤더
  sh.getRange(r, 1, 1, 4).merge()
    .setValue('🎬 유튜브 인사이트 — 자동 학습 결과')
    .setBackground('#1F4E78').setFontColor('#FFFFFF')
    .setFontWeight('bold').setFontSize(14).setHorizontalAlignment('center');
  r++;

  sh.getRange(r, 1, 1, 4).merge()
    .setValue('갱신: ' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm') +
              ' | 분석 영상: ' + stats.totalCount + '개' +
              ' | 평균 조회수: ' + stats.avgViews.toLocaleString() + '회' +
              ' | 평균 retention: ' + stats.avgRetention + '%')
    .setFontStyle('italic').setFontColor('#666').setHorizontalAlignment('center');
  r += 2;

  // 1) 권장 (맨 위 강조)
  sh.getRange(r, 1, 1, 4).merge()
    .setValue('💡 다음 스크립트 권장')
    .setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold').setHorizontalAlignment('center');
  r++;
  sh.getRange(r, 1, 1, 4).merge().setValue(insights.next_script_recommendation).setWrap(true).setVerticalAlignment('top');
  sh.setRowHeight(r, 80);
  r += 2;

  // 2) Top 키워드
  sh.getRange(r, 1, 1, 4).merge().setValue('★ Top 키워드 (스크립트에 우선 반영)').setBackground('#FFE699').setFontWeight('bold');
  r++;
  sh.getRange(r, 1, 1, 3).setValues([['키워드', '빈도', '평균 조회수']]).setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center');
  r++;
  var startKwR = r;
  insights.top_keywords.forEach(function(k) {
    sh.getRange(r, 1, 1, 3).setValues([[k.keyword, k.count, k.avg_views]]);
    r++;
  });
  sh.getRange(startKwR, 1, insights.top_keywords.length, 3).setBorder(true,true,true,true,true,true);
  r++;

  // 3) 후킹 패턴
  sh.getRange(r, 1, 1, 4).merge().setValue('★ 후킹 패턴').setBackground('#FFE699').setFontWeight('bold');
  r++;
  insights.hooking_patterns.forEach(function(p) {
    sh.getRange(r, 1).setValue(p.pattern).setFontWeight('bold');
    sh.getRange(r, 2, 1, 3).merge().setValue((p.examples || []).join(' | ')).setWrap(true);
    sh.setRowHeight(r, 30);
    r++;
  });
  r++;

  // 4) 우수 영상 공통점
  sh.getRange(r, 1, 1, 4).merge().setValue('★ 우수 영상 공통점').setBackground('#C8E6C9').setFontWeight('bold');
  r++;
  insights.outperformer_traits.forEach(function(t) {
    sh.getRange(r, 1, 1, 4).merge().setValue('  ✓ ' + t);
    r++;
  });
  r++;

  // 5) 저조 패턴 (회피)
  if (insights.underperformer_traits && insights.underperformer_traits.length > 0) {
    sh.getRange(r, 1, 1, 4).merge().setValue('★ 저조 영상 패턴 (회피)').setBackground('#FFCDD2').setFontWeight('bold');
    r++;
    insights.underperformer_traits.forEach(function(t) {
      sh.getRange(r, 1, 1, 4).merge().setValue('  ✗ ' + t);
      r++;
    });
    r++;
  }

  // 6) Top 10 조회수 영상
  sh.getRange(r, 1, 1, 4).merge().setValue('★ Top 10 조회수 영상').setBackground('#FFE699').setFontWeight('bold');
  r++;
  sh.getRange(r, 1, 1, 4).setValues([['제목', '조회수', '날짜', '링크']]).setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center');
  r++;
  var startTopR = r;
  stats.topByViews.forEach(function(v) {
    sh.getRange(r, 1, 1, 4).setValues([[v.title, v.views, v.date, v.link]]);
    r++;
  });
  sh.getRange(startTopR, 1, stats.topByViews.length, 4).setBorder(true,true,true,true,true,true);
  r++;

  // 7) Top 5 retention
  if (stats.topByRetention.length > 0) {
    sh.getRange(r, 1, 1, 4).merge().setValue('★ Top 5 시청 지속률 (retention)').setBackground('#FFE699').setFontWeight('bold');
    r++;
    sh.getRange(r, 1, 1, 4).setValues([['제목', '조회수', 'retention%', '링크']]).setBackground('#D9E1F2').setFontWeight('bold').setHorizontalAlignment('center');
    r++;
    var startRetR = r;
    stats.topByRetention.forEach(function(v) {
      sh.getRange(r, 1, 1, 4).setValues([[v.title, v.views, v.retention + '%', v.link]]);
      r++;
    });
    sh.getRange(startRetR, 1, stats.topByRetention.length, 4).setBorder(true,true,true,true,true,true);
  }

  // 컬럼 너비
  sh.setColumnWidth(1, 320);
  sh.setColumnWidth(2, 100);
  sh.setColumnWidth(3, 100);
  sh.setColumnWidth(4, 260);
  sh.setFrozenRows(2);
}


// ============== Helper ==============

function parseISO8601DurationSeconds(s) {
  if (!s) return 0;
  var m = s.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!m) return 0;
  return (parseInt(m[1] || 0, 10) * 3600)
       + (parseInt(m[2] || 0, 10) * 60)
       + parseInt(m[3] || 0, 10);
}


// ============== 메뉴 / 트리거 셋업 ==============

function addYouTubeMenuItem() {
  SpreadsheetApp.getUi()
    .createMenu('🎬 YouTube')
    .addItem('🔄 지금 갱신 (데이터)', 'fetchYouTubeAnalyticsDaily')
    .addItem('🧠 인사이트 생성 (지금)', 'generateYouTubeInsights')
    .addSeparator()
    .addItem('⏰ Daily Trigger 설정', 'setupYouTubeTriggers')
    .addItem('📋 로그 보기', 'showLastLog')
    .addToUi();
}

function showLastLog() {
  var log = Logger.getLog();
  SpreadsheetApp.getUi().alert('최근 실행 로그', log || '(로그 없음)',
                               SpreadsheetApp.getUi().ButtonSet.OK);
}

/**
 * 매일 새벽 트리거 2개:
 *   - 03:30 fetchYouTubeAnalyticsDaily (데이터 수집)
 *   - 03:40 generateYouTubeInsights (인사이트 자동 학습)
 */
function setupYouTubeTriggers() {
  // 기존 트리거 정리
  ScriptApp.getProjectTriggers().forEach(function(t) {
    var fn = t.getHandlerFunction();
    if (fn === 'fetchYouTubeAnalyticsDaily' || fn === 'generateYouTubeInsights') {
      ScriptApp.deleteTrigger(t);
    }
  });

  // 데이터 수집 03:30
  ScriptApp.newTrigger('fetchYouTubeAnalyticsDaily')
    .timeBased().atHour(3).nearMinute(30).everyDays(1).inTimezone('Asia/Seoul').create();

  // 인사이트 생성 03:40
  ScriptApp.newTrigger('generateYouTubeInsights')
    .timeBased().atHour(3).nearMinute(40).everyDays(1).inTimezone('Asia/Seoul').create();

  SpreadsheetApp.getUi().alert('트리거 2개 등록됨',
    '03:30 데이터 수집 (fetchYouTubeAnalyticsDaily)\n03:40 인사이트 생성 (generateYouTubeInsights)\n매일 새벽 자동 실행.',
    SpreadsheetApp.getUi().ButtonSet.OK);
}

// 구버전 호환 (기존 트리거 함수)
function createTimeDrivenTrigger() {
  setupYouTubeTriggers();
}
