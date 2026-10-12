/**
 * price_sync.gs — 폰스팟 시세 수집 & 변동 감지 (1단계)
 *
 * 원천: citymall.co.kr 뒤의 자체 API (qwe123.co.kr), sellChannelIdx=1 = 폰스팟
 * 만드는 탭 2개 (없으면 자동 생성):
 *   시세_현재 — 최신 스냅샷. 매 실행마다 덮어씀. 약 600행.
 *   시세_변동 — 값이 바뀐 건만 누적. 초안 생성과 '최근 30일 최저' 판정의 원장.
 *
 * 스케줄 (installPriceTriggers 로 등록):
 *   매시 실행하되 09~19시에만 동작. 09시는 개점 전 스냅샷.
 *   10 / 14 / 18시는 '초안 생성 시각'으로 표시만 해둠 (2단계에서 사용).
 *
 * ⚠️ 서버가 갱신 시각을 안 준다 (63개 필드에 날짜 없음, /model의 modelDisplayUpdateAt은 전부 null).
 *    그래서 '값이 바뀌었는가'로 업데이트를 감지한다.
 *    변동 없음 = 담당자 미업데이트가 아니다. 정책이 어제와 같은 날일 수도 있다.
 */

var PS = {
  API: 'https://qwe123.co.kr',
  SELL_CHANNEL: 1,              // 폰스팟
  CARRIERS: [                   // 알뜰폰(4)은 상품 0건이라 제외
    { idx: 1, name: 'KT' },
    { idx: 2, name: 'SKT' },
    { idx: 3, name: 'LG' }
  ],

  SHEET_NOW: '시세_현재',
  SHEET_DIFF: '시세_변동',
  LOG_SHEET: '동기화_로그',

  OPEN_HOUR: 9,                 // 이 시각부터
  CLOSE_HOUR: 19,               // 이 시각까지 (포함)
  DRAFT_HOURS: [10, 14, 18],    // 초안 생성 시각 (2단계)

  ALERT_PAYBACK: true,          // 페이백 전환은 즉시 알림
  ALERT_DROP: 200000,           // 이 금액 이상 하락하면 즉시 알림

  PROP_TG_TOKEN: 'TELEGRAM_BOT_TOKEN',
  PROP_TG_CHAT: 'TELEGRAM_CHAT_ID'
};

// 6개 조합: 지원금유형 × 가입유형
/**
 * 6조합. vis 는 그 가입유형이 사이트에 실제로 노출되는지 알려주는 필드다.
 *
 * 이걸 안 보면 사이트에 없는 조건을 광고하게 된다.
 * 2026-09-08 실측: KT 갤럭시 Z폴드8 256G(초이스110)는
 * productDisplayIsVisiblePort = 0 — 번호이동으로는 사이트에 안 보이는데
 * 우리 시세_현재에는 들어와 있었다. 지금은 하한선에 걸려 글에 안 나갔을 뿐이고,
 * 폴드8은 플래그십 정규식에 걸리므로 조건이 좋아지면 그대로 나갔을 것이다.
 */
var PS_COMBOS = [
  { field: 'calcPublicNew',     fund: '공시지원금', sub: '신규',   vis: 'productDisplayIsVisibleNew'    },
  { field: 'calcPublicPort',    fund: '공시지원금', sub: '번호이동', vis: 'productDisplayIsVisiblePort'   },
  { field: 'calcPublicDevice',  fund: '공시지원금', sub: '기기변경', vis: 'productDisplayIsVisibleDevice' },
  { field: 'calcContractNew',   fund: '선택약정',  sub: '신규',   vis: 'productDisplayIsVisibleNew'    },
  { field: 'calcContractPort',  fund: '선택약정',  sub: '번호이동', vis: 'productDisplayIsVisiblePort'   },
  { field: 'calcContractDevice',fund: '선택약정',  sub: '기기변경', vis: 'productDisplayIsVisibleDevice' }
];

/** 노출 필터를 껐다 켜는 스위치. 끄면 예전처럼 전부 수집한다(권장하지 않음). */
var PS_ONLY_VISIBLE = true;

