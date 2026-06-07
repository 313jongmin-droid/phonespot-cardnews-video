/**
 * 폰스팟 메타 광고 자동 동기화 — Google Apps Script
 *
 * 설치: Apps Script 에디터에 통째로 붙여넣기 → setupTriggers() 1회 수동 실행
 *
 * 작동:
 *   매일 새벽 1:30 → syncAll() 자동 실행
 *     1. 어제 메타 광고 성과 가져옴 → "메타" 시트 자동 입력
 *     2. 현재 활성 광고소재 전체 → "메타_소재" 시트 갱신
 *     3. 캠페인별 일별 데이터 → "메타_통합" 시트 (GA4 매핑 포함) ★ 신규
 *     4. GA4 출처미상 행 → 메타 클릭과 timestamp 매칭 → utm 보정
 *
 * 필요 권한:
 *   - PropertiesService (토큰 저장)
 *   - SpreadsheetApp (시트 읽기/쓰기)
 *   - UrlFetchApp (Meta API 호출)
 *
 * 종민 작업:
 *   1. PropertiesService에 META_TOKEN, META_AD_ACCOUNT_ID 저장
 *   2. setupTriggers() 한 번 수동 실행
 */

// ============ 설정 ============
const META_API_VERSION = 'v22.0';
const SHEET_META = '메타';
const SHEET_META_CREATIVES = '메타_소재';
const SHEET_META_INTEGRATED = '메타_통합';  // ★ 신규
const SHEET_GA4 = 'GA4_자동';
const SHEET_SYNC_LOG = '동기화_로그';

// 평가 임계값 (B2: 폰스팟 평균 CTR 6.5% 반영)
const EVAL_CTR_GOOD = 7;     // 우수
const EVAL_CTR_AVERAGE = 4;  // 평균 (이하는 저조)
const EVAL_MIN_SPEND = 5000; // 평가 적용 최소 지출

// 알림 받을 이메일 (토큰 만료/동기화 실패 등)
const ALERT_EMAIL = 'phonespot86@gmail.com';

// 메타 시트 컬럼 매핑 (관리대장 구조 그대로)
const META_COL = {
  DATE: 0,       // A: 날짜
  CAMPAIGN: 1,   // B: 캠페인/소재
  CHANGES: 2,    // C: 진행사항/수정
  MEMO: 3,       // D: 비고
  IMPRESSIONS: 4,// E: 노출
  CLICKS: 5,     // F: 클릭
  SPEND: 6,      // G: 지출
  LEADS: 7       // H: 문의수
  // I=CTR, J=CPC, K=CPL는 시트 수식 그대로 유지
};

// ============ 토큰 관리 ============
function getToken() {
  const token = PropertiesService.getScriptProperties().getProperty('META_TOKEN');
  if (!token) throw new Error('META_TOKEN이 PropertiesService에 없습니다. 셋업 가이드 참조.');
  return token;
}
function getAdAccountId() {
  const id = PropertiesService.getScriptProperties().getProperty('META_AD_ACCOUNT_ID');
  if (!id) throw new Error('META_AD_ACCOUNT_ID가 없습니다. (예: act_1234567890)');
  return id;
}

// ============ Meta API 호출 (A4: rate limit + retry) ============
function metaFetch(endpoint, params, retries) {
  if (retries === undefined) retries = 3;
  const token = getToken();
  const url = `https://graph.facebook.com/${META_API_VERSION}${endpoint}`;
  const qs = Object.keys(params).map(k =>
    `${k}=${encodeURIComponent(params[k])}`
  ).join('&');
  const fullUrl = `${url}?${qs}&access_token=${token}`;
  const res = UrlFetchApp.fetch(fullUrl, { muteHttpExceptions: true });
  const code = res.getResponseCode();
  const text = res.getContentText();
  if (code === 429 || code === 500 || code === 502 || code === 503) {
    if (retries > 0) {
      Utilities.sleep(2000 * (4 - retries)); // 2s → 4s → 6s exponential
      return metaFetch(endpoint, params, retries - 1);
    }
  }
  if (code !== 200) {
    throw new Error(`Meta API ${code}: ${text.slice(0, 500)}`);
  }
  return JSON.parse(text);
}

