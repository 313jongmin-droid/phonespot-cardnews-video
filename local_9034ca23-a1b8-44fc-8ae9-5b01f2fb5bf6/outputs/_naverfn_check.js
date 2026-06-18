function refreshNaverGA4AllRows() {
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName(SHEET_NAVER_INTEGRATED);
  const ui = SpreadsheetApp.getUi();
  if (!sh) { ui.alert('네이버_통합 시트 없음.'); return; }
  const last = sh.getLastRow();
  if (last < 2) { ui.alert('네이버_통합 데이터 행 없음.'); return; }

  for (let row = 2; row <= last; row++) {
    const ymdText = `TEXT(A${row},"yyyymmdd")`;
    const utmSlug = `IFERROR(VLOOKUP(E${row}, FILTER('UTM_매핑'!B:C, 'UTM_매핑'!A:A="네이버"), 2, FALSE),E${row})`;
    const ga4Base = `'GA4_자동'!A:A,${ymdText},'GA4_자동'!B:B,"naver",'GA4_자동'!D:D,${utmSlug}`;
    sh.getRange(row, 11).setFormula(`=IFERROR(SUMIFS('GA4_자동'!G:G,${ga4Base},'GA4_자동'!E:E,"session_start"),0)`);
    sh.getRange(row, 12).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"kakao_chat_click"),0)`);
    sh.getRange(row, 13).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"phone_click"),0)`);
    sh.getRange(row, 14).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_click"),0)`);
    sh.getRange(row, 15).setFormula(`=IFERROR(SUMIFS('GA4_자동'!F:F,${ga4Base},'GA4_자동'!E:E,"citymarket_arrival"),0)`);
    sh.getRange(row, 16).setFormula(`=IFERROR(IF(K${row}=0,0,L${row}/K${row}),0)`);
    sh.getRange(row, 17).setFormula(`=IFERROR(IF(L${row}=0,"-",H${row}/L${row}),"-")`);
    sh.getRange(row, 18).setFormula(`=COUNTIFS('문의접수'!D:D,"네이버",'문의접수'!A:A,A${row})`);
    sh.getRange(row, 19).setFormula(`=IFERROR(IF(R${row}=0,"-",H${row}/R${row}),"-")`);
  }
  SpreadsheetApp.flush();
  const msg = '네이버_통합 ' + (last - 1) + '개 행 GA4 수식 재작성 (통합 UTM_매핑 기준)';
  Logger.log(msg);
  if (typeof logSync_ === 'function') logSync_('refreshNaverGA4AllRows', msg);
  ui.alert('✅ 완료', msg + '\n\nGA4세션·카톡·문의 컬럼이 다시 채워졌는지 확인하세요.', ui.ButtonSet.OK);
}
