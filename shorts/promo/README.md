# 폰스팟 홍보영상(promo) 트랙 — 정본 마스터 가이드 (현행 2026-06-15)

> **이 파일이 promo 트랙의 단일 정본(③ 마스터 가이드).** 상위 구조: `CLAUDE.md`(헤드) → `_docs/SYSTEM_MAP.md` 대단원 C(영상) → **이 README**.
> promo를 고치려면 **이 파일만** 읽으면 됨(경로·핵심함수·"수정 시 읽을 것"·함정 다 박혀 있음). 1회성 요약본 생성 ❌.
>
> 카드뉴스 쇼츠 엔진에 **기생**하는 트랙. casual/newsroom과 **다른 결**(타이포/모션그래픽) + **나레이션 없음(효과음+음악)**.
> casual/newsroom 코드 무수정. promo 자산은 `promo/` + `src/components/promo/` + `scripts/promo_*.py` + `run_promo*.bat` + `public/sfx/` + `public/music/` 에만 존재.

## 1. 한눈에
- 같은 Remotion 엔진·브랜드 재사용, **비주얼만 promo 전용**. **나레이션 없음 — 효과음 + 음악 기반.**
- **스타일 23종 + 프리셋 4종**(플러그인). 새 스타일/스크립트는 파일 추가만으로 자동 등록.
- **편집 원본 = MD**(`promo/review/NNN_*.md`). 렌더 직전 MD→JSON 자동 변환.
- **비트(섹션)별로 본문 · 타이포 스타일 · 효과음을 함께 디렉팅**. 효과음은 스타일(모션)에 자동 매칭.
- **음악 = 무드풀 자동선택**(프리셋→무드→로테이션). 파일명으로 시작 지점 지정.
- 출력은 `promo/out/` **한 곳만**(복사본 없음). 카드뉴스 발행폴더 `../upload/`와 분리.

## 2. 빠른 실행 (PC)
```
run_promo.bat                  ← 번호 목록 → 번호 입력 → 1편 렌더
run_promo_batch.bat            ← promo/*.json 전부(각 스크립트 지정 preset)
run_promo_batch.bat showcase   ← 전부 한 프리셋으로 통일
```
- 결과: `promo/out/NNN_이름_프리셋.mp4`. **재렌더 시 덮어쓰지 않고 `_1`,`_2`… 자동 넘버링**(기존 파일 보존). **효과음+음악 기반, 나레이션 없음.**
- 미리보기: `npx remotion studio` → 컴포지션 `Promo-<style>` / `Promo-<preset>` (하이픈 주의).
- 첫 실행은 Chromium ~300MB 다운로드(1회). Node.js + Python 필요.

## 3. 폴더 / 파일
```
shorts/
├─ promo/
│  ├─ 001_jeongchalje.json … 012_secret.json   ← 스크립트(렌더 입력, 자동 생성물)
│  ├─ review/                                   ← ★편집은 여기서★
│  │   ├─ NNN_이름.md      (화면/스타일/효과음/dur — 사람이 편집)
│  │   └─ _LEARN.md        (수정 패턴 학습 누적, 새 초안 전 Claude가 읽음)
│  ├─ _orig/               (Claude 초안 스냅샷 = 학습 비교 기준)
│  ├─ _brand.json          (채널·kakao·litt·location — 한 곳서 관리)
│  ├─ _manifest.csv        (렌더 변주 기록 — 학습/성과귀속 대비, 자동 추가)
│  ├─ _template/           (새 스크립트 템플릿)
│  ├─ preview/             (샌드박스 프리뷰·SFX 데모, 참고용)
│  ├─ GUIDE_TYPOGRAPHY.md · GUIDE_INFOGRAPHIC.md · STYLE_CATALOG.md
│  ├─ GUIDE_BEST_TYPO_AD.md · TOPIC_BANK.md · FORMAT_BANK.md · PRODUCTION_PROCESS.md · HOOK_LEARNING.md
│  └─ README.md (이 문서 = 정본)
├─ run_promo.bat · run_promo_batch.bat          ← ASCII 전용
├─ public/sfx/   (punch·pop·tick·whoosh·ding·glitch.mp3)
├─ public/music/ (<무드>_<번호>[__시작초].mp3 + README_MUSIC.md)
├─ public/fonts/PretendardVariable.woff2
├─ scripts/  promo_list.py · promo_get.py · promo_md2json.py · promo_json2md.py
│            promo_review.py · promo_learn.py · promo_merge_brand.py · promo_pick_music.py · promo_manifest.py
│            promo_check_sync.py(MD↔JSON 정합) · promo_score.py(성과 축집계) · promo_results_add.py(성과 1행 수동)
└─ src/components/promo/
   ├─ PromoShort.tsx        (디스패처: 섹션별 스타일/효과음 + 음악(music_src/music_start) + 고정 타이밍 + 비네트)
   └─ styles/
      ├─ shared.tsx (팔레트 3색[오렌지 #FF5A1F·흰 #FFFFFF·검정 #0E0E10, 보조 그레이 #8C8C92]·VARIANTS·CtaBlock·헬퍼·PromoStyle·BasicOpening/Outro)
      ├─ registry.ts (PROMO_STYLES 23 · PROMO_PRESETS 4 · getStyle · SFX_BY_STYLE · sfxForStyle)
      └─ <23개 스타일>.tsx
```
※ `scripts/generate_tts.py`는 casual용 — promo는 나레이션 없어 미사용.

