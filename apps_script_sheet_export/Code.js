/**
 * 폰스팟 광고운영 관리대장 시트 — read 전용 web app
 * (B1 셋업, 2026-06-15)
 *
 * 별도 Apps Script 프로젝트로 격리. 본점 generator.html doGet과 충돌 없음.
 *
 * GET 요청 형식:
 *   <WEB_APP_URL>?token=<TOKEN>&sheet=<SHEET_NAME>
 *
 * 파라미터:
 *   token        (필수) Script Properties 의 EXPORT_TOKEN 과 일치해야 함
 *   sheet        (필수) 탭 이름. 특수값:
 *                  __list  : 모든 탭 목록 + 행/열 개수
 *                  __meta  : 시트 메타데이터 (id, name, locale, timezone)
 *   offset       (선택) 시작 행 (1-based, 기본 1)
 *   limit        (선택) 가져올 행 수 (기본 = 전체)
 *   includeFormulas (선택) "true" 면 수식도 같이 반환
 *
 * 반환: JSON
 *   { ok: true, sheet, totalRows, totalCols, startRow, numRows, values, formulas? }
 *   { ok: true, sheets: [...] }                  (sheet=__list)
 *   { ok: true, id, name, locale, timezone }     (sheet=__meta)
 *   { ok: false, error: "..." }                  (실패)
 *
 * 보안 모델:
 *   - 토큰 = Script Properties EXPORT_TOKEN
 *   - URL + 토큰 둘 다 알아야 시트 read 가능
 *   - URL/토큰은 _secrets/ + GitHub Secrets에만 박힘 (.gitignore)
 *   - write 기능 0 (read 전용)
 */

// 폰스팟 광고운영 관리대장 Sheet ID (변경 시 여기만 수정)
var SHEET_ID = '1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI';

function doGet(e) {
  var out = function (obj) {
    return ContentService.createTextOutput(JSON.stringify(obj))
      .setMimeType(ContentService.MimeType.JSON);
  };

  try {
    var params = (e && e.parameter) || {};

    // 1. 토큰 인증
    var expected = PropertiesService.getScriptProperties().getProperty('EXPORT_TOKEN');
    if (!expected) {
      return out({ ok: false, error: 'EXPORT_TOKEN not set in script properties' });
    }
    if (params.token !== expected) {
      return out({ ok: false, error: 'invalid token' });
    }

    // 2. 시트 열기
    var ss = SpreadsheetApp.openById(SHEET_ID);

    // 3. 탭 목록 (__list)
    if (params.sheet === '__list') {
      var sheets = ss.getSheets().map(function (s) {
        return {
          name: s.getName(),
          rows: s.getLastRow(),
          cols: s.getLastColumn(),
          hidden: s.isSheetHidden(),
        };
      });
      return out({ ok: true, count: sheets.length, sheets: sheets });
    }

    // 4. 메타데이터 (__meta)
    if (params.sheet === '__meta') {
      return out({
        ok: true,
        id: ss.getId(),
        name: ss.getName(),
        locale: ss.getSpreadsheetLocale(),
        timezone: ss.getSpreadsheetTimeZone(),
      });
    }

    // 5. 특정 탭 데이터
    if (!params.sheet) {
      return out({ ok: false, error: 'sheet parameter required (use __list to see tabs)' });
    }

    var sheet = ss.getSheetByName(params.sheet);
    if (!sheet) {
      return out({ ok: false, error: 'sheet not found: ' + params.sheet });
    }

    var lastRow = sheet.getLastRow();
    var lastCol = sheet.getLastColumn();

    if (lastRow === 0 || lastCol === 0) {
      return out({
        ok: true,
        sheet: params.sheet,
        totalRows: 0,
        totalCols: 0,
        startRow: 1,
        numRows: 0,
        values: [],
      });
    }

    // 6. offset/limit (큰 시트용 페이지네이션)
    var startRow = Math.max(1, parseInt(params.offset, 10) || 1);
    if (startRow > lastRow) {
      return out({
        ok: true,
        sheet: params.sheet,
        totalRows: lastRow,
        totalCols: lastCol,
        startRow: startRow,
        numRows: 0,
        values: [],
      });
    }

    var maxRows = lastRow - startRow + 1;
    var numRows = Math.min(parseInt(params.limit, 10) || maxRows, maxRows);

    var range = sheet.getRange(startRow, 1, numRows, lastCol);
    var values = range.getValues();
    var formulas = params.includeFormulas === 'true' ? range.getFormulas() : null;

    var result = {
      ok: true,
      sheet: params.sheet,
      totalRows: lastRow,
      totalCols: lastCol,
      startRow: startRow,
      numRows: numRows,
      values: values,
    };
    if (formulas) result.formulas = formulas;

    return out(result);

  } catch (err) {
    return out({ ok: false, error: String(err && err.message || err), stack: err && err.stack || null });
  }
}

