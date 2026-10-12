/**
 * draft_gen.gs — 폰스팟 스레드 초안 생성 (2단계)  [v2]
 *
 * price_sync.gs 가 쌓아둔 시세_현재 를 읽어 2단 체인 초안을 만든다.
 *
 * 하루 3체인 — 12시(점심) / 18시(퇴근) / 21시(취침 전).
 * 컨셉(플래그십·가성비·DP)은 시간대에 고정하지 않고 3일 주기로 돌린다.
 * 시간대 효과와 컨셉 효과를 나중에 분리하기 위해서다. 아래 '진입점' 참고.
 *
 * ★ v2 핵심 변경: 2단계는 통신사별 **대표 요금제 하나로 고정**한다.
 *   기종별 최저가를 그냥 나열하면 요금제가 28,000~110,000원으로 섞이는데
 *   아래에 조건을 한 줄로 쓰면 네 요금제 가격을 한 조건으로 표시하는 셈이 된다.
 *   (지원금 오인 유도에 정확히 걸리는 형태라 반드시 고정해야 한다)
 *
 * 발행은 publish_threads.gs 가 맡는다. 여기서는 초안만 만든다.
 */

var DG = {
  SHEET_NOW:   '시세_현재',
  SHEET_CONF:  '시세_설정',
  SHEET_DRAFT: '시세_초안', SHEET_DIFF: '시세_변동',
  LOG_SHEET:   '동기화_로그',

  MONTHS: 24,
  MAX_LEN: 480,            // 스레드 500자. 여유 20자.
  CUT_RATE: 100,           // 할인율 컷. 100% = 기기값 0원 이하.
  MAX_PER_CARRIER: 3,      // 통신사당 최대
  SKIP_BELOW_CUT: true,    // 컷 미달 통신사는 뺀다. false면 상위 2개로 채운다.
  LOWCOST_MAX: 600000,     // 출고가 이 미만이면 '저가' 카테고리
  SHOW_TCO_LINE: true,

  PROP_TG_TOKEN: 'TELEGRAM_BOT_TOKEN',
  PROP_TG_CHAT:  'TELEGRAM_CHAT_ID'
};

// 통신사별 대표 요금제. 시세_설정 G열로 덮어쓸 수 있다.
var DG_REP_PLAN = { KT: '초이스110', SKT: '베스트 109', LG: '플러스 플랜115' };

/**
 * 훅 문구 풀 — 후킹-분류표 v1의 사건축 × 표현축.
 * 1단계 첫 줄은 이것만 쓴다. 카테고리 라벨(저가/갤럭시/애플)은 선정 기준일 뿐
 * 글에 노출하지 않는다. 표현축이 성과 측정의 실험 대상이므로 반드시 로테이션한다.
 * [기종] [금액] [변동] 치환.
 */
var DG_HOOKS = {
  PB:    [['TEASE','[기종] 이제 돈 돌려받네요'],
          ['NUM','[기종] [금액]입니다'],
          ['EXC','[기종] 이거 실화인가요']],
  DROP:  [['TEASE','[기종] 가격 많이 떨어졌네요'],
          ['EXC','[기종] 미쳤네요..'],
          ['NUM','[기종] [금액]까지 내려왔어요!']],
  LOW30: [['NUM','[기종], 30일 중 오늘이 제일 낮네요'],
          ['TEASE','[기종] 이 가격 한 달 만이에요']],
  // 변동 전용. 어제 실제로 내려간 것만 쓰므로 사실 확인이 되는 표현이다.
  CHANGE:[['NUM','[기종] [변동] 내려갔어요'],
          ['TEASE','조용히 내려간 폰이 있어요'],
          ['EXC','[기종] 이만큼 빠졌네요'],
          ['RANK','최근 가격 내려간 폰 정리']],
  // 2026-10-07: #2 는 성적이 유의하게 낮아 DG_HOOK_OFF 로 껐다(배수 0.55, 구간 0.37~0.83).
  // 지우지 않는다 — 지우면 뒤 인덱스가 밀려 훅_성과에 쌓인 과거 기록이 다른 문구를 가리킨다.
  // #3·#4 는 신규폰에서 12배 차이를 낸 '비교' 프레이밍을 가성비에도 옮겨본 것이다.
  RANK:  [['RANK','오늘 가성비 TOP 3'],
          ['RANK','오늘 제일 많이 돌려주는 폰 세 대'],
          ['TEASE','싼 폰 찾으면 오늘은 이 세 대예요'],
          ['RANK','같은 폰, 통신사별 가격 비교'],
          ['RANK','통신사별로 얼마나 다른지 정리했어요']],
  // 플래그십 전용. '가성비'라고 쓰면 최신폰 글에 안 맞는다.
  RANK_FLAG: [['RANK','최신폰 오늘 가격입니다'],
          ['TEASE','신형 중에 오늘 이게 제일 좋아요'],
          ['RANK','오늘 최신폰 TOP 3']],
  // 신규폰 출시 기간 전용. [기종]은 용량 없이, [금액]은 최저가, [변동]은 출고가 대비 할인액.
  // 결함·품절·대란 같은 말은 쓰지 않는다. 확인되는 숫자만.
  // 2026-10-07 실측: #0(비교형) 5건 중앙 1,682 vs 나머지 11건 전부 240 이하. 완전분리, 12.3배.
  // #1(금액형)·#3(할인액형)을 끄고 비교형 변형 #4·#5 를 넣었다.
  // 매일 같은 문장을 쓰면 피로가 쌓이므로 '비교 형식 안에서' 돌린다.
  LAUNCH:[['RANK','[기종] 통신사별 가격 비교'],
          ['NUM','[기종] [금액]부터예요'],
          ['QUES','[기종] 어디가 제일 쌀까요?'],
          ['TEASE','[기종] 출고가보다 [변동] 낮아요'],
          ['RANK','[기종] KT·SKT·LG 얼마나 다른지'],
          ['RANK','[기종] 3사 가격 정리했습니다']],
  // 재고 수량은 API에 없다. '남은', '마감 임박' 처럼 재고 상태를 단정하는 표현은 쓰지 않는다.
  SCARCE:[['TEASE','전시폰인데 이 가격 흔치 않아요'],
          ['QUES','전시폰이 왜 이렇게 싼지 아세요?'],
          ['NUM','전시폰 [기종] [금액]'],
          ['EXC','개봉만 했는데 이 가격이에요']]
};

/**
 * 쓰지 않을 문구 틀. 성적이 나쁘다고 **지우지 말고 여기 적는다** —
 * 틀 식별자는 '풀이름#순번' 이라서, 배열에서 빼면 뒤 항목들의 번호가 밀리고
 * 훅_성과·요인_성과에 쌓인 과거 기록이 엉뚱한 문구를 가리키게 된다.
 * 2026-10-07 기준 근거:
 *   RANK#2  '싼 폰 찾으면 오늘은 이 세 대예요'  배수 0.55 (0.37~0.83) — 유의하게 낮음
 *   LAUNCH#1 '[기종] [금액]부터예요'            중앙 87  — 비교형의 1/19
 *   LAUNCH#3 '[기종] 출고가보다 [변동] 낮아요'   중앙 98  — 비교형의 1/17
 */
var DG_HOOK_OFF = ['RANK#2', 'LAUNCH#1', 'LAUNCH#3'];

/**
 * 「변동」 운영 규칙 (2026-10-07 추가)
 *
 * 성숙분 90건 분석에서 주제 효과가 유의했고(F(4,72)=3.27, p=0.016),
 * 「변동」이 기준(DP) 대비 2.34배(1.41~3.87)로 1위, 「가성비」가 0.66배로 최하였다.
 * 그런데 변동은 소재가 없으면 칸이 통째로 비고(14일 중 3일), 소재가 18건 있는 날에도
 * 상위 4개만 쓰고 나머지를 버렸다. 그래서 두 가지를 바꾼다.
 *
 *  (가) FALLBACK — 변동 차례에 소재가 없으면 건너뛰지 말고 가성비 글로 채운다.
 *  (나) SECOND   — 소재가 MIN_ITEMS 이상인 날은 가성비 차례를 '변동 2회차'로 쓴다.
 *                  1회차에 쓴 기종은 제외하고 다음 낙폭들로 만든다.
 *
 * 주제 효과는 이미 판정이 끝났으므로 배분이 기울어도 잃는 게 적다.
 * 다만 요인 추정의 균형 설계는 깨진다 — 앞으로 주제 비교는 기간을 나눠서 봐야 한다.
 */
var DG_CHG2 = {
  FALLBACK: true,     // (가)
  SECOND: true,       // (나)
  // 1회차에 쓴 기종을 뺀 뒤 남은 기종 수 기준.
  // 2026-09-20~10-06 재현: 남은 소재가 2종 이상인 날이 17일 중 5일(29%)이었다.
  // 6종으로 잡으면 2일(12%)밖에 안 걸려 규칙이 거의 돌지 않는다. 1종이면 글이 너무 얇다.
  MIN_ITEMS: 2
};

/** 한 번에 만들 시안 수. 같은 사건에 표현만 바꿔서 낸다. */
/**
 * 시안 개수. 1이면 "가장 좋은 것 하나"만 만들어 바로 올린다.
 * 사장님 검토 단계를 없앤 대신, 훅은 무작위가 아니라 훅_성과 점수로 고른다.
 * 3으로 되돌리면 예전의 3안 승인 방식으로 돌아간다.
 */
var DG_VARIANTS = 1;

/** true면 초안을 '승인' 상태로 써서 5분 안에 그대로 발행된다. */
var DG_AUTO_APPROVE = true;

/**
 * 하한선 — 실구매가가 이 값보다 크면(=페이백이 작으면) 목록에서 뺀다.
 * 오늘 실제로 '가성비 TOP 3'에 390,000원짜리가 들어갔던 게 이걸 안 둬서다.
 * 조건이 나쁜 날은 항목이 줄고, DG_MIN_ITEMS 미만이면 아예 안 올린다.
 */