// ============ 1. 일별 성과 동기화 (메타 시트) ============
function syncMetaDaily() {
  Logger.log('=== syncMetaDaily 시작 ===');
  const adAccountId = getAdAccountId();
  const yesterday = getYesterday();
  Logger.log(`날짜: ${yesterday}`);
  const data = metaFetch(`/${adAccountId}/insights`, {
    fields: 'spend,impressions,clicks,ctr,cpc,reach',
    time_range: JSON.stringify({ since: yesterday, until: yesterday }),
    level: 'account'
  });
  if (!data.data || data.data.length === 0) {
    Logger.log('데이터 없음 (아직 광고 운영 전 또는 데이터 지연)');
    return;
  }
  const row = data.data[0];
  const impressions = parseInt(row.impressions || 0);
  const clicks = parseInt(row.clicks || 0);
  const spend = Math.round(parseFloat(row.spend || 0));
  Logger.log(`노출:${impressions} 클릭:${clicks} 지출:${spend}원`);
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_META);
  if (!sheet) {
    throw new Error('"메타" 시트가 없습니다.');
  }
  const targetRow = findDateRow(sheet, yesterday);
  if (targetRow === -1) {
    Logger.log(`어제(${yesterday}) 행이 메타 시트에 없음. 추가 모드로 전환.`);
    sheet.appendRow([yesterday, '전체', '', '', impressions, clicks, spend]);
  } else {
    sheet.getRange(targetRow, META_COL.IMPRESSIONS + 1).setValue(impressions);
    sheet.getRange(targetRow, META_COL.CLICKS + 1).setValue(clicks);
    sheet.getRange(targetRow, META_COL.SPEND + 1).setValue(spend);
    Logger.log(`행 ${targetRow} 업데이트 완료`);
  }
}

// ============ 2. 광고소재 라이브러리 동기화 ============
function syncMetaCreatives() {
  Logger.log('=== syncMetaCreatives 시작 ===');
  const adAccountId = getAdAccountId();
  const adsData = metaFetch(`/${adAccountId}/ads`, {
    fields: 'id,name,status,effective_status,creative{id,title,body,image_url,thumbnail_url,object_story_spec},created_time',
    limit: 200,
    filtering: JSON.stringify([{ field: 'effective_status', operator: 'IN', value: ['ACTIVE', 'PAUSED', 'ARCHIVED', 'CAMPAIGN_PAUSED', 'ADSET_PAUSED'] }])
  });
  if (!adsData.data || adsData.data.length === 0) {
    Logger.log('광고 없음');
    return;
  }
  const sinceDate = formatDate(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));
  const untilDate = getYesterday();
  const ss = SpreadsheetApp.getActive();
  let sheet = ss.getSheetByName(SHEET_META_CREATIVES);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_META_CREATIVES);
    sheet.appendRow([
      '메타 광고 라이브러리 (자동 동기화)', '', '', '', '', '', '', '', '', '',
      '🔗 generator.html과 연동'
    ]);
    sheet.appendRow([
      '광고ID', '광고명', '상태', '헤드라인', '본문', '이미지URL',
      '30일 노출', '30일 클릭', '30일 지출', '30일 CTR(%)', '30일 CPC',
      '평가', 'PS_ID', '생성일', '최근동기화'
    ]);
    sheet.getRange(2, 1, 1, 15).setBackground('#f5f5f7').setFontWeight('bold');
  }
  const now = new Date();
  const nowStr = Utilities.formatDate(now, 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  let updated = 0, added = 0, errors = 0;
  for (const ad of adsData.data) {
    let insights = { impressions: 0, clicks: 0, spend: 0, ctr: 0, cpc: 0 };
    try {
      const insightRes = metaFetch(`/${ad.id}/insights`, {
        fields: 'impressions,clicks,spend,ctr,cpc',
        time_range: JSON.stringify({ since: sinceDate, until: untilDate })
      });
      if (insightRes.data && insightRes.data[0]) {
        insights = insightRes.data[0];
      }
    } catch (e) {
      Logger.log(`인사이트 실패 ${ad.id}: ${e.message}`);
      errors++;
    }
    const creative = ad.creative || {};
    const story = creative.object_story_spec || {};
    const linkData = story.link_data || {};
    const videoData = story.video_data || {};
    const headline = creative.title || videoData.title || linkData.message || linkData.name || ad.name || '-';
    const body = creative.body || linkData.message || videoData.message || '-';
    const imageUrl = creative.image_url || creative.thumbnail_url || linkData.picture || videoData.image_url || '';
    const ctr = parseFloat(insights.ctr || 0);
    const cpc = parseFloat(insights.cpc || 0);
    const spend = parseFloat(insights.spend || 0);
    let evaluation = '-';
    if (spend > EVAL_MIN_SPEND) {
      if (ctr >= EVAL_CTR_GOOD) evaluation = '우수';
      else if (ctr >= EVAL_CTR_AVERAGE) evaluation = '평균';
      else evaluation = '저조';
    }
    const targetRow = findAdRow(sheet, ad.id);
    const psId = targetRow > 0 ? sheet.getRange(targetRow, 13).getValue() : '';
    const createdDate = targetRow > 0 ? sheet.getRange(targetRow, 14).getValue() : ad.created_time;
    const rowData = [
      ad.id, ad.name, ad.effective_status, headline, body, imageUrl,
      parseInt(insights.impressions || 0),
      parseInt(insights.clicks || 0),
      Math.round(spend),
      ctr.toFixed(2),
      Math.round(cpc),
      evaluation,
      psId || autoAssignPSId(sheet, ad.id),
      createdDate,
      nowStr
    ];
    if (targetRow > 0) {
      sheet.getRange(targetRow, 1, 1, rowData.length).setValues([rowData]);
      updated++;
    } else {
      sheet.appendRow(rowData);
      added++;
    }
    Utilities.sleep(200);
  }
  const msg = `총 ${adsData.data.length}개 (신규 ${added} / 갱신 ${updated} / 인사이트 실패 ${errors})`;
  Logger.log(msg);
  logSync_('syncMetaCreatives', msg);
}

