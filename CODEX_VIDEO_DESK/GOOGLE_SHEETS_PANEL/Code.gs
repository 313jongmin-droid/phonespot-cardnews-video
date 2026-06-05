/**
 * PhoneSpot Google Sheets Control Panel
 *
 * Files:
 * - Code.gs
 * - Sidebar.html
 */

const PHONESPOT_SHEET_NAME = 'PhoneSpot 작업대장';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('폰스팟 제작')
    .addItem('제작 패널 열기', 'showPhoneSpotPanel')
    .addItem('작업대장 시트 만들기/정리', 'ensurePhoneSpotSheet')
    .addToUi();
}

function showPhoneSpotPanel() {
  ensurePhoneSpotSheet();
  const html = HtmlService.createHtmlOutputFromFile('Sidebar')
    .setTitle('폰스팟 제작 패널');
  SpreadsheetApp.getUi().showSidebar(html);
}

function ensurePhoneSpotSheet() {
  const ss = SpreadsheetApp.getActive();
  let sheet = ss.getSheetByName(PHONESPOT_SHEET_NAME);
  if (!sheet) sheet = ss.insertSheet(PHONESPOT_SHEET_NAME);

  const headers = [
    '날짜', '슬러그', '제목', '담당자',
    '카드뉴스 상태', '영상 상태', '필요 일러스트', '검수',
    '유튜브', '인스타', '틱톡', '결과', '메모', '업데이트'
  ];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, headers.length)
    .setFontWeight('bold')
    .setBackground('#111827')
    .setFontColor('#ffffff');
  formatPhoneSpotSheet_(sheet);
  return true;
}

function formatPhoneSpotSheet_(sheet) {
  const widths = [90, 260, 320, 90, 110, 130, 120, 90, 90, 90, 90, 220, 260, 150];
  widths.forEach((w, i) => sheet.setColumnWidth(i + 1, w));
  sheet.getRange('A:N').setVerticalAlignment('middle');
  sheet.getRange('A:N').setWrapStrategy(SpreadsheetApp.WrapStrategy.CLIP);
  sheet.getRange('B:B').setFontWeight('bold');
  sheet.getRange('F:F').setBackground('#fff7ed');
  sheet.getRange('H:H').setBackground('#f0fdf4');
  if (!sheet.getFilter()) {
    const lastRow = Math.max(sheet.getLastRow(), 2);
    sheet.getRange(1, 1, lastRow, 14).createFilter();
  }
}

function getRowsForSidebar() {
  ensurePhoneSpotSheet();
  const sheet = SpreadsheetApp.getActive().getSheetByName(PHONESPOT_SHEET_NAME);
  const values = sheet.getDataRange().getValues();
  if (values.length <= 1) return [];
  const headers = values[0];
  return values.slice(1).filter(row => row[1]).map((row, idx) => {
    const item = { rowNumber: idx + 2 };
    headers.forEach((h, i) => item[h] = row[i]);
    return item;
  });
}

function upsertRowsFromLocal(slugs) {
  ensurePhoneSpotSheet();
  const sheet = SpreadsheetApp.getActive().getSheetByName(PHONESPOT_SHEET_NAME);
  const existing = sheet.getDataRange().getValues();
  const bySlug = {};
  for (let i = 1; i < existing.length; i++) {
    const slug = existing[i][1];
    if (slug) bySlug[slug] = i + 1;
  }
  const now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
  if (!slugs || !slugs.length) {
    setQueueNotice('로컬 엔진에서 슬러그를 받지 못했습니다. 로컬 엔진 실행, 카드뉴스 동기화, 포트를 확인하세요.');
    return { ok: true, count: 0 };
  }
  (slugs || []).forEach(s => {
    const row = [
      s.date || '', s.slug || '', '', '',
      s.flag || '', '', '', '',
      '', '', '', '', '', now
    ];
    if (bySlug[s.slug]) {
      const r = bySlug[s.slug];
      sheet.getRange(r, 1).setValue(row[0]);
      sheet.getRange(r, 5).setValue(row[4]);
      sheet.getRange(r, 14).setValue(now);
    } else {
      sheet.appendRow(row);
    }
  });
  formatPhoneSpotSheet_(sheet);
  return { ok: true, count: (slugs || []).length };
}

function markActionResult(slug, action, ok, message) {
  ensurePhoneSpotSheet();
  const sheet = SpreadsheetApp.getActive().getSheetByName(PHONESPOT_SHEET_NAME);
  const values = sheet.getDataRange().getValues();
  const now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
  const statusMap = {
    video_prepare: ok ? '프롬프트 준비됨' : '프롬프트 실패',
    video_import_render: ok ? '렌더 시작됨' : '렌더 실패',
    video_render_selected: ok ? '재렌더 시작됨' : '재렌더 실패',
    system_update: ok ? '업데이트 시작됨' : '업데이트 실패',
  };
  for (let i = 1; i < values.length; i++) {
    if (values[i][1] === slug) {
      sheet.getRange(i + 1, 6).setValue(statusMap[action] || (ok ? action : '실패'));
      sheet.getRange(i + 1, 13).setValue(message || '');
      sheet.getRange(i + 1, 14).setValue(now);
      return { ok: true };
    }
  }
  sheet.appendRow(['', slug, '', '', '', statusMap[action] || action, '', '', '', '', '', '', message || '', now]);
  return { ok: true };
}

function markReview(slug, value) {
  ensurePhoneSpotSheet();
  const sheet = SpreadsheetApp.getActive().getSheetByName(PHONESPOT_SHEET_NAME);
  const values = sheet.getDataRange().getValues();
  const now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
  for (let i = 1; i < values.length; i++) {
    if (values[i][1] === slug) {
      sheet.getRange(i + 1, 8).setValue(value);
      sheet.getRange(i + 1, 14).setValue(now);
      return { ok: true };
    }
  }
  sheet.appendRow(['', slug, '', '', '', '', '', value, '', '', '', '', '', now]);
  return { ok: true };
}


function setQueueNotice(message) {
  ensurePhoneSpotSheet();
  const sheet = SpreadsheetApp.getActive().getSheetByName(PHONESPOT_SHEET_NAME);
  const now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
  sheet.getRange(2, 1, 1, 14).setValues([[
    now,
    'SYSTEM_NOTICE',
    message || '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '시스템 안내 행입니다. 슬러그 새로고침이 성공하면 실제 데이터가 아래/위에 채워집니다.',
    now
  ]]);
  sheet.getRange(2, 1, 1, 14).setBackground('#fff7ed').setFontColor('#9a3412');
  return { ok: true };
}
