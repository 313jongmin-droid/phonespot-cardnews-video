# 폰스팟 홍보영상(promo) 트랙 — 매뉴얼 (현행 2026-05-31)

> 카드뉴스 쇼츠 엔진에 **기생**하는 홍보영상 트랙. 카드뉴스(casual)와 **다른 결**(타이포/모션그래픽).
> casual/newsroom 코드는 안 건드림. promo 관련은 `promo/` + `src/components/promo/` + `scripts/promo_*.py` + `run_promo*.bat` + `public/sfx/` 에만 있음.

## 1. 한눈에
- 같은 Remotion 엔진·브랜드 재사용, **비주얼만 promo 전용**. **나레이션 없음 — 효과음(+음악) 기반.**
- **스타일 17종 + 프리셋 4종**(플러그인). 새 스타일/스크립트는 파일 추가만으로 자동 등록.
- **편집 원본 = MD**(`promo/review/NNN_*.md`). 렌더 직전 MD→JSON 자동 변환.
- **비트(섹션)별로 본문·타이포 스타일·효과음을 함께 디렉팅**.
- 출력은 `out/promo/` **한 곳만**(복사본 없음). 카드뉴스 발행폴더 `../upload/`와 분리.

## 2. 빠른 실행 (PC)
```
run_promo.bat            ← 번호 목록 뜸 → 번호 입력 → 1편 렌더
run_promo_batch.bat            ← promo/*.json 전부(각 스크립트 지정 preset)
run_promo_batch.bat showcase   ← 전부 한 프리셋으로 통일
```
- 결과: `out\promo\NNN_이름_프리셋.mp4` (한 곳만, 복사본 없음). **효과음(+음악) 기반, 나레이션 없음.**
- 미리보기: `npx remotion studio` → 컴포지션 `Promo-<style>` / `Promo-<preset>` (하이픈 주의).
- 첫 실행은 Chromium ~300MB 다운로드(1회). Node.js + Python 필요.

## 3. 폴더 / 파일
```
shorts/
├─ promo/
│  ├─ 001_jeongchalje.json … 012_secret.json   ← 스크립트(렌더 입력, 자동 생성물)
│  ├─ review/                                   ← ★편집은 여기서★
│  │   ├─ NNN_이름.md      (화면/나레이션/스타일/효과음 — 사람이 편집)
│  │   └─ _LEARN.md        (수정 패턴 학습 누적, 새 초안 전 Claude가 읽음)
│  ├─ _orig/               (Claude 초안 스냅샷 = 학습 비교 기준)
│  ├─ _brand.json          (채널·kakao·litt·location — 한 곳서 관리)
│  ├─ _template/           (새 스크립트 템플릿)
│  ├─ preview/             (샌드박스 프리뷰·SFX 데모, 참고용)
│  ├─ GUIDE_TYPOGRAPHY.md · GUIDE_INFOGRAPHIC.md · STYLE_CATALOG.md
│  ├─ GUIDE_BEST_TYPO_AD.md · TOPIC_BANK.md · FORMAT_BANK.md · PRODUCTION_PROCESS.md
│  └─ README.md (이 문서)
├─ run_promo.bat · run_promo_batch.bat
├─ public/sfx/ (whoosh·pop·tick·ding.mp3)  · public/fonts/PretendardVariable.woff2
├─ scripts/  promo_list.py · promo_get.py · promo_md2json.py · promo_json2md.py
│            promo_review.py · promo_learn.py · promo_merge_brand.py · generate_tts.py
└─ src/components/promo/
   ├─ PromoShort.tsx        (디스패처: 섹션별 스타일/효과음 + 오디오 + 타이밍 + 비네트)
   └─ styles/
      ├─ shared.tsx (팔레트·VARIANTS·CtaBlock·헬퍼·PromoStyle·BasicOpening/Outro)
      ├─ registry.ts (PROMO_STYLES 17 · PROMO_PRESETS 4 · getStyle)
      └─ <17개 스타일>.tsx
```

## 4. 편집 워크플로 (★ 핵심)
1. `promo/review/NNN_이름.md` 열기 → 비트별 **4줄** 수정:
   - `스타일:` (17종 중 하나, 비우면 프리셋 기본)
   - `효과음:` (`whoosh`/`pop`/`tick`/`ding`/`none`, 비우면 자동: 전환 whoosh·CTA ding)
   - `화면:` 자막 토막을 ` | ` 로 구분
   - `나레이션:` (참고용 메모 — 현재 음성 출력 안 함. 효과음+음악 기반)
   - `dur:` (선택) 그 섹션 길이 초. 없으면 기본(2.4s, CTA 3.0s)
2. `run_promo.bat` → 번호 입력. **렌더 직전 MD→JSON 자동 변환**(`promo_md2json.py`), 브랜드값 자동 병합(`_brand.json`).
3. 수정 끝나면 Claude에게 **"검토"** → `promo_learn.py`로 `_orig` 대비 변경분 추출 → `review/_LEARN.md`에 규칙 누적 → 다음 초안 반영.

