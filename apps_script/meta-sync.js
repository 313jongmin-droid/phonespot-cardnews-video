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
const SHEET_UTM_MAPPING = 'UTM_매핑';  // ★ 복구 2026-06-12 (선언 누락 → ReferenceError 수정)
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

// ============ ★ 신규 3. 광고그룹별 통합 (메타_통합 시트) — 2026-06-10 광고그룹 단위 전환 ============
//   - 메타 API: level=adset, 광고그룹별 노출/클릭/지출
//   - GA4 매핑: UTM_매핑 시트 (한글 광고그룹명 → 영문 슬러그) VLOOKUP → GA4 utm_campaign 매칭
//   - 한 행 = 1일 × 1광고그룹. KT 캠페인 자동 제외.
function syncMetaCampaignIntegrated(targetDate) {
  Logger.log('=== syncMetaCampaignIntegrated 시작 (광고그룹 단위) ===');
  if (typeof ensureUtmNamedRanges_ === 'function') ensureUtmNamedRanges_();
  const adAccountId = getAdAccountId();

  const tz = 'Asia/Seoul';
  const target = targetDate ? new Date(targetDate) : (function(){
    const y = new Date(); y.setDate(y.getDate()-1); return y;
  })();
  const ymd = Utilities.formatDate(target, tz, 'yyyy-MM-dd');
  Logger.log(`날짜: ${ymd}`);

  // Meta API — adset 레벨 (★ 2026-06-10: campaign → adset 전환)
  const data = metaFetch(`/${adAccountId}/insights`, {
    fields: 'campaign_id,campaign_name,adset_id,adset_name,impressions,clicks,spend',
    time_range: JSON.stringify({ since: ymd, until: ymd }),
    level: 'adset'
  });
  if (!data.data || data.data.length === 0) {
    Logger.log('데이터 없음: ' + ymd);
    return;
  }

  // KT 캠페인 자동 제외
  const filtered = data.data.filter(item => {
    const camp = String(item.campaign_name || '');
    return !['KT', '다이렉트샵'].some(kw => camp.includes(kw));
  });
  if (filtered.length === 0) {
    Logger.log('KT 제외 후 데이터 없음');
    return;
  }

  // 시트 + 19컬럼 헤더 (광고그룹ID·광고그룹명 박힘)
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(SHEET_META_INTEGRATED);
  if (!sh) {
    sh = ss.insertSheet(SHEET_META_INTEGRATED);
    const headers = ['날짜','캠페인ID','캠페인명','광고그룹ID','광고그룹명',
                     '노출','클릭','지출','CTR','CPC',
                     'GA4세션','카톡클릭','전화클릭','시티마켓 클릭','시티마켓 직접','카톡전환률','카톡당CPC',
                     '문의수','CPL','개통수','메모'];
    sh.getRange(1, 1, 1, headers.length).setValues([headers])
      .setBackground('#1F4E78').setFontColor('#FFFFFF')
      .setFontWeight('bold').setHorizontalAlignment('center');
    sh.setFrozenRows(1);
    sh.setColumnWidth(1, 90);
    sh.setColumnWidth(2, 130); sh.setColumnWidth(3, 180);
    sh.setColumnWidth(4, 130); sh.setColumnWidth(5, 180);
    for (let c = 6; c <= 16; c++) sh.setColumnWidth(c, 90);
    for (let c = 17; c <= 19; c++) sh.setColumnWidth(c, 100);
  } else {
    // 헤더 자동 갱신 (17→19컬럼 마이그레이션)
    const curHeader = sh.getRange(1, 1, 1, 21).getValues()[0];
    if (curHeader[3] !== '광고그룹ID' || curHeader[4] !== '광고그룹명' || curHeader[14] !== '시티마켓 직접' || curHeader[18] !== 'CPL') {
      const headers = ['날짜','캠페인ID','캠페인명','광고그룹ID','광고그룹명',
                       '노출','클릭','지출','CTR','CPC',
                       'GA4세션','카톡클릭','전화클릭','시티마켓','카톡전환률','카톡당CPC',
                       '문의수','개통수','메모'];
      sh.getRange(1, 1, 1, headers.length).setValues([headers])
        .setBackground('#1F4E78').setFontColor('#FFFFFF')
        .setFontWeight('bold').setHorizontalAlignment('center');
    }
  }

  // 같은 날짜 행 중복 제거 (재실행 안전)
  const lastRow = sh.getLastRow();
  if (lastRow >= 2) {
    const dates = sh.getRange(2, 1, lastRow - 1, 1).getDisplayValues();
    for (let i = dates.length - 1; i >= 0; i--) {
      if (dates[i][0] === ymd) sh.deleteRow(i + 2);
    }
  }

  // 신규 광고그룹명 자동 발견 → UTM_매핑 시트에 추가
  const adsetNames = filtered.map(item => item.adset_name).filter(Boolean);
  autoDiscoverAdsets_(adsetNames);

  // 데이터 추가
  const startRow = sh.getLastRow() + 1;
  filtered.forEach((item, i) => {
    const r = startRow + i;
    sh.getRange(r, 1).setValue(new Date(ymd)).setNumberFormat('yyyy-mm-dd');
    sh.getRange(r, 2).setValue(item.campaign_id);
    sh.getRange(r, 3).setValue(item.campaign_name);
    sh.getRange(r, 4).setValue(item.adset_id);             // ★ 광고그룹ID
    sh.getRange(r, 5).setValue(item.adset_name);           // ★ 광고그룹명
    sh.getRange(r, 6).setValue(Number(item.impressions) || 0).setNumberFormat('#,##0');
    sh.getRange(r, 7).setValue(Number(item.clicks) || 0).setNumberFormat('#,##0');
    sh.getRange(r, 8).setValue(Math.round(Number(item.spend) || 0)).setNumberFormat('#,##0"원"');
    sh.getRange(r, 9).setFormula(`=IFERROR(G${r}/F${r},0)`).setNumberFormat('0.00%');
    sh.getRange(r, 10).setFormula(`=IFERROR(H${r}/G${r},0)`).setNumberFormat('#,##0"원"');

    // GA4 매핑 — 광고그룹명(E열) → UTM_매핑 VLOOKUP → 영문 슬러그 → GA4 D열 매칭
    const ymdText = `TEXT(A${r},"yyyymmdd")`;
    // ★ 2026-06-12 B2 수정: 슬러그 미입력 시 ""가 GA4 빈 campaign 행을 오매칭 → 과대계상.
    //   미매핑이면 실제 campaign에 절대 없는 토큰으로 치환해 SUMIFS가 0 반환하도록 가드.
    const slugRaw = `IFERROR(VLOOKUP(E${r}, FILTER(UTM_KEYVAL, UTM_CH="페북"), 2, FALSE),"")`;
    const slugLookup = `IF(${slugRaw}="","__UNMAPPED_NO_MATCH__",${slugRaw})`;
    const ga4Base = `'GA4_자동'!A:A,${ymdText},'GA4_자동'!B:B,"meta",'GA4_자동'!D:D,${slugLookup}`;
    sh.getRange(r, 11).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!G:G,${ga4Base},'GA4_자동'!E:E,"session_start"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(r, 12).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"kakao_chat_click"),0)`
    ).setNumberFormat('#,##0');
    sh.getRange(r, 13).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"phone_click"),0)`
    ).setNumberFormat('#,##0');
    // N (14) = 시티마켓 클릭 (리틀리 경유, citymarket_click 이벤트만)
    sh.getRange(r, 14).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click"),0)`
    ).setNumberFormat('#,##0');
    // O (15) = 시티마켓 직접 (광고→시티마켓 직접 도달, citymarket_arrival 이벤트만, GTM 2026-06-15)
    sh.getRange(r, 15).setFormula(
      `=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_arrival"),0)`
    ).setNumberFormat('#,##0');
    // P (16) = 카톡전환률 (L=카톡클릭 / K=세션, 컬럼 위치 그대로)
    sh.getRange(r, 16).setFormula(
      `=IFERROR(IF(K${r}=0,0,L${r}/K${r}),0)`
    ).setNumberFormat('0.00%');
    // Q (17) = 카톡당CPC (H=지출 / L=카톡클릭)
    sh.getRange(r, 17).setFormula(
      `=IFERROR(IF(L${r}=0,"-",H${r}/L${r}),"-")`
    ).setNumberFormat('#,##0"원"');
    // R (18) = 문의수 자동 매핑 = 문의접수 D열 "페북" + "인스타" + "스레드" 합산 (메타 산하 전체)
    sh.getRange(r, 18).setFormula(
      `=COUNTIFS('문의접수'!D:D,"페북",'문의접수'!A:A,A${r})+COUNTIFS('문의접수'!D:D,"인스타",'문의접수'!A:A,A${r})+COUNTIFS('문의접수'!D:D,"스레드",'문의접수'!A:A,A${r})`
    ).setNumberFormat('#,##0');
    // S (19) = CPL = 지출 / 문의수 (광고그룹별 행마다 같은 채널 일자 합계, 부정확하지만 0보다 나음)
    sh.getRange(r, 19).setFormula(
      `=IFERROR(IF(R${r}=0,"-",H${r}/R${r}),"-")`
    ).setNumberFormat('#,##0"원"');
  });

  const msg = `✅ 메타_통합 ${ymd} ${filtered.length}개 광고그룹 (KT 제외 ${data.data.length - filtered.length})`;
  Logger.log(msg);
  logSync_('syncMetaCampaignIntegrated', msg);
}