var DG_FLOOR = { 'DP': -20000, '플래그십': 0, '가성비': -50000 };
var DG_MIN_ITEMS = 2;

/**
 * '변동' 컨셉 전용 기준.
 * DROP_MIN 이상 내려간 건만 소재로 쓴다. 몇 천원 움직인 걸 "내려갔어요"라고 하면 신뢰를 깎는다.
 * LOOKBACK_H 안에 감지된 변동만 본다 — 어제 것을 오늘 아침에 말하는 게 이 글의 전부다.
 */
/**
 * 실측으로 조정한 값이다.
 * 2026-08-25~09-09 2주간 시세_변동이 7건뿐이었다. 하락 -50,000 이상은 1건.
 * 변동 슬롯은 4일에 한 번 오는데 그때마다 건너뛰면 8시 표본이 영영 안 쌓인다.
 *   LOOKBACK_H 100 — 지난 변동 슬롯(4일 전) 이후를 다 모은다
 *   DROP_MIN 30,000 — 실구매가 136,000→106,000 은 22% 하락이라 소재가 된다
 *   MIN_ITEMS 1 — 단일 기종도 올린다. 오히려 훅이 더 세다
 */
var DG_CHG = { DROP_MIN: 30000, LOOKBACK_H: 96, MAX_ITEMS: 4, MIN_ITEMS: 1,
               HOLD_H: 3,          // 지금 가격이 이만큼 유지돼야 쓴다
               MAX_DROP: 500000 }; // 4일에 50만원 넘게 내렸다면 데이터부터 의심한다

/** 하락으로 DROP 훅을 쓸 최소 폭 */
var DG_DROP_MIN = 50000;

/**
 * 플래그십 = 최신 세대. 14시 글은 이것만, 18시 글은 이걸 뺀 나머지.
 * 새 기종이 나오면 여기에 추가한다.
 */
// 아이폰17e·S25FE 같은 보급형이 걸리지 않도록 뒤에 e/FE 가 붙은 건 제외한다
// 플래그십 판정. 새 기종이 나오면 여기만 넓힌다.
// 2026-09-21: 아이폰18프로·프로맥스가 데이터에 들어왔는데 17까지만 보던 탓에 플래그십에서 빠져 있었다.
// 숫자 범위로 적어 다음 세대(S27·아이폰19·폴드9)도 자동으로 들어오게 했다. e·FE 는 계속 제외.
var DG_FLAGSHIP = /(S2[6-9]|아이폰\s?(?:1[7-9]|에어)|Z\s?(?:폴드|플립)\s?(?:[89]|1\d)|폴드\s?울트라)(?![eE]|\s?FE)/i;
function isFlagship_(r) { return DG_FLAGSHIP.test(String(r.model)); }

/**
 * 신규폰 출시 기간.
 * 이 기간에는 플래그십 차례(하루 1번, 시간대는 로테이션 그대로)에 신규폰 글을 대신 올린다.
 * 2026-09-21 결정 — 아이폰18프로·프로맥스 9/18 국내 출시.
 *   네이버 데이터랩(9/20): 아이폰18 16.5 vs 아이폰17 3.6 vs S26 2.2 (상대지수)
 *   출시 관심은 빨리 식는다(9/13 32.1 → 9/16 16.7). 그래서 기간을 4주로 끊는다.
 * 기간이 끝나면 아무것도 안 해도 원래 플래그십 글로 돌아간다.
 * 다음 신규폰 때는 RE·PREV·FROM·UNTIL 만 바꾸면 된다.
 */
var DG_LAUNCH = {
  RE: /아이폰\s?18/,            // 신규폰 기종
  PREV: ['18', '17'],           // 전작 비교: 기종명에서 앞을 뒤로 바꾼 게 전작
  FROM: '2026-09-18', UNTIL: '2026-10-18'   // 서울 날짜, 양끝 포함
};
function launchActive_() {
  var d = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
  return !!DG_LAUNCH && d >= DG_LAUNCH.FROM && d <= DG_LAUNCH.UNTIL;
}

/**
 * 2/2 맨 아래 고정 문구 — 사전승낙서.
 * 2026-09-21: 프로필 링크로는 안 열린다는 제보. 번호를 글자로도 적어 둔다 —
 * 링크가 막혀도 손님이 ictmarket.or.kr 에서 번호로 직접 조회할 수 있다.
 * 비우면('') 아무것도 안 붙는다. 500자 계산은 이 길이를 먼저 빼고 한다.
 */
var DG_FOOTER = '\n\n📑 사전승낙서 PRE0000194479\n'
  + 'https://ictmarket.or.kr:8443/precon/pop_CertIcon.do?PRECON_REQ_ID=PRE0000194479&YN=1';

var DG_HEAD = ['생성시각','배치','안','종류','태그','통신사','1단계','2단계','메타','상태','발행링크'];

// ─────────────────────────────────────────────
// 진입점
// ─────────────────────────────────────────────

/**
 * 시간대 3개 × 컨셉 3개.
 *
 *   8시 출근  /  12시 점심  /  18시 퇴근  /  21시 취침 전
 *
 * 시간대에 컨셉을 붙박이로 매어두면, 21시 성과가 좋을 때 그게 시간 때문인지
 * 그 컨셉 때문인지 영영 구분할 수 없다(교란). 그래서 주기로 돌린다.
 *
 * 슬롯이 4개면 컨셉도 4개여야 라틴 방격이 성립한다.
 * 3개짜리로 4슬롯을 돌리면 8시와 21시가 **매일 같은 컨셉**이 되어 완전히 교란된다.
 * 그래서 '변동'(어제 바뀐 가격)을 네 번째 컨셉으로 넣었다.
 *
 *         8시        12시       18시       21시
 *   D+0   플래그십    가성비     DP        변동
 *   D+1   가성비      DP        변동      플래그십
 *   D+2   DP         변동       플래그십   가성비
 *   D+3   변동        플래그십   가성비     DP
 *
 * 4일이면 모든 컨셉이 모든 시간대를 정확히 한 번씩 지난다.
 * 16일(=4주기)이면 셀마다 4표본. 시간대 효과와 컨셉 효과를 따로 뽑을 수 있다.
 * 로테이션을 끄고 시간대를 고정하고 싶으면 DG_ROTATE 를 false 로 둔다.
 */
var DG_ROTATE = true;
var DG_SLOTS  = [8, 12, 18, 21];
var DG_KINDS  = ['플래그십', '가성비', 'DP', '변동'];
var DG_FIXED  = { 8: '변동', 12: '플래그십', 18: '가성비', 21: 'DP' };   // DG_ROTATE = false 일 때

function generateSlot8()  { runSlot_(8); }
function generateSlot12() { runSlot_(12); }
function generateSlot18() { runSlot_(18); }
function generateSlot21() { runSlot_(21); }

function runSlot_(hour) {
  var kind = kindForSlot_(hour, new Date());

  // (나) 하락 소재가 넉넉한 날은 가성비 칸을 '변동 2회차'로 쓴다.
  //     성과 차이가 2.34배 대 0.66배라 같은 칸에서 기대값이 크게 다르다.
  if (kind === '가성비' && DG_CHG2.SECOND) {
    try {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var rows = readNow_(ss);
      var ex = todayChangeModels_();
      var avail = chgPicks_(ss, rows, ex);
      if (avail.length >= DG_CHG2.MIN_ITEMS) {
        dgLog_('OK', '가성비 칸 → 변동 2회차 (소재 ' + avail.length + '종, 1회차 제외 후)');
        runDraft_('변동', hour, { second: true, exclude: ex });
        return;
      }
    } catch (e) { dgLog_('WARN', '2회차 판정 실패, 원래 컨셉으로 진행: ' + String(e).slice(0, 120)); }
  }

  // 변동 차례도 '오늘 이미 쓴 기종'을 제외한다.
  // 가성비 칸이 변동 2회차로 먼저 돌 수 있어(예: 8시 가성비 / 18시 변동),
  // 제외를 안 하면 같은 기종이 하루에 두 번 나간다.
  if (kind === '변동') { runDraft_(kind, hour, { exclude: todayChangeModels_() }); return; }

  runDraft_(kind, hour);
}

/** 오늘 이미 변동 글에 쓴 기종 목록. 2회차가 같은 기종을 또 쓰지 않게. */
function todayChangeModels_() {
  var out = [];
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(DG.SHEET_DRAFT);
    if (!sh || sh.getLastRow() < 2) return out;
    var n = Math.min(40, sh.getLastRow() - 1);
    var v = sh.getRange(sh.getLastRow() - n + 1, 1, n, 10).getValues();
    var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
    v.forEach(function (r) {
      var stamp = r[0] instanceof Date
        ? Utilities.formatDate(r[0], 'Asia/Seoul', 'yyyy-MM-dd')
        : String(r[0]).slice(0, 10);
      if (stamp !== today) return;
      if (String(r[3]).trim() !== '변동') return;
      var st = String(r[9]).trim();
      if (st === '미선택' || st === '만료' || st === '보류') return;   // 안 나간 글은 제외 대상이 아니다
      var m = String(r[8]).match(/기종목록=([^;]*)/);
      if (m && m[1]) out = out.concat(m[1].split('|'));
      else {
        var d = String(r[8]).match(/대표=([^;]*)/);        // 옛 글은 대표 기종만 있다
        if (d && d[1]) out.push(d[1]);
      }
    });
  } catch (e) { /* noop */ }
  return out;
}