규칙: `화면`(짧게) / `나레이션`(자연스럽게) 분리 · 마크다운 에디터가 `-`를 `*`로 바꿔도 인식됨.
⚠ 가격 숫자(실구매가·지원금액·요금) 금지(단통법·표시광고법) · 경쟁사 지목/비방 금지("허위매물"은 업계 일반 표현으로만).

## 5. 스타일 / 프리셋
- **타이포(11)**: kinetic · kinetic-box · reveal · oversize · karaoke · swiss · mask · fluid · crawl · marker · glitch
- **인포(6)**: counter · barcompare · timeline · steps · checklist · pictogram + donut · linegraph · statgrid · ranking · gauge · table (인포 총 12)
- 컴포지션 id = `Promo-<id>`. 설명: `STYLE_CATALOG.md` / `GUIDE_TYPOGRAPHY.md` / `GUIDE_INFOGRAPHIC.md`.
- **프리셋(styleMap)**: `showcase`(디렉터컷) · `punchy` · `calm` · `data`. 컴포지션 `Promo-<preset>`.
- 우선순위: **섹션의 `스타일:` > 프리셋 styleMap > promoStyle**. (MD에서 비트별로 덮어쓰면 그게 최우선)

## 6. 효과음(SFX) — 스타일(모션) 기반
- 음원 6종: `public/sfx/punch·pop·tick·whoosh·ding·glitch.mp3`(ffmpeg 합성, 무료). 더 좋은 SFX는 같은 파일명 덮어쓰기.
- **효과음은 섹션 역할이 아니라 그 섹션의 스타일(화면 모션)에 맞춰 자동 선택**(`registry.ts`의 `SFX_BY_STYLE`).
  - 스케일펀치/대형(kinetic·kinetic-box·oversize) → **punch**
  - 차분 리빌/모핑/선(reveal·mask·fluid·crawl·linegraph) → **whoosh**
  - 팝/슬램(karaoke·marker·barcompare·steps·pictogram·statgrid·ranking) → **pop**
  - 스냅/카운트/게이지/표(swiss·counter·timeline·donut·gauge·table) → **tick**
  - glitch → **glitch** · checklist(✓확정) → **ding**
- 우선순위: MD `효과음:` 직접 지정 > 스타일 기본 > (역할 fallback: CTA=ding/그외=whoosh). `none`이면 끔.
- 전체 끄기: 컴포지션 `sfx={false}` (기본 on). 매핑 바꾸려면 `SFX_BY_STYLE` 한 줄 수정.

## 7. 새 스크립트 추가
- 템플릿 복사 → `promo/013_<이름>.json`(또는 review MD 작성 후 `py scripts\promo_md2json.py`).
- 목록 자동 갱신(`promo_list.py`). 번호는 파일명 앞 3자리(고정).

## 8. 새 스타일 추가 (파일1 + 한 줄)
1. `src/components/promo/styles/<id>.tsx`: `export const <id>: PromoStyle = { Opening, Scene, Outro };`
   (CTA는 `shared.tsx`의 `CtaBlock` 재사용 권장)
2. `registry.ts`의 `PROMO_STYLES`에 한 줄: `{ id: "<id>", label: "<이름>", style: <id> },` (`cat`은 선택).
→ Root가 `Promo-<id>` 자동 등록.

## 9. 품질 기준
1080×1920 / 30fps / yuv420p / CRF 18 · 폰트 Pretendard · **나레이션 없음**. 타이밍 고정(섹션 기본 2.4s·CTA 3.0s, 스크립트 `dur`(초)로 조정). 효과음 `public/sfx/`, 음악 `public/music/bed.mp3`(있으면 music 옵션 on).

## 10. 트러블슈팅
| 증상 | 원인 | 해결 |
|---|---|---|
| bat이 한글 깨진 명령 에러 | **.bat에 한글 넣으면 cmd가 파싱 깨뜨림** | bat은 **영문(ASCII)만**. 한글은 .json·.md·.py에만 |
| 렌더 파일이 안 보임 | promo는 `out\promo\` 하위(루트 아님). 시각은 **UTC 표시**(한국=+9) | `out\promo\` 확인 |
| 카드뉴스가 promo 내용으로 | public 작업영역 공유 | 카드뉴스는 `run_B_casual.bat` 재실행 |
| "Composition not found" | id는 하이픈 `Promo-kinetic` | `Promo-<style/preset>` 사용 |
| 컷이 음성과 안 맞음 | 섹션 길이를 구절 수로 균등 분배(근사) | 단어 정밀 싱크는 별도 |
| 파일 삭제 안 됨(이 환경) | 마운트가 rm 불가(rename/덮어쓰기만) | 권한 요청 후 삭제 |

## 11. 점검 결과 (2026-05-31)
- 스타일 17 + 프리셋 4 등록, 섹션별 스타일/효과음 지원, SFX 레이어, MD↔JSON 변환·왕복 무결성 OK.
- promo 코드 `tsc --noEmit` 통과(casual/newsroom 무수정). 실제 렌더는 PC가 최종 확인.
- 규제: 전 스크립트 가격 숫자 없음, 경쟁사 비방 없음.