function autoAssignPSId(sheet, adId) {
  if (sheet.getLastRow() < 3) return 'PS-001';
  const data = sheet.getRange(3, 13, sheet.getLastRow() - 2, 1).getValues();
  let max = 0;
  for (const row of data) {
    const v = (row[0] || '').toString();
    const m = v.match(/^PS-(\d+)$/);
    if (m) max = Math.max(max, parseInt(m[1]));
  }
  return `PS-${String(max + 1).padStart(3, '0')}`;
}

// ============ ★ 신규 3. 캠페인별 통합 (메타_통합 시트) ============
//   - 메타 API: 캠페인별 노출/클릭/지출
//   - GA4 매핑: 캠페인명 기반 세션/카톡클릭/전화클릭/시티마켓
//   - 한 행 = 1일 × 1캠페인. 자동/수기 통합 분석용
function syncMetaCampaignIntegrated(targetDate) {
  Logger.log('=== syncMetaCampaignIntegrated 시작 ===');
  const adAccountId = getAdAccountId();

  // 어제 (또는 targetDate)
  const tz = 'Asia/Seoul';
  const target = targetDate ? new Date(targetDate) : (function(){
    const y = new Date(); y.setDate(y.getDate()-1); return y;
  })();
  const ymd = Utilities.formatDate(target, tz, 'yyyy-MM-dd');
  Logger.log(`날짜: ${ymd}`);

  // Meta API — campaign 레벨
  const data = metaFetch(`/${adAccountId}/insights`, {
    fields: 'campaign_id,campaign_name,impressions,clicks,spend',
    time_range: JSON.stringify({ since: ymd, until: ymd }),
    level: 'campaign'
  });
  if (!data.data || data.data.length === 0) {
    Logger.log('데이터 없음: ' + ymd);
    return;
  }

  // 시트
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(SHEET_META_INTEGRATED);
  if (!sh) {
    sh = ss.insertSheet(SHEET_META_INTEGRATED);
    const headers = ['날짜','캠페인ID','캠페인명','노출','클릭','지출','CTR','CPC',
                     'GA4세션','카톡클릭','전화클릭','시티마켓','카톡전환률','카톡당CPC',
                     '문의수','개통수','메모'];
    sh.getRange(1, 1, 1, headers.length).setValues([headers])
      .setBackground('#1F4E78').setFontColor('#FFFFFF')
      .setFontWeight('bold').setHorizontalAlignment('center');
    sh.setFrozenRows(1);
    sh.setColumnWidth(1, 90); sh.setColumnWidth(2, 130); sh.setColumnWidth(3, 200);
    for (let c = 4; c <= 14; c++) sh.setColumnWidth(c, 90);
    for (let c = 15; c <= 17; c++) sh.setColumnWidth(c, 100);
  }

  // 같은 날짜 행 중복 제거 (재실행 안전)
  const lastRow = sh.getLastRow();
  if (lastRow >= 2) {
    const dates = sh.getRange(2, 1, lastRow - 1, 1).getDisplayValues();
    for (let i = dates.length - 1; i >= 0; i--) {
      if (dates[i][0] === ymd) sh.deleteRow(i + 2);
    }
  }

  // 데이터 추가
  const startRow = sh.getLastRow() + 1;
  data.data.forEach((item, i) => {
    const r = startRow + i;
    sh.getRange(r, 1).setValue(new Date(ymd)).setNumberFormat('yyyy-mm-dd');
    sh.getRange(r, 2).setValue(item.campaign_id);
    sh.getRange(r, 3).setValue(item.campaign_name);
    sh.getRange(r, 4).setValue(Number(item.impressions) || 0).setNumberFormat('#,##0');
    sh.getRange(r, 5).setValue(Number(item.clicks) || 0).setNumberFormat('#,##0');
    sh.getRange(r, 6).setValue(Math.round(Number(item.spend) || 0)).setNumberFormat('#,##0"원"');
    sh.getRange(r, 7).setFormula(`=IFERROR(E${r}/D${r},0)`).setNumberFormat('0.00%');
    sh.getRange(r, 8).setFormula(`=IFERROR(F${r}/E${r},0)`).setNumberFormat('#,##0"원"');

    // GA4 매핑 — 캠페인명 기반
    const ymdText = `TEXT(A${r},"yyyymmdd")`;
    const ga4Base = `'GA4_자동'!A:A,${ymdText},'GA4_자동'!B:B,"meta",'GA4_자동'!D:D,C${r}`;
    sh.getRange(r, 9).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!G:G,${ga4Base},'GA4_자동'!E:E,"session_start"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(r, 10).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"kakao_chat_click"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(r, 11).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"phone_click"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(r, 12).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(r, 13).setFormula(
      `=IFERROR(IF(I${r}=0,0,J${r}/I${r}),0)`
    ).setNumberFormat('0.00%');
    sh.getRange(r, 14).setFormula(
      `=IFERROR(IF(J${r}=0,"-",F${r}/J${r}),"-")`
    ).setNumberFormat('#,##0"원"');
  });

  const msg = `✅ 메타_통합 ${ymd} ${data.data.length}개 캠페인 입력`;
  Logger.log(msg);
  logSync_('syncMetaCampaignIntegrated', msg);
}