/** 지금 변동 소재가 몇 종 있는지, 2회차가 가능한지 로그로 본다. 시트를 안 건드린다. */
function checkChangePool() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var rows = readNow_(ss);
  var ex = todayChangeModels_();
  var all = chgPicks_(ss, rows, []);
  var rest = chgPicks_(ss, rows, ex);
  Logger.log('하락 소재 %s종 (최근 %s일, %s 이상 하락)', all.length,
    Math.round(DG_CHG.LOOKBACK_H / 24), dgWon_(DG_CHG.DROP_MIN));
  all.forEach(function (r) {
    Logger.log('   %s %s  %s → %s  (%s 하락)', r.carrier, name_(r),
      priceText_(r.before), priceText_(r.price), dgWon_(Math.abs(r.delta)));
  });
  Logger.log('오늘 1회차에 쓴 기종: %s', ex.length ? ex.join(', ') : '(없음)');
  Logger.log('2회차용 남은 소재 %s종 → 기준 %s종 %s', rest.length, DG_CHG2.MIN_ITEMS,
    rest.length >= DG_CHG2.MIN_ITEMS ? '충족 (가성비 칸이 변동으로 바뀝니다)' : '미달 (가성비 그대로)');
}

/** 그 날짜 그 시간대에 어떤 컨셉이 걸리는지 */
function kindForSlot_(hour, date) {
  if (!DG_ROTATE) return DG_FIXED[hour];
  var slotIdx = DG_SLOTS.indexOf(hour);
  if (slotIdx < 0) return DG_KINDS[0];
  var n = DG_KINDS.length;
  return DG_KINDS[((dayNum_(date) + slotIdx) % n + n) % n];
}

/** KST 기준 일련 일자. 서버 시간대에 흔들리지 않게 날짜 문자열을 거쳐서 만든다. */
function dayNum_(date) {
  var p = Utilities.formatDate(date, 'Asia/Seoul', 'yyyy-MM-dd').split('-');
  return Math.floor(Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000);
}

/** 앞으로 6일 배치표를 로그로 본다 */
function showRotation() {
  var now = new Date();
  // 주기는 컨셉 개수를 따라간다. 숫자를 박아두면 슬롯을 늘릴 때마다 로그가 거짓말을 한다.
  Logger.log('로테이션 %s', DG_ROTATE ? 'ON (' + DG_KINDS.length + '일 주기)' : 'OFF (고정)');
  for (var i = 0; i < 8; i++) {
    var x = new Date(now.getTime() + i * 86400000);
    Logger.log('%s   8시 %s   12시 %s   18시 %s   21시 %s',
      Utilities.formatDate(x, 'Asia/Seoul', 'MM/dd(E)'),
      kindForSlot_(8, x), kindForSlot_(12, x), kindForSlot_(18, x), kindForSlot_(21, x));
  }
  if (DG_CHG2.SECOND) Logger.log('※ 가성비 칸은 하락 소재가 %s종 이상 남은 날 「변동 2회차」로 바뀝니다.', DG_CHG2.MIN_ITEMS);
  if (DG_CHG2.FALLBACK) Logger.log('※ 변동 칸은 소재가 없으면 비우지 않고 가성비 글로 채웁니다.');
  Logger.log('※ 꺼둔 훅: %s', DG_HOOK_OFF.join(', ') || '(없음)');
}

// ── 수동 실행용 (트리거는 위의 generateSlotNN 을 쓴다)
function generateDpDraft()       { runDraft_('DP', 0); }
function generateFlagshipDraft() { runDraft_('플래그십', 0); }
function generateValueDraft()    { runDraft_('가성비', 0); }

function installDraftSettings() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss.getSheetByName(DG.SHEET_CONF)) { Logger.log('시세_설정 이미 있음'); return; }
  var sh = ss.insertSheet(DG.SHEET_CONF);
  sh.getRange(1, 1, 5, 7).setValues([
    ['통신사','대표요금제월액','유지일수','유지후하한요금제','부가월액','부가유지일수','대표요금제명'],
    ['KT',  110000, 185, 47000,  9900, 30, '초이스110'],
    ['SKT', 109000, 185, 42000, 10000, 95, '베스트 109'],
    ['LG',  115000, 185, 45000, 39890, 95, '플러스 플랜115'],
    ['※ 2026-08-25 씨티몰 상세 실측. 조건이 바뀌면 이 표만 고치면 됩니다.','','','','','','']
  ]);
  sh.getRange(1, 1, 1, 7).setFontWeight('bold');
  sh.setFrozenRows(1);
  Logger.log('시세_설정 생성 완료');
}

function installDraftTriggers() {
  if (!threadsGuard_('installDraftTriggers')) return;
  // 옛 트리거(10/14/18시)가 남아 있으면 지우고 다시 건다. 두 번 실행해도 안전하다.
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction().indexOf('generate') === 0) ScriptApp.deleteTrigger(t);
  });
  DG_SLOTS.forEach(function (h) {
    ScriptApp.newTrigger('generateSlot' + h).timeBased().everyDays(1).atHour(h).create();
  });
  Logger.log('초안 트리거 등록: 8시 / 12시 / 18시 / 21시');
  showRotation();
}

/** 시트를 안 건드리고 로그로만 확인 */
function checkDrafts() {
  ['DP', '플래그십', '가성비'].forEach(function (kind) {
    Logger.log('████ %s', kind);
    for (var i = 0; i < DG_VARIANTS; i++) {
      var d = buildDraft_(kind, i);
      if (!d) { Logger.log('  (만들 수 없음)'); break; }
      Logger.log('── %s안 %s (%s자)\n%s', String(i + 1), d.tag, String(d.len1), d.post1);
      if (i === 0) Logger.log('── 공통 2/2 (%s자)\n%s', String(d.len2), d.post2);
    }
  });
}

// ─────────────────────────────────────────────
// 본체
// ─────────────────────────────────────────────

/**
 * 같은 사건에 표현만 바꿔 시안 3개를 만든다.
 * 사장님이 하나를 '승인'하면 나머지는 publish_threads 가 '미선택'으로 정리한다.
 */
function runDraft_(kind, slot, opt) {
  if (!threadsGuard_('runDraft_')) return;
  opt = opt || {};
  var ds = [];
  try {
    for (var i = 0; i < DG_VARIANTS; i++) {
      var d = buildDraft_(kind, i, opt);
      if (!d) break;
      // 같은 문구가 두 번 나오면 버린다 (풀이 짧을 때)
      var dup = ds.some(function (x) { return x.post1 === d.post1; });
      if (!dup) ds.push(d);
    }
  } catch (err) { dgLog_('FAIL', kind + ': ' + String(err).slice(0, 200)); return; }
  if (!ds.length) {
    // (가) 변동 소재가 없으면 칸을 비우지 말고 가성비 글로 채운다.
    //     2026-09-24~10/07 사이 14일 중 3일이 이 이유로 통째로 비었다.
    //     2회차(가성비 칸을 빌린 경우)가 실패한 때도 원래 주인인 가성비로 돌아간다.
    if (kind === '변동' && DG_CHG2.FALLBACK && !opt.fb) {
      dgLog_('OK', '변동 소재 없음 → 가성비로 대체' + (opt.second ? ' (2회차 실패)' : ''));
      runDraft_('가성비', slot, { fb: true });
      return;
    }
    dgLog_('SKIP', kind + ': 조건 맞는 상품 없음');
    // 조용히 넘어가면 "안 올라온 것"과 "고장난 것"을 구분할 수 없다.
    var why = (kind === '변동')
      ? '최근 ' + Math.round(DG_CHG.LOOKBACK_H / 24) + '일간 '
        + dgWon_(DG_CHG.DROP_MIN) + ' 이상 내려간 기종이 없습니다.'
      : '하한선(' + dgWon_(Math.abs(DG_FLOOR[kind] || 0))
        + ' 이상 페이백)을 넘는 기종이 ' + DG_MIN_ITEMS + '개가 안 됩니다.';
    dgAlert_('ℹ️ ' + kind + ' 오늘은 건너뜁니다\n' + why + '\n'
           + '고장이 아닙니다. 소재 없는 날은 안 올리는 게 방침입니다.');
    return;
  }

  // 슬롯을 배치명과 메타에 박아둔다. 나중에 시간대별 성과를 가를 때 쓴다.
  if (slot) ds.forEach(function (d) { d.meta = d.meta + ';슬롯=' + slot; });
  if (opt.fb) ds.forEach(function (d) { d.meta = d.meta + ';대체=변동소재없음'; });
  // 훅을 왜 그걸로 골랐는지는 메타에 남긴다. 스레드 탭 비고까지 따라가므로
  // 나중에 "이 훅이 왜 뽑혔지"를 시트만 보고도 알 수 있다.
  ds.forEach(function (d) {
    if (d.tid) d.meta = d.meta + ';훅=' + d.tid;       // 어느 문구 틀인지 — 학습의 단위
    if (d.why) d.meta = d.meta + ';근거=' + d.why;
  });

  // 1안 직행은 기계가 고른 것이다. 표시를 안 하면 훅_성과에 전부 '수동'으로 찍혀
  // 나중에 선택 편향을 보정할 때 사람 선택과 구분이 안 된다.
  // (autoPublishPending 이 붙이던 표시인데, 1안 직행에서는 그게 안 돌아서 비어 있었다)
  if (DG_AUTO_APPROVE && DG_VARIANTS === 1) {
    ds.forEach(function (d) { d.meta = d.meta + ';선정=자동'; });
  }

  var batch = kind + '-' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'MMdd-HHmm')
            + (slot ? '-S' + slot : '');
  writeDrafts_(batch, ds);

  // 1안 직행일 때는 생성 시점에 알리지 않는다.
  // 어차피 몇 분 뒤 발행 알림이 같은 내용을 들고 오므로 두 번 울릴 뿐이다.
  // 3안 승인 방식에서는 이 알림이 있어야 고를 수 있으니 그대로 둔다.
  if (!(DG_AUTO_APPROVE && DG_VARIANTS === 1)) {
    dgAlert_(renderBatch_(batch, kind, ds));
  }

  dgLog_('OK', kind + ' ' + ds.length + '안 생성 ' + batch
       + (ds[0] && ds[0].why ? ' · ' + ds[0].why : ''));
  Logger.log('%s %s안 생성 (%s)%s', kind, ds.length, batch,
    ds[0] && ds[0].why ? '  훅 근거: ' + ds[0].why : '');
}