// ⚠️ '키'는 16번째(P열)에 고정이다. draft_gen·publish_threads 가 인덱스 15로 읽는다.
//    새 열은 반드시 그 뒤에 붙일 것.
var PS_HEAD_NOW = ['수집시각','통신사','기종','용량','모델코드','출고가','요금제','요금제월정액',
                   '가입유형','지원금유형','공시지원금','추가지원','특별할인','실구매가','페이백','키',
                   '제조사'];
var PS_HEAD_DIFF = ['감지시각','통신사','기종','용량','요금제','가입유형','지원금유형',
                    '이전가','현재가','차액','구분','키'];

// ─────────────────────────────────────────────
// 진입점
// ─────────────────────────────────────────────

/** 트리거용. 영업시간 밖이면 아무것도 안 한다. */
function syncPrices() {
  if (!threadsGuard_('syncPrices')) return;
  var h = Number(Utilities.formatDate(new Date(), 'Asia/Seoul', 'H'));
  if (h < PS.OPEN_HOUR || h > PS.CLOSE_HOUR) return;
  runPriceSync_();
}

/** 시간 상관없이 강제 실행. 테스트·수동 확인용. */
function syncPricesNow() {
  if (!threadsGuard_('syncPricesNow')) return;
  runPriceSync_();
}

/** 트리거 등록 — 1회만 실행. 313jongmin 계정에서 실행할 것. */
function installPriceTriggers() {
  if (!threadsGuard_('installPriceTriggers')) return;
  ScriptApp.newTrigger('syncPrices').timeBased().everyHours(1).create();
  Logger.log('트리거 등록 완료: syncPrices 매시 (실제 동작은 %s~%s시)', PS.OPEN_HOUR, PS.CLOSE_HOUR);
}

// ─────────────────────────────────────────────
// 본체
// ─────────────────────────────────────────────

function runPriceSync_() {
  var t0 = Date.now();
  var now = new Date();
  var stamp = Utilities.formatDate(now, 'Asia/Seoul', 'yyyy-MM-dd HH:mm');

  var rows;
  try {
    rows = fetchAllPrices_();
  } catch (err) {
    psLog_('FAIL', String(err).slice(0, 300));
    psAlert_('⚠️ 시세 수집 실패\n' + String(err).slice(0, 300));
    return;
  }
  if (!rows.length) { psLog_('WARN', 'API가 0건을 반환. 스냅샷 유지.'); return; }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var shNow  = psSheet_(ss, PS.SHEET_NOW,  PS_HEAD_NOW);
  var shDiff = psSheet_(ss, PS.SHEET_DIFF, PS_HEAD_DIFF);

  var prev = readSnapshot_(shNow);          // 키 -> 실구매가
  var diffs = [], urgent = [];

  rows.forEach(function (r) {
    var before = prev[r.key];
    if (before === undefined) {
      // 스냅샷이 처음이면 전부 '신규'가 되어 노이즈가 된다. 최초 1회는 기록하지 않는다.
      if (Object.keys(prev).length) {
        diffs.push([stamp, r.carrier, r.model, r.size, r.plan, r.sub, r.fund,
                    '', r.price, '', '신규', r.key]);
      }
      return;
    }
    if (before === r.price) return;

    var delta = r.price - before;
    var kind = delta < 0 ? '하락' : '상승';
    if (before >= 0 && r.price < 0) kind = '페이백 전환';

    diffs.push([stamp, r.carrier, r.model, r.size, r.plan, r.sub, r.fund,
                before, r.price, delta, kind, r.key]);

    var isUrgent = (PS.ALERT_PAYBACK && kind === '페이백 전환')
                || (delta <= -PS.ALERT_DROP);
    if (isUrgent) urgent.push({ r: r, before: before, delta: delta, kind: kind });
  });

  writeSnapshot_(shNow, rows, stamp);
  if (diffs.length) shDiff.getRange(shDiff.getLastRow() + 1, 1, diffs.length, PS_HEAD_DIFF.length)
                          .setValues(diffs);

  if (urgent.length) psAlert_(buildUrgentMessage_(urgent, stamp));

  var msg = '수집 ' + rows.length + '행 / 변동 ' + diffs.length
          + ' / 긴급 ' + urgent.length
          + ' / ' + Math.round((Date.now() - t0) / 1000) + '초';
  psLog_('OK', msg);
  Logger.log(msg);
  if (diffs.length) Logger.log('변동 샘플: ' + diffs.slice(0, 5).map(function (d) {
    return d[1] + ' ' + d[2] + ' ' + d[5] + ' ' + d[7] + '→' + d[8];
  }).join(' | '));
}