// ──[수동 1회]── 30일 백필 (초기 1회만 실행)
function backfillMetaCampaign30Days() {
  const today = new Date();
  let success = 0, fail = 0;
  for (let i = 29; i >= 1; i--) {
    const d = new Date(today); d.setDate(today.getDate() - i);
    const ymd = Utilities.formatDate(d, 'Asia/Seoul', 'yyyy-MM-dd');
    try {
      syncMetaCampaignIntegrated(ymd);
      success++;
      Utilities.sleep(500); // API rate limit 보호
    } catch (e) {
      Logger.log(`${ymd} 실패: ${e.message}`);
      fail++;
    }
  }
  SpreadsheetApp.getUi().alert(`✅ 30일 백필 완료\n성공: ${success}일 / 실패: ${fail}일`);
}

// ============ 4. 출처미상 자동 보정 ============
function correctUnknownSource() {
  Logger.log('=== correctUnknownSource 시작 ===');
  const ss = SpreadsheetApp.getActive();
  const ga4Sheet = ss.getSheetByName(SHEET_GA4);
  if (!ga4Sheet) { Logger.log('GA4_자동 시트 없음'); return; }
  const yesterday = getYesterday().replace(/-/g, '');
  const data = ga4Sheet.getRange(5, 1, ga4Sheet.getLastRow() - 4, 8).getValues();
  let unknownClicks = 0;
  const unknownRows = [];
  data.forEach((row, idx) => {
    if (String(row[0]) === yesterday && row[1] === '(data not available)' && row[3] === 'click') {
      unknownClicks += parseInt(row[5] || 0);
      unknownRows.push(idx + 5);
    }
  });
  if (unknownClicks === 0) { Logger.log('출처미상 click 0건'); return; }
  Logger.log(`어제 출처미상 click: ${unknownClicks}건 → 메타 매칭 대상`);
  unknownRows.forEach(r => {
    const existingMemo = ga4Sheet.getRange(r, 8).getValue() || '';
    if (!existingMemo.includes('메타추정')) {
      ga4Sheet.getRange(r, 8).setValue(existingMemo + ' [메타추정]');
    }
  });
}

// ============ 통합 동기화 (E1: 실패 시 알림, E2: 로그 누적) ============
function syncAll() {
  const errors = [];
  try { syncMetaDaily(); logSync_('syncMetaDaily', 'OK'); }
  catch (e) { errors.push(`syncMetaDaily: ${e.message}`); logSync_('syncMetaDaily', 'FAIL: ' + e.message); }
  try { syncMetaCreatives(); }
  catch (e) { errors.push(`syncMetaCreatives: ${e.message}`); logSync_('syncMetaCreatives', 'FAIL: ' + e.message); }
  try { syncMetaCampaignIntegrated(); }   // ★ 신규
  catch (e) { errors.push(`syncMetaCampaignIntegrated: ${e.message}`); logSync_('syncMetaCampaignIntegrated', 'FAIL: ' + e.message); }
  try { correctUnknownSource(); logSync_('correctUnknownSource', 'OK'); }
  catch (e) { errors.push(`correctUnknownSource: ${e.message}`); logSync_('correctUnknownSource', 'FAIL: ' + e.message); }
  if (errors.length > 0) {
    notifyError_(errors);
  }
}