function buildDraft_(kind, variantIdx, opt) {
  opt = opt || {};
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var conf = readConf_(ss);
  var rows = readNow_(ss);
  if (!conf || !rows.length) return null;

  if (kind === 'DP')  return buildDp_(rows, conf, variantIdx);
  if (kind === '변동') return buildChange_(ss, rows, conf, variantIdx, opt);
  if (kind === '플래그십' && launchActive_()) {
    var ld = buildLaunch_(rows, conf);
    if (ld) return ld;
    dgLog_('WARN', '신규폰 데이터 없음 → 일반 플래그십으로 대체');
  }
  return buildDaily_(rows, conf, variantIdx, kind);   // '플래그십' | '가성비'
}

/** 종합 — 1/2 카테고리 1위 3대, 2/2 통신사별 대표요금제 순위 */
function buildDaily_(rows, conf, variantIdx, scope) {
  var flagOnly = (scope === '플래그십');
  var floor = DG_FLOOR[scope];
  var pool = rows.filter(function (r) {
    if (r.sub !== '번호이동' || r.fund !== '공시지원금' || isDp_(r.model)) return false;
    if (floor != null && r.price > floor) return false;   // 하한선 미달은 아예 뺀다
    return flagOnly ? isFlagship_(r) : !isFlagship_(r);   // 가성비 글은 플래그십을 뺀다
  });
  if (pool.length < DG_MIN_ITEMS) return null;            // 조건 나쁜 날은 안 올린다

  // ── 1/2 : 카테고리별 할인율 1위. 요금제 무관(조건을 안 쓰므로 섞여도 된다).
  var picks;
  if (flagOnly) {
    // 플래그십은 대표 요금제로 조건이 고정돼 있어 총비용 비교가 유효하다.
    // 그래서 기종마다 **총비용이 가장 싼 통신사**를 고른다.
    //
    // 실구매가만 보면 틀린다 — 2026-09-08 실측:
    //   갤럭시 S26 256G  LG 실구매 -106,000 → 총비용 1,523,965
    //                    SKT 실구매  -6,000 → 총비용 1,440,439  ← 8.3만원 싸다
    // 기기값 1등을 그대로 내보내면, 우리가 유일하게 하고 있다던
    // "요금제까지 계산한 순위"를 스스로 어기는 셈이 된다.
    var byModel = {};
    pool.forEach(function (r) {
      var k = r.model;
      var prev = byModel[k];
      if (!prev || tco_(r.price, conf[r.carrier]) < tco_(prev.price, conf[prev.carrier])) {
        byModel[k] = r;
      }
    });
    picks = Object.keys(byModel).map(function (k) { return byModel[k]; })
      .sort(function (a, b) { return a.price - b.price; })   // 표시 금액이 큰 순
      .slice(0, 3).map(function (r) { return ['플래그십', r]; });
  } else {
    picks = [
      ['저가',   best_(pool, function (r) { return r.listPrice < DG.LOWCOST_MAX; })],
      ['갤럭시', best_(pool, function (r) { return isSamsung_(r) && r.listPrice >= DG.LOWCOST_MAX; })],
      ['애플',   best_(pool, function (r) { return isApple_(r); })]
    ].filter(function (p) { return p[1]; });
  }
  if (picks.length < DG_MIN_ITEMS) return null;

  // ── 훅. 대표 기종은 3대 중 절대 페이백이 가장 큰 것.
  //    오늘 그 기종이 실제로 떨어졌으면 사건 훅(DROP/PB), 아니면 랭킹 훅.
  var lead = picks.map(function (p) { return p[1]; })
                  .sort(function (a, b) { return a.price - b.price; })[0];
  var diff = todayDiff_(lead.key);
  var event = flagOnly ? 'RANK_FLAG' : 'RANK';
  if (diff) {
    if (diff.before >= 0 && lead.price < 0) event = 'PB';
    else if (diff.delta <= -DG_DROP_MIN) event = 'DROP';
  }
  var hook = (DG_VARIANTS === 1) ? pickHookScored_(event, lead, diff)
                                 : pickHook_(event, lead, diff, variantIdx);

  // 카테고리 라벨은 붙이지 않는다. 훅 한 줄 + 가격만.
  // 훅에 대표 기종의 금액이 이미 들어갔으면(NUM) 그 줄은 목록에서 뺀다. 같은 말 두 번 안 한다.
  var ordered = [lead].concat(picks.map(function (p) { return p[1]; })
                                   .filter(function (r) { return r !== lead; }));
  if (hookHasPrice_(hook.text, lead)) ordered = ordered.slice(1);

  // 줄마다 통신사를 붙인다. 같은 A17이 KT 10만 / SKT 25만이라
  // 통신사 없이 나열하면 1/2만 보고 오신 손님과 값이 안 맞는다.
  // 날짜도 넣는다 — 시세는 2시간마다 바뀌는데 글은 계속 남는다.
  var post1 = hook.text + '\n\n'
    + ordered.map(function (r) {
        return r.carrier + ' ' + name_(r) + ' → ' + priceText_(r.price);
      }).join('\n')
    + '\n\n' + today_() + ' 번호이동 기준';

  // ── 2/2
  // 플래그십: 대표 요금제 하나로 고정하고 조건을 아래 한 줄로 정리한다.
  // 가성비 : 저가 기종은 대표 요금제(고가)에 거의 없다. 요금제를 고정하면 목록이 비어버린다.
  //          그래서 기종별 최저가를 쓰되 줄마다 요금제를 병기하고, 조건은 링크로 넘긴다.
  //          (요금제가 섞인 채로 조건 한 줄을 붙이면 지원금 오인 유도가 된다)
  var blocks = [], listed = [];
  ['KT', 'SKT', 'LG'].forEach(function (c) {
    var cf = conf[c];
    if (!cf) return;
    var mine = pool.filter(function (r) {
      return r.carrier === c && (flagOnly ? samePlan_(r.plan, cf.planName) : true);
    }).sort(function (a, b) { return rate_(b) - rate_(a); });

    // 가성비는 같은 기종이 요금제별로 여러 줄 나오므로 기종당 하나만
    if (!flagOnly) {
      var seenM = {};
      mine = mine.filter(function (r) {
        if (seenM[r.model]) return false;
        seenM[r.model] = true; return true;
      });
    }

    var over = mine.filter(function (r) { return rate_(r) >= DG.CUT_RATE; })
                   .slice(0, DG.MAX_PER_CARRIER);
    if (!over.length) {
      if (DG.SKIP_BELOW_CUT) return;          // 조건 나쁜 통신사는 아예 뺀다
      over = mine.slice(0, 2);
    }
    listed = listed.concat(over.map(function (r) { return { r: r, c: c }; }));

    var header = flagOnly ? '[' + c + ' · ' + dgWon_(cf.fee) + ' 요금제]' : '[' + c + ']';
    blocks.push(header + '\n' + over.map(function (r) {
      return name_(r) + ' → ' + priceText_(r.price)
           + (flagOnly ? '' : ' (' + shortPlan_(r.plan) + ')');
    }).join('\n'));
  });
  if (!blocks.length) return null;

  var tcoLine = '';
  if (DG.SHOW_TCO_LINE && listed.length > 1) {
    var byPrice = listed.slice().sort(function (a, b) { return a.r.price - b.r.price; })[0];
    var byTotal = listed.slice().sort(function (a, b) {
      return tco_(a.r.price, conf[a.c]) - tco_(b.r.price, conf[b.c]); })[0];
    if (byPrice.r.key !== byTotal.r.key) {
      tcoLine = '\n※ 기기값만 보면 ' + byPrice.c + ' ' + name_(byPrice.r) + '이지만, '
              + '요금제·부가까지 ' + DG.MONTHS + '개월로 계산하면 '
              + byTotal.c + ' ' + name_(byTotal.r) + '가 '
              + dgWon_(tco_(byPrice.r.price, conf[byPrice.c]) - tco_(byTotal.r.price, conf[byTotal.c]))
              + ' 저렴합니다.\n';
    }
  }

  var post2 = fit_(function (bs) {
    return (flagOnly ? '통신사별 순위입니다. (대표 요금제 기준)' : '통신사별 순위입니다.') + '\n\n'
      + bs.join('\n\n') + '\n\n'
      + (flagOnly
          ? '185일 유지 후 하한 요금제로 변경 가능\n부가서비스 유지 · 미가입 시 추가금\n'
          : '요금제마다 유지 조건이 다릅니다. 링크에서 확인해주세요.\n')
      + '폰 반납 없음 · 카드 조건 없음\n'
      + tcoLine
      + '\n전체 조건·기종 → citymall.co.kr/order-intake/pb';
  }, blocks);

  var tagEvent = (event === 'RANK_FLAG') ? 'RANK' : event;
  var packed = pack_(scope || '종합', '[' + tagEvent + '/' + hook.expr + ']',
               picks.map(function (p) { return p[1].carrier; }).join('+'),
               post1, post2,
               '대표=' + lead.model + ';금액=' + Math.abs(lead.price)
               + ';카테고리=' + picks.map(function (p) { return p[0]; }).join('/')
               + ';통신사=' + blocks.length + ';체인=2;이미지=N'
               + vtag_([lead].concat(picks.map(function (p) { return p[1]; }))));
  packed.why = hook.why || '';
  packed.tid = hook.tid || '';
  return packed;
}

/**
 * 변동 — 어제 실제로 내려간 가격. 출근길 8시 슬롯의 기본 소재.
 *
 * 왜 이 컨셉을 만들었나.
 *  ① 슬롯이 4개인데 컨셉이 3개면 라틴 방격이 안 서고 8시·21시가 매일 같은 컨셉이 된다.
 *  ② 시세_변동 탭을 2주 넘게 쌓기만 하고 한 번도 쓰지 않고 있었다.
 *  ③ 2026-09-08 14시에 KT 갤럭시Z플립7이 355,000 → 205,000 으로 15만원 내렸는데,
 *     플립7은 플래그십 정규식에 안 걸리고 가성비 하한선(-50,000)도 못 넘어
 *     **그 좋은 소재가 그냥 지나갔다.** 이 컨셉이 그걸 줍는다.
 *
 * 다른 컨셉과 형식이 달라(순위표가 아니라 변화표) 반복 피로도 덜 쌓인다.
 * 변동이 없는 날은 안 올린다 — 그게 정상이다.
 */