## 4. 편집 워크플로 (★ 핵심)
1. `promo/review/NNN_이름.md` 열기 → 비트별 수정:
   - `스타일:` (23종 중 하나, 비우면 프리셋 기본)
   - `효과음:` (`punch`/`pop`/`tick`/`whoosh`/`ding`/`glitch`/`none`, 비우면 자동 = 스타일 기반 §6)
   - `화면:` 자막 토막을 ` | ` 로 구분
   - `dur:` (선택) 그 섹션 길이 초. 없으면 기본(2.2s, CTA 2.8s)
2. `run_promo.bat` → 번호 입력. **렌더 직전**: MD→JSON 변환(`promo_md2json.py`, MD가 권위) → 브랜드 병합(`promo_merge_brand.py`) → 음악 선택(`promo_pick_music.py`).
3. 수정 끝나면 Claude에게 **"검토"** → `promo_learn.py`로 `_orig` 대비 변경분 추출 → `review/_LEARN.md`에 규칙 누적 → 다음 초안 반영.

규칙: `화면` 짧게 · 마크다운 에디터가 `-`를 `*`로 바꿔도 인식됨 · **숫자는 평문 `1,2,3,4`(원형숫자 ①②③ 금지)** · 대본 머리에 `- 후킹: <타입>` 선언 가능(학습용, §13).
⚠ 가격 숫자(실구매가·지원금액·요금) 금지(단통법·표시광고법) · 경쟁사 지목/비방 금지("허위매물"은 업계 일반 표현으로만).

## 5. 스타일 / 프리셋 (총 23 + 4)
- **타이포(11)**: kinetic · kinetic-box · reveal · oversize · karaoke · swiss · mask · fluid · crawl · marker · glitch
- **인포(12)**: counter · barcompare · timeline · steps · checklist · pictogram · donut · linegraph · statgrid · ranking · gauge · table
- 컴포지션 id = `Promo-<id>`. 설명: `STYLE_CATALOG.md` / `GUIDE_TYPOGRAPHY.md` / `GUIDE_INFOGRAPHIC.md`.
- **프리셋(styleMap)**: `showcase`(디렉터컷) · `punchy` · `calm` · `data`. 컴포지션 `Promo-<preset>`.
- 스타일 우선순위: **섹션 `스타일:` > 프리셋 styleMap > promoStyle**.

## 6. 효과음(SFX) — 스타일(모션) 기반
- 음원 6종: `public/sfx/punch·pop·tick·whoosh·ding·glitch.mp3`(ffmpeg 합성, 무료). 더 좋은 SFX는 같은 파일명 덮어쓰기.
- **섹션 역할이 아니라 그 섹션의 스타일(화면 모션)에 맞춰 자동 선택** = `registry.ts`의 `SFX_BY_STYLE` + `sfxForStyle`.
  - 스케일펀치/대형(kinetic·kinetic-box·oversize) → **punch**
  - 차분 리빌/모핑/선(reveal·mask·fluid·crawl·linegraph) → **whoosh**
  - 팝/슬램(karaoke·marker·barcompare·steps·pictogram·statgrid·ranking) → **pop**
  - 스냅/카운트/게이지/표(swiss·counter·timeline·donut·gauge·table) → **tick**
  - glitch → **glitch** · checklist(✓ 확정) → **ding**
