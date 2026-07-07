# 슈퍼톤 나레이션 가이드 (폰스팟 promo_ai)

> Higgsfield TTS(Hana=성우톤, 영어권 preset)를 슈퍼톤으로 대체. 한국어 캐주얼 톤 + 개인 목소리 클론.
> 나레이션 소스만 교체 — 청크자막·효과·모션·1.35배속 등 나머지 WORKFLOW 룰은 그대로.

---

## 0. 왜 슈퍼톤
- **한국어 1등**(한국 회사·하이브 자회사). 아나운서 아닌 **캐주얼·젊은 preset이 풍부** → 클론 안 해도 자연스러운 한국어.
- **음성 클론**(파일 업로드)도 지원 → 원하는 개인 목소리 톤.
- **Starter $2.99/mo** = 파일 업로드 클론 + **무제한 상업이용**. (Free는 'Supertone' 출처표시 필요)

## 1. 셋업
1. play.supertone.ai 가입 (2주 무료체험, 카드 불필요)
2. **Starter 구독 $2.99/mo** (무제한 상업 + 파일 클론)
3. 법인결제/세금계산서 = **Business Contact 문의**로 확인(국내 법인이라 가능성 높음)

## 2. 워크플로 (Claude ↔ 종민, 004 흐름과 동일)
```
① Claude: 대본 작성 (전문용어 X, 1인칭 썰톤, 7비트) — 문장 단위로 쪼개서
② 종민: 슈퍼톤 Play에서
   - 한국어 캐주얼 보이스 선택 (또는 클론 보이스)
   - 문장별 생성 → mp3 다운로드
③ 종민: 폴더 투입 → assets/audio/narration/<slug>_n1~nN.mp3
④ Claude: ffmpeg 합성 (1.35배속 + 청크자막 + 컷 매핑)
```

## ★ 크레딧 승인 룰 (2026-07-06, 종민 — 필수)
- `text_to_speech`(생성)는 **크레딧 소모** → 실행 전 종민에게 "이 문장/컷 N개, 예상 ~X크레딧" 밝히고 **승인받은 뒤** 실행. 무단 생성 ❌.
- 무료 조회(`preview_voice`·`predict_duration`·`get_credit_balance`·`search_voice`)는 승인 없이 OK.
- ★ **생성 직후 매번 `get_credit_balance`로 잔액 보고**(종민 요청 2026-07-06). 형식: "이번 ~N크레딧 차감 / 잔액 X". (Higgsfield balance 보고 룰과 동일 결.)
- ★ **톤 미세조정(피치·속도·스타일)은 1문장만 테스트**(≈28크레딧)로 방향 확인 → 확정되면 6문장 전체. 조정마다 6문장 재생성(≈145) 반복 = 낭비.
- 실측 코스트: sona_speech_2 기준 문장(~4초) ≈ 28크레딧. Starter 20,000/월 ≈ 700문장.

## 3. 보이스 선택 팁 + 표준 보이스 지정
- **★ 글래머 실사 라인 표준 보이스 = Selena** `voice_id=2d172d6efe637391880b10` (2026-07-06 종민, 004로 확정).
- **★ 카드뉴스영상(casual) 표준 보이스 = Sora** `voice_id=f32a02422bd88da70fddb2` (2026-07-07 종민 확정). style=friendly 기본(중립 원하면 neutral), 광고 나레이션 친근·중립 톤. 실사 라인 Selena와 **트랙별 화자 고정**(섞지 않음).
  - 세팅: **neutral 기본 + 반전·현타 비트만 lazy** / **pitch_shift = -2**(성숙하게) / speed는 ffmpeg 1.35배속.
  - 이유: Bomi(c94c72e2)는 큐트해서 섹시·청순 글래머와 안 맞아 교체. teasing 통일은 과하게 들뜸 → neutral 기반 채택.
  - Selena styles: neutral·kind·lazy·teasing·happy·sad·angry → 비트별 감정 배분 가능.