function buildChange_(ss, rows, conf, variantIdx, opt) {
  opt = opt || {};
  var picks = chgPicks_(ss, rows, opt.exclude);
  if (!picks || picks.length < DG_CHG.MIN_ITEMS) return null;
  opt.variantIdx = variantIdx;
  return buildChangeFrom_(picks, opt);
}

/**
 * 하락 소재를 뽑는다. buildChange_ 와 '2회차 가능한가' 판정이 **같은 코드**를 써야
 * "소재 있다고 했는데 글이 안 만들어지는" 어긋남이 생기지 않는다.
 * exclude: 제외할 기종명 배열(1회차에 이미 쓴 기종).
 */
function chgPicks_(ss, rows, exclude) {
  var ex = {};
  (exclude || []).forEach(function (m) { if (m) ex[String(m).trim()] = 1; });
  var sh = ss.getSheetByName(DG.SHEET_DIFF);
  if (!sh || sh.getLastRow() < 2) return [];

  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 12).getValues();
  var now  = Date.now();
  var base = now - DG_CHG.LOOKBACK_H * 3600000;

  // '지금 가격'은 시세_현재가 기준이다. 사이트에 안 보이는 조합은 여기 없으므로 자동 제외.
  var cur = {};
  rows.forEach(function (r) {
    if (r.sub === '번호이동' && r.fund === '공시지원금') cur[r.key] = r;
  });

  // 키별 변동 이력
  var hist = {};
  v.forEach(function (r) {
    var t = r[0] instanceof Date ? r[0].getTime() : Date.parse(String(r[0]).replace(' ', 'T') + '+09:00');
    if (!t) return;
    if (r[5] !== '번호이동' || r[6] !== '공시지원금') return;
    var k = String(r[11]);
    (hist[k] = hist[k] || []).push({ t: t, before: Number(r[7]), after: Number(r[8]) });
  });

  /*
   * 하락 = "4일 전 그 시점의 가격" − "지금 가격".  직전 기록 대비가 아니다.
   *
   * 2026-09-18 실제 사고: 09:29에 LG 플래그십 전 기종이 +940,000 튀었다가(지원금 입력 중
   * 일시 상태로 보임) 10:29에 원래 값으로 돌아왔다. 직전 틱 대비로 보면 10:29가
   * '94만원 하락'이 되고, 그게 9/18·9/19 두 번 "갤럭시 S26 940,000원 내려갔어요"로 나갔다.
   * 4일 전과 비교하면 그 기종은 오히려 7만원 올라 있었다. 거짓 주장이었다.
   *
   * 기준 시점 비교는 튀었다 돌아온 값을 저절로 걸러낸다. 또 지금 가격이 HOLD_H 시간
   * 이상 유지된 것만 쓴다 — 반대로 잠깐 튀어 내려간 값이 소재가 되는 것도 막는다.
   */
  var cand = [];
  Object.keys(hist).forEach(function (k) {
    var nowR = cur[k];
    if (!nowR) return;
    var h = hist[k].sort(function (a, b) { return a.t - b.t; });
    if (!h.some(function (x) { return x.t >= base; })) return;     // 창 안에 움직임이 있어야 '최근'

    var basePrice = null;
    for (var i = 0; i < h.length; i++) {
      if (h[i].t <= base) basePrice = h[i].after;
      else { if (basePrice === null) basePrice = h[i].before; break; }
    }
    if (basePrice === null || isNaN(basePrice)) return;

    var delta = nowR.price - basePrice;
    if (!(delta <= -DG_CHG.DROP_MIN)) return;
    if (now - h[h.length - 1].t < DG_CHG.HOLD_H * 3600000) return;   // 방금 바뀐 값은 보류
    if (-delta > DG_CHG.MAX_DROP) {                                     // 비정상적으로 큰 폭
      dgLog_('WARN', '변동 소재 보류(폭 과대) ' + k + ' ' + basePrice + '→' + nowR.price);
      return;
    }
    cand.push({ carrier: nowR.carrier, model: String(nowR.model), size: nowR.size || '',
                plan: String(nowR.plan), before: basePrice, price: nowR.price,
                delta: delta, key: k });
  });

  // 같은 기종의 용량 변형이 여러 개면 낙폭이 큰 하나만
  var byModel = {};
  cand.forEach(function (r) {
    if (!byModel[r.model] || r.delta < byModel[r.model].delta) byModel[r.model] = r;
  });

  // 글에 넣을 개수(MAX_ITEMS)로 자르지 않는다 — 여기서 자르면 '소재가 몇 종 있나'를
  // 세는 쪽(2회차 판정)이 항상 상한에 걸려 판정이 불가능해진다. 자르는 건 글 만들 때 한다.
  return Object.keys(byModel).filter(function (m) { return !ex[m.trim()]; })
    .map(function (m) { return byModel[m]; })
    .sort(function (a, b) { return a.delta - b.delta; });     // 많이 내린 순
}

/** 뽑힌 소재로 글을 만든다 */
function buildChangeFrom_(picks, opt) {
  opt = opt || {};
  picks = picks.slice(0, DG_CHG.MAX_ITEMS);
  var lead = picks[0];
  var hook = (DG_VARIANTS === 1)
    ? pickHookScored_('CHANGE', lead, { delta: lead.delta, before: lead.before })
    : pickHook_('CHANGE', lead, { delta: lead.delta, before: lead.before }, opt.variantIdx);

  var post1 = hook.text + '\n\n'
    + picks.map(function (r) {
        return r.carrier + ' ' + name_(r) + ' → ' + priceText_(r.before)
             + '에서 ' + priceText_(r.price);
      }).join('\n')
    + '\n\n' + today_() + ' 번호이동 기준 · '
    + Math.round(DG_CHG.LOOKBACK_H / 24) + '일 전 대비';

  var post2 = fit_(function (ls) {
    return '최근 조건이 바뀐 기종입니다.\n\n'
      + ls.join('\n') + '\n\n'
      + '요금제마다 유지 조건이 다릅니다. 링크에서 확인해주세요.\n'
      + '폰 반납 없음 · 카드 조건 없음\n'
      + '\n가격은 통신사 정책에 따라 수시로 바뀝니다.\n'
      + '전체 조건·기종 → citymall.co.kr/order-intake/pb';
  }, picks.map(function (r) {
    return r.carrier + ' ' + name_(r) + ' → ' + priceText_(r.price)
         + ' (' + shortPlan_(r.plan) + ', ' + dgWon_(Math.abs(r.delta)) + ' 하락)';
  }));

  var packedChg = pack_('변동', '[DROP/' + hook.expr + ']',
    picks.map(function (r) { return r.carrier; }).join('+'), post1, post2,
    '대표=' + lead.model + ';변동=' + Math.abs(lead.delta) + ';건수=' + picks.length
    + ';기종목록=' + picks.map(function (r) { return r.model; }).join('|')
    + (opt.second ? ';회차=2' : '')
    + ';체인=2;이미지=N' + vtag_(picks));
  packedChg.why = hook.why || '';
  packedChg.tid = hook.tid || '';
  return packedChg;
}

/**
 * 신규폰 — 출시 기간 동안 플래그십 차례를 대신한다.
 *  1/2 : 대표 기종(출고가가 가장 낮은 모델) 최소 용량을 3사 가격으로, 상위 모델은 최저 통신사 1줄
 *  2/2 : 3사 2년 총비용 + 같은 통신사·같은 요금제의 전작 가격 차이
 * 모든 가격은 통신사별 **대표 요금제** 줄만 쓴다. 요금제를 섞으면 3사 비교가 성립하지 않는다.
 * 하한선(DG_FLOOR)은 적용하지 않는다 — 신규폰은 원래 페이백이 없고, 이 글의 목적은 '얼마인가'다.
 */