- 우선순위: MD `효과음:` 직접 지정 > 스타일 기본 > (역할 fallback: CTA=ding / 그외=whoosh). `none`이면 끔.
- 전체 끄기: 컴포지션 `sfx={false}` (기본 on). 매핑 바꾸려면 `SFX_BY_STYLE` 한 줄 수정.

## 7. 음악(BGM) — 무드풀 자동선택
- 폴더: `public/music/`. 파일명 규칙 **`<무드>_<번호>[__시작초].mp3`** (예 `confident_01.mp3`, `upbeat_02__70.mp3` = 1:10부터).
- 무드 4종 ↔ 프리셋 자동 매핑(`MOOD_BY_PRESET`): showcase→**confident** · punchy→**upbeat** · calm→**calm** · data→**minimal**.
- 선택 로직 `scripts/promo_pick_music.py`(인자 `preset slug`): 프리셋→무드 곡 글롭 → slug 번호로 **로테이션**(같은 무드 영상도 곡 다르게) → 없으면 폴더 내 아무 곡 fallback → `music_src`+`music_start`를 스크립트에 기록.
- 파일명 끝 `__NN` = 시작 초. `PromoShort.tsx`의 `<Audio trimBefore={music_start*fps}>`로 그 지점부터 사용. 영상 길이만큼만(15~20초) 잘려 페이드 인/아웃(볼륨 0.5).
- 무드당 2~3곡 권장(로테이션). 곡 없으면 음악 자동 off(에러 X). 개별 지정: 스크립트 `mood` 또는 `music`(파일명)이 최우선. 출처: YouTube 오디오 보관함·Pixabay Music·Uppbeat·FMA(상업 free 확인). 상세 = `public/music/README_MUSIC.md`.

## 8. 새 스크립트 / 새 스타일 추가
- **스크립트**: 템플릿 복사 → `promo/013_<이름>.json`(또는 review MD 작성 후 `py scripts\promo_md2json.py`). 목록 자동 갱신. 번호 = 파일명 앞 3자리(고정).
- **스타일(파일1 + 한 줄)**: ① `src/components/promo/styles/<id>.tsx`에 `export const <id>: PromoStyle = { Opening, Scene, Outro };`(CTA는 `shared.tsx`의 `CtaBlock` 재사용) ② `registry.ts`의 `PROMO_STYLES`에 `{ id:"<id>", label:"<이름>", style:<id> }` 한 줄 → Root가 `Promo-<id>` 자동 등록. ③ 효과음 궁합 다르면 `SFX_BY_STYLE`에 `<id>:"<sfx>"` 한 줄.

## 9. 품질 기준 / 사양
- 1080×1920 · 30fps · yuv420p · CRF 18 · 폰트 Pretendard · **나레이션 없음**.
- 타이밍 고정(섹션 기본 **2.2s · CTA 2.8s**, 스크립트 `dur`(초)로 조정) — `Root.tsx`의 `calcPromo`/`promoSeconds`. (opening/outro는 casual과 공유라 promo만 바꿀 땐 `PROMO_SEC`/`PROMO_CTA`만)
- 효과음 `public/sfx/` · 음악 `public/music/`(무드풀, §7).

## 10. 수정 시 읽을 것 (어디를 고치려면 어디로)
| 고치려는 것 | 파일 / 함수 |
|---|---|
| 섹션 타이밍·길이 | `src/Root.tsx` `calcPromo`/`promoSeconds` (`PROMO_SEC`/`PROMO_CTA`) |
| 효과음 ↔ 스타일 매핑 | `styles/registry.ts` `SFX_BY_STYLE` / `sfxForStyle` |
| 효과음·음악 재생/페이드/볼륨 | `PromoShort.tsx` (`sfxAt`, music `<Audio trimBefore>`·volume) |
| 음악 선택·로테이션·시작점 | `scripts/promo_pick_music.py` + `public/music/README_MUSIC.md` |
| 스타일 추가/모션 | `styles/<id>.tsx` + `registry.ts` `PROMO_STYLES` |
| 팔레트·CTA·VARIANTS | `styles/shared.tsx` |
| 편집→렌더 변환 | `scripts/promo_md2json.py`(MD 권위) / `promo_json2md.py` |
| 브랜드값 | `promo/_brand.json` + `promo_merge_brand.py` |
| 빌드 흐름 | `run_promo.bat` / `run_promo_batch.bat` (ASCII 전용) |

