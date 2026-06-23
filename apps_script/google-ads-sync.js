/**
 * 구글 Ads API 자동수집 (2026-06-19 신설) — 메타 패턴의 구글판
 *
 * 역할: 구글+ 시트의 D(노출)/E(클릭)/F(지출)을 Google Ads API로 자동 채움.
 *       (기존 google-sync.js 는 GA4 매칭(G~P) 담당. 이 파일은 운영데이터(D~F) 담당.)
 *
 * 흐름: refresh_token -> access_token -> searchStream(GAQL, ad_group 단위, segments.date)
 *       -> (날짜+광고그룹명) 키로 구글+ A~F upsert -> syncGoogleGA4() 호출해 G~P 수식 재적용.
 *
 * 사전 - 스크립트 속성 6개 (값 채팅 노출 금지):
 *   GOOGLE_ADS_DEVELOPER_TOKEN / CLIENT_ID / CLIENT_SECRET / REFRESH_TOKEN
 *   GOOGLE_ADS_LOGIN_CUSTOMER_ID(MCC, 숫자만) / GOOGLE_ADS_CUSTOMER_ID(광고계정, 숫자만)
 *
 * 전제: CUSTOMER_ID 계정이 MCC(LOGIN_CUSTOMER_ID) 아래 연결돼야 함. 미연결 시 USER_PERMISSION_DENIED.
 * 통화: 한국 계정 cost_micros / 1,000,000 = 원.
 */

var GADS_API_VERSION = 'v23';
var GADS_SHEET = '구글+';

function _gadsAccessToken_() {
  const p = PropertiesService.getScriptProperties();
  const cid = p.getProperty('GOOGLE_ADS_CLIENT_ID');
  const sec = p.getProperty('GOOGLE_ADS_CLIENT_SECRET');
  const ref = p.getProperty('GOOGLE_ADS_REFRESH_TOKEN');
  if (!cid || !sec || !ref) throw new Error('Script Property 누락: CLIENT_ID/SECRET/REFRESH_TOKEN');
  const res = UrlFetchApp.fetch('https://oauth2.googleapis.com/token', {
    method: 'post',
    payload: { client_id: cid, client_secret: sec, refresh_token: ref, grant_type: 'refresh_token' },
    muteHttpExceptions: true
  });
  const code = res.getResponseCode();
  const body = res.getContentText();
  if (code !== 200) throw new Error('토큰 갱신 실패(' + code + '): ' + body.slice(0, 300));
  return JSON.parse(body).access_token;
}

function _gadsSearch_(gaql) {
  const p = PropertiesService.getScriptProperties();
  const dev = p.getProperty('GOOGLE_ADS_DEVELOPER_TOKEN');
  const login = String(p.getProperty('GOOGLE_ADS_LOGIN_CUSTOMER_ID') || '').replace(/[^0-9]/g, '');
  const cust = String(p.getProperty('GOOGLE_ADS_CUSTOMER_ID') || '').replace(/[^0-9]/g, '');
  if (!dev) throw new Error('Script Property 누락: DEVELOPER_TOKEN');
  if (!cust) throw new Error('Script Property 누락: CUSTOMER_ID');
  const token = _gadsAccessToken_();
  const url = 'https://googleads.googleapis.com/' + GADS_API_VERSION + '/customers/' + cust + '/googleAds:searchStream';
  const headers = { 'Authorization': 'Bearer ' + token, 'developer-token': dev };
  if (login) headers['login-customer-id'] = login;
  const res = UrlFetchApp.fetch(url, {
    method: 'post', contentType: 'application/json',
    headers: headers, payload: JSON.stringify({ query: gaql }),
    muteHttpExceptions: true
  });
  const code = res.getResponseCode();
  const body = res.getContentText();
  if (code !== 200) {
    let hint = '';
    if (/USER_PERMISSION_DENIED/.test(body)) hint = '\n-> 광고계정 MCC 미연결/권한없음. 진단 메뉴로 확인.';
    else if (/DEVELOPER_TOKEN/.test(body)) hint = '\n-> 개발자토큰/접근권한(Explorer 이상) 확인.';
    throw new Error('Ads API 오류(' + code + '): ' + body.slice(0, 400) + hint);
  }
  const parsed = JSON.parse(body);
  const rows = [];
  (Array.isArray(parsed) ? parsed : [parsed]).forEach(function (batch) {
    (batch.results || []).forEach(function (r) { rows.push(r); });
  });
  return rows;
}