function buildLaunch_(rows, conf) {
  function sizeN(s) { return String(s || '').replace(/\s+/g, '').replace(/GB$/i, 'G').toUpperCase(); }
  function sizeV(s) { var t = sizeN(s), n = parseFloat(t); return /T/.test(t) ? n * 1024 : n; }
  var rep = rows.filter(function (r) {
    return r.sub === '번호이동' && r.fund === '공시지원금' && !isDp_(r.model)
        && conf[r.carrier] && samePlan_(r.plan, conf[r.carrier].planName);
  });
  var mine = rep.filter(function (r) { return DG_LAUNCH.RE.test(String(r.model)); });
  if (!mine.length) return null;

  // 모델별 최소 용량만
  var minSize = {};
  mine.forEach(function (r) {
    if (minSize[r.model] == null || sizeV(r.size) < minSize[r.model]) minSize[r.model] = sizeV(r.size);
  });
  mine = mine.filter(function (r) { return sizeV(r.size) === minSize[r.model]; });

  var models = Object.keys(minSize).sort(function (a, b) {
    var la = mine.filter(function (r) { return r.model === a; })[0].listPrice;
    var lb = mine.filter(function (r) { return r.model === b; })[0].listPrice;
    return la - lb;
  });
  var main = models[0];
  var mainRows = mine.filter(function (r) { return r.model === main; })
                     .sort(function (a, b) { return a.price - b.price; });
  var others = models.slice(1).map(function (m) {
    return mine.filter(function (r) { return r.model === m; })
               .sort(function (a, b) { return a.price - b.price; })[0];
  });
  var lead = mainRows[0];

  var hookLead = { model: lead.model, size: '', price: lead.price, key: lead.key };
  var off = lead.listPrice - lead.price;
  var hook = pickHookScored_('LAUNCH', hookLead, { delta: -off, before: lead.listPrice });

  var post1 = hook.text + '\n\n'
    + mainRows.concat(others).map(function (r) {
        return r.carrier + ' ' + name_(r) + ' → ' + priceText_(r.price);
      }).join('\n')
    + '\n\n출고가 ' + dgWon_(lead.listPrice) + ' (' + name_(lead) + ')'
    + '\n' + today_() + ' 번호이동 · 대표 요금제 기준';

  // 2/2 — 총비용 순
  var byTco = mainRows.slice().sort(function (a, b) {
    return tco_(a.price, conf[a.carrier]) - tco_(b.price, conf[b.carrier]);
  });
  var tcoLines = byTco.map(function (r) {
    return r.carrier + ' ' + shortPlan_(r.plan) + ' → ' + dgWon_(tco_(r.price, conf[r.carrier]));
  });
  var gap = byTco.length > 1
    ? tco_(byTco[1].price, conf[byTco[1].carrier]) - tco_(byTco[0].price, conf[byTco[0].carrier]) : 0;

  // 전작 — 총비용 1위 통신사, 같은 요금제, 같은 용량
  var prevLine = '';
  var best = byTco[0];
  var prevModel = String(best.model).replace(DG_LAUNCH.PREV[0], DG_LAUNCH.PREV[1]);
  var prev = rep.filter(function (r) {
    return r.carrier === best.carrier && r.model === prevModel && sizeN(r.size) === sizeN(best.size);
  })[0];
  if (prev && prev.price < best.price) {
    prevLine = '\n전작과 비교하면 (' + best.carrier + ' 같은 요금제)\n'
      + name_(best) + ' → ' + priceText_(best.price) + '\n'
      + prev.model + ' ' + best.size + ' → ' + priceText_(prev.price) + '\n'
      + '차이 ' + dgWon_(best.price - prev.price) + '\n';
  }

  var post2 = '2년 총비용으로 보면 (' + name_(lead) + ')\n'
    + '요금제 ' + DG.MONTHS + '개월 · 부가 포함\n\n'
    + tcoLines.join('\n') + '\n'
    + (gap > 0 ? '→ ' + byTco[0].carrier + '가 ' + dgWon_(gap) + ' 저렴\n' : '')
    + prevLine
    + '\n185일 유지 후 하한 요금제로 변경 가능\n부가서비스 유지 · 미가입 시 추가금\n'
    + '폰 반납 없음 · 카드 조건 없음\n'
    + '\n전체 조건·기종 → citymall.co.kr/order-intake/pb';
  if (post2.length > DG.MAX_LEN - DG_FOOTER.length) post2 = post2.replace(prevLine, '');

  var packed = pack_('신규폰', '[NEW/' + hook.expr + ']',
    mainRows.map(function (r) { return r.carrier; }).join('+'), post1, post2,
    '대표=' + lead.model + ';금액=' + lead.price + ';사건=신규폰;체인=2;이미지=N'
    + vtag_(mainRows.concat(others).concat(prev ? [prev] : [])));
  packed.why = hook.why || '';
  packed.tid = hook.tid || '';
  return packed;
}

/** 신규폰 글 미리보기 — 올리지 않고 로그에만 찍는다 */
function previewLaunch() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var d = buildLaunch_(readNow_(ss), readConf_(ss));
  if (!d) { Logger.log('신규폰 데이터 없음'); return; }
  Logger.log('기간 %s ~ %s · 지금 %s', DG_LAUNCH.FROM, DG_LAUNCH.UNTIL, launchActive_() ? '적용 중' : '기간 밖');
  Logger.log('훅 %s · %s\n━━ 1/2 (%s자)\n%s\n━━ 2/2 (%s자)\n%s', d.tag, d.why, d.len1, d.post1, d.len2, d.post2);
}

/** DP — KT 개봉(전시)폰 전용. 초이스90 조건. */
function buildDp_(rows, conf, variantIdx) {
  var dpFloor = DG_FLOOR['DP'];
  var dp = rows.filter(function (r) {
    if (r.carrier !== 'KT' || !isDp_(r.model)) return false;
    if (r.sub !== '번호이동' || r.fund !== '공시지원금') return false;
    return dpFloor == null || r.price <= dpFloor;      // 조건 나쁜 전시폰은 뺀다
  }).sort(function (a, b) { return a.price - b.price; });
  if (dp.length < DG_MIN_ITEMS) return null;

  var head = dp[0];
  // 기기변경도 페이백이 나오면 그 자체가 소재다 (드문 일)
  var dev = rows.filter(function (r) {
    return r.carrier === 'KT' && r.model === head.model && r.sub === '기기변경' && r.fund === '공시지원금';
  })[0];

  var hook = (DG_VARIANTS === 1) ? pickHookScored_('SCARCE', head, null)
                                 : pickHook_('SCARCE', head, null, variantIdx);
  var top = dp.slice(0, 3);
  if (hookHasPrice_(hook.text, head)) top = dp.slice(1, 4);   // 훅에 이미 금액이 있으면 다음 것부터
  var post1 = hook.text + '\n\n'
    + top.map(function (r) { return name_(r) + ' → ' + priceText_(r.price); }).join('\n')
    + '\n\n개봉만 한 새 제품입니다\n' + today_() + ' KT 번호이동 기준';

  var lines = dp.slice(0, 6).map(function (r) { return name_(r) + ' → ' + priceText_(r.price); });
  var devLine = (dev && dev.price < 0)
    ? '\n기기변경도 ' + name_(dev) + ' → ' + priceText_(dev.price) + ' 가능합니다.\n' : '';

  var post2 = fit_(function (ls) {
    return 'KT 전시폰(DP) 오늘 조건입니다.\n\n'
      + ls.join('\n') + '\n\n'
      + '90,000원 요금제 185일 유지 후\n47,000원 이상 요금제로 변경 가능합니다.\n\n'
      + '부가서비스 유지 · 미가입 시 추가금\n'
      + '폰 반납 없음 · 카드 조건 없음\n'
      + devLine
      + '\n전시폰은 개봉만 하고 사용하지 않은 제품입니다.\n재고는 상담 시 확인해 드립니다.\n'
      + '\n전체 조건 → citymall.co.kr/order-intake/pb';
  }, lines);

  var packedDp = pack_('DP', '[SCARCE/' + hook.expr + ']', 'KT', post1, post2,
    '금액=' + Math.abs(head.price) + ';통신사=KT;기종=' + head.model + ';체인=2;이미지=N'
    + vtag_([head].concat(top)));
  packedDp.why = hook.why || '';
  packedDp.tid = hook.tid || '';
  return packedDp;
}

// ─────────────────────────────────────────────
// 보조
// ─────────────────────────────────────────────

/**
 * 발행 직전 재검증용 태그.
 * 초안에 실린 가격을 시세_현재의 key 와 함께 박아둔다.
 * 몇 시간 뒤에 승인이 들어와도, publish 가 이걸로 "그 가격이 아직 유효한가"를 확인한다.
 * key 안의 '|' 는 셀에서 읽기 나쁘니 '~' 로 바꿔 저장한다.
 */
function vtag_(rows) {
  var seen = {};
  var parts = rows.filter(function (r) { return r && r.key; }).filter(function (r) {
    if (seen[r.key]) return false; seen[r.key] = true; return true;
  }).map(function (r) {
    return String(r.key).replace(/\|/g, '~') + '@' + Math.round(r.price);
  });
  return parts.length ? ';검증=' + parts.join(',') : '';
}

function pack_(kind, tag, carrier, p1, p2, meta) {
  if (p2 && DG_FOOTER && p2.indexOf(DG_FOOTER.trim()) < 0) p2 = p2 + DG_FOOTER;
  return {
    stamp: Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm'),
    kind: kind, tag: tag, carrier: carrier,
    post1: p1, post2: p2, len1: p1.length, len2: p2.length, meta: meta, why: ''
  };
}

/** 500자를 넘으면 목록을 뒤에서부터 줄인다 */
function fit_(render, items) {
  var out = render(items);
  while (out.length > DG.MAX_LEN - DG_FOOTER.length && items.length > 1) {
    items = items.slice(0, items.length - 1);
    out = render(items);
  }
  return out;
}

/**
 * 사건에 맞는 훅 하나를 고른다.
 * 최근 시세_초안에 쓴 문구는 피한다 — 표현축을 돌려야 성과 비교가 된다.
 */
/**
 * 훅을 훅_성과 점수로 고른다. auto_select 의 UCB 점수를 그대로 쓴다 —
 * 적게 써본 표현에 가산점이 붙어 탐색이 저절로 일어나고, 표본이 쌓이면 수렴한다.
 * auto_select 가 없거나 데이터가 없으면 무작위로 떨어진다(=올바른 출발점).
 */
/**
 * 훅을 '문구 틀(템플릿)' 단위로 고른다.
 *
 * ── 왜 바꿨나 (2026-09-21 점검) ──
 * 예전엔 표현축(TEASE/NUM/RANK…)으로 점수를 합쳐서 매겼다. 그게 컨셉 사이에 점수를 섞었다.
 *   · 변동 컨셉: "최근 가격 내려간 폰 정리"(RANK) 평균 961 → 전시폰의 NUM 성공(448·357) 때문에
 *     NUM 이 더 높아 보여 "[기종] [변동] 내려갔어요"로 갈아탔고, 평균 109 로 떨어졌다.
 *   · 플래그십: "신형 중에 오늘 이게 제일 좋아요"(TEASE) 1303·1162 → 가성비의 TEASE 실패(42·57)와
 *     섞여 TEASE 점수가 깎였고, "오늘 최신폰 TOP 3"만 4번 연속 나갔다. 중앙 139 → 66.
 * 같은 기간 표현이 안 바뀐 가성비·DP 는 오히려 올랐다 — 계정 전체 피로가 아니라 이 섞임이 원인이다.
 *
 * ── 지금 규칙 ──
 *  ① 점수는 템플릿별(컨셉 안의 문구 틀 하나하나)로 매긴다.
 *  ② 표본이 적은 틀은 같은 컨셉 평균 쪽으로 당겨서 본다(수축). 무한대 가산점은 없다.
 *  ③ 이미 올렸지만 아직 D+5 성적이 안 들어온 사용분도 '써본 횟수'로 센다.
 *     예전엔 이게 빠져서 한 문구가 5일 내리 나갔다("전시폰이 왜 이렇게 싼지 아세요?" 5연속).
 *  ④ 같은 틀은 NO_REPEAT_H 안에 다시 안 쓴다. 대안이 없을 때만 가장 오래전에 쓴 것.
 */
