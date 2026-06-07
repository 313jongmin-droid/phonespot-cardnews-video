/**
 * PhoneSpot Google Sheets - Work Queue Web API
 *
 * 이 파일은 기존 Code.gs 를 건드리지 않는 "추가 파일" 입니다.
 * Apps Script 에서 새 스크립트 파일 `Api.gs` 를 만들고 이 내용을 붙여넣으세요.
 *
 * 목적: 각 PC 의 로컬 동기화 스크립트(sheets_sync.py)가 HTTPS 로
 *       작업 큐(작업대장 시트)를 읽고/쓰게 해서, 시트를 "큐 마스터"로 만든다.
 *
 * 배포: 배포 > 새 배포 > 유형 "웹 앱"
 *       - 실행: 나(스크립트 소유자)
 *       - 액세스 권한: 링크가 있는 모든 사용자
 *       배포 후 나오는 .../exec URL 을 sheets_endpoint.txt 1번째 줄에 넣는다.
 *
 * 보안: 스크립트 속성(PHONESPOT_TOKEN)에 토큰을 넣으면 그 토큰을 가진 요청만
 *       쓰기/읽기가 됩니다. 토큰을 안 넣으면 누구나 접근 가능하니 반드시 설정 권장.
 *       (프로젝트 설정 > 스크립트 속성 > PHONESPOT_TOKEN = 임의의 긴 문자열)
 */

// Code.gs 의 PHONESPOT_SHEET_NAME 과 충돌하지 않도록 별도 이름 사용.
var API_SHEET_NAME = 'PhoneSpot 작업대장';
var API_HEADERS = [
  '날짜', '슬러그', '제목', '담당자',
  '카드뉴스 상태', '영상 상태', '필요 일러스트', '검수',
  '유튜브', '인스타', '틱톡', '결과', '메모', '업데이트'
];

function api_token_() {
  return PropertiesService.getScriptProperties().getProperty('PHONESPOT_TOKEN') || '';
}

function api_checkToken_(token) {
  var expected = api_token_();
  if (!expected) return true; // 토큰 미설정 시 통과(설정 강력 권장)
  return String(token || '') === expected;
}

function api_sheet_() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(API_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(API_SHEET_NAME);
    sheet.getRange(1, 1, 1, API_HEADERS.length).setValues([API_HEADERS]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function api_colIndex_(header) {
  var i = API_HEADERS.indexOf(header);
  return i < 0 ? -1 : i + 1; // 1-based
}

function api_json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/** 시트 전체 행을 {헤더:값} 객체 배열로 반환 */
function api_readRows_() {
  var sheet = api_sheet_();
  var values = sheet.getDataRange().getValues();
  if (values.length <= 1) return [];
  var headers = values[0];
  var out = [];
  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    var slug = row[1]; // B열 = 슬러그
    if (!slug) continue;
    var item = { rowNumber: r + 1 };
    for (var c = 0; c < headers.length; c++) {
      item[headers[c]] = row[c];
    }
    out.push(item);
  }
  return out;
}

/**
 * upsert: items = [{ slug: '...', fields: { '헤더': 값, ... } }]
 * 지정된 칸만 갱신, 슬러그 없으면 새 행 추가. '업데이트' 칸은 자동 기록.
 */
function api_upsert_(items) {
  var sheet = api_sheet_();
  var values = sheet.getDataRange().getValues();
  var bySlug = {};
  for (var i = 1; i < values.length; i++) {
    var s = values[i][1];
    if (s) bySlug[s] = i + 1; // 1-based row
  }
  var now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
  var updateCol = api_colIndex_('업데이트');
  var slugCol = api_colIndex_('슬러그');
  var changed = 0;

  (items || []).forEach(function (it) {
    var slug = it && it.slug;
    if (!slug) return;
    var fields = it.fields || {};
    var rowNum = bySlug[slug];
    if (!rowNum) {
      // 새 행 추가
      var blank = new Array(API_HEADERS.length).fill('');
      blank[slugCol - 1] = slug;
      sheet.appendRow(blank);
      rowNum = sheet.getLastRow();
      bySlug[slug] = rowNum;
    }
    Object.keys(fields).forEach(function (header) {
      var col = api_colIndex_(header);
      if (col > 0) sheet.getRange(rowNum, col).setValue(fields[header]);
    });
    if (updateCol > 0) sheet.getRange(rowNum, updateCol).setValue(now);
    changed++;
  });
  return changed;
}

function doGet(e) {
  var p = (e && e.parameter) || {};
  if (!api_checkToken_(p.token)) {
    return api_json_({ ok: false, error: 'invalid token' });
  }
  // 기본 동작 = 행 읽기 (헬스체크 겸용)
  return api_json_({ ok: true, op: 'pull', rows: api_readRows_() });
}

function doPost(e) {
  var body = {};
  try {
    if (e && e.postData && e.postData.contents) {
      body = JSON.parse(e.postData.contents);
    }
  } catch (err) {
    return api_json_({ ok: false, error: 'bad json' });
  }
  if (!api_checkToken_(body.token)) {
    return api_json_({ ok: false, error: 'invalid token' });
  }
  var op = body.op || 'pull';
  if (op === 'pull') {
    return api_json_({ ok: true, op: 'pull', rows: api_readRows_() });
  }
  if (op === 'push' || op === 'migrate') {
    var changed = api_upsert_(body.items || []);
    return api_json_({ ok: true, op: op, changed: changed });
  }
  return api_json_({ ok: false, error: 'unknown op: ' + op });
}