// ─────────────────────────────────────────────
// API
// ─────────────────────────────────────────────

function fetchAllPrices_() {
  var hidden = 0;   // 사이트 미노출이라 건너뛴 조합 수
  var out = [];

  PS.CARRIERS.forEach(function (c) {
    var url = PS.API + '/phone-price-lookup/products'
            + '?carrierIdx=' + c.idx + '&sellChannelIdx=' + PS.SELL_CHANNEL;
    var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) {
      throw new Error(c.name + ' ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 150));
    }
    var list = JSON.parse(res.getContentText());
    if (!Array.isArray(list)) throw new Error(c.name + ' 응답이 배열이 아님');

    list.forEach(function (p) {
      // "갤럭시 S26_256G" → 기종 / 용량.
      // 다만 '_' 뒤가 늘 용량인 건 아니다 — "갤럭시A17_ZEM포켓피스" 같은 파생 상품이 있다.
      // 용량 패턴이 아니면 기종명에 그대로 붙인다. 안 그러면 서로 다른 상품이
      // 같은 기종명으로 합쳐져 보이고, 글에도 잘린 이름이 나간다.
      var petName = String(p.modelPetName || '');
      var us = petName.indexOf('_');
      var model = petName, size = '';
      if (us > 0) {
        var head = petName.slice(0, us), tail = petName.slice(us + 1);
        if (/^\d+\s*(G|GB|TB|T)$/i.test(tail.trim())) { model = head; size = tail.trim(); }
        else { model = head + ' ' + tail; }      // 파생 상품명은 기종에 포함
      }

      // 모델 자체가 사이트에서 숨겨졌으면 전 조합을 건너뛴다.
      if (PS_ONLY_VISIBLE && p.modelDisplayIsVisible === 0) { hidden += 6; return; }

      PS_COMBOS.forEach(function (cb) {
        var calc = p[cb.field];
        if (!calc || typeof calc.purchasePrice !== 'number') return;   // 혜택 준비중 등
        // 사이트에 그 가입유형으로 안 보이는 조합은 수집하지 않는다.
        if (PS_ONLY_VISIBLE && p[cb.vis] === 0) { hidden++; return; }

        out.push({
          carrier: c.name,
          model: model,
          size: size,
          code: p.modelName,
          maker: p.manufactureName || '',     // '삼성전자' / 'Apple' — 정규식 추정보다 정확
          listPrice: p.modelPrice,
          plan: p.pricePlanName,
          planFee: p.pricePlanBasicPrice,
          sub: cb.sub,
          fund: cb.fund,
          support: calc.supplyPrice,
          additional: calc.additionalSupport,
          special: calc.specialDiscount,
          price: calc.purchasePrice,
          payback: calc.purchasePrice < 0 ? 'Y' : '',
          // 키는 사람이 읽을 수 있게. 요금제명이 바뀌면 별개 항목으로 잡히는데 그게 맞다.
          key: [c.name, p.modelName, p.pricePlanName, cb.fund, cb.sub].join('|')
        });
      });
    });
  });

  if (hidden) Logger.log('사이트 미노출로 제외한 조합 %s개', hidden);
  return out;
}

// ─────────────────────────────────────────────
// 시트
// ─────────────────────────────────────────────

