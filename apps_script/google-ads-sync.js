/**
 * 구글 Ads API 자동수집 (2026-06-19 신설) — 메타 패턴의 구글판
 *
 * 역할: 구글_통합 시트의 D(노출)/E(클릭)/F(지출)을 Google Ads API로 자동 채움.
 *       (기존 google-sync.js 는 GA4 매칭(G~P) 담당. 이 파일은 운영데이터(D~F) 담당.)
 *
 * 흐름: refresh_token → access_token → searchStream(GAQL, ad_group 단위, segments.date)
 *       → (날짜+광고그룹명) 키로 구글_통합 A~F upsert → syncGoogleGA4() 호출해 G~P 수식 재적용.
 *
 * 사전 — Apps Script 프로젝트 설정 → 스크립트 속성에 6개 등록 (값은 채팅에 노출 금지):
 *   GOOGLE_ADS_DEVELOPER_TOKEN   개발자 토큰 (관리자/MCC 소속)
 *   GOOGLE_ADS_CLIENT_ID         OAuth 클라이언트 ID
 *   GOOGLE_ADS_CLIENT_SECRET     OAuth 클라이언트 secret
 *   GOOGLE_ADS_REFRESH_TOKEN     OAuth Playground에서 받은 refresh token (1//...)
 *   GOOGLE_ADS_LOGIN_CUSTOMER_ID 관리자(MCC) 계정 ID (숫자만, 하이픈 제거)
 *   GOOGLE_ADS_CUSTOMER_ID       조회할 광고 계정 ID (숫자만, 하이픈 제거)
 *
 * 전제: GOOGLE_ADS_CUSTOMER_ID 계정이 MCC(LOGIN_CUSTOMER_ID) 아래 연결돼 있어야 함.
 *       미연결 시 API가 USER_PERMISSION_DENIED 반환 → 알림으로 표시.
 *
 * 통화: 한국 계정은 cost_micros 단위가 KRW 백만분의1 → /1,000,000 = 원.
 */

var GADS_API_VERSION = 'v23'; // 2026-06 최신. 종료되면 이 값만 올리면 됨(v19는 2026-02 종료).
var GADS_SHEET = '구글_통합';

// ============ 1) access token (refresh → access) ============
function _gadsAccessToken_() {
  const p = PropertiesService.getScriptProperties();
  const cid = p.getProperty('GOOGLE_ADS_CLIENT_ID');
  const sec = p.getProperty('GOOGLE_ADS_CLIENT_SECRET');
  const ref = p.getProperty('GOOGLE_ADS_REFRESH_TOKEN');
  if (!cid || !sec || !ref) throw new Error('Script Property 누락: GOOGLE_ADS_CLIENT_ID/SECRET/REFRESH_TOKEN');
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

// ============ 2) GAQL searchStream ============
function _gadsSearch_(gaql) {
  const p = PropertiesService.getScriptProperties();
  const dev = p.getProperty('GOOGLE_ADS_DEVELOPER_TOKEN');
  const login = String(p.getProperty('GOOGLE_ADS_LOGIN_CUSTOMER_ID') || '').replace(/[^0-9]/g, '');
  const cust = String(p.getProperty('GOOGLE_ADS_CUSTOMER_ID') || '').replace(/[^0-9]/g, '');
  if (!dev) throw new Error('Script Property 누락: GOOGLE_ADS_DEVELOPER_TOKEN');
  if (!cust) throw new Error('Script Property 누락: GOOGLE_ADS_CUSTOMER_ID');

  const token = _gadsAccessToken_();
  const url = 'https://googleads.googleapis.com/' + GADS_API_VERSION +
    '/customers/' + cust + '/googleAds:searchStream';
  const headers = {
    'Authorization': 'Bearer ' + token,
    'developer-token': dev
  };
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
    if (/USER_PERMISSION_DENIED/.test(body)) hint = '\n→ 광고계정이 MCC 아래 연결 안 됨/권한 없음. 관리자 계정에서 계정 연결 후 재시도.';
    else if (/DEVELOPER_TOKEN/.test(body)) hint = '\n→ 개발자 토큰/접근권한(Explorer 이상) 확인.';
    throw new Error('Ads API 오류(' + code + '): ' + body.slice(0, 400) + hint);
  }
  // searchStream = 배치 배열. 각 배치.results 합치기.
  const parsed = JSON.parse(body);
  const rows = [];
  (Array.isArray(parsed) ? parsed : [parsed]).forEach(function (batch) {
    (batch.results || []).forEach(function (r) { rows.push(r); });
  });
  return rows;
}