var DG_HK = { SHRINK: 2, C: 0.8, NO_REPEAT_H: 44, PENDING_DAYS: 6 };

function pickHookScored_(event, lead, diff) {
  var pool = DG_HOOKS[event] || DG_HOOKS.RANK;
  var poolKey = DG_HOOKS[event] ? event : 'RANK';

  var sc = null;
  try { if (typeof hookTemplateScores_ === 'function') sc = hookTemplateScores_(); } catch (e) { /* noop */ }
  // 요인 모형이 서 있으면 그걸 먼저 쓴다 — 슬롯·주제 효과를 뺀 순수 훅 효과다.
  // 2026-09-23: 풀 평균만 보면 "전시폰이 잘 나오는 것"이 그 풀의 훅 점수로 둔갑한다.
  var fm = null;
  try { if (typeof hookFactorScores_ === 'function') fm = hookFactorScores_(); } catch (e) { /* noop */ }
  var used = recentTemplateUse_();
  var now = Date.now();
  var N = (sc ? sc.total : 0) + Object.keys(used).reduce(function (a, k) { return a + used[k].pend; }, 0);
  var prior = (sc && sc.byPool[poolKey] && sc.byPool[poolKey].n) ? sc.byPool[poolKey].mean : 0;

  var cands = pool.map(function (h, i) {
    var tid = poolKey + '#' + i;
    if (DG_HOOK_OFF.indexOf(tid) >= 0) return null;        // 꺼둔 틀
    var st = sc && sc.byT[tid];
    var n = st ? st.n : 0, sum = st ? st.sum : 0;
    var mean = (sum + DG_HK.SHRINK * prior) / (n + DG_HK.SHRINK);
    // 모형 추정치는 이미 축소(릿지)가 들어가 있으므로 그대로 쓴다.
    // 풀 기준 틀은 계수가 0 — 같은 풀 안에서 0을 기준으로 비교하는 게 맞다.
    var fmT = fm && fm.byT ? fm.byT[tid] : null;
    if (fm) mean = fmT ? fmT.est : 0;
    var u = used[tid] || { pend: 0, last: 0 };
    var bonus = DG_HK.C * Math.sqrt(2 * Math.log(N + 2) / (n + u.pend + 1));
    return { i: i, tid: tid, expr: h[0], n: n, pend: u.pend, last: u.last, mean: mean,
             score: mean + bonus, recent: u.last && (now - u.last) < DG_HK.NO_REPEAT_H * 3600000,
             tie: Math.random() };
  }).filter(function (c) { return c; });
  if (!cands.length) {                                      // 풀 전체가 꺼져 있으면 안전하게 되돌린다
    dgLog_('WARN', '훅 풀 ' + poolKey + ' 전체가 꺼져 있음 — DG_HOOK_OFF 확인');
    cands = pool.map(function (h, i) {
      return { i: i, tid: poolKey + '#' + i, expr: h[0], n: 0, pend: 0, last: 0,
               mean: 0, score: 0, recent: false, tie: Math.random() };
    });
  }

  var ok = cands.filter(function (c) { return !c.recent; });
  var best;
  if (ok.length) {
    best = ok.sort(function (a, b) { return (b.score - a.score) || (b.tie - a.tie); })[0];
  } else {
    best = cands.sort(function (a, b) { return a.last - b.last; })[0];   // 다 최근이면 가장 오래전 것
  }

  var picked = pickHook_(event, lead, diff, best.i);
  picked.tid = best.tid;
  picked.why = (fm ? '모형 ' : '') + best.tid + ' n=' + best.n + (best.pend ? '(+' + best.pend + '대기)' : '')
             + ' 기대 ' + (Math.round(best.mean * 100) / 100);
  return picked;
}

/** 모든 훅 틀 목록. 식별자는 풀이름#순번 — 예: CHANGE#3 */
function hookTemplates_() {
  var out = [];
  Object.keys(DG_HOOKS).forEach(function (pk) {
    DG_HOOKS[pk].forEach(function (h, i) {
      var esc = h[1].replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                    .replace(/\\\[기종\\\]|\\\[금액\\\]|\\\[변동\\\]/g, '.+');
      out.push({ tid: pk + '#' + i, pool: pk, expr: h[0], text: h[1],
                 literal: !/\[기종\]|\[금액\]|\[변동\]/.test(h[1]),
                 re: new RegExp('^' + esc + '$') });
    });
  });
  return out;
}

/** 발행된 첫 줄에서 어느 틀로 만든 글인지 되찾는다. 고정 문구를 먼저 본다. */
function templateOf_(line) {
  var t = String(line || '').trim();
  if (!t) return '';
  var ts = hookTemplates_();
  for (var i = 0; i < ts.length; i++) if (ts[i].literal && ts[i].text === t) return ts[i].tid;
  var hit = ts.filter(function (x) { return !x.literal && x.re.test(t); })
              .sort(function (a, b) { return b.text.length - a.text.length; })[0];
  return hit ? hit.tid : '';
}

/** 최근 PENDING_DAYS 안에 발행된 틀별 사용 횟수와 마지막 사용 시각 */
function recentTemplateUse_() {
  var out = {};
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(DG.SHEET_DRAFT);
    if (!sh || sh.getLastRow() < 2) return out;
    var n = Math.min(200, sh.getLastRow() - 1);
    var v = sh.getRange(sh.getLastRow() - n + 1, 1, n, 10).getValues();
    var cutoff = Date.now() - DG_HK.PENDING_DAYS * 86400000;
    v.forEach(function (r) {
      var st = String(r[9]).trim();
      if (st !== '발행완료' && st !== '승인' && st !== '발행중') return;
      var t = r[0] instanceof Date ? r[0].getTime()
            : Date.parse(String(r[0]).replace(' ', 'T') + ':00+09:00');
      if (!t || t < cutoff) return;
      var m = String(r[8]).match(/훅=([A-Z_]+#\d+)/);
      var tid = m ? m[1] : templateOf_(String(r[6]).split('\n')[0]);
      if (!tid) return;
      var u = out[tid] || (out[tid] = { pend: 0, last: 0 });
      u.pend++; if (t > u.last) u.last = t;
    });
  } catch (e) { /* noop */ }
  return out;
}

function pickHook_(event, lead, diff, idx) {
  var pool = DG_HOOKS[event] || DG_HOOKS.RANK;
  var pk = DG_HOOKS[event] ? event : 'RANK';
  var use = pool;
  // 꺼둔 틀은 무작위 선택에서도 뺀다. 인덱스를 직접 받은 경우(점수 기반 선택)는 이미 걸러져 있다.
  if (idx == null) {
    var onIdx = [];
    pool.forEach(function (h, i) { if (DG_HOOK_OFF.indexOf(pk + '#' + i) < 0) onIdx.push(h); });
    if (onIdx.length) pool = onIdx;
  }
  if (idx == null) {
    // 인덱스가 없으면 최근에 안 쓴 것 중에서 뽑는다
    var recent = recentHooks_();
    var fresh = pool.filter(function (h) { return recent.indexOf(h[1]) < 0; });
    use = fresh.length ? fresh : pool;
  }
  var pick = (idx == null)
    ? use[Math.floor(Math.random() * use.length)]
    : use[idx % use.length];

  var text = pick[1]
    .replace(/\[기종\]/g, lead ? name_(lead) : '')
    .replace(/\[금액\]/g, lead ? priceText_(lead.price) : '')
    .replace(/\[변동\]/g, diff ? dgWon_(Math.abs(diff.delta)) : '');
  return { text: text, expr: pick[0], raw: pick[1] };
}

/** 훅 문구에 이 상품의 금액이 이미 들어가 있는가 */
function hookHasPrice_(text, r) {
  if (!r) return false;
  return String(text).indexOf(dgWon_(Math.abs(r.price))) >= 0;
}

/** 최근 20건의 훅 원본 문구 (치환 전 템플릿으로 비교하려고 태그+첫줄을 본다) */
function recentHooks_() {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(DG.SHEET_DRAFT);
    if (!sh || sh.getLastRow() < 2) return [];
    var n = Math.min(20, sh.getLastRow() - 1);
    return sh.getRange(sh.getLastRow() - n + 1, DG.COL_POST1 || 5, n, 1).getValues()
             .map(function (r) { return String(r[0]).split('\n')[0]; });
  } catch (e) { return []; }
}

/** 오늘 시세_변동에서 이 키의 변동을 찾는다. 없으면 null. */
function todayDiff_(key) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('시세_변동');
    if (!sh || sh.getLastRow() < 2) return null;
    var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
    var v = sh.getRange(2, 1, sh.getLastRow() - 1, 12).getValues();
    for (var i = v.length - 1; i >= 0; i--) {
      if (v[i][11] === key && String(v[i][0]).indexOf(today) === 0) {
        return { before: v[i][7] === '' ? null : Number(v[i][7]),
                 price: Number(v[i][8]),
                 delta: v[i][9] === '' ? 0 : Number(v[i][9]) };
      }
    }
    return null;
  } catch (e) { return null; }
}

function best_(pool, pred) {
  var s = pool.filter(pred).sort(function (a, b) { return rate_(b) - rate_(a); });
  return s.length ? s[0] : null;
}