function psSheet_(ss, name, header) {
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

/** 시세_현재에서 키 -> 실구매가 맵을 읽는다. */
function readSnapshot_(sh) {
  var last = sh.getLastRow();
  if (last < 2) return {};
  var n = last - 1;
  var keys   = sh.getRange(2, 16, n, 1).getValues();   // P 키
  var prices = sh.getRange(2, 14, n, 1).getValues();   // N 실구매가
  var map = {};
  for (var i = 0; i < n; i++) {
    var k = keys[i][0];
    if (k) map[k] = Number(prices[i][0]);
  }
  return map;
}

function writeSnapshot_(sh, rows, stamp) {
  var body = rows.map(function (r) {
    return [stamp, r.carrier, r.model, r.size, r.code, r.listPrice, r.plan, r.planFee,
            r.sub, r.fund, r.support, r.additional, r.special, r.price, r.payback, r.key,
            r.maker];
  });

  var last = sh.getLastRow();
  if (last > 1) sh.getRange(2, 1, last - 1, PS_HEAD_NOW.length).clearContent();
  if (body.length) sh.getRange(2, 1, body.length, PS_HEAD_NOW.length).setValues(body);
}

// ─────────────────────────────────────────────
// 알림
// ─────────────────────────────────────────────

function buildUrgentMessage_(urgent, stamp) {
  var lines = ['🚨 시세 급변 (' + stamp + ')', ''];
  urgent.slice(0, 15).forEach(function (u) {
    var r = u.r;
    var nowTxt = r.price < 0 ? '페이백 ' + won_(-r.price) : won_(r.price);
    lines.push('· ' + r.carrier + ' ' + r.model + (r.size ? ' ' + r.size : '')
             + ' / ' + r.sub + ' / ' + r.fund);
    lines.push('  ' + won_(u.before) + ' → ' + nowTxt + '  (' + won_(u.delta) + ')');
    lines.push('  요금제 ' + r.plan);
    lines.push('');
  });
  if (urgent.length > 15) lines.push('외 ' + (urgent.length - 15) + '건');
  return lines.join('\n');
}

/** 1254000 → "1,254,000원". toLocaleString은 런타임 따라 다르게 나와서 직접 찍는다. */
function won_(n) {
  var s = String(Math.abs(Math.round(Number(n) || 0)));
  var out = '';
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 === 0) out += ',';
    out += s[i];
  }
  return (Number(n) < 0 ? '-' : '') + out + '원';
}

/**
 * 텔레그램으로 보낸다. 스크립트 속성에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 가 있어야 한다.
 * 없으면 메일로 대체한다 (조용히 사라지는 것보다 낫다).
 */
function psAlert_(text) {
  if (threadsMuted_()) { threadsMuteLog_('syncPrices', text); return; }   // alerts.js TELEGRAM_ALL_OFF 따름
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty(PS.PROP_TG_TOKEN);
  var chat  = props.getProperty(PS.PROP_TG_CHAT);

  if (token && chat) {
    try {
      var res = UrlFetchApp.fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
        method: 'post',
        payload: { chat_id: chat, text: text, disable_web_page_preview: 'true' },
        muteHttpExceptions: true
      });
      if (res.getResponseCode() === 200) return;
      psLog_('WARN', '텔레그램 전송 실패 ' + res.getContentText().slice(0, 150));
    } catch (e) {
      psLog_('WARN', '텔레그램 예외 ' + String(e).slice(0, 150));
    }
  }

  try {
    MailApp.sendEmail(Session.getEffectiveUser().getEmail(), '[폰스팟] 시세 알림', text);
  } catch (e) { /* noop */ }
}

function psLog_(result, message) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(PS.LOG_SHEET);
    if (sh) sh.appendRow([new Date(), 'syncPrices', result, message]);
  } catch (e) { /* 로그 실패로 본작업을 죽이지 않는다 */ }
}

// ─────────────────────────────────────────────
// 점검
// ─────────────────────────────────────────────

/** 붙여넣고 제일 먼저 실행해볼 것. 시트를 건드리지 않고 API만 확인한다. */
function checkPriceApi() {
  var rows = fetchAllPrices_();
  Logger.log('수집 %s행', rows.length);

  var byCarrier = {};
  rows.forEach(function (r) { byCarrier[r.carrier] = (byCarrier[r.carrier] || 0) + 1; });
  Logger.log('통신사별: %s', JSON.stringify(byCarrier));

  var pb = rows.filter(function (r) { return r.price < 0; });
  Logger.log('페이백 %s건', pb.length);
  pb.slice(0, 5).forEach(function (r) {
    Logger.log('  %s %s %s / %s / %s → 페이백 %s',
      r.carrier, r.model, r.size, r.sub, r.plan, won_(-r.price));
  });

  var s = rows[0];
  Logger.log('샘플: %s %s %s %s / 출고 %s / 실구매 %s / 키 %s',
    s.carrier, s.model, s.size, s.sub, won_(s.listPrice), won_(s.price), s.key);
}