// ============ ★ UTM_매핑 통합 시트 자동 발견 (2026-06-15 통합 갱신) ============
// 통합 시트 구조: A 채널 | B 광고그룹명(한글) | C utm_campaign(영문) | D 첫발견일 | E 상태 | F 메모
function autoDiscoverAdsets_(adsetNames) {
  const ss = SpreadsheetApp.getActive();
  let sheet = ss.getSheetByName(SHEET_UTM_MAPPING);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_UTM_MAPPING);
    sheet.appendRow(['채널', '광고그룹명(한글)', 'utm_campaign(영문)', '첫 발견일', '상태', '메모']);
    sheet.getRange(1, 1, 1, 6).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(1, 90); sheet.setColumnWidth(2, 220); sheet.setColumnWidth(3, 180);
    sheet.setColumnWidth(4, 110); sheet.setColumnWidth(5, 100); sheet.setColumnWidth(6, 200);
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(['페북', '네이버', '당근', '구글', '카카오'], true).build();
    sheet.getRange(2, 1, sheet.getMaxRows() - 1, 1).setDataValidation(rule);
  }
  const existingSet = new Set();
  if (sheet.getLastRow() >= 2) {
    sheet.getRange(2, 1, sheet.getLastRow() - 1, 2).getValues()
      .forEach(r => { if (r[0] === '페북' && r[1]) existingSet.add(String(r[1]).trim()); });
  }
  const today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
  let added = 0;
  const newNames = [];
  (adsetNames || []).forEach(name => {
    const n = String(name || '').trim();
    if (!n) return;
    if (existingSet.has(n)) return;
    sheet.appendRow(['페북', n, '', today, '⚠️ 매핑 필요', '']);
    existingSet.add(n);
    newNames.push(n);
    added++;
  });
  if (added > 0) {
    Logger.log(`UTM_매핑: 신규 페북 광고그룹 ${added}개 발견 — ${newNames.join(', ')}`);
    if (typeof logSync_ === 'function') {
      logSync_('autoDiscoverAdsets', `신규 ${added}개: ${newNames.slice(0, 3).join(', ')}...`);
    }
  }
  return added;
}

// 메뉴 호출 — 미매핑 페북 광고그룹 보기 (채널=페북 + C열 비어있는 행)
function showUnmappedAdsets() {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(SHEET_UTM_MAPPING);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('UTM_매핑 시트 아직 없음. syncMetaCampaignIntegrated 1회 실행 후 확인.');
    return;
  }
  if (sheet.getLastRow() < 2) {
    SpreadsheetApp.getUi().alert('UTM_매핑 시트 비어있음.');
    return;
  }
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 3).getValues();
  const unmapped = data.filter(r => r[0] === '페북' && r[1] && !r[2]);
  if (unmapped.length === 0) {
    SpreadsheetApp.getUi().alert('✅ 미매핑 페북 광고그룹 없음. 모두 영문 슬러그 박혀있음.');
    return;
  }
  const msg = unmapped.map((r, i) => `${i + 1}. ${r[1]}`).join('\n');
  SpreadsheetApp.getUi().alert(
    `⚠️ 미매핑 페북 광고그룹 ${unmapped.length}개\n\n${msg}\n\n` +
    `UTM_매핑 시트 C열에 영문 슬러그 박기 (1회). 박으면 메타_통합 GA4 컬럼 자동 매칭.`
  );
}

