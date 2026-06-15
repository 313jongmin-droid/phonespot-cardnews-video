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
 */
function testSelf() {
  var expected = PropertiesService.getScriptProperties().getProperty('EXPORT_TOKEN');
  if (!expected) {
    Logger.log('FAIL: EXPORT_TOKEN not set in Script Properties');
    return;
  }
  Logger.log('EXPORT_TOKEN set: ' + (expected.length > 0));

  try {
    var ss = SpreadsheetApp.openById(SHEET_ID);
    Logger.log('Sheet OK: ' + ss.getName());
    Logger.log('Tab count: ' + ss.getSheets().length);
    Logger.log('Tabs: ' + ss.getSheets().map(function (s) { return s.getName(); }).join(', '));
  } catch (err) {
    Logger.log('FAIL: ' + err);
  }
}