/**
 * 콘솔에서 직접 실행할 수 있는 자가 검증 함수
 * Apps Script Editor에서 testSelf 선택 후 실행 → 시트 ID + 토큰 작동 확인
 * (V8 런타임에서 Logger.log는 좌측 "실행" 메뉴 → Cloud 로그에 박힘)
 */
function testSelf() {
  var expected = PropertiesService.getScriptProperties().getProperty('EXPORT_TOKEN');
  if (!expected) {
    console.log('FAIL: EXPORT_TOKEN not set in Script Properties');
    return;
  }
  console.log('EXPORT_TOKEN set: ' + (expected.length > 0));

  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    console.log('Sheet OK: ' + ss.getName());
    console.log('Tab count: ' + ss.getSheets().length);
    console.log('Tabs: ' + ss.getSheets().map(function (s) { return s.getName(); }).join(', '));
  } catch (err) {
    console.log('FAIL: ' + err);
  }
}

/* ============================================================
 *  Drive Snapshot 자동 export (2026-06-15 추가)
 *
 *  목적: 클로드 workspace proxy가 script.google.com 차단해서
 *        web_fetch로 직접 호출 불가. 대신 Drive에 JSON 파일
 *        저장하면 Drive MCP로 read 가능.
 *
 *  흐름:
 *    1. setupExportTrigger() 1회 실행 → 매일 03:00 자동 트리거 등록
 *    2. exportAllSheetsToDrive() 매일 03:00 자동 실행
 *    3. 각 탭을 <탭명>.json 으로 Drive 폴더에 저장 (덮어쓰기)
 *    4. __meta.json 에 전체 탭 목록 + 타임스탬프 박음
 *    5. 클로드는 Drive MCP read_file_content로 각 JSON read
 *
 *  사장님 작업 (1회):
 *    A. Drive에 폴더 생성 (예: "PhoneSpot Sheet Snapshots")
 *    B. 폴더 ID 받기 (URL 끝부분 = .../folders/<ID>)
 *    C. Apps Script 스크립트 속성에 SNAPSHOT_FOLDER_ID 등록
 *    D. setupExportTrigger() 1회 실행 → 트리거 등록
 *    E. exportAllSheetsToDrive() 1회 수동 실행 → 첫 snapshot 생성
 * ============================================================ */