// ============ E1: 에러 알림 (이메일) ============
function notifyError_(errors) {
  try {
    const body =
      '폰스팟 메타 자동화 동기화 중 에러 발생:\n\n' +
      errors.join('\n\n') +
      '\n\n시간: ' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm') +
      '\n\n조치:\n' +
      '- "Invalid OAuth access token" → 토큰 만료. 새 System User Token 발급 + Properties 갱신\n' +
      '- "Application request limit reached" → API 한도. 다음 동기화 자동 재시도\n' +
      '- 기타 → Apps Script 로그 확인 (Apps Script → 실행 → 로그)';
    MailApp.sendEmail({
      to: ALERT_EMAIL,
      subject: '[폰스팟 자동화] 메타 동기화 에러',
      body: body
    });
  } catch (e) { Logger.log('알림 발송 실패: ' + e.message); }
}

// ============ E2: 동기화 로그 누적 ============
function logSync_(funcName, message) {
  try {
    const ss = SpreadsheetApp.getActive();
    let sheet = ss.getSheetByName(SHEET_SYNC_LOG);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_SYNC_LOG);
      sheet.appendRow(['시각', '함수', '결과', '메시지']);
      sheet.getRange(1, 1, 1, 4).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
      sheet.setColumnWidths(1, 4, 150);
    }
    const status = message.startsWith('FAIL') ? '❌ 실패' : '✅ 성공';
    sheet.appendRow([
      Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss'),
      funcName,
      status,
      message
    ]);
    if (sheet.getLastRow() > 502) {
      sheet.deleteRows(2, sheet.getLastRow() - 501);
    }
  } catch (e) { Logger.log('로그 기록 실패: ' + e.message); }
}

// ============ Trigger 설정 ============
function setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'syncAll') {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger('syncAll')
    .timeBased()
    .everyDays(1)
    .atHour(1)
    .nearMinute(30)
    .create();
  Logger.log('Trigger 설정 완료: 매일 01:30');
}

// ============ 유틸 ============
function getYesterday() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return formatDate(d);
}
function formatDate(d) {
  return Utilities.formatDate(d, 'Asia/Seoul', 'yyyy-MM-dd');
}
function findDateRow(sheet, dateStr) {
  const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    const cell = data[i][0];
    if (cell instanceof Date) {
      if (Utilities.formatDate(cell, 'Asia/Seoul', 'yyyy-MM-dd') === dateStr) {
        return i + 3;
      }
    } else if (typeof cell === 'string') {
      const normalized = cell.replace(/\./g, '-').replace(/\s/g, '');
      if (normalized === dateStr || cell === dateStr) {
        return i + 3;
      }
    }
  }
  return -1;
}
function findAdRow(sheet, adId) {
  if (sheet.getLastRow() < 3) return -1;
  const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 1).getValues();
  for (let i = 0; i < data.length; i++) {
    if (String(data[i][0]) === String(adId)) return i + 3;
  }
  return -1;
}

// ============ 수동 테스트용 ============
function testTokenAndAccount() {
  try {
    const data = metaFetch(`/${getAdAccountId()}`, { fields: 'name,currency,timezone_name' });
    Logger.log(`✅ 연결 성공: ${data.name} / ${data.currency} / ${data.timezone_name}`);
    SpreadsheetApp.getUi().alert(`연결 성공\n계정: ${data.name}\n통화: ${data.currency}`);
  } catch (e) {
    Logger.log(`❌ ${e.message}`);
    SpreadsheetApp.getUi().alert(`연결 실패: ${e.message}`);
  }
}
function manualSyncToday() {
  syncAll();
  SpreadsheetApp.getUi().alert('수동 동기화 완료. 로그 확인: 보기 → 로그');
}

