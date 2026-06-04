# last_build

> 마지막 영상 빌드 기록. 빌드 직후 AI 또는 사람이 갱신.

---

```yaml
date:           ""              # 예: 2026-05-28 02:35
slug:           ""              # 예: galaxy_price_hike_europe_2026
track:          ""              # casual / newsroom / codex_remotion / hyperframes
command:        ""              # 예: run_B_casual.bat
output_file:    ""              # 예: out/galaxy_price_hike_europe_2026.mp4
upload_file:    ""              # 예: upload/galaxy_price_hike_europe_2026.mp4
duration_sec:   0
file_size_mb:   0
pixel_format:   ""              # yuv420p 기대
bitrate_mbps:   0
quality_check:                  # verify_video_quality.py 결과
  pass:         false
  failed_items: []
notes:          ""              # 자유 메모 (이슈·관찰사항)
```

---

## 채우기 가이드

- **date** — ISO 형식 (`YYYY-MM-DD HH:MM`)
- **slug / track** — `harness/ACTIVE_TASK.md`의 현재 값과 동기화
- **command** — 어떤 .bat 실행했는지
- **output_file / upload_file** — 실제 생성 경로
- **duration_sec** — ffprobe로 확인 가능 (`py scripts\verify_video_quality.py <mp4>` 출력 참조)
- **file_size_mb** — `out/<slug>.mp4` 크기
- **pixel_format / bitrate_mbps** — verify 스크립트 출력
- **quality_check** — `pass: true/false` + 실패 항목 리스트
- **notes** — 빌드 중 발견한 이슈, 다음에 고칠 점 등

---

## 예시

```yaml
date:           2026-05-28 02:35
slug:           galaxy_price_hike_europe_2026
track:          casual
command:        run_B_casual.bat
output_file:    out/galaxy_price_hike_europe_2026.mp4
upload_file:    upload/galaxy_price_hike_europe_2026.mp4
duration_sec:   52
file_size_mb:   9.4
pixel_format:   yuv420p
bitrate_mbps:   8.2
quality_check:
  pass:         true
  failed_items: []
notes:          "TTS 속도 +40%. 자막 청크 5번째 약간 길어서 다음번 줄이는 게 좋음."
```

---

## [promo] promo_jeongchalje — 2026-05-29 (Claude, additive)

- 트랙 신규: **promo** (타이포/모션그래픽). 카드뉴스영상(casual)과 다른 결.
- 추가 파일(캐주얼/뉴스룸 무수정):
  - `src/components/promo/PromoShort.tsx` (신규)
  - `src/Root.tsx` — `PromoShort` 컴포지션만 추가 등록 (백업: `src/Root.tsx.promobak_*`)
  - `promo/promo_jeongchalje.json` — 홍보 스크립트(훅+팩트3+CTA, 가격 숫자 없음)
  - `run_promo.bat` — 카드뉴스 입력 없이 promo 스크립트→public→TTS→PromoShort 렌더
- 검증: `tsc --noEmit` 통과 (casual/newsroom/promo 전부 컴파일 OK).
- 렌더(사람): `run_promo.bat` → `out/promo_jeongchalje_<date>_promo.mp4`
- 주의: promo 빌드는 public/ 작업영역을 덮어씀 → 카드뉴스는 `run_B_casual.bat` 재실행으로 복구.
- 규제 메모: "지원금" 표현은 일반 수준 유지(숫자 없음), "허위매물"은 업계 일반 비유로만(특정 업체 비방 금지).

## [promo] 스타일 스위처 구조 — 2026-05-29 업데이트

- 구조: 스타일 = 플러그인. `src/components/promo/styles/`
  - `shared.tsx` (팔레트·변주·CtaBlock·헬퍼·PromoStyle 인터페이스)
  - `kinetic.tsx` (비트컷), `reveal.tsx` (줄 리빌)
  - `registry.ts` (PROMO_STYLES 배열)
- `PromoShort.tsx` = 디스패처(promoStyle prop으로 스타일 선택, 오디오는 공통 재생).
- `Root.tsx` = PROMO_STYLES 순회하여 `Promo_<id>` 컴포지션 자동 등록.
- `run_promo.bat` = 실행 시 스타일 선택(kinetic/reveal) → `out/promo_jeongchalje_<date>_<style>.mp4`.
- 새 스타일 추가법: `styles/<id>.tsx`에 PromoStyle 1개 export + `registry.ts`에 한 줄 → 컴포지션·실행 자동 반영.
- 검증: promo 코드 단독 `tsc --noEmit` 통과. (풀프로젝트 tsc는 샌드박스 마운트의 stale public/shorts_script.json 때문에 일시 에러 — 호스트 원본 386줄 정상, 무관.)