// ============ ★ UTM_매핑 정비 (2026-06-18) ============
// utm_campaign이 채워졌는데 상태가 ⚠️/공백으로 남은 정상 행을 '✅ 매핑됨'으로 갱신.
// 시프트 행(B=채널명)·안내행(※)은 제외 → cleanup 전에 돌려도 안전.
function flipMappedUtmStatus() {
  const ss = SpreadsheetApp.getActive();
  const ui = SpreadsheetApp.getUi();
  const sheet = ss.getSheetByName(SHEET_UTM_MAPPING);
  if (!sheet || sheet.getLastRow() < 2) { ui.alert('UTM_매핑 시트 없음/비어있음.'); return; }
  const CHANNELS = ['페북', '네이버', '당근', '구글', '카카오'];
  const last = sheet.getLastRow();
  const vals = sheet.getRange(2, 1, last - 1, 6).getValues();
  let flipped = 0;
  for (let i = 0; i < vals.length; i++) {
    const ch = String(vals[i][0]).trim();
    const name = String(vals[i][1]).trim();
    const utm = String(vals[i][2]).trim();
    const status = String(vals[i][4]).trim();
    if (CHANNELS.indexOf(ch) < 0) continue;
    if (CHANNELS.indexOf(name) >= 0) continue;
    if (name.indexOf('※') >= 0 || utm.indexOf('※') >= 0) continue;
    if (utm && status !== '✅ 매핑됨') { sheet.getRange(i + 2, 5).setValue('✅ 매핑됨'); flipped++; }
  }
  const msg = 'utm 채워진 행 ' + flipped + '개 상태 ✅ 매핑됨으로 갱신';
  Logger.log(msg);
  if (typeof logSync_ === 'function') logSync_('flipMappedUtmStatus', msg);
  ui.alert('✅ 완료', msg, ui.ButtonSet.OK);
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

// ============ Trigger 설정 (★ 2026-06-10/11: syncAll + 인사이트 MD 듀얼) ============
function setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(t => {
    const fn = t.getHandlerFunction();
    if (fn === 'syncAll' || fn === 'generateMetaInsightsMarkdown' || fn === 'syncInstagramDaily') {
      ScriptApp.deleteTrigger(t);
    }
  });
  ScriptApp.newTrigger('syncAll')
    .timeBased().everyDays(1).atHour(1).nearMinute(30).create();
  ScriptApp.newTrigger('generateMetaInsightsMarkdown')
    .timeBased().everyDays(1).atHour(1).nearMinute(45).create();
  ScriptApp.newTrigger('syncInstagramDaily')
    .timeBased().everyDays(1).atHour(2).nearMinute(0).create();
  Logger.log('Trigger 설정 완료: 01:30 syncAll + 01:45 generateMetaInsightsMarkdown + 02:00 syncInstagramDaily');
  SpreadsheetApp.getUi().alert('트리거 3개 등록',
    '01:30 데이터 sync (syncAll)\n01:45 인사이트 MD 생성 + Drive 저장\n02:00 인스타 sync (최근 7일)\n매일 새벽 자동.',
    SpreadsheetApp.getUi().ButtonSet.OK);
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
    // ★ 2026-06-12 B1 수정: 15→17열 (16열 카테고리 / 17열 지역 = 종민 수기 라벨 포함)
    const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 17).getValues();
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
      createdDate: row[13] ? String(row[13]) : '',
      category: String(row[15] || '').trim(),  // ★ 16열 카테고리 (드롭다운 9개)
      region: String(row[16] || '').trim()      // ★ 17열 지역 (공백=전국)
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
    // 16열 = 카테고리, 17열 = 지역 (종민 수기 라벨, 2026-06-12 ~ Task 44). 1~15열 자동 동기화 영역 + 16·17열 보호 영역.
    const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 17).getValues();
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
      createdDate: row[13],
      category: String(row[15] || '').trim(),  // ★ 16열 — 종민 수기 라벨링 (카테고리 9개 드롭다운)
      region: String(row[16] || '').trim()      // ★ 17열 — 종민 수기 자유 텍스트 (공백=전국, "광교점"·"수원점" 등)
    }));
    return ContentService.createTextOutput(JSON.stringify(json))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (e) {
    return ContentService.createTextOutput(JSON.stringify({ error: e.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// ============ 옵션 C 폐기 (2026-06-09) ============
// 컨셉_태그 컬럼 시스템 종민 결정으로 전체 제거. 카피 생성은 기존 폼(USP/추가 키워드)
// + 신규 컨셉 자유 입력바(generator.html) 활용. 시트 P열에 남아있는 컨셉_태그 컬럼은
// 종민이 시트에서 수동 삭제 가능 (그대로 둬도 무관).

// ============ 🤖 Apify 벤치마크 수집 (2026-06-09) ============
// Meta Ad Library를 신원 인증 없이 우회. Apify scraper 호출.
// Actor: curious_coder/facebook-ads-library-scraper ($0.00075/광고)
// 토큰: PropertiesService → APIFY_TOKEN

const APIFY_ACTOR_ID = 'curious_coder/facebook-ads-library-scraper';

function getApifyToken_() {
  const t = PropertiesService.getScriptProperties().getProperty('APIFY_TOKEN');
  if (!t) throw new Error('APIFY_TOKEN이 PropertiesService에 없음. 프로젝트 설정 → 스크립트 속성에서 추가하세요.');
  return t;
}

// 핵심 호출 함수
function fetchBenchmarkFromApify_(searchTerm, count, countryCode) {
  const token = getApifyToken_();
  const cc = countryCode || 'KR';
  const searchUrl = 'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=' + cc +
                    '&q=' + encodeURIComponent(searchTerm) + '&search_type=keyword_unordered&media_type=all';
  const input = {
    urls: [{url: searchUrl}],
    count: count || 30,
    'scrapePageAds.activeStatus': 'active',
    'scrapePageAds.countryCode': cc
  };
  // Apify run-sync-get-dataset-items: 동기 호출, 결과 즉시 반환
  const actorPath = APIFY_ACTOR_ID.replace('/', '~');
  const apiUrl = 'https://api.apify.com/v2/acts/' + actorPath +
                 '/run-sync-get-dataset-items?token=' + token;
  const res = UrlFetchApp.fetch(apiUrl, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(input),
    muteHttpExceptions: true
  });
  const code = res.getResponseCode();
  if (code !== 200 && code !== 201) {
    throw new Error('Apify 호출 실패 ' + code + ': ' + res.getContentText().slice(0, 400));
  }
  return JSON.parse(res.getContentText());
}

// Apify 결과 → 시트 저장 (벤치마크_경쟁사_광고 시트 재활용 + 추가 컬럼)
function saveBenchmarkToSheet_(items, searchTerm) {
  const ss = SpreadsheetApp.getActive();
  let sheet = ss.getSheetByName(SHEET_BM_CP);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_BM_CP);
    sheet.appendRow(['벤치마크·경쟁사 광고 라이브러리 (Apify + Meta Ad Library)']);
    sheet.appendRow([
      'ID', '구분', '페이지명', '페이지ID', '팔로워',
      '본문 발췌', '광고 형식', 'CTA', '게재 시작일', '게재 위치',
      '운영 일수', '위치 수', '변형 수', '점수', '등급',
      '썸네일 URL', 'Ad Library URL', '검색 키워드', '수집일'
    ]);
    sheet.getRange(2, 1, 1, 19).setBackground('#1F4E78').setFontColor('#FFFFFF').setFontWeight('bold');
    sheet.setColumnWidths(1, 19, 110);
    sheet.setColumnWidth(6, 320);  // 본문 발췌
    sheet.setColumnWidth(17, 200); // Ad Library URL
  }

  const today = new Date();
  const nowStr = Utilities.formatDate(today, 'Asia/Seoul', 'yyyy-MM-dd');
  let added = 0;
  let goodCount = 0;
  // 중복 체크 (광고 ID 끝 8자리 기준)
  let existingSet = new Set();
  if (sheet.getLastRow() >= 3) {
    const existing = sheet.getRange(3, 1, sheet.getLastRow() - 2, 1).getValues();
    existing.forEach(r => existingSet.add(String(r[0]).slice(-8)));
  }

  for (const item of items) {
    const adId = String(item.ad_archive_id || '');
    if (!adId) continue;
    const idSuffix = adId.slice(-8);
    if (existingSet.has(idSuffix)) continue;

    const s = item.snapshot || {};
    const body = (s.body && s.body.text) || '';
    const bodyExcerpt = body.split('\n').filter(l => l.trim()).slice(0, 3).join(' | ').slice(0, 280);
    const platforms = item.publisher_platform || [];
    const startDate = item.start_date ? new Date(item.start_date * 1000) : null;
    const days = startDate ? Math.floor((today - startDate) / (1000 * 60 * 60 * 24)) : 0;
    const collation = item.collation_count || 1;

    // 점수 계산 (운영일수 + 채널수 + 변형수)
    let score = 0;
    if (days >= 90) score += 3;
    else if (days >= 30) score += 2;
    else if (days >= 7) score += 1;
    if (platforms.length >= 4) score += 2;
    else if (platforms.length >= 2) score += 1;
    if (collation >= 3) score += 1;

    let grade;
    if (score >= 5) grade = '★★★ 검증됨';
    else if (score >= 3) grade = '★★ 양호';
    else if (score >= 1) grade = '★ 신규';
    else grade = '평가 보류';
    if (score >= 5) goodCount++;

    // 썸네일
    const videos = s.videos || [];
    const images = s.images || [];
    const thumbnail = (videos[0] && videos[0].video_preview_image_url) ||
                      (images[0] && images[0].original_image_url) ||
                      (images[0] && images[0].resized_image_url) || '';

    const seq = sheet.getLastRow() - 1 + added + 1;
    const newId = 'BM-' + String(seq).padStart(3, '0') + '_' + adId.slice(-6);
    existingSet.add(idSuffix);

    sheet.appendRow([
      newId, 'BM',
      s.page_name || '-',
      s.page_id || '-',
      s.page_like_count || 0,
      bodyExcerpt || '-',
      s.display_format || '-',
      s.cta_text || '-',
      item.start_date_formatted || '-',
      platforms.join(', '),
      days,
      platforms.length,
      collation,
      score,
      grade,
      thumbnail,
      item.ad_library_url || '-',
      searchTerm,
      nowStr
    ]);
    added++;
    Utilities.sleep(50);
  }

  applyBenchmarkGradeFormatting_(sheet);
  return { added, goodCount, totalReceived: items.length };
}

function applyBenchmarkGradeFormatting_(sheet) {
  const range = sheet.getRange('O3:O1000');
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

// 메뉴 단발 (키워드 prompt)
function promptApifyBenchmark() {
  const ui = SpreadsheetApp.getUi();
  const kw = ui.prompt('🤖 Apify 벤치마크 수집',
    '검색 키워드 (예: 휴대폰성지, 갤럭시 S26 자급제, 통신비 절약):',
    ui.ButtonSet.OK_CANCEL);
  if (kw.getSelectedButton() !== ui.Button.OK) return;
  const term = kw.getResponseText().trim();
  if (!term) return;

  const cnt = ui.prompt('광고 수 (기본 30, 최대 200)',
    '비용: 30개 ≈ 30원, 100개 ≈ 100원, 200개 ≈ 200원',
    ui.ButtonSet.OK_CANCEL);
  if (cnt.getSelectedButton() !== ui.Button.OK) return;
  const count = Math.max(1, Math.min(200, parseInt(cnt.getResponseText()) || 30));

  try {
    Logger.log('Apify call: ' + term + ' / ' + count);
    const items = fetchBenchmarkFromApify_(term, count, 'KR');
    const r = saveBenchmarkToSheet_(items, term);
    ui.alert(
      '✅ Apify 수집 완료\n\n' +
      '키워드: ' + term + '\n' +
      '수신: ' + r.totalReceived + '건 / 신규 저장 ' + r.added + '건\n' +
      '★★★ 검증됨: ' + r.goodCount + '건\n' +
      '예상 비용: $' + (r.totalReceived * 0.00075).toFixed(4) + '\n\n' +
      '시트: 벤치마크_경쟁사_광고'
    );
    logSync_('promptApifyBenchmark', term + ': ' + r.added + ' new, ' + r.goodCount + ' verified');
  } catch (e) {
    ui.alert('❌ 실패: ' + e.message);
    logSync_('promptApifyBenchmark', 'FAIL: ' + e.message);
  }
}

// generator.html 페이지 로드 시 시트 누적분 fetch (자동 import)
function getBenchmarkForGenerator() {
  try {
    const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_BM_CP);
    if (!sheet) return { ok: true, items: [] };
    if (sheet.getLastRow() < 3) return { ok: true, items: [] };
    // 헤더 정의: ID/구분/페이지명/페이지ID/팔로워/본문 발췌/광고 형식/CTA/게재 시작일/게재 위치/운영 일수/위치 수/변형 수/점수/등급/썸네일 URL/Ad Library URL/검색 키워드/수집일 / 카테고리(★수기) / 후킹 구조(★수기) / 지역(★수기)
    // 20·21·22열 = 종민 수기 라벨 (Task 43 + Task 44). 1~19열 자동 수집 + 20·21·22열 보호 영역.
    const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 22).getValues();
    const items = [];
    for (const row of data) {
      const id = String(row[0] || '');
      if (!id.startsWith('BM') && !id.startsWith('CP')) continue;
      items.push({
        id: id,
        kind: String(row[1] || 'BM'),      // BM/CP 구분자 (옛 'category' 키였으나 의미상 'kind'로 변경)
        pageName: String(row[2] || '-'),
        pageId: String(row[3] || '-'),
        followers: parseInt(row[4]) || 0,
        body: String(row[5] || ''),
        format: String(row[6] || '-'),
        cta: String(row[7] || '-'),
        startDate: String(row[8] || '-'),
        platforms: String(row[9] || '').split(',').map(s => s.trim()).filter(Boolean),
        days: parseInt(row[10]) || 0,
        platformCount: parseInt(row[11]) || 0,
        collation: parseInt(row[12]) || 1,
        score: parseInt(row[13]) || 0,
        grade: String(row[14] || '평가 보류'),
        thumbnail: String(row[15] || ''),
        adLibraryUrl: String(row[16] || ''),
        searchTerm: String(row[17] || ''),
        collectedAt: String(row[18] || ''),
        category: String(row[19] || '').trim(),       // ★ 20열 — 종민 수기 라벨 (상품 카테고리)
        hookStructure: String(row[20] || '').trim(),  // ★ 21열 — 종민 수기 라벨 (후킹 구조)
        region: String(row[21] || '').trim()           // ★ 22열 — 종민 수기 자유 텍스트 (공백=전국)
      });
    }
    return { ok: true, items: items, count: items.length };
  } catch (e) {
    return { ok: false, error: e.message, items: [] };
  }
}