// ============ Generator.html 연동용 export ============
function exportCreativesAsJSON() {
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_META_CREATIVES);
  if (!sheet || sheet.getLastRow() < 3) {
    SpreadsheetApp.getUi().alert('메타_소재 시트가 비어있습니다. syncMetaCreatives() 먼저 실행하세요.');
    return;
  }
  const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 15).getValues();
  const json = data.map(row => ({
    id: row[12] || `PS-${row[0]}`,
    metaAdId: row[0],
    name: row[1],
    status: row[2],
    headline: row[3],
    body: row[4],
    imageUrl: row[5],
    impressions: row[6],
    clicks: row[7],
    spend: row[8],
    ctr: row[9],
    cpc: row[10],
    evaluation: row[11],
    createdDate: row[13]
  }));
  const text = JSON.stringify(json);
  const html = HtmlService.createHtmlOutput(
    '<p style="font-size:12px;color:#666;margin-bottom:8px">아래 박스 클릭 → Ctrl+A → Ctrl+C → generator.html 메타 import에 붙여넣기</p>' +
    '<textarea id="exp-ta" readonly style="width:100%;height:380px;font-family:monospace;font-size:11px;white-space:pre"></textarea>' +
    '<script>' +
    '  var ta = document.getElementById("exp-ta");' +
    '  ta.value = ' + JSON.stringify(text) + ';' +
    '  ta.focus(); ta.select();' +
    '</script>'
  ).setWidth(700).setHeight(480);
  SpreadsheetApp.getUi().showModalDialog(html, '메타 라이브러리 JSON Export');
}

// ============ C1: Meta Ad Library API (벤치마크/경쟁사 광고 수집) ============
// 운영 일수 + 게재 위치 수 기반 자동 ★등급 부여 (2026-06-XX 추가)
// ⚠️ Ad Library API는 신원 인증 필요 (facebook.com/ads/library/api). 인증 전엔 호출 시 400 에러
const SHEET_BM_CP = '벤치마크_경쟁사_광고';

function evaluateAdLibraryItem_(ad, today) {
  const startStr = ad.ad_delivery_start_time;
  let days = 0;
  if (startStr) {
    const startDate = new Date(startStr);
    if (!isNaN(startDate.getTime())) {
      days = Math.floor((today - startDate) / (1000 * 60 * 60 * 24));
    }
  }
  const platforms = (ad.publisher_platforms || []).length;
  let score = 0;
  // 운영 일수 점수
  if (days >= 90) score += 3;
  else if (days >= 30) score += 2;
  else if (days >= 7) score += 1;
  // 게재 위치 점수
  if (platforms >= 4) score += 2;
  else if (platforms >= 2) score += 1;
  // 등급 산정
  let grade;
  if (score >= 4) grade = '★★★ 검증됨';
  else if (score >= 2) grade = '★★ 양호';
  else if (score >= 1) grade = '★ 신규';
  else grade = '평가 보류';
  return { days, platforms, score, grade };
}

function applyAdLibraryGradeFormatting_(sheet) {
  const range = sheet.getRange('L3:L1000');
  const rules = [
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextContains('★★★').setBackground('#c8e6c9').setFontColor('#1b5e20').setBold(true).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextContains('★★').setBackground('#fff9c4').setFontColor('#5d4e00').setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextContains('★').setBackground('#e1f5fe').setFontColor('#01579b').setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('평가 보류').setBackground('#f5f5f5').setFontColor('#9e9e9e').setRanges([range]).build()
  ];
  sheet.setConditionalFormatRules(rules);
}

