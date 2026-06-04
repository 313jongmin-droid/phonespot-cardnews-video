# ACTIVE_TASK

> 현재 작업 대상·상태를 짧게 기록. 새 작업 시작 시 AI/사람이 가장 먼저 갱신.

---

## 현재 상태

```yaml
current_slug:        promo_jeongchalje
current_track:       promo          # NEW: 타이포/모션그래픽 홍보영상 (카드뉴스영상과 다른 결)
status:              building
requested_by_user:   "엔진 기생 + 홍보영상은 타이포/모션그래픽으로 완전히 다른 결"
last_action:         "promo 스타일 레지스트리 구축(kinetic/reveal) + Root에 Promo_<style> 자동 등록 + run_promo.bat 스타일 선택형. promo코드 단독 tsc 통과"
next_action:         "run_promo.bat 실행→스타일 선택(kinetic/reveal)→out/promo_jeongchalje_<date>_<style>.mp4. 새 스타일은 styles/<id>.tsx + registry 한 줄"
do_not_touch:                        # promo 작업은 캐주얼/뉴스룸 트랙 무수정
  - src/components/casual/
  - src/components/HookCard.tsx
  - src/components/FactCard.tsx
  - src/Composition.tsx
  - codex/
  - out_codex/
```

---

## 필드 설명

- **current_slug** — 작업 중인 슬러그 (예: `galaxy_price_hike_europe_2026`)
- **current_track** — 빌드 트랙:
  - `casual` — Claude 기본 캐주얼 (실행: `run_B_casual.bat`)
  - `newsroom` — Claude 뉴스룸 톤 (있다면)
  - `codex_remotion` — Codex Remotion 비교 빌드
  - `hyperframes` — Codex HyperFrames 비교 빌드
- **status** — 작업 단계:
  - `idle` — 아무것도 안 함
  - `collecting` — 카드뉴스에서 자산 수집 중
  - `building` — Remotion 빌드 진행 중
  - `reviewing` — 사장님 검토 대기 또는 진행 중
  - `blocked` — 막힌 상태 (이유는 `next_action`에 기록)
- **requested_by_user** — 사용자가 이번 작업을 지시한 한 줄 요약
- **last_action** — 마지막으로 수행한 작업 한 줄
- **next_action** — 다음 해야 할 작업 한 줄
- **do_not_touch** — 이번 작업에서 손대면 안 되는 파일·폴더 리스트

---

## 예시

```yaml
current_slug:        galaxy_price_hike_europe_2026
current_track:       casual
status:              building
requested_by_user:   "갤럭시 가격 인상 토픽 쇼츠 빌드"
last_action:         "captions.md 청크 분할 완료 + shorts_script.json 생성"
next_action:         "run_B_casual.bat 실행해서 out/<slug>.mp4 만들기"
do_not_touch:
  - public/assets/illustrations/
  - upload_codex/
```