## 11. 함정 / 트러블슈팅
| 증상 | 원인 | 해결 |
|---|---|---|
| bat이 한글 깨진 명령 에러 | **.bat에 한글 넣으면 cmd가 파싱 깨짐** | bat은 **영문(ASCII)만**. 한글은 .json·.md·.py에만 |
| 렌더 파일이 안 보임 | promo는 `promo/out/` 하위(루트 아님). 시각은 **UTC 표시**(한국=+9) | `promo/out/` 확인 |
| 파일 날짜/내용이 옛것·잘림 | **이 폴더가 구글 드라이브 스트리밍** → 접근 계층마다 placeholder 캐시 다름 | 드라이브 폴더 "오프라인 사용 가능(mirror)"로 전환 → 진본 1개 |
| 효과음이 맥락과 무관 | (구) 역할 기반이었음 | 현재 스타일 기반(`SFX_BY_STYLE`). MD `효과음:`으로 비트별 덮어쓰기 |
| 같은 곡만 반복 | 그 무드 곡 1개뿐 | 무드당 2~3곡 넣으면 slug 로테이션 |
| "Composition not found" | id는 하이픈 | `Promo-<style/preset>` 사용 |
| 카드뉴스가 promo 내용으로 | public 작업영역 공유 | 카드뉴스는 `run_B_casual.bat` 재실행 |

## 12. 점검 결과 (2026-06-15)
- 스타일 23 + 프리셋 4 등록. 효과음 **스타일(모션) 기반**(`SFX_BY_STYLE`, 6종 — punch·glitch 합성 추가). 음악 **무드풀**(프리셋→무드 로테이션 + 파일명 `__초` 시작점).
- **팔레트 3색**(오렌지 #FF5A1F 강조 10% · 흰 #FFFFFF · 검정 #0E0E10, 보조 그레이 #8C8C92) — 다색 구성 제거, CTA/아웃트로도 검정바탕+오렌지강조. **템포** 본문 2.2s·CTA 2.8s(살짝 빠르게). **숫자 평문화**. **재렌더 자동 넘버링**(`_1`,`_2`).
- 출력: `promo/out/`만(upload 복사 폐기). 재렌더는 `_1`,`_2` 자동 넘버링(덮어쓰기 X) — bat의 `:uniq`/`:nextname`. 나레이션 제거 — 효과음+음악만.
- casual/newsroom 무수정. 규제: 전 스크립트 가격 숫자 없음, 경쟁사 비방 없음.
- ※ 샌드박스 tsc는 드라이브 스트리밍 절단으로 부분 검증 한계 — 최종 렌더는 PC가 확정.

## 13. 학습 루프(②) — 인사이트→훅 + 변주 매니페스트
- 대본 첫 줄(훅)을 `유튜브_인사이트`/`메타_인사이트` Top 후킹 패턴으로 작성하고, review MD 머리에 `- 후킹: <타입>` 선언. 8종: 질문형·단언형·비교형·한정형·가격강조·감성·공감·위협형·FOMO형 (가격강조는 금액 X, 정찰·투명 메시지만).
- 렌더마다 `scripts/promo_manifest.py`가 `promo/_manifest.csv`에 변주 1행 자동 기록(ts·outfile·preset·hook_pattern·hook_text·styles·music·n_facts). bat이 렌더 직후 호출.
- 이 CSV + 업로드 영상 매칭(= C단계, ads/API)으로 "어떤 후킹/스타일/프리셋이 이겼나" 집계. 상세 = `promo/HOOK_LEARNING.md`.
- ⚠ 초기 표본 작을 땐 통계 노이즈 → 데이터 쌓고 판단(자동 최적화는 누적 후).
- **200~300편 데이터기반 자가개선 전체 설계**(생성기→배치렌더→업로드로그→귀속→스코어링·가지치기, YT/IG 귀속, 통계 게이트) = `promo/AUTOLOOP_DESIGN.md` (설계·미구현, Phase 0 완료).
