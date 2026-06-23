/**
 * 협업 리스트업 — '채널 리스트업' + '협업메일 현황' 2탭을 1탭으로 병합 (2026-06-23, 사장님 요청)
 *
 * 설계: 채널 리스트업(마스터 후보 목록)에 협업메일 현황의 추적 칸(발송일/회신일/발송 경로)을
 *       그대로 붙여 단일 표로 만든다. 기존엔 협업현황이 채널명만 적으면 리스트업에서 수식으로
 *       나머지를 끌어왔는데, 병합 후엔 한 행에 다 있으므로 탭 간 수식 링크 불필요.
 *
 * 동작:
 *   1) '협업 리스트업' 탭 생성(있으면 내용 초기화).
 *   2) '채널 리스트업'에서 채널 행을 값으로 읽어 마스터 컬럼 채움(헤더명 기준 매핑 = 컬럼 이동 내성).
 *   3) '협업메일 현황'에 실제 입력된 발송일/회신일/발송 경로가 있으면 채널명 매칭해 이관.
 *   4) 우측에 요약(총 발송/회신/회신율) 자동집계 수식.
 *   5) 원본 2탭 → 이름에 ' (구)' 붙이고 숨김(되돌리기 가능).
 *
 * 실행: Apps Script 편집기 함수 드롭다운에서 buildCollabListup 선택 → ▶ 실행 (1회).
 */

var COLLAB_NEW_SHEET = '협업 리스트업';
var COLLAB_SRC_LIST = '채널 리스트업';
var COLLAB_SRC_MAIL = '협업메일 현황';

// 병합 표 컬럼(순서 = 출력 순서). 마스터 14개 + 추적 3개 + 비고.
var COLLAB_HEADERS = [
  '채널명', '플랫폼', '채널 링크', '카테고리·주제', '소속(MCN)', '연락처',
  '팔로워 수', '보통 조회수', '평균 좋아요', '평균 댓글', '참여율',
  '주 콘텐츠 형식', '적합도', '주 시청자층',
  '발송일', '회신일', '발송 경로', '비고'
];

// 헤더 행(채널명 포함 행)을 첫 6행에서 탐색해 {헤더명: 0based열} 반환
function collabFindHeader_(sheet) {
  if (!sheet) return null;
  var scan = sheet.getRange(1, 1, Math.min(6, sheet.getLastRow() || 1), sheet.getLastColumn() || 1).getValues();
  for (var r = 0; r < scan.length; r++) {
    var row = scan[r];
    for (var c = 0; c < row.length; c++) {
      if (String(row[c]).trim() === '채널명') {
        var map = {};
        for (var k = 0; k < row.length; k++) {
          var h = String(row[k]).trim();
          if (h) map[h] = k;
        }
        return { headerRow: r + 1, map: map }; // 1based headerRow
      }
    }
  }
  return null;
}