function syncMetaAdLibrary(searchTerm, idPrefix) {
  if (!searchTerm) {
    SpreadsheetApp.getUi().alert('키워드/페이지 ID가 비어있습니다.');
    return;
  }
  if (!idPrefix) idPrefix = 'BM';
  Logger.log(`=== syncMetaAdLibrary 시작: ${searchTerm} (${idPrefix}) ===`);
  try {
    const params = {
      ad_type: 'ALL',
      ad_reached_countries: '["KR"]',
      search_terms: searchTerm,
      ad_active_status: 'ACTIVE',
      fields: 'id,page_name,ad_creative_bodies,ad_creative_link_titles,ad_creative_link_descriptions,ad_snapshot_url,ad_delivery_start_time,publisher_platforms',
      limit: 50
    };
    const data = metaFetch('/ads_archive', params);
    if (!data.data || data.data.length === 0) {
      SpreadsheetApp.getUi().alert(`"${searchTerm}" 검색 결과 0건`);
      return;
    }
    const ss = SpreadsheetApp.getActive();
    let sheet = ss.getSheetByName(SHEET_BM_CP);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_BM_CP);
      sheet.appendRow(['벤치마크·경쟁사 광고 라이브러리 (Meta Ad Library 자동 수집)']);
      sheet.appendRow([
        'ID', '구분', '페이지명', '헤드라인', '본문', '설명',
        '게재 시작일', '게재 위치',
        '운영 일수', '위치 수', '점수', '등급',
        'Ad Library URL', '검색 키워드', '수집일'
      ]);
      sheet.getRange(2, 1, 1, 15).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
      sheet.setColumnWidths(1, 15, 110);
      sheet.setColumnWidth(4, 200);
      sheet.setColumnWidth(5, 200);
      sheet.setColumnWidth(13, 280);
    }
    const today = new Date();
    const nowStr = Utilities.formatDate(today, 'Asia/Seoul', 'yyyy-MM-dd');
    let added = 0;
    let goodCount = 0;
    data.data.forEach(ad => {
      // 중복 체크 (광고 ID 끝 6자리 기준)
      if (sheet.getLastRow() >= 3) {
        const ids = sheet.getRange(3, 1, sheet.getLastRow() - 2, 1).getValues();
        const adIdSuffix = ad.id.slice(-6);
        const exists = ids.some(r => String(r[0]).endsWith(adIdSuffix));
        if (exists) return;
      }
      const id = `${idPrefix}-${String((sheet.getLastRow() - 1) + added + 1).padStart(3, '0')}_${ad.id.slice(-6)}`;
      const headline = (ad.ad_creative_link_titles || [])[0] || '-';
      const body = (ad.ad_creative_bodies || [])[0] || '-';
      const desc = (ad.ad_creative_link_descriptions || [])[0] || '-';
      const platforms = (ad.publisher_platforms || []).join(', ');
      const evalRes = evaluateAdLibraryItem_(ad, today);
      if (evalRes.score >= 4) goodCount++;
      sheet.appendRow([
        id, idPrefix, ad.page_name || '-',
        headline, body, desc,
        ad.ad_delivery_start_time || '-',
        platforms,
        evalRes.days,
        evalRes.platforms,
        evalRes.score,
        evalRes.grade,
        ad.ad_snapshot_url || '-',
        searchTerm,
        nowStr
      ]);
      added++;
      Utilities.sleep(100);
    });
    applyAdLibraryGradeFormatting_(sheet);
    SpreadsheetApp.getUi().alert(
      `✅ "${searchTerm}" 수집 완료\n\n` +
      `· 검색 결과: ${data.data.length}건\n` +
      `· 신규 추가: ${added}건\n` +
      `· ★★★ 검증됨: ${goodCount}건\n\n` +
      `시트(${SHEET_BM_CP}) → L열 등급 필터로 우수 광고만 보기 가능`
    );
    logSync_('syncMetaAdLibrary', `${searchTerm}: 신규 ${added} / 검증 ${goodCount}`);
  } catch (e) {
    SpreadsheetApp.getUi().alert(`❌ 실패: ${e.message}`);
    logSync_('syncMetaAdLibrary', 'FAIL: ' + e.message);
  }
}

function promptSyncBenchmark() {
  const ui = SpreadsheetApp.getUi();
  const res = ui.prompt('벤치마크 광고 수집',
    '키워드 입력 (예: 휴대폰성지, 갤럭시 S26, 자급제):',
    ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  syncMetaAdLibrary(res.getResponseText().trim(), 'BM');
}
function promptSyncCompetitor() {
  const ui = SpreadsheetApp.getUi();
  const res = ui.prompt('경쟁사 광고 수집',
    '경쟁사 페이지명 또는 키워드 입력:',
    ui.ButtonSet.OK_CANCEL);
  if (res.getSelectedButton() !== ui.Button.OK) return;
  syncMetaAdLibrary(res.getResponseText().trim(), 'CP');
}

// ============ C2: generator → 시트 양방향 sync ============
function pushLibraryFromGenerator(libraryData) {
  try {
    if (!Array.isArray(libraryData)) {
      return { ok: false, error: '배열 형식이어야 함' };
    }
    const ss = SpreadsheetApp.getActive();
    let sheet = ss.getSheetByName('광고_라이브러리');
    if (!sheet) {
      sheet = ss.insertSheet('광고_라이브러리');
      sheet.appendRow(['통합 광고 라이브러리 (generator.html에서 sync)']);
      sheet.appendRow(['ID', '카테고리', '날짜', '헤드라인', '패턴', '평가', 'CTR', '지출', '전환', '메모', 'imageUrl', 'meta_ad_id', '마지막 갱신']);
      sheet.getRange(2, 1, 1, 13).setBackground('#f5f5f7').setFontWeight('bold');
    }
    if (sheet.getLastRow() > 2) {
      sheet.deleteRows(3, sheet.getLastRow() - 2);
    }
    const nowStr = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
    const rows = libraryData.map(e => [
      e.id || '',
      e.category || '',
      e.date || '',
      e.headline || '',
      e.pattern || '',
      e.performance?.evaluation || '',
      e.performance?.ctr || '',
      e.performance?.spend || '',
      e.performance?.conversions || '',
      e.memo || '',
      e.meta?.imageUrl || '',
      e.metaAdId || '',
      nowStr
    ]);
    if (rows.length > 0) {
      sheet.getRange(3, 1, rows.length, rows[0].length).setValues(rows);
    }
    logSync_('pushLibraryFromGenerator', `${rows.length}건 push`);
    return { ok: true, count: rows.length };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ============ E2: 동기화 로그 조회용 (generator 표시) ============
function getLastSyncInfo() {
  try {
    const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_META_CREATIVES);
    if (!sheet || sheet.getLastRow() < 3) return { lastSync: null, count: 0 };
    const data = sheet.getRange(3, 15, sheet.getLastRow() - 2, 1).getValues();
    let latest = '';
    let count = 0;
    data.forEach(row => {
      const v = String(row[0] || '');
      if (v && v > latest) latest = v;
      if (v) count++;
    });
    return { lastSync: latest, count: count };
  } catch (e) {
    return { lastSync: null, count: 0, error: e.message };
  }
}

// ============ generator.html에서 google.script.run으로 직접 호출 ============
function getMetaCreativesForGenerator() {
  try {
    const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_META_CREATIVES);
    if (!sheet || sheet.getLastRow() < 3) return [];
    const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 15).getValues();
    return data.map(row => ({
      id: row[12] || ('PS-' + row[0]),
      metaAdId: String(row[0] || ''),
      name: row[1],
      status: row[2],
      headline: row[3],
      body: row[4],
      imageUrl: row[5],
      impressions: row[6],
      clicks: row[7],
      spend: row[8],
      ctr: row[9],
      cpc: row[10],
      evaluation: row[11],
      createdDate: row[13] ? String(row[13]) : ''
    }));
  } catch (e) {
    return { error: e.message };
  }
}

