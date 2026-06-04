# COMMANDS

> 상황별 실행 명령 모음. AI는 사장님 요청을 이 표로 매핑.

---

## 영상 빌드

### 단일 캐주얼 영상 (Claude 기본)
```cmd
run_B_casual.bat
```
- 가장 최근 슬러그 또는 환경변수 `SLUG`로 1건 빌드
- 출력: `out/<slug>.mp4` + `upload/<slug>.mp4` + `upload/<slug>.md`

### 여러 슬러그 일괄 빌드 (Claude 기본)
```cmd
run_B_batch.bat
```
- `articles/*.json` 중 빌드 가능한 슬러그 순회
- 출력: `out/` + `upload/`에 누적

### 자동화 통합 실행
```cmd
run_auto.bat
```
- ⚠ **현재 자동화는 카드뉴스 자동화가 안정화될 때까지 잠정 보류**
- 재개 시점은 `harness/ACTIVE_TASK.md`에서 확인

---

## Codex 비교 빌드

### Codex Remotion 캐주얼
```cmd
run_codex_casual.bat
```
- Codex가 수정한 컴포넌트로 빌드
- 출력: `out_codex/<slug>.mp4` + `upload_codex/<slug>.mp4`
- 원본 보존: `*.codexbak_*`

### Codex HyperFrames
```cmd
run_codex_hyperframes.bat
```
- Codex HyperFrames 실험 빌드
- 출력: `hyperframes_codex/` 폴더

---

## 검사·검증

### TypeScript 타입 검사 (렌더 전)
```cmd
node_modules\.bin\tsc.cmd --noEmit
```
- `.ts`/`.tsx` 컴포넌트 수정 후 필수

### 영상 품질 검사 (렌더 후)
```cmd
py scripts\verify_video_quality.py <mp4 path>
```
- 픽셀포맷(yuv420p), 비트레이트, 길이, 해상도 확인
- 자세한 기준은 `harness/QUALITY_RULES.md`

### 빌드 전 폴리시 검증
```cmd
py scripts\validate_polish.py
```
- 청크 길이·visual 매핑·금지어 등 사전 점검

---

## TTS / 음성

### 수동 TTS 샘플 (보이스 비교)
```cmd
py scripts\tts_voice_test.py
```
- 기본 ko-KR-SunHiNeural 외 다른 보이스(InJoonNeural / HyunsuNeural) 샘플 생성

### 청크별 mp3 재생성 (특정 슬러그)
```cmd
set SLUG=<slug>
py scripts\generate_tts.py
```

---

## 슬러그 관리

### 사용 가능한 슬러그 목록
```cmd
py scripts\list_slugs.py
```

### 가장 최근 슬러그 추출
```cmd
py scripts\get_slug.py
```

### 출력 파일명 다음 번호 추출
```cmd
py scripts\next_outfile.py
```

---

## 자산 처리

### `public/`으로 자산 복사 (Remotion 빌드 전)
```cmd
py scripts\copy_assets.py
```

### `shorts_script.json` 빌드 (captions.md → 청크 메타)
```cmd
py scripts\build_script.py
```

---

## 트러블슈팅 명령

### node_modules 재설치 필요 시
```cmd
npm install
```
- `node_modules/` 손상되면. 평소엔 건드리지 말 것.

### Remotion 캐시 클리어
```cmd
npx remotion render --clean
```

### 사용 가능한 Remotion 컴포지션 목록
```cmd
npx remotion compositions
```

### Codex folder wrapper
```cmd
codex\run_codex_remotion.bat
```
- Same Codex Remotion build, launched from the Codex-only folder.