// ★ 2026-06-12: 컨셉/지역 앵글 → 라이브러리·벤치마크 광고 의미(주제) 매칭 (Gemini)
// generator.html이 google.script.run으로 호출. payload={concept,region,category,usp,candidates:[{id,text}]}
function getSemanticAdMatches(payload) {
  try {
    payload = payload || {};
    const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
    if (!key) return { ok: false, error: 'GEMINI_API_KEY 없음 (스크립트 속성 추가 필요)', scores: {} };
    const cands = (payload.candidates || []).slice(0, 40);
    if (cands.length === 0) return { ok: true, scores: {} };
    const angle = [payload.concept, payload.region, payload.category, payload.usp]
      .map(function(s){ return String(s || '').trim(); }).filter(Boolean).join(' / ');
    if (!angle) return { ok: true, scores: {} };
    const list = cands.map(function(c){ return '[' + c.id + '] ' + String(c.text || '').slice(0, 140); }).join('\n');
    const prompt =
      '광고 캠페인 앵글: "' + angle + '".\n' +
      '아래 기존 광고들 중 이 앵글과 주제·맥락이 유사한 것을 0~100으로 평가해라. ' +
      '단어가 정확히 같지 않아도 의미가 통하면 높게 (예: "액정 깨진 폰" 앵글 ↔ "중고폰 보상/파손/수리" 광고 = 높음). 무관하면 낮게.\n\n' +
      '광고 목록:\n' + list + '\n\n' +
      'JSON 배열로만 응답: [{"id":"광고ID","score":0-100}]. 모든 광고에 점수. 다른 설명 금지.';
    const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=' + key;
    const res = UrlFetchApp.fetch(url, {
      method: 'POST', contentType: 'application/json',
      payload: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.2, response_mime_type: 'application/json' } }),
      muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) return { ok: false, error: 'Gemini ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 200), scores: {} };
    const data = JSON.parse(res.getContentText());
    const arr = JSON.parse(data.candidates[0].content.parts[0].text);
    const scores = {};
    (Array.isArray(arr) ? arr : []).forEach(function(x){ if (x && x.id != null) scores[String(x.id)] = Number(x.score) || 0; });
    return { ok: true, scores: scores };
  } catch (e) {
    return { ok: false, error: e.message, scores: {} };
  }
}

// 벤치마크 시트 행 삭제 (BM ID 또는 광고 archive ID로)
function deleteBenchmarkFromSheet(idOrAdId) {
  try {
    const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_BM_CP);
    if (!sheet) return { ok: false, error: '벤치마크 시트 없음' };
    if (sheet.getLastRow() < 3) return { ok: false, error: '데이터 없음' };
    const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 1).getValues();
    const target = String(idOrAdId || '').trim();
    if (!target) return { ok: false, error: 'ID 없음' };
    // 정확 매치 + 끝자리 매치 둘 다 시도
    for (let i = 0; i < data.length; i++) {
      const rowId = String(data[i][0] || '');
      if (rowId === target || rowId.endsWith('_' + target) || rowId.endsWith(target.slice(-6))) {
        sheet.deleteRow(i + 3);
        return { ok: true, deleted: rowId };
      }
    }
    return { ok: false, error: 'ID 못 찾음: ' + target };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// 여러 개 일괄 삭제