- 밈 마스코트 라인은 `[Meme]` 계열(GenZZZ·NyangNyangi 등)에서 별도 지정.
- ★ **라인별 화자 1개 고정**(일관성) — 정한 voice_id를 라인명과 함께 메모해 계속 사용.

## 4. 속도 (폰스팟 1.35배속 룰 유지)
- 슈퍼톤 Play의 **Speed 조절**로 맞추거나, 원본 생성 후 ffmpeg `atempo=1.35`(기존 WORKFLOW 방식).
- ★ **문장별 생성** 권장 — 청크 자막 싱크가 쉬워짐(비트별 타임코드 산출 편함).

## 5. 클론 (선택 — 개인 목소리)
- Starter = **오디오 파일 업로드 클론**. 한국인 목소리 샘플(★ 동의 필수, 음성권) → 등록 → 그 톤으로 전체 나레이션.
- 본인 or 동의받은 사람만. 무단 복제 금지.

## 6. 나중 자동화 (볼륨 커지면)
- 슈퍼톤 **REST API**(Developers, Creator 플랜↑) → **커스텀 MCP 래퍼** 만들어 Claude 직접 연동. 그 전엔 웹→투입으로 충분.

## 7. WORKFLOW 연동
- `WORKFLOW.md` "1. 나레이션"에서 **TTS = 슈퍼톤(한국어 캐주얼/클론)**으로 교체. 004의 Quinn(영어권 성우)은 임시였음.
- 나머지(자막 전문일치·청크·효과4·켄번스줌·sound off)는 전부 동일.

---

## 8. 카드뉴스영상(casual) 파이프라인 자동 통합 (2026-07-07)

`shorts/scripts/generate_tts.py`에 **슈퍼톤(Sora) 우선 + edge-tts 자동 폴백** 내장. 패널에서 카드뉴스영상 렌더 돌리면 자동 적용.

**동작**: `supertone_enabled()`(엔진 auto/supertone + 키 존재) → 슈퍼톤 REST(`/text-to-speech/{voice}`) 성공 시 Sora, 실패/키없음/크레딧부족 → **edge-tts로 폴백**(무료). 엔진 전환 시 캐시 자동 무효화, 같은 스크립트 재렌더는 mp3 재사용(재소모 X).

**키 세팅(둘 중 하나, 렌더PC)**:
- `_secrets/supertone_key.txt`에 API 키 한 줄 (권장 — worker가 확실히 읽음, 영속).
- 또는 `setx SUPERTONE_API_KEY "키"` (영구 환경변수).
- (임시 `set SUPERTONE_API_KEY=`는 그 창에서만 — worker가 못 물려받을 수 있음.)

**환경변수 토글**:
- `PHONESPOT_TTS_ENGINE` = `auto`(기본, 키 있으면 슈퍼톤) / `edge`(강제 무료) / `supertone`(강제).
- `PHONESPOT_SUPERTONE_VOICE`(기본 Sora `f32a02422bd88da70fddb2`) · `_STYLE`(friendly) · `_MODEL`(sona_speech_1) · `_SPEED`(1.4, edge +42% 대응).

**★ 한계(정직)**: 슈퍼톤은 단어 타임스탬프(WordBoundary)를 안 줘서, 자막 싱크가 edge의 정밀(word_boundary) → **character_weight 근사 싱크**로 떨어짐(깨지진 않음, 설계된 폴백). 렌더PC 첫 결과에서 자막 드리프트 확인 → 심하면 `PHONESPOT_TTS_ENGINE=edge`로 되돌리거나, 나중에 whisper 강제정렬 추가.

**비용**: 1편 30~35초 ≈ 250~360크레딧(모델 따라). 승인 룰(§0) 적용 — 자동 렌더는 사장님이 "패널 렌더=슈퍼톤" 승인한 것으로 간주, 생성 후 잔액 보고 권장.