function exportAllSheetsToDrive() {
  var folderId = PropertiesService.getScriptProperties().getProperty('SNAPSHOT_FOLDER_ID');
  if (!folderId) {
    var msg = 'SNAPSHOT_FOLDER_ID not set in script properties. ' +
              'Drive 폴더 만들고 ID 등록 필요 (가이드: ads/MULTI_BRAND_ARCHITECTURE.md).';
    console.log(msg);
    throw new Error(msg);
  }

  var folder;
  try {
    folder = DriveApp.getFolderById(folderId);
  } catch (err) {
    throw new Error('Drive folder not found: ' + folderId + ' (' + err + ')');
  }

  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sheets = ss.getSheets();
  var summary = [];
  var startedAt = new Date();

  sheets.forEach(function (sheet) {
    var name = sheet.getName();
    try {
      var lastRow = sheet.getLastRow();
      var lastCol = sheet.getLastColumn();

      if (lastRow === 0 || lastCol === 0) {
        summary.push({ name: name, rows: 0, cols: 0, skipped: true });
        return;
      }

      var range = sheet.getRange(1, 1, lastRow, lastCol);
      var data = {
        sheet: name,
        timestamp: startedAt.toISOString(),
        timezone: 'Asia/Seoul',
        totalRows: lastRow,
        totalCols: lastCol,
        hidden: sheet.isSheetHidden(),
        values: range.getValues(),
        formulas: range.getFormulas(),
      };

      // 파일명 안전화 (윈도우 금지 문자 제거)
      var safeFileName = name.replace(/[<>:"/\\|?*]/g, '_') + '.json';
      var content = JSON.stringify(data);

      // 기존 파일 있으면 덮어쓰기 (최신본만 유지, 용량 증가 방지)
      var existing = folder.getFilesByName(safeFileName);
      if (existing.hasNext()) {
        var file = existing.next();
        file.setContent(content);
        summary.push({ name: name, rows: lastRow, cols: lastCol, action: 'updated', fileId: file.getId() });
      } else {
        var created = folder.createFile(safeFileName, content, MimeType.PLAIN_TEXT);
        summary.push({ name: name, rows: lastRow, cols: lastCol, action: 'created', fileId: created.getId() });
      }
    } catch (err) {
      summary.push({ name: name, error: String(err && err.message || err) });
    }
  });

  // 메타 파일 (전체 탭 목록 + 타임스탬프)
  var metaContent = JSON.stringify({
    timestamp: startedAt.toISOString(),
    timezone: 'Asia/Seoul',
    sheetId: SHEET_ID,
    spreadsheetName: ss.getName(),
    spreadsheetLocale: ss.getSpreadsheetLocale(),
    count: sheets.length,
    durationMs: new Date().getTime() - startedAt.getTime(),
    summary: summary,
  });

  var metaExisting = folder.getFilesByName('__meta.json');
  if (metaExisting.hasNext()) {
    metaExisting.next().setContent(metaContent);
  } else {
    folder.createFile('__meta.json', metaContent, MimeType.PLAIN_TEXT);
  }

  // 헤더 전용 단일 파일 (큰 파일 read 한계 우회용)
  // 각 탭의 첫 5행 + 컬럼 헤더만 모은 단일 JSON
  // 30탭 × 5행 × 20-30열 ≈ 5KB 이하 = 토큰 한계 안 걸림
  var headers = {};
  sheets.forEach(function (sheet) {
    var name = sheet.getName();
    try {
      var lastRow = sheet.getLastRow();
      var lastCol = sheet.getLastColumn();
      if (lastRow === 0 || lastCol === 0) {
        headers[name] = { rows: 0, cols: 0 };
        return;
      }
      var headRows = Math.min(5, lastRow);
      var headRange = sheet.getRange(1, 1, headRows, lastCol);
      headers[name] = {
        totalRows: lastRow,
        totalCols: lastCol,
        head: headRange.getValues(),
      };
    } catch (err) {
      headers[name] = { error: String(err && err.message || err) };
    }
  });

  var headersContent = JSON.stringify({
    timestamp: startedAt.toISOString(),
    sheetId: SHEET_ID,
    spreadsheetName: ss.getName(),
    headers: headers,
  });

  var headersExisting = folder.getFilesByName('__headers.json');
  if (headersExisting.hasNext()) {
    headersExisting.next().setContent(headersContent);
  } else {
    folder.createFile('__headers.json', headersContent, MimeType.PLAIN_TEXT);
  }

  console.log('Exported ' + summary.length + ' sheets to Drive folder ' + folderId);
  console.log('Duration: ' + (new Date().getTime() - startedAt.getTime()) + 'ms');
  return summary;
}

/**
 * 매일 03:00 KST 자동 export 트리거 등록 (1회 실행)
 * 기존 트리거 있으면 제거 후 재등록 = idempotent
 */
function setupExportTrigger() {
  // 기존 트리거 제거
  var removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'exportAllSheetsToDrive') {
      ScriptApp.deleteTrigger(t);
      removed++;
    }
  });

  // 매일 03:00 KST 트리거 등록
  ScriptApp.newTrigger('exportAllSheetsToDrive')
    .timeBased()
    .atHour(3)
    .everyDays(1)
    .create();

  console.log('Trigger registered: exportAllSheetsToDrive daily at 03:00 KST');
  console.log('Removed old triggers: ' + removed);
}
