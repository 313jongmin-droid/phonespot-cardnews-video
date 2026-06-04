/**
 * YouTube Data + Analytics → '유튜브' 시트 sync.
 *
 * 매뉴얼 (ads/MANUAL.md) 정책 따름:
 *   - '유튜브' 시트 A:I 만 건드림 (K~P 자동 수식 영역 X)
 *   - A 날짜 / B 포맷 / C 주제 / D 링크 / E 조회수 / F 좋아요 / G 팔로워 / H 운영메모 / I 비고
 *   - video_id 로 dedup. 기존 행은 A~G, I 갱신 (H 유지). 새 영상은 새 행 append.
 *
 * Advanced Services 필요 (Apps Script Editor → Services + 버튼):
 *   - YouTube Data API v3   (identifier: YouTube)
 *   - YouTube Analytics API  (identifier: YouTubeAnalytics)
 *
 * 메뉴 통합: onOpen() 에 메뉴 항목 추가 (별도 함수 setupYouTubeMenu 참고)
 * 트리거: createTimeDrivenTrigger() 한 번 실행하면 매일 03:30 자동
 */

var YT_SHEET_TAB = '유튜브';
var SHEET_DATA_START_ROW = 2;


// ============== 메인 진입점 ==============

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
  var ss = SpreadsheetApp.openById('1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI');
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
  var updates = [];  // [rowNum, [A,B,C,D,E,F,G,I]]
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
      return c.slice(0, 7).concat(['', c[7]]);  // A..G + H(빈) + I
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

/**
 * 시트 「🛠 폰스팟 운영」 메뉴에 「🎬 YouTube stats 갱신」 항목 추가.
 * 기존 onOpen() 함수가 있으면 그 안에 다음 한 줄 추가:
 *
 *   .addItem('🎬 YouTube stats 갱신', 'fetchYouTubeAnalyticsDaily')
 *
 * 또는 이 함수를 onOpen 에서 호출.
 */
function addYouTubeMenuItem() {
  SpreadsheetApp.getUi()
    .createMenu('🎬 YouTube')
    .addItem('지금 갱신', 'fetchYouTubeAnalyticsDaily')
    .addItem('로그 보기', 'showLastLog')
    .addToUi();
}

function showLastLog() {
  var log = Logger.getLog();
  SpreadsheetApp.getUi().alert('최근 실행 로그', log || '(로그 없음)',
                               SpreadsheetApp.getUi().ButtonSet.OK);
}

/**
 * 매일 새벽 03:30 자동 실행 트리거 등록. 한 번만 실행.
 */
function createTimeDrivenTrigger() {
  // 기존 트리거 정리
  var triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(function(t) {
    if (t.getHandlerFunction() === 'fetchYouTubeAnalyticsDaily') {
      ScriptApp.deleteTrigger(t);
    }
  });
  // 새 트리거
  ScriptApp.newTrigger('fetchYouTubeAnalyticsDaily')
    .timeBased()
    .atHour(3)
    .nearMinute(30)
    .everyDays(1)
    .inTimezone('Asia/Seoul')
    .create();
  SpreadsheetApp.getUi().alert('트리거 등록됨', '매일 새벽 3:30 자동 실행됩니다',
                               SpreadsheetApp.getUi().ButtonSet.OK);
}