function syncGoogleAdsData(opts) {
  opts = opts || {};
  const interactive = opts.interactive !== false;
  const days = Number(opts.days) || 7;
  const ui = (function () { try { return SpreadsheetApp.getUi(); } catch (e) { return null; } })();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(GADS_SHEET);
  if (!sheet) {
    if (typeof createGoogleIntegratedSheet === 'function') createGoogleIntegratedSheet();
    sheet = ss.getSheetByName(GADS_SHEET);
  }
  if (!sheet) { if (ui) ui.alert('구글+ 시트 없음. 시트 신설 먼저.'); return { ok: false }; }
  const tz = 'Asia/Seoul';
  const end = new Date();
  const start = new Date(); start.setDate(start.getDate() - (days - 1));
  const fmt = function (d) { return Utilities.formatDate(d, tz, 'yyyy-MM-dd'); };
  const startStr = fmt(start), endStr = fmt(end);
  const gaql = 'SELECT segments.date, campaign.name, ad_group.name, metrics.impressions, metrics.clicks, metrics.cost_micros FROM ad_group WHERE segments.date BETWEEN \'' + startStr + '\' AND \'' + endStr + '\' AND metrics.impressions > 0';
  let apiRows;
  try {
    apiRows = _gadsSearch_(gaql);
  } catch (e) {
    Logger.log('syncGoogleAdsData 실패: ' + e.message);
    if (typeof logSync_ === 'function') logSync_('syncGoogleAdsData', 'fail', e.message);
    if (interactive && ui) ui.alert('구글 Ads 수집 실패\n\n' + e.message);
    return { ok: false, error: e.message };
  }
  const agg = {};
  apiRows.forEach(function (r) {
    const seg = r.segments || {}, camp = r.campaign || {}, ag = r.adGroup || {}, m = r.metrics || {};
    const date = String(seg.date || '').slice(0, 10);
    const adgroup = String(ag.name || '').trim();
    if (!date || !adgroup) return;
    const key = date + '|' + adgroup;
    if (!agg[key]) agg[key] = { date: date, campaign: String(camp.name || '').trim(), adgroup: adgroup, imp: 0, clk: 0, cost: 0 };
    agg[key].imp += Number(m.impressions) || 0;
    agg[key].clk += Number(m.clicks) || 0;
    agg[key].cost += (Number(m.costMicros) || 0) / 1000000;
  });
  const lastRow = sheet.getLastRow();
  const idx = {};
  if (lastRow >= 2) {
    const cur = sheet.getRange(2, 1, lastRow - 1, 3).getDisplayValues();
    cur.forEach(function (row, i) {
      const d = String(row[0] || '').slice(0, 10);
      const ag = String(row[2] || '').trim();
      if (d && ag) idx[d + '|' + ag] = i + 2;
    });
  }
  let updated = 0, inserted = 0;
  let appendRow = sheet.getLastRow() + 1;
  Object.keys(agg).forEach(function (key) {
    const a = agg[key];
    const cost = Math.round(a.cost);
    let row = idx[key];
    if (row) {
      sheet.getRange(row, 4).setValue(a.imp);
      sheet.getRange(row, 5).setValue(a.clk);
      sheet.getRange(row, 6).setValue(cost);
      updated++;
    } else {
      sheet.getRange(appendRow, 1, 1, 6).setValues([[a.date, a.campaign, a.adgroup, a.imp, a.clk, cost]]);
      idx[key] = appendRow;
      appendRow++;
      inserted++;
    }
  });
  SpreadsheetApp.flush();
  let ga4 = { updated: 0 };
  if (typeof syncGoogleGA4 === 'function') {
    try { ga4 = syncGoogleGA4({ interactive: false }) || ga4; } catch (e) { Logger.log('syncGoogleGA4 후속 실패: ' + e.message); }
  }
  const msg = '구글 Ads 수집 ' + startStr + '~' + endStr + ' / 갱신 ' + updated + ' 신규 ' + inserted + ' (GA4 ' + (ga4.updated || 0) + '행)';
  Logger.log(msg);
  if (typeof logSync_ === 'function') logSync_('syncGoogleAdsData', 'ok', msg);
  if (interactive && ui) {
    ui.alert('구글 Ads 수집 완료\n\n기간: ' + startStr + ' ~ ' + endStr + '\n갱신 ' + updated + '행 / 신규 ' + inserted + '행\nGA4 매칭 ' + (ga4.updated || 0) + '행\n\n' + (updated + inserted === 0 ? '집계 행 없음(노출0/권한 점검).' : 'D~F 채워짐.'));
  }
  return { ok: true, updated: updated, inserted: inserted, ga4: ga4.updated || 0 };
}