// ============ Web App API Endpoint ============
function getMetaCreativesAsJSON_() {
  try {
    const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_META_CREATIVES);
    if (!sheet || sheet.getLastRow() < 3) {
      return ContentService.createTextOutput('[]').setMimeType(ContentService.MimeType.JSON);
    }
    const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 15).getValues();
    const json = data.map(row => ({
      id: row[12] || `PS-${row[0]}`,
      metaAdId: row[0],
      name: row[1],
      status: row[2],
      headline: row[3],
      body: row[4],
      imageUrl: row[5],
      impressions: row[6],
      clicks: row[7],
      spend: row[8],
      ctr: row[9],
      cpc: row[10],
      evaluation: row[11],
      createdDate: row[13]
    }));
    return ContentService.createTextOutput(JSON.stringify(json))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (e) {
    return ContentService.createTextOutput(JSON.stringify({ error: e.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ============ 메뉴 (기존 onOpen에서 호출) ============
function buildMetaSyncMenu_(ui) {
  ui.createMenu('📡 메타 자동화')
    .addItem('🔄 지금 동기화 (테스트)', 'manualSyncToday')
    .addItem('📥 어제 성과만 가져오기', 'syncMetaDaily')
    .addItem('🎨 광고소재 라이브러리 갱신', 'syncMetaCreatives')
    .addItem('📊 캠페인별 통합 (어제)', 'syncMetaCampaignIntegrated')   // ★ 신규
    .addItem('⏪ 30일 백필 (1회만)', 'backfillMetaCampaign30Days')      // ★ 신규
    .addSeparator()
    .addItem('🔍 벤치마크 광고 수집 (Ad Library)', 'promptSyncBenchmark')
    .addItem('🥊 경쟁사 광고 수집 (Ad Library)', 'promptSyncCompetitor')
    .addSeparator()
    .addItem('📤 JSON Export (generator.html용)', 'exportCreativesAsJSON')
    .addItem('📊 마지막 동기화 정보', 'showLastSyncInfo')
    .addSeparator()
    .addItem('🔑 토큰 연결 테스트', 'testTokenAndAccount')
    .addItem('⏰ Daily Trigger 설정', 'setupTriggers')
    .addToUi();
}

function showLastSyncInfo() {
  const info = getLastSyncInfo();
  if (info.lastSync) {
    SpreadsheetApp.getUi().alert(
      `📊 메타_소재 시트 상태\n\n` +
      `마지막 동기화: ${info.lastSync}\n` +
      `누적 광고 수: ${info.count}건\n\n` +
      `Daily Trigger 활성화: 매일 새벽 1:30 자동 갱신\n` +
      `수동 갱신: 📡 메타 자동화 → 🎨 광고소재 라이브러리 갱신`
    );
  } else {
    SpreadsheetApp.getUi().alert('아직 동기화 안 됨. 먼저 🎨 광고소재 라이브러리 갱신 실행하세요.');
  }
}