function deleteBenchmarksFromSheet(ids) {
  if (!Array.isArray(ids)) return { ok: false, error: '배열 아님' };
  try {
    const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_BM_CP);
    if (!sheet) return { ok: false, error: '벤치마크 시트 없음' };
    if (sheet.getLastRow() < 3) return { ok: false, error: '데이터 없음' };
    const data = sheet.getRange(3, 1, sheet.getLastRow() - 2, 1).getValues();
    const targets = new Set(ids.map(x => String(x).trim()).filter(Boolean));
    // 뒤에서부터 삭제 (인덱스 안정성)
    const rowsToDelete = [];
    for (let i = 0; i < data.length; i++) {
      const rowId = String(data[i][0] || '');
      const matches = Array.from(targets).some(t =>
        rowId === t || rowId.endsWith('_' + t) || rowId.endsWith(t.slice(-6)));
      if (matches) rowsToDelete.push(i + 3);
    }
    for (let i = rowsToDelete.length - 1; i >= 0; i--) {
      sheet.deleteRow(rowsToDelete[i]);
    }
    return { ok: true, deleted: rowsToDelete.length };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// 시트 직접 링크 (gid)
function getBenchmarkSheetUrl() {
  try {
    const ss = SpreadsheetApp.getActive();
    const sheet = ss.getSheetByName(SHEET_BM_CP);
    if (!sheet) return { ok: false, error: '벤치마크 시트 없음' };
    return {
      ok: true,
      url: ss.getUrl() + '#gid=' + sheet.getSheetId(),
      rowCount: Math.max(0, sheet.getLastRow() - 2)
    };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// generator.html에서 호출 (Web App API)
function searchBenchmarkViaApify(searchTerm, count, countryCode) {
  try {
    const items = fetchBenchmarkFromApify_(searchTerm, count || 20, countryCode || 'KR');
    const today = new Date();
    const processed = items.map(item => {
      const s = item.snapshot || {};
      const startDate = item.start_date ? new Date(item.start_date * 1000) : null;
      const days = startDate ? Math.floor((today - startDate) / (1000 * 60 * 60 * 24)) : 0;
      const platforms = item.publisher_platform || [];
      const collation = item.collation_count || 1;
      const videos = s.videos || [];
      const images = s.images || [];
      const thumbnail = (videos[0] && videos[0].video_preview_image_url) ||
                        (images[0] && images[0].original_image_url) || '';
      let score = 0;
      if (days >= 90) score += 3;
      else if (days >= 30) score += 2;
      else if (days >= 7) score += 1;
      if (platforms.length >= 4) score += 2;
      else if (platforms.length >= 2) score += 1;
      if (collation >= 3) score += 1;
      let grade;
      if (score >= 5) grade = '★★★ 검증됨';
      else if (score >= 3) grade = '★★ 양호';
      else if (score >= 1) grade = '★ 신규';
      else grade = '평가 보류';
      const body = (s.body && s.body.text) || '';
      return {
        adId: String(item.ad_archive_id || ''),
        pageName: s.page_name || '-',
        pageId: s.page_id || '-',
        pageFollowers: s.page_like_count || 0,
        body: body,
        bodyExcerpt: body.slice(0, 400),
        displayFormat: s.display_format || '-',
        cta: s.cta_text || '-',
        startDate: item.start_date_formatted || '-',
        days, platforms, collation, score, grade, thumbnail,
        adLibraryUrl: item.ad_library_url || ''
      };
    });
    return { ok: true, totalReceived: items.length, items: processed };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// generator.html에서 선택한 광고들 시트 저장
function saveBenchmarkSelectedFromGenerator(itemsRaw, searchTerm) {
  try {
    // generator.html이 보낸 processed item을 raw 형태로 복구해서 saveBenchmarkToSheet_ 재활용
    const items = (itemsRaw || []).map(p => ({
      ad_archive_id: p.adId,
      collation_count: p.collation,
      publisher_platform: p.platforms,
      start_date: null, // 이미 days 계산됨, 시트 저장 시 startDate 문자열만 씀
      start_date_formatted: p.startDate,
      ad_library_url: p.adLibraryUrl,
      snapshot: {
        page_name: p.pageName,
        page_id: p.pageId,
        page_like_count: p.pageFollowers,
        body: { text: p.body || p.bodyExcerpt || '' },
        display_format: p.displayFormat,
        cta_text: p.cta,
        videos: p.thumbnail ? [{video_preview_image_url: p.thumbnail}] : []
      }
    }));
    // days 계산을 위해 start_date 추정 (역산)
    items.forEach((it, i) => {
      const days = itemsRaw[i].days || 0;
      it.start_date = Math.floor((Date.now() - days * 86400 * 1000) / 1000);
    });
    const r = saveBenchmarkToSheet_(items, searchTerm || 'manual');
    return { ok: true, added: r.added, goodCount: r.goodCount };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// ============ 메뉴 (기존 onOpen에서 호출) ============
// 원칙 (2026-06-09): 시트 메뉴 = 자동화·백엔드 운영. 사용자 도구(벤치마크 수집, 카피·이미지 생성, JSON Export 등) 전부 generator.html(Web App) 내부에서 처리.
function buildMetaSyncMenu_(ui) {
  ui.createMenu('📘 메타')
    .addItem('🔄 지금 동기화 (테스트)', 'manualSyncToday')
    .addItem('📥 어제 성과만 가져오기', 'syncMetaDaily')
    .addItem('🎨 광고소재 라이브러리 갱신', 'syncMetaCreatives')
    .addItem('📊 광고그룹별 통합 (어제)', 'syncMetaCampaignIntegrated')
    .addItem('⏪ 30일 백필 (1회만)', 'backfillMetaCampaign30Days')
    .addSeparator()
    .addItem('🔍 미매핑 광고그룹 보기', 'showUnmappedAdsets')
    .addItem('✅ utm 채운 행 상태 갱신', 'flipMappedUtmStatus')
    .addItem('🧠 인사이트 MD 생성', 'generateMetaInsightsMarkdown')
    .addItem('🏷️ 라벨링 드롭다운 설정 (1회)', 'setupLabelingDropdowns')
    .addSeparator()
    .addItem('📷 인스타 동기화 (최근 7일)', 'syncInstagramDaily')
    .addItem('⏪ 인스타 전체 백필 (1회만)', 'backfillInstagramAll')
    .addSeparator()
    .addItem('📊 마지막 동기화 정보', 'showLastSyncInfo')
    .addItem('🔑 토큰 연결 테스트 (메타)', 'testTokenAndAccount')
    .addItem('⏰ Daily Trigger 설정', 'setupTriggers')
    .addToUi();
  // 폐기된 사용자 도구 메뉴 (generator.html로 이동, 2026-06-09):
  //  - 🤖 Apify 벤치마크 수집 → generator 벤치마크 탭 🔍 검색바
  //  - 🔍 벤치마크 / 🥊 경쟁사 (Ad Library 인증 필요) → 신원인증 못 받아 폐기
  //  - 📤 JSON Export → generator가 직접 google.script.run으로 호출
  // promptApifyBenchmark / promptSyncBenchmark / promptSyncCompetitor / exportCreativesAsJSON
  // 함수는 코드에 남겨두지만 메뉴에서만 제거 (호환·복구용).
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

// ============ ★ 인스타 자동 동기화 (Instagram Graph API) ============
//   - 매일 02:00 syncInstagramDaily(): 시트 비어있으면 전체 / 데이터 있으면 최근 7일
//   - 초기 1회 backfillInstagramAll(): 강제 전체 백필 (UI alert)
//
//   시트 구조 (인스타 시트, 4행부터 데이터):
//     A 날짜 / B 포맷(수기) / C 주제 / D 링크(매칭 키) / E 조회수(views) / F 좋아요 / G 팔로워 / H 메모(수기) / I 비고(수기)
//
//   매칭: D 링크(permalink) — 있으면 E·F·G 갱신 / 없으면 신규 append (timestamp 오름차순)
//   사전: PropertiesService INSTAGRAM_BUSINESS_ID 등록 (17841474706647015 = @phonespot.kr)
//   토큰: 기존 META_TOKEN 재활용 (instagram_basic + instagram_manage_insights scopes 필요)

const SHEET_INSTAGRAM = '인스타';
const INSTAGRAM_DATA_START_ROW = 4;

function getInstagramBusinessId_() {
  const id = PropertiesService.getScriptProperties().getProperty('INSTAGRAM_BUSINESS_ID');
  if (!id) throw new Error('INSTAGRAM_BUSINESS_ID 없음. 스크립트 속성에 17841474706647015 박기.');
  return id;
}

function syncInstagramDaily() {
  // 매일 02:00 자동: 시트 비어있으면 전체 / 데이터 있으면 최근 7일
  syncInstagram_('auto');
}

function backfillInstagramAll() {
  // 초기 1회만 (강제 전체)
  syncInstagram_('full');
  try {
    SpreadsheetApp.getUi().alert('✅ 인스타 전체 백필 완료. 이후 매일 02:00 최근 7일만 자동 갱신.');
  } catch (e) { /* trigger 환경에서는 UI 없음 */ }
}

function syncInstagram_(mode) {
  Logger.log('=== syncInstagram_ 시작 (mode: ' + mode + ') ===');
  const igUserId = getInstagramBusinessId_();
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(SHEET_INSTAGRAM);
  if (!sheet) throw new Error('"' + SHEET_INSTAGRAM + '" 시트 없음');

  // 시트 비어있으면 mode 강제 full (auto의 분기)
  const isEmpty = sheet.getLastRow() < INSTAGRAM_DATA_START_ROW;
  const fetchMode = (mode === 'full' || (mode === 'auto' && isEmpty)) ? 'full' : 'recent';
  Logger.log('실제 모드: ' + fetchMode);

  // 팔로워 수 (계정 전체, 현재 시점)
  let followers = 0;
  try {
    const userRes = metaFetch('/' + igUserId, { fields: 'followers_count' });
    followers = Number(userRes.followers_count) || 0;
    Logger.log('팔로워: ' + followers);
  } catch (e) {
    Logger.log('팔로워 조회 실패: ' + e.message);
  }

  // 게시물 fetch (recent 모드는 since=7일 전)
  const sinceTs = fetchMode === 'recent'
    ? Math.floor((Date.now() - 7 * 86400 * 1000) / 1000)
    : null;
  const allMedia = fetchInstagramMedia_(igUserId, sinceTs);
  Logger.log('수집 게시물: ' + allMedia.length + '개');
  if (allMedia.length === 0) {
    logSync_('syncInstagram', 'OK (' + fetchMode + ') 게시물 0건');
    return;
  }

  // 게시물별 조회수(views) fetch (Reels/Image/Video 통합 metric)
  for (let i = 0; i < allMedia.length; i++) {
    const m = allMedia[i];
    try {
      const insightRes = metaFetch('/' + m.id + '/insights', { metric: 'views' });
      const v = (insightRes.data || []).find(function(d){ return d.name === 'views'; });
      m.views = (v && v.values && v.values[0]) ? Number(v.values[0].value) || 0 : 0;
    } catch (e) {
      // views 미지원 시 reach 폴백
      try {
        const r2 = metaFetch('/' + m.id + '/insights', { metric: 'reach' });
        const r = (r2.data || []).find(function(d){ return d.name === 'reach'; });
        m.views = (r && r.values && r.values[0]) ? Number(r.values[0].value) || 0 : 0;
      } catch (e2) {
        m.views = 0;
      }
    }
    if ((i + 1) % 10 === 0) Utilities.sleep(500);
  }

  // 기존 행 매칭 (D열 permalink)
  const existingMap = {};
  if (sheet.getLastRow() >= INSTAGRAM_DATA_START_ROW) {
    const lastRow = sheet.getLastRow();
    const links = sheet.getRange(INSTAGRAM_DATA_START_ROW, 4, lastRow - INSTAGRAM_DATA_START_ROW + 1, 1).getValues();
    links.forEach(function(row, idx) {
      const link = String(row[0] || '').trim();
      if (link) existingMap[link] = INSTAGRAM_DATA_START_ROW + idx;
    });
  }

  // 정렬: timestamp 오름차순 (최신 하단)
  allMedia.sort(function(a, b) { return new Date(a.timestamp) - new Date(b.timestamp); });

  let updated = 0, added = 0;
  allMedia.forEach(function(m) {
    const dateStr = Utilities.formatDate(new Date(m.timestamp), 'Asia/Seoul', 'yyyy-MM-dd');
    const caption = String(m.caption || '').replace(/\n/g, ' ').slice(0, 60);
    const existRow = existingMap[m.permalink];
    if (existRow) {
      // 기존: E·F·G만 갱신 (날짜·주제·링크·메모·비고는 보존)
      sheet.getRange(existRow, 5).setValue(m.views);
      sheet.getRange(existRow, 6).setValue(Number(m.like_count) || 0);
      sheet.getRange(existRow, 7).setValue(followers);
      updated++;
    } else {
      // 신규 append
      const newRow = Math.max(sheet.getLastRow() + 1, INSTAGRAM_DATA_START_ROW);
      sheet.getRange(newRow, 1).setValue(dateStr);
      // B열 포맷 = 수기, 안 박음
      sheet.getRange(newRow, 3).setValue(caption);
      sheet.getRange(newRow, 4).setValue(m.permalink);
      sheet.getRange(newRow, 5).setValue(m.views);
      sheet.getRange(newRow, 6).setValue(Number(m.like_count) || 0);
      sheet.getRange(newRow, 7).setValue(followers);
      existingMap[m.permalink] = newRow;
      added++;
    }
  });

  const msg = '✅ 인스타 ' + fetchMode + ' — 신규 ' + added + ' / 갱신 ' + updated + ' / 팔로워 ' + followers;
  Logger.log(msg);
  logSync_('syncInstagram', msg);
}

function fetchInstagramMedia_(igUserId, sinceTs) {
  const all = [];
  const endpoint = '/' + igUserId + '/media';
  const baseParams = {
    fields: 'id,caption,media_type,timestamp,permalink,like_count',
    limit: 100
  };
  if (sinceTs) baseParams.since = sinceTs;

  let nextCursor = null;
  let safety = 0;
  while (safety < 30) {  // max 30 페이지 (3000 게시물 상한)
    safety++;
    const params = Object.assign({}, baseParams);
    if (nextCursor) params.after = nextCursor;
    const res = metaFetch(endpoint, params);
    if (!res.data || res.data.length === 0) break;
    res.data.forEach(function(m) { all.push(m); });
    if (res.paging && res.paging.cursors && res.paging.cursors.after && res.paging.next) {
      nextCursor = res.paging.cursors.after;
    } else {
      break;
    }
  }
  return all;
}


// ============ ★ 2026-06-10/11 패치 — 메타 자동 학습 (Drive MD) ============
const META_INSIGHTS_DRIVE_FOLDER = 'phonespot_cardnews_state';
const META_INSIGHTS_FILE = 'meta_insights.md';
const META_GEMINI_MODEL = 'gemini-2.5-flash';

function generateMetaInsightsMarkdown() {
  Logger.log('=== generateMetaInsightsMarkdown 시작 ===');
  const ss = SpreadsheetApp.getActive();
  const creativesSheet = ss.getSheetByName(SHEET_META_CREATIVES);
  const integratedSheet = ss.getSheetByName(SHEET_META_INTEGRATED);

  if (!creativesSheet || creativesSheet.getLastRow() < 3) {
    Logger.log('메타_소재 데이터 없음 → 종료');
    return;
  }
  const cData = creativesSheet.getRange(3, 1, creativesSheet.getLastRow() - 2, 15).getValues();
  const ads = cData.map(row => ({
    id: row[0], name: row[1], status: row[2],
    headline: String(row[3] || '').trim(),
    body: String(row[4] || '').trim(),
    impressions: Number(row[6]) || 0,
    clicks: Number(row[7]) || 0,
    spend: Number(row[8]) || 0,
    ctr: Number(row[9]) || 0,
    cpc: Number(row[10]) || 0,
    evaluation: row[11]
  })).filter(a => a.headline && a.headline !== '-' && a.spend >= EVAL_MIN_SPEND);

  if (ads.length === 0) {
    Logger.log('유효 광고 없음');
    return;
  }
  const avgCTR = ads.reduce((s, a) => s + a.ctr, 0) / ads.length;
  const cpcSamples = ads.filter(a => a.cpc > 0);
  const avgCPC = cpcSamples.length > 0
    ? cpcSamples.reduce((s, a) => s + a.cpc, 0) / cpcSamples.length : 0;
  const outperformers = ads.filter(a => a.ctr >= EVAL_CTR_GOOD).sort((a, b) => b.ctr - a.ctr);
  const underperformers = ads.filter(a => a.ctr < EVAL_CTR_AVERAGE).sort((a, b) => a.ctr - b.ctr);
  const topByCTR = ads.slice().sort((a, b) => b.ctr - a.ctr).slice(0, 10);

  // 광고그룹별 카톡전환 효율 (메타_통합 19컬럼: 광고그룹명=E열, 노출=F, 클릭=G, 지출=H, GA4세션=K, 카톡클릭=L)
  let topCampaigns = [];
  if (integratedSheet && integratedSheet.getLastRow() >= 2) {
    const iData = integratedSheet.getRange(2, 1, integratedSheet.getLastRow() - 1, 16).getValues();
    const byCamp = {};
    iData.forEach(row => {
      const name = String(row[4] || '').trim();  // E열=광고그룹명
      if (!name) return;
      if (!byCamp[name]) byCamp[name] = { name, spend: 0, kakaoClicks: 0, sessions: 0 };
      byCamp[name].spend += Number(row[7]) || 0;       // H열=지출
      byCamp[name].kakaoClicks += Number(row[11]) || 0; // L열=카톡클릭
      byCamp[name].sessions += Number(row[10]) || 0;    // K열=GA4세션
    });
    topCampaigns = Object.keys(byCamp).map(k => {
      const c = byCamp[k];
      return {
        name: c.name, spend: c.spend, kakaoClicks: c.kakaoClicks, sessions: c.sessions,
        kakaoConvRate: c.sessions > 0 ? c.kakaoClicks / c.sessions : 0,
        costPerKakao: c.kakaoClicks > 0 ? c.spend / c.kakaoClicks : 0
      };
    }).filter(c => c.spend > 0 && c.kakaoClicks > 0)
      .sort((a, b) => a.costPerKakao - b.costPerKakao)
      .slice(0, 10);
  }

  const insights = analyzeMetaWithGemini_(topByCTR, outperformers, underperformers, topCampaigns, avgCTR);
  const md = buildMetaMarkdown_(insights, {
    totalAds: ads.length, avgCTR, avgCPC: Math.round(avgCPC),
    topByCTR, outperformers: outperformers.slice(0, 10),
    underperformers: underperformers.slice(0, 10), topCampaigns
  });
  saveMetaInsightsToDrive_(md);
  logSync_('generateMetaInsightsMarkdown', `OK (${ads.length} ads / ${topCampaigns.length} 광고그룹)`);
}

function analyzeMetaWithGemini_(topByCTR, outperformers, underperformers, topCampaigns, avgCTR) {
  const key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) return fallbackMetaAnalyze_(topByCTR);

  const topAds = topByCTR.map(a =>
    '[CTR ' + a.ctr + '% / CPC ' + a.cpc + '원] ' + a.headline +
    (a.body && a.body !== '-' ? ' :: ' + a.body.substring(0, 100) : '')
  ).join('\n');
  const outAds = outperformers.slice(0, 10).map(a => '[CTR ' + a.ctr + '%] ' + a.headline).join('\n');
  const underAds = underperformers.slice(0, 10).map(a => '[CTR ' + a.ctr + '%] ' + a.headline).join('\n');
  const campaigns = topCampaigns.slice(0, 5).map(c =>
    '[카톡당 ' + Math.round(c.costPerKakao) + '원, 전환률 ' + (c.kakaoConvRate * 100).toFixed(2) + '%] ' + c.name
  ).join('\n');

  const prompt =
    '폰스팟 (휴대폰 매장, 안양/광교) 메타 광고 성과 분석. 평균 CTR ' + avgCTR.toFixed(2) + '%.\n\n' +
    '=== Top CTR 광고 ===\n' + topAds + '\n\n' +
    '=== 우수 광고 (CTR ' + EVAL_CTR_GOOD + '% 이상) ===\n' + (outAds || '(없음)') + '\n\n' +
    '=== 저조 광고 (CTR ' + EVAL_CTR_AVERAGE + '% 미만) ===\n' + (underAds || '(없음)') + '\n\n' +
    '=== 카톡전환 효율 Top 광고그룹 ===\n' + (campaigns || '(없음)') + '\n\n' +
    'JSON 형식으로만 응답:\n' +
    '{\n' +
    '  "top_keywords": [{"keyword":"키워드","count":빈도,"avg_ctr":평균CTR}],\n' +
    '  "winning_headline_patterns": [{"pattern":"패턴명","examples":["헤드라인 예시"]}],\n' +
    '  "winning_body_patterns": [{"pattern":"패턴명","examples":["본문 발췌"]}],\n' +
    '  "outperformer_traits": ["우수 광고 공통점"],\n' +
    '  "underperformer_traits": ["저조 광고 공통점"],\n' +
    '  "high_conversion_campaign_traits": ["카톡전환 좋은 광고그룹 공통점"],\n' +
    '  "next_ad_recommendation": "다음 광고 카피 룰 3-5문장",\n' +
    '  "cardnews_hooking_suggestion": "카드뉴스/쇼츠 후킹 적용 2-3문장"\n' +
    '}\n\n' +
    '키워드: 한국어 명사, 휴대폰/통신 도메인. 조사 제거. 최대 15개.\n' +
    '헤드라인 패턴: 의문/숫자/가격/감정/시간/긴급 등. 최대 5개.';

  const url = 'https://generativelanguage.googleapis.com/v1beta/models/' +
    META_GEMINI_MODEL + ':generateContent?key=' + key;
  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.3, response_mime_type: 'application/json' }
  };
  try {
    const res = UrlFetchApp.fetch(url, {
      method: 'POST', contentType: 'application/json',
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    if (res.getResponseCode() !== 200) return fallbackMetaAnalyze_(topByCTR);
    const data = JSON.parse(res.getContentText());
    return JSON.parse(data.candidates[0].content.parts[0].text);
  } catch (e) {
    return fallbackMetaAnalyze_(topByCTR);
  }
}

function fallbackMetaAnalyze_(topByCTR) {
  const stopwords = ['은','는','이','가','을','를','의','에','와','과','로','으로','도','만','폰스팟','지금','바로'];
  const wordCount = {};
  topByCTR.forEach(a => {
    const text = (a.headline + ' ' + a.body).split(/[\s,/!?.~()|\[\]]+/);
    text.filter(w => w.length >= 2 && stopwords.indexOf(w) === -1).forEach(w => {
      if (!wordCount[w]) wordCount[w] = { count: 0, totalCTR: 0 };
      wordCount[w].count++;
      wordCount[w].totalCTR += a.ctr;
    });
  });
  const keywords = Object.keys(wordCount).map(k => ({
    keyword: k, count: wordCount[k].count,
    avg_ctr: Number((wordCount[k].totalCTR / wordCount[k].count).toFixed(2))
  })).sort((a, b) => (b.count * b.avg_ctr) - (a.count * a.avg_ctr)).slice(0, 15);

  return {
    top_keywords: keywords,
    winning_headline_patterns: [
      { pattern: '숫자 포함', examples: topByCTR.filter(a => /\d/.test(a.headline)).slice(0, 3).map(a => a.headline) },
      { pattern: '의문문', examples: topByCTR.filter(a => /\?/.test(a.headline)).slice(0, 3).map(a => a.headline) }
    ],
    winning_body_patterns: [],
    outperformer_traits: ['(Gemini 비활성 — GEMINI_API_KEY 설정 시 정확 분석)'],
    underperformer_traits: [],
    high_conversion_campaign_traits: [],
    next_ad_recommendation: 'PropertiesService에 GEMINI_API_KEY 저장 후 정확 분석 활성화.',
    cardnews_hooking_suggestion: '(Gemini 분석 활성화 필요)'
  };
}

function buildMetaMarkdown_(insights, stats) {
  const nowStr = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  let md = '';
  md += '# 폰스팟 메타 광고 인사이트 (자동 학습)\n\n';
  md += '> **자동 생성** | 갱신: ' + nowStr + ' | 분석 광고 ' + stats.totalAds +
        '개 | 평균 CTR ' + stats.avgCTR.toFixed(2) + '% | 평균 CPC ' + stats.avgCPC.toLocaleString() + '원\n\n';
  md += '광고 카피 작성 (generator.html) + 카드뉴스/쇼츠 후킹 reference 자동 Read.\n\n---\n\n';
  md += '## 💡 다음 광고 카피 권장\n\n' + insights.next_ad_recommendation + '\n\n---\n\n';
  md += '## 📰 카드뉴스/쇼츠 후킹 적용\n\n' + insights.cardnews_hooking_suggestion + '\n\n---\n\n';
  md += '## ★ Top 키워드 (가중치 +30%)\n\n| 키워드 | 빈도 | 평균 CTR |\n|---|---|---|\n';
  insights.top_keywords.forEach(k => {
    md += '| ' + k.keyword + ' | ' + k.count + ' | ' + k.avg_ctr + '% |\n';
  });
  md += '\n---\n\n## ★ 우수 헤드라인 패턴 (+20%)\n\n';
  insights.winning_headline_patterns.forEach(p => {
    md += '### ' + p.pattern + '\n';
    (p.examples || []).forEach(ex => { md += '- ' + ex + '\n'; });
    md += '\n';
  });
  md += '---\n\n## ★ 우수 광고 공통점\n\n';
  insights.outperformer_traits.forEach(t => { md += '- ✓ ' + t + '\n'; });
  md += '\n---\n\n';
  if (insights.underperformer_traits && insights.underperformer_traits.length > 0) {
    md += '## ★ 회피 패턴 (-40%)\n\n';
    insights.underperformer_traits.forEach(t => { md += '- ✗ ' + t + '\n'; });
    md += '\n---\n\n';
  }
  if (insights.high_conversion_campaign_traits && insights.high_conversion_campaign_traits.length > 0) {
    md += '## ★ 카톡전환 우수 광고그룹 공통점\n\n';
    insights.high_conversion_campaign_traits.forEach(t => { md += '- 🟢 ' + t + '\n'; });
    md += '\n---\n\n';
  }
  md += '## Top 10 CTR 광고\n\n';
  stats.topByCTR.forEach((a, i) => {
    md += (i + 1) + '. **[CTR ' + a.ctr + '% / CPC ' + a.cpc.toLocaleString() + '원]** ' + a.headline + '\n';
    if (a.body && a.body !== '-') {
      md += '   - 본문: ' + a.body.substring(0, 100) + (a.body.length > 100 ? '...' : '') + '\n';
    }
  });
  md += '\n---\n\n';
  if (stats.topCampaigns.length > 0) {
    md += '## Top 광고그룹 (카톡전환 효율)\n\n';
    md += '| 광고그룹 | 지출 | 카톡클릭 | 카톡당CPC | 전환률 |\n|---|---|---|---|---|\n';
    stats.topCampaigns.forEach(c => {
      md += '| ' + c.name + ' | ' + Math.round(c.spend).toLocaleString() + '원 | ' +
            c.kakaoClicks + ' | ' + Math.round(c.costPerKakao).toLocaleString() + '원 | ' +
            (c.kakaoConvRate * 100).toFixed(2) + '% |\n';
    });
    md += '\n---\n\n';
  }
  md += '## 매장 정합 (휴대폰 도메인)\n\n';
  md += '- 모델명 (갤럭시/아이폰 + 숫자) 강조\n';
  md += '- 가격/지원금/공시지원 우선\n';
  md += '- 통신사 (SKT/KT/LG) + 매장 지역 (안양/광교) 노출 시 가중\n';
  return md;
}

function saveMetaInsightsToDrive_(content) {
  const folders = DriveApp.getFoldersByName(META_INSIGHTS_DRIVE_FOLDER);
  const folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(META_INSIGHTS_DRIVE_FOLDER);
  const files = folder.getFilesByName(META_INSIGHTS_FILE);
  if (files.hasNext()) {
    files.next().setContent(content);
  } else {
    folder.createFile(META_INSIGHTS_FILE, content, MimeType.PLAIN_TEXT);
  }
}

// ============ 🏷️ 카테고리/지역/후킹 구조 라벨링 설정 (Task 43 + 44, 2026-06-12) ============
function setupLabelingDropdowns() {
  const ss = SpreadsheetApp.getActive();
  const ui = SpreadsheetApp.getUi();
  const categories = ['휴대폰', '유심만', '알뜰폰', '중고폰', '키즈폰', '효도폰', '공짜폰', '인터넷', '인터넷+TV'];
  const hookStructures = ['질문형', '단언형', '비교형', '한정형', '가격강조', '감성/공감', '위협형', 'FOMO형'];
  const msgs = [];

  // 메타_소재 시트 16·17열 (P·Q)
  const ms = ss.getSheetByName(SHEET_META_CREATIVES);
  if (ms) {
    const lastRow = Math.max(ms.getLastRow(), 100);
    ms.getRange(2, 16).setValue('카테고리').setFontWeight('bold').setBackground('#f5f5f7');
    ms.setColumnWidth(16, 110);
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(categories, true).setAllowInvalid(false)
      .setHelpText('카테고리 9개 중 선택.').build();
    ms.getRange(3, 16, lastRow - 2, 1).setDataValidation(rule);
    ms.getRange(2, 17).setValue('지역').setFontWeight('bold').setBackground('#f5f5f7');
    ms.setColumnWidth(17, 110);
    msgs.push('✅ 메타_소재 P열: 카테고리 ' + categories.length + '개');
    msgs.push('✅ 메타_소재 Q열: 지역 자유 텍스트 (공백=전국)');
  } else {
    msgs.push('⚠️ 메타_소재 시트 없음');
  }

  // 벤치마크 시트 20·21·22열 (T·U·V)
  const bm = ss.getSheetByName(SHEET_BM_CP);
  if (bm) {
    const lastRow = Math.max(bm.getLastRow(), 100);
    bm.getRange(2, 20).setValue('카테고리').setFontWeight('bold').setBackground('#1F4E78').setFontColor('#FFFFFF');
    bm.setColumnWidth(20, 110);
    const catRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(categories, true).setAllowInvalid(false)
      .setHelpText('카테고리 9개 중 선택.').build();
    bm.getRange(3, 20, lastRow - 2, 1).setDataValidation(catRule);
    bm.getRange(2, 21).setValue('후킹 구조').setFontWeight('bold').setBackground('#1F4E78').setFontColor('#FFFFFF');
    bm.setColumnWidth(21, 110);
    const hookRule = SpreadsheetApp.newDataValidation()
      .requireValueInList(hookStructures, true).setAllowInvalid(false)
      .setHelpText('후킹 구조 8개 중 선택.').build();
    bm.getRange(3, 21, lastRow - 2, 1).setDataValidation(hookRule);
    bm.getRange(2, 22).setValue('지역').setFontWeight('bold').setBackground('#1F4E78').setFontColor('#FFFFFF');
    bm.setColumnWidth(22, 110);
    msgs.push('✅ 벤치마크 T열: 카테고리 ' + categories.length + '개');
    msgs.push('✅ 벤치마크 U열: 후킹 구조 ' + hookStructures.length + '개');
    msgs.push('✅ 벤치마크 V열: 지역 자유 텍스트 (공백=전국)');
  } else {
    msgs.push('⚠️ 벤치마크 시트 없음');
  }

  ui.alert('🏷️ 라벨링 컬럼 설정 완료',
    msgs.join('\n') + '\n\n다음:\n1. 카테고리/후킹 구조: 드롭다운 선택\n2. 지역: 직접 입력 ("광교점", 공백=전국)',
    ui.ButtonSet.OK);
}