function syncGoogleAdsData30() { return syncGoogleAdsData({ days: 30 }); }

function listAccessibleGoogleAdsCustomers() {
  const ui = SpreadsheetApp.getUi();
  const p = PropertiesService.getScriptProperties();
  const dev = p.getProperty('GOOGLE_ADS_DEVELOPER_TOKEN');
  if (!dev) { ui.alert('DEVELOPER_TOKEN 미등록'); return; }
  try {
    const token = _gadsAccessToken_();
    const url = 'https://googleads.googleapis.com/' + GADS_API_VERSION + '/customers:listAccessibleCustomers';
    const res = UrlFetchApp.fetch(url, { method: 'get', headers: { 'Authorization': 'Bearer ' + token, 'developer-token': dev }, muteHttpExceptions: true });
    const code = res.getResponseCode();
    const body = res.getContentText();
    if (code !== 200) { ui.alert('조회 실패(' + code + ')\n\n' + body.slice(0, 400)); return; }
    const names = (JSON.parse(body).resourceNames || []).map(function (n) { return String(n).replace('customers/', ''); });
    const login = String(p.getProperty('GOOGLE_ADS_LOGIN_CUSTOMER_ID') || '').replace(/[^0-9]/g, '');
    const cust = String(p.getProperty('GOOGLE_ADS_CUSTOMER_ID') || '').replace(/[^0-9]/g, '');
    ui.alert('접근 가능한 계정(refresh_token 사용자 직접권한):\n\n' + (names.length ? names.join('\n') : '(없음)') + '\n\n[현재 등록값]\nLOGIN(MCC): ' + (login || '미등록') + '\nCUSTOMER: ' + (cust || '미등록') + '\n\n위 목록에 MCC 번호가 있어야 정상. CUSTOMER가 목록에 없으면 MCC 아래 연결 필요.');
  } catch (e) { ui.alert('실패: ' + e.message); }
}

function testGoogleAds() {
  const ui = SpreadsheetApp.getUi();
  try {
    const rows = _gadsSearch_('SELECT customer.id, customer.descriptive_name, customer.currency_code FROM customer LIMIT 1');
    if (!rows.length) { ui.alert('응답 왔으나 0행. 권한/계정ID 점검.'); return; }
    const c = rows[0].customer || {};
    ui.alert('구글 Ads 연결 성공\n\n계정: ' + (c.descriptiveName || '(이름없음)') + '\nID: ' + (c.id || '') + '\n통화: ' + (c.currencyCode || ''));
  } catch (e) { ui.alert('연결 실패\n\n' + e.message); }
}

function setupGoogleAdsTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'syncGoogleAdsData') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('syncGoogleAdsData').timeBased().atHour(2).nearMinute(25).everyDays(1).create();
  Logger.log('구글 Ads 수집 트리거 등록: 매일 02:25');
  try { SpreadsheetApp.getUi().alert('구글 Ads 수집 트리거 등록(매일 02:25). 사전: Script Property 6개.'); } catch (e) {}
}
