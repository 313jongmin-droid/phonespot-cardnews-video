# PIPELINE_SUMMARY

> 카드뉴스 → 쇼츠 영상 전체 흐름·핵심 파일 한눈 정리.
> 처음 보는 AI는 이 문서로 구조를 파악한 뒤 필요한 파일만 직접 읽는다.

---

## 입력 (카드뉴스 단계 산출물)

| 경로 | 내용 |
|---|---|
| `../articles/<slug>.json` | 카드뉴스 메타 (slug, title, cards 6장, captions_md, source_line) |
| `../images/<slug>/1.png ~ 5.png` | 카드 1~5 배경 이미지 (GPT 생성) |
| `../output/<slug>/captions.md` | 5채널 SNS 캡션 (네이버·스레드·인스타·유튜브·틱톡) |

---

## 중간 산출물 (영상 빌드 과정에서 생성)

| 경로 | 생성 시점 | 용도 |
|---|---|---|
| `output/<slug>/shorts_script.json` | `build_script.py` 실행 후 | 영상 청크·visual·TTS 메타 |
| `public/shorts_script.json` | `copy_assets.py` 실행 후 | Remotion이 읽는 위치로 복사 |
| `public/assets/` | `copy_assets.py` 실행 후 | 이미지·일러스트·로고 작업 영역 |
| `public/audio/` | `generate_tts.py` 실행 후 | edge-tts mp3 (청크별) |

---

## 출력 (최종 산출물)

| 경로 | 트랙 |
|---|---|
| `out/<slug>.mp4` | Claude 기본 빌드 |
| `out_codex/<slug>.mp4` | Codex 비교 빌드 |
| `upload/<slug>.mp4` + `upload/<slug>.md` | Claude 업로드 패키지 (mp4 + 캡션) |
| `upload_codex/<slug>.mp4` + `upload_codex/<slug>.md` | Codex 업로드 패키지 |

---

## 핵심 Python 스크립트 (`scripts/`)

| 파일 | 역할 |
|---|---|
| `build_script.py` | captions.md → shorts_script.json 변환 (청크 분할·visual 매핑·TTS 메타 작성) |
| `copy_assets.py` | shorts_script.json + 자산을 `public/`로 복사 (Remotion이 읽을 수 있게) |
| `generate_tts.py` | edge-tts로 청크별 mp3 생성 → `public/audio/` 저장 |
| `validate_polish.py` | 빌드 전 검증 (청크 길이·visual 매핑·금지어 등) |
| `list_slugs.py` | 사용 가능한 슬러그 나열 |
| `get_slug.py` | 가장 최근 슬러그 또는 환경변수에서 슬러그 추출 |
| `next_outfile.py` | 출력 mp4 파일명 결정 (중복 방지) |

---

## 핵심 Remotion 컴포넌트 (`src/`)

| 파일 | 역할 |
|---|---|
| `Root.tsx` | Remotion 엔트리 (composition 등록) |
| `Composition.tsx` | 전체 타임라인 조립 (청크 순서·전환) |
| `components/casual/CasualCard.tsx` | 캐주얼 톤 카드 (이미지 + 헤드라인) |
| `components/casual/CasualCaption.tsx` | 캐주얼 톤 자막 (하단 큰 텍스트) |
| `components/casual/Infographics.tsx` | 동적 인포그래픽 (stat / compare / timeline / pricebar / calendar / bankaccount) |
| `components/casual/Illustrations.tsx` | 정적 일러스트 로더 (`public/assets/illustrations/` 매핑) |
| `components/casual/PhonespotLogo.tsx` | 폰스팟 로고 표시 (고정 색상·위치) |

---

## 트랙별 흐름

### Claude 캐주얼 (`run_B_casual.bat`)

```
articles/<slug>.json
images/<slug>/*.png
output/<slug>/captions.md
        ↓
[build_script.py]   shorts_script.json 생성
        ↓
[copy_assets.py]    public/로 자산 복사
        ↓
[generate_tts.py]   edge-tts 청크별 mp3
        ↓
[validate_polish.py] 검증
        ↓
[Remotion render]    out/<slug>.mp4
        ↓
[upload 패키징]      upload/<slug>.mp4 + .md
```

### Codex 비교 빌드 (`run_codex_casual.bat`, `run_codex_hyperframes.bat`)
동일한 입력 → Codex 수정 컴포넌트 → `out_codex/`, `upload_codex/`로 분리 저장. 백업 파일은 `*.codexbak_*`.

---

## 자산 폴더 구조 (참고용, AI가 재귀 스캔 금지)

```
public/
├── shorts_script.json          # build_script.py 결과
├── audio/                      # edge-tts mp3 — 절대 스캔 X
├── assets/
│   ├── 1.png ~ 5.png           # 카드뉴스 원본 카드 1~5 — 직접 스캔 X
│   ├── logos/                  # 통신사·브랜드 로고 PNG
│   └── illustrations/          # 정적 일러스트 PNG
```

---

## AI가 작업할 때 보통 만지는 파일 범위

- 청크/자막 다듬기 → `output/<slug>/shorts_script.json`
- 자막 톤 규칙 변경 → `src/components/casual/CasualCaption.tsx` + `harness/CAPTION_RULES.md`
- 새 visual 추가 → `src/components/casual/Illustrations.tsx` 또는 `Infographics.tsx`
- 빌드 룰 수정 → `scripts/build_script.py`

위 외 파일은 명시적 요청 없으면 손대지 말 것.