function rate_(r) {
  return r.listPrice ? (r.listPrice - r.price) / r.listPrice * 100 : 0;
}

function name_(r) { return r.model + (r.size ? ' ' + r.size : ''); }

/** 글에 박는 기준일. 시간이 지나 값이 달라져도 오해가 안 생기게. */
function today_() { return Utilities.formatDate(new Date(), 'Asia/Seoul', 'M/d'); }

function priceText_(p) {
  return p < 0 ? '0원 + ' + dgWon_(-p) + ' 페이백' : dgWon_(p);
}

function isDp_(m)      { return /개봉/.test(String(m)); }
// 제조사는 API 값(제조사 열)을 먼저 본다. 비어 있을 때만 기종명으로 추정한다.
// 기존 방식은 "애플이 아니면 삼성"이라, 삼성·애플이 아닌 기기가 갤럭시로 분류됐다.
function isApple_(r) {
  if (r.maker) return /apple|애플/i.test(r.maker);
  return /아이폰|iPhone/i.test(r.model);
}
function isSamsung_(r) {
  if (r.maker) return /samsung|삼성/i.test(r.maker);
  return /갤럭시|Galaxy/i.test(r.model);
}

/** 목록에 병기할 짧은 요금제명. '초이스110 (혜택 선택 가능)' → '초이스110' */
function shortPlan_(p) { return String(p || '').replace(/\(.*$/, '').trim(); }

/** 요금제명 비교 — 괄호 뒷부분과 공백 차이를 무시한다 */
function samePlan_(a, b) {
  function norm(s) { return String(s || '').replace(/\(.*$/, '').replace(/\s+/g, ''); }
  return norm(a) === norm(b);
}

function tco_(price, c) {
  if (!c) return Infinity;
  var M = 30.4375, keepM = c.keepDays / M;
  return Math.round(price + c.fee * keepM + c.lowFee * (DG.MONTHS - keepM) + c.addFee * (c.addDays / M));
}

function readConf_(ss) {
  var sh = ss.getSheetByName(DG.SHEET_CONF);
  if (!sh || sh.getLastRow() < 2) return null;
  var v = sh.getRange(2, 1, sh.getLastRow() - 1, 7).getValues(), out = {};
  v.forEach(function (r) {
    var c = String(r[0]).trim();
    if (!c || !Number(r[1])) return;
    out[c] = { fee: Number(r[1]), keepDays: Number(r[2]), lowFee: Number(r[3]),
               addFee: Number(r[4]), addDays: Number(r[5]),
               planName: String(r[6] || DG_REP_PLAN[c] || '') };
  });
  return Object.keys(out).length ? out : null;
}

function readNow_(ss) {
  var sh = ss.getSheetByName(DG.SHEET_NOW);
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 17).getValues()
    .filter(function (r) { return r[15]; })
    .map(function (r) {
      return { carrier: r[1], model: r[2], size: r[3], listPrice: Number(r[5]),
               plan: r[6], planFee: Number(r[7]), sub: r[8], fund: r[9],
               price: Number(r[13]), key: r[15], maker: String(r[16] || '') };
    });
}

function writeDrafts_(batch, ds) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(DG.SHEET_DRAFT);
  if (!sh) {
    sh = ss.insertSheet(DG.SHEET_DRAFT);
    sh.getRange(1, 1, 1, DG_HEAD.length).setValues([DG_HEAD]).setFontWeight('bold');
    sh.setFrozenRows(1);
    sh.setColumnWidth(7, 320); sh.setColumnWidth(8, 420);
  }
  var start = sh.getLastRow() + 1;
  var rows = ds.map(function (d, i) {
    return [d.stamp, batch, i + 1 + '안', d.kind, d.tag, d.carrier,
            d.post1, d.post2, d.meta,
            (DG_AUTO_APPROVE && DG_VARIANTS === 1) ? '승인' : '대기', ''];
  });
  sh.getRange(start, 1, rows.length, DG_HEAD.length).setValues(rows);
  sh.getRange(start, 10, rows.length, 1).setDataValidation(
    SpreadsheetApp.newDataValidation()
      .requireValueInList(
        ['대기', '승인', '보류', '미선택', '발행완료', '만료', '점검필요'], true).build());
}

function renderBatch_(batch, kind, ds) {
  if (DG_AUTO_APPROVE && DG_VARIANTS === 1) {
    var d = ds[0];
    return '🚀 ' + kind + ' 곧 발행됩니다  (' + batch + ')\n'
      + '훅 ' + d.tag + (d.why ? ' · ' + d.why : '') + '\n'
      + '멈추려면 시세_초안 상태를 「보류」로 바꾸세요. 5분 안에.\n'
      + '\n━━━ 1/2 (' + d.len1 + '자)\n' + d.post1
      + '\n\n━━━ 2/2 (' + d.len2 + '자)\n' + d.post2;
  }
  var out = '📝 ' + kind + ' 시안 ' + ds.length + '개  (' + batch + ')\n'
          + '아래 중 하나만 골라 시세_초안 상태를 「승인」으로 바꾸세요.\n';
  ds.forEach(function (d, i) {
    out += '\n━━━ ' + (i + 1) + '안  ' + d.tag + '  (' + d.len1 + '자)\n' + d.post1 + '\n';
  });
  out += '\n━━━ 공통 2/2  (' + ds[0].len2 + '자)\n' + ds[0].post2;
  return out;
}

function dgWon_(n) {
  var s = String(Math.abs(Math.round(Number(n) || 0))), o = '';
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 === 0) o += ',';
    o += s[i];
  }
  return (Number(n) < 0 ? '-' : '') + o + '원';
}

function dgLog_(result, message) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(DG.LOG_SHEET);
    if (sh) sh.appendRow([new Date(), 'generateDrafts', result, message]);
  } catch (e) { /* noop */ }
}

function dgAlert_(text) {
  if (threadsMuted_()) { threadsMuteLog_('generateDrafts', text); return; }   // alerts.js TELEGRAM_ALL_OFF 따름
  var p = PropertiesService.getScriptProperties();
  var token = p.getProperty(DG.PROP_TG_TOKEN), chat = p.getProperty(DG.PROP_TG_CHAT);
  if (token && chat) {
    try {
      var res = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
        method: 'post', muteHttpExceptions: true,
        payload: { chat_id: chat, text: text, disable_web_page_preview: 'true' }
      });
      if (res.getResponseCode() === 200) return;
      dgLog_('WARN', '텔레그램 실패 ' + res.getContentText().slice(0, 120));
    } catch (e) { dgLog_('WARN', String(e).slice(0, 120)); }
  }
  try { MailApp.sendEmail(Session.getEffectiveUser().getEmail(), '[폰스팟] 스레드 초안', text); }
  catch (e) { /* noop */ }
}

// ─────────────────────────────────────────────
// 진단
// ─────────────────────────────────────────────

/**
 * 초안이 왜 안 만들어지는지 짚어준다. 시트를 건드리지 않는다.
 * checkDrafts 가 '(만들 수 없음)' 을 뱉으면 이걸 먼저 실행할 것.
 */
function diagnoseDraft() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var ok = true;

  var confSh = ss.getSheetByName(DG.SHEET_CONF);
  if (!confSh) { Logger.log('❌ 시세_설정 탭 없음 → installDraftSettings 실행'); ok = false; }
  else {
    var conf = readConf_(ss);
    if (!conf) { Logger.log('❌ 시세_설정 내용 비었거나 형식 오류'); ok = false; }
    else Logger.log('✅ 시세_설정 %s개 통신사: %s', Object.keys(conf).length,
      Object.keys(conf).map(function (c) {
        return c + '(' + conf[c].fee + '/' + conf[c].planName + ')'; }).join(', '));
  }

  var nowSh = ss.getSheetByName(DG.SHEET_NOW);
  if (!nowSh) {
    Logger.log('❌ 시세_현재 탭 없음 → price-sync 의 syncPricesNow 를 먼저 실행');
    ok = false;
  } else {
    var rows = readNow_(ss);
    Logger.log('%s 시세_현재 %s행', rows.length ? '✅' : '❌', rows.length);
    if (!rows.length) { Logger.log('   → syncPricesNow 실행 필요'); ok = false; }
    else {
      var port = rows.filter(function (r) {
        return r.sub === '번호이동' && r.fund === '공시지원금'; });
      Logger.log('   번호이동·공시지원금 %s행', port.length);

      var byC = {};
      port.forEach(function (r) { byC[r.carrier] = (byC[r.carrier] || 0) + 1; });
      Logger.log('   통신사별: %s', JSON.stringify(byC));

      var dp = port.filter(function (r) { return isDp_(r.model); });
      Logger.log('   개봉(DP) %s행 %s', dp.length,
        dp.length ? '· 최저 ' + dp.sort(function (a, b) { return a.price - b.price; })[0].model : '');

      var conf2 = readConf_(ss);
      if (conf2) {
        ['KT', 'SKT', 'LG'].forEach(function (c) {
          if (!conf2[c]) return;
          var m = port.filter(function (r) {
            return r.carrier === c && samePlan_(r.plan, conf2[c].planName); });
          var over = m.filter(function (r) { return rate_(r) >= DG.CUT_RATE; });
          Logger.log('   %s 대표요금제「%s」매칭 %s행 · 할인율 %s%% 이상 %s행',
            c, conf2[c].planName, m.length, DG.CUT_RATE, over.length);
          if (!m.length) {
            var seen = {};
            port.filter(function (r) { return r.carrier === c; })
                .forEach(function (r) { seen[r.plan] = true; });
            Logger.log('      ⚠️ 요금제명 불일치. 시트에 있는 %s 요금제: %s',
              c, Object.keys(seen).slice(0, 6).join(' / '));
          }
        });
      }
    }
  }

  Logger.log(ok ? '── 전제조건 통과. checkDrafts 다시 실행해보세요.'
                : '── 위 ❌ 항목부터 해결하세요.');
}