# 폰스팟 뉴스 쇼츠 (Phase 1)

> **AI 작업자(Claude / Codex 등)는 먼저 `harness/README_FOR_AI.md`를 읽을 것.** 전체 폴더 재귀 탐색 금지.

카드뉴스 자동화 결과물 1편을 입력으로 받아, 1080×1920 세로 쇼츠 뉴스 영상(.mp4)을 자동 생성합니다.

기술 스택: **Remotion(React) + edge-tts(무료 TTS) + ChatGPT 이미지(시네마틱)**. 전체 비용 0원.

## 입력 자산 (영상 1편당)

| 자산 | 위치 | 필수 | 출처 |
|---|---|---|---|
| shorts_script.json | `../output/<slug>/shorts_script.json` | ✅ | 수동 작성 또는 카드뉴스 자동화 확장 |
| AI 시네마틱 이미지 3장 | `../images/<slug>/hero.png`, `camera_macro.png`, `price_compare.png` | ✅ | 종민님이 ChatGPT에서 생성 |
| AI 표지 이미지 | `../images/<slug>/cover.png` | ✅ | 카드뉴스 시스템이 이미 생성 |
| 카드뉴스 결과 6장 | `../output/<slug>/9x16/card_1.jpg ~ card_6.jpg` | ✅ | 카드뉴스 자동화가 이미 생성 |

## 사전 요구사항 (1회만)

1. **Node.js LTS**: https://nodejs.org/en/download
2. **Python 3.10+**: 카드뉴스 자동화에 이미 사용 중인 환경
3. 인터넷 연결: 첫 실행 시 Chromium ~300MB 자동 다운로드

## 실행

```cmd
run.bat
```

기본 슬러그는 `galaxy_a37_korea_may_launch`. 다른 슬러그로 실행:

```cmd
run.bat ios26_5_rcs_2026
```

## 진행 단계 (run.bat 내부)

| 단계 | 작업 | 첫 실행 | 이후 실행 |
|---|---|---|---|
| 1 | npm install | 1~2분 | 스킵 |
| 2 | edge-tts pip install | 10초 | 빠른 체크 |
| 3 | 자산 복사 (이미지/스크립트 → public/) | 5초 | 5초 |
| 4 | TTS 생성 (7개 mp3) | 30~60초 | 30~60초 |
| 5 | Remotion 렌더 (Chromium 첫 다운로드 포함) | 5~10분 | 1~2분 |

**총 소요 시간**: 첫 실행 7~15분 / 이후 2~3분

## 결과물

- `out/shorts.mp4` — 1080×1920, 30fps, H.264, 약 35~40초
- ko-KR-SunHiNeural 보이스
- Karaoke 자막 (단어별 등장 + 강조 단어 오렌지 박스)
- ChatGPT 시네마틱 이미지 풀스크린 배경
- 카드뉴스 결과물을 일부 fact에 활용
- Channel intro/outro 자동

## 폴더 구조

```
phonespot-news-shorts/
├── package.json
├── tsconfig.json
├── run.bat
├── README.md
├── src/
│   ├── index.ts
│   ├── Root.tsx                  # Composition + audio 길이 자동 측정
│   ├── Composition.tsx           # 메인 시퀀스 조합
│   └── components/
│       ├── ChannelBadge.tsx      # 좌상단 채널 라벨 + 진행 표시
│       ├── ChannelIntro.tsx      # 0.6초 인트로
│       ├── ChannelOutro.tsx      # 1.0초 아웃트로 + 구독 유도
│       ├── HookCard.tsx          # 후킹 헤드라인 (0~3초)
│       ├── FactCard.tsx          # 5개 팩트 카드
│       ├── CtaCard.tsx           # 매장 안내 (마지막)
│       ├── KaraokeSubtitle.tsx   # 단어별 자막 (강조 박스)
│       └── StatBlock.tsx         # 큰 숫자 강조 박스
├── scripts/
│   ├── copy_assets.py            # 슬러그별 자산을 public/으로 복사
│   └── generate_tts.py           # edge-tts로 mp3 7개 생성
├── public/                       # Remotion 정적 자원 (자동 채워짐)
│   ├── shorts_script.json
│   ├── assets/*.png *.jpg        # 배경 이미지
│   └── audio/*.mp3               # TTS
└── out/
    └── shorts.mp4                # 최종 결과
```

## 콘텐츠 수정

### TTS 멘트 / 자막 / Stat 수정
`../output/<slug>/shorts_script.json` 편집 후 `run.bat` 재실행.

### 컴포넌트 디자인 수정
`src/components/*.tsx` 직접 편집.

### 미리보기 (디자인 조정 시)
```cmd
npx remotion studio src/index.ts
```
브라우저에서 실시간 프리뷰. 코드 저장하면 자동 갱신.

## 트러블슈팅

| 증상 | 해결 |
|---|---|
| `node`/`npx` 없음 | nodejs.org에서 LTS 설치 후 새 명령창 |
| `python` 없음 | python.org 3.10+ 설치 |
| edge-tts 401/403 | 회사망/학교망 차단. 모바일 핫스팟 시도 |
| Chromium 다운로드 실패 | 방화벽 확인. 재시도 |
| 이미지 누락 | `images/<slug>/` 또는 `output/<slug>/9x16/`에 파일 확인 |
| 한국어 폰트 깨짐 | Windows 기본 한글 폰트 fallback 정상 동작. Pretendard 추가는 web font 등록 필요 |

## 비용

| 구성 | 비용 |
|---|---|
| Remotion (개인/3인 이하) | 0원 |
| edge-tts | 0원 |
| ChatGPT 이미지 | 0원 (무료 플랜) 또는 $20/월 (Plus) |
| Pretendard 폰트 | 0원 (OFL) |
| 호스팅/처리 | 0원 (로컬) |

## 다음 단계

이 시범 영상의 비주얼/사운드/길이 평가 후:
- 만족 → 다른 카드뉴스 슬러그로 자동 변환 (run.bat <slug>)
- 디자인 수정 → `src/components/*.tsx`
- 음성 변경 → `scripts/generate_tts.py`의 VOICE 상수
- BGM 추가 → public/bgm/에 mp3 + Composition.tsx에서 `<Audio>` 추가