// ============ 3) 메인: 노출/클릭/지출 수집 → 구글_통합 upsert ============
// opts.days(기본 7): 최근 N일. opts.interactive(기본 true).
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
  if (!sheet) { if (ui) ui.alert('❌ 구글_통합 시트 없음. 🔵 구글 → 시트 신설 먼저.'); return { ok: false }; }

  // 날짜 범위
  const tz = 'Asia/Seoul';
  const end = new Date();
  const start = new Date(); start.setDate(start.getDate() - (days - 1));
  const fmt = function (d) { return Utilities.formatDate(d, tz, 'yyyy-MM-dd'); };
  const startStr = fmt(start), endStr = fmt(end);

  const gaql =
    'SELECT segments.date, campaign.name, ad_group.name, ' +
    'metrics.impressions, metrics.clicks, metrics.cost_micros ' +
    'FROM ad_group ' +
    "WHERE segments.date BETWEEN '" + startStr + "' AND '" + endStr + "' " +
    'AND metrics.impressions > 0';

  let apiRows;
  try {
    apiRows = _gadsSearch_(gaql);
  } catch (e) {
    Logger.log('syncGoogleAdsData 실패: ' + e.message);
    if (typeof logSync_ === 'function') logSync_('syncGoogleAdsData', 'fail', e.message);
    if (interactive && ui) ui.alert('❌ 구글 Ads 수집 실패\n\n' + e.message);
    return { ok: false, error: e.message };
  }

  // API 행 → {date, campaign, adgroup, imp, clk, cost(원)}
  const agg = {}; // key=date|adgroup → 합산(여러 캠페인 동일 광고그룹명 대비 X: 광고그룹명+date 유일 가정, 다르면 합산)
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

  // 기존 시트 인덱스: key(date|adgroup) → rowNumber
  const lastRow = sheet.getLastRow();
  const idx = {};
  if (lastRow >= 2) {
    const cur = sheet.getRange(2, 1, lastRow - 1, 3).getDisplayValues(); // A날짜 B캠페인 C광고그룹
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
    const cost = Math.round(a.cost); // 원 단위 반올림
    let row = idx[key];
    if (row) {
      // 기존 행: D~F만 갱신 (A~C, G~ 보존)
      sheet.getRange(row, 4).setValue(a.imp);
      sheet.getRange(row, 5).setValue(a.clk);
      sheet.getRange(row, 6).setValue(cost);
      updated++;
    } else {
      // 신규 행: A~F 기록
      sheet.getRange(appendRow, 1, 1, 6).setValues([[a.date, a.campaign, a.adgroup, a.imp, a.clk, cost]]);
      idx[key] = appendRow;
      appendRow++;
      inserted++;
    }
  });

  SpreadsheetApp.flush();

  // GA4 매칭 수식 재적용 (G~P)
  let ga4 = { updated: 0 };
  if (typeof syncGoogleGA4 === 'function') {
    try { ga4 = syncGoogleGA4({ interactive: false }) || ga4; } catch (e) { Logger.log('syncGoogleGA4 후속 실패: ' + e.message); }
  }

  const msg = '구글 Ads 수집 ' + startStr + '~' + endStr + ' / 갱신 ' + updated + ' 신규 ' + inserted + ' (GA4 ' + (ga4.updated || 0) + '행)';
  Logger.log(msg);
  if (typeof logSync_ === 'function') logSync_('syncGoogleAdsData', 'ok', msg);
  if (interactive && ui) {
    ui.alert('✅ 구글 Ads 수집 완료\n\n· 기간: ' + startStr + ' ~ ' + endStr +
      '\n· 갱신 ' + updated + '행 / 신규 ' + inserted + '행\n· GA4 매칭 ' + (ga4.updated || 0) + '행\n\n' +
      (updated + inserted === 0 ? '집계 행 없음 (해당 기간 노출 0 또는 권한 점검).' : 'D~F(노출/클릭/지출) 채워짐. 미매핑은 🔍 미매핑 광고그룹 보기.'));
  }
  return { ok: true, updated: updated, inserted: inserted, ga4: ga4.updated || 0 };
}

// 최근 30일 1회 백필
function syncGoogleAdsData30() { return syncGoogleAdsData({ days: 30 }); }

// 연결 테스트 (계정 정보만 호출)
function testGoogleAds() {
  const ui = SpreadsheetApp.getUi();
  try {
    const rows = _gadsSearch_('SELECT customer.id, customer.descriptive_name, customer.currency_code FROM customer LIMIT 1');
    if (!rows.length) { ui.alert('⚠️ 응답은 왔으나 결과 0행. 권한/계정ID 점검.'); return; }
    const c = rows[0].customer || {};
    ui.alert('✅ 구글 Ads 연결 성공\n\n· 계정: ' + (c.descriptiveName || '(이름없음)') + '\n· ID: ' + (c.id || '') + '\n· 통화: ' + (c.currencyCode || ''));
  } catch (e) {
    ui.alert('❌ 연결 실패\n\n' + e.message);
  }
}

// ============ 트리거 (매일 02:25, GA4 매칭 02:35 앞에서 데이터 먼저 채움) ============
function setupGoogleAdsTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'syncGoogleAdsData') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('syncGoogleAdsData').timeBased().atHour(2).nearMinute(25).everyDays(1).create();
  Logger.log('구글 Ads 수집 트리거 등록: 매일 02:25');
  try { SpreadsheetApp.getUi().alert('✅ 구글 Ads 수집 트리거 등록 (매일 02:25).\n사전: Script Property 6개 등록 필수.'); } catch (e) {}
}