function buildCollabListup() {
  var ss = SpreadsheetApp.getActive();
  var listSh = ss.getSheetByName(COLLAB_SRC_LIST);
  var mailSh = ss.getSheetByName(COLLAB_SRC_MAIL);
  var ui = (function () { try { return SpreadsheetApp.getUi(); } catch (e) { return null; } })();
  if (!listSh) { if (ui) ui.alert("'" + COLLAB_SRC_LIST + "' 탭을 찾을 수 없습니다."); return; }

  // --- 1) 마스터(채널 리스트업) 읽기 ---
  var lh = collabFindHeader_(listSh);
  if (!lh) { if (ui) ui.alert("'" + COLLAB_SRC_LIST + "'에서 '채널명' 헤더를 못 찾았습니다."); return; }
  var lLast = listSh.getLastRow();
  var lData = lLast > lh.headerRow
    ? listSh.getRange(lh.headerRow + 1, 1, lLast - lh.headerRow, listSh.getLastColumn()).getValues()
    : [];

  // --- 2) 협업메일 현황의 추적 데이터(채널명 -> {발송일,회신일,발송경로}) ---
  var track = {};
  if (mailSh) {
    var mh = collabFindHeader_(mailSh);
    if (mh) {
      var mLast = mailSh.getLastRow();
      if (mLast > mh.headerRow) {
        var mData = mailSh.getRange(mh.headerRow + 1, 1, mLast - mh.headerRow, mailSh.getLastColumn()).getValues();
        var ci = mh.map['채널명'];
        mData.forEach(function (row) {
          var name = String(row[ci] || '').trim();
          if (!name) return;
          var snd = mh.map['발송일'] != null ? row[mh.map['발송일']] : '';
          var rep = mh.map['회신일'] != null ? row[mh.map['회신일']] : '';
          var via = mh.map['발송 경로'] != null ? row[mh.map['발송 경로']] : '';
          if (snd !== '' || rep !== '' || via !== '') track[name] = { snd: snd, rep: rep, via: via };
        });
      }
    }
  }

  // --- 3) 병합 행 만들기 ---
  // 마스터 헤더명 -> 병합 컬럼명 (대부분 동일, 비고는 끝)
  var fromList = ['채널명', '플랫폼', '채널 링크', '카테고리·주제', '소속(MCN)', '연락처',
    '팔로워 수', '보통 조회수', '평균 좋아요', '평균 댓글', '참여율', '주 콘텐츠 형식',
    '적합도', '주 시청자층', '비고'];
  var rows = [];
  lData.forEach(function (lr) {
    var name = String(lr[lh.map['채널명']] != null ? lr[lh.map['채널명']] : '').trim();
    if (!name) return;
    var get = function (hdr) { var i = lh.map[hdr]; return (i != null && lr[i] != null) ? lr[i] : ''; };
    var t = track[name] || { snd: '', rep: '', via: '' };
    rows.push([
      get('채널명'), get('플랫폼'), get('채널 링크'), get('카테고리·주제'), get('소속(MCN)'), get('연락처'),
      get('팔로워 수'), get('보통 조회수'), get('평균 좋아요'), get('평균 댓글'), get('참여율'),
      get('주 콘텐츠 형식'), get('적합도'), get('주 시청자층'),
      t.snd, t.rep, t.via, get('비고')
    ]);
  });

  // --- 4) 출력 탭 준비 ---
  var out = ss.getSheetByName(COLLAB_NEW_SHEET);
  if (!out) out = ss.insertSheet(COLLAB_NEW_SHEET);
  else out.clear();
  out.clearConditionalFormatRules && out.setConditionalFormatRules([]);

  var nCol = COLLAB_HEADERS.length; // 18
  // 제목(1행) + 헤더(2행) + 데이터(3행~)
  out.getRange(1, 1).setValue('협업 리스트업 (채널 후보 + 메일 발송/회신 통합)');
  out.getRange(1, 1, 1, nCol).merge().setFontWeight('bold').setFontSize(13)
    .setBackground('#1F2A44').setFontColor('#FFFFFF').setHorizontalAlignment('left');
  out.getRange(2, 1, 1, nCol).setValues([COLLAB_HEADERS])
    .setFontWeight('bold').setBackground('#EEF1F5').setFontColor('#1F2A44')
    .setHorizontalAlignment('center');
  if (rows.length) out.getRange(3, 1, rows.length, nCol).setValues(rows);

  var dataLast = 2 + rows.length;
  // 테두리/정렬
  out.getRange(2, 1, rows.length + 1, nCol).setBorder(true, true, true, true, true, true, '#D6DAE0', SpreadsheetApp.BorderStyle.SOLID);
  out.setFrozenRows(2);
  out.setFrozenColumns(1);
  // 적합도(M=13열) 색상: 상=초록 / 중=노랑 / 하=회색
  if (rows.length) {
    var sfRange = out.getRange(3, 13, rows.length, 1);
    var rules = [];
    rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('상').setBackground('#D9EAD3').setRanges([sfRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('중').setBackground('#FFF2CC').setRanges([sfRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('하').setBackground('#EFEFEF').setRanges([sfRange]).build());
    out.setConditionalFormatRules(rules);
  }

  // 컬럼 폭
  var widths = [120, 90, 230, 120, 90, 110, 80, 90, 80, 80, 70, 130, 60, 110, 90, 90, 90, 200];
  widths.forEach(function (w, i) { out.setColumnWidth(i + 1, w); });

  // --- 5) 요약(자동집계) 우측 블록 (col 20~21) ---
  var sumCol = nCol + 2; // 20
  out.getRange(2, sumCol).setValue('요약 (자동 집계)').setFontWeight('bold').setBackground('#EEF1F5');
  var dataStart = 3, dataEnd = Math.max(3, dataLast);
  var sndRef = 'O' + dataStart + ':O' + dataEnd; // 발송일 = O열(15)
  var repRef = 'P' + dataStart + ':P' + dataEnd; // 회신일 = P열(16)
  out.getRange(3, sumCol).setValue('총 발송 건수');
  out.getRange(3, sumCol + 1).setFormula('=COUNTA(' + sndRef + ')');
  out.getRange(4, sumCol).setValue('회신 받음');
  out.getRange(4, sumCol + 1).setFormula('=COUNTA(' + repRef + ')');
  out.getRange(5, sumCol).setValue('회신율');
  out.getRange(5, sumCol + 1).setFormula('=IFERROR(COUNTA(' + repRef + ')/COUNTA(' + sndRef + '),0)').setNumberFormat('0.0%');
  out.getRange(7, sumCol).setValue('[사용법]').setFontWeight('bold');
  out.getRange(8, sumCol).setValue('· 적합도 상으로 선별한 채널에 메일 발송 시, 발송일/회신일/발송 경로만 입력.');
  out.getRange(9, sumCol).setValue('· 발송일·회신일 채우면 우측 요약 자동 집계.');
  out.getRange(10, sumCol).setValue('· 채널 정보(플랫폼/링크/팔로워 등)는 이 표에 직접 입력·관리.');
  out.setColumnWidth(sumCol, 120);
  out.setColumnWidth(sumCol + 1, 90);

  // --- 6) 원본 2탭: (구) 표시 + 숨김 ---
  var hidden = [];
  [listSh, mailSh].forEach(function (sh) {
    if (!sh) return;
    var nm = sh.getName();
    if (nm.indexOf('(구)') < 0) {
      var nn = nm + ' (구)';
      if (!ss.getSheetByName(nn)) sh.setName(nn);
    }
    sh.hideSheet();
    hidden.push(sh.getName());
  });

  // 새 탭을 앞으로
  ss.setActiveSheet(out);
  ss.moveActiveSheet(1);

  var msg = "'" + COLLAB_NEW_SHEET + "' 생성 완료\n\n채널 " + rows.length + "행 병합" +
    "\n원본 숨김: " + (hidden.join(', ') || '없음') +
    "\n\n발송일/회신일/발송 경로만 입력하면 우측 요약 자동 집계됩니다.";
  Logger.log(msg);
  if (ui) ui.alert(msg);
  return { rows: rows.length, hidden: hidden };
}
