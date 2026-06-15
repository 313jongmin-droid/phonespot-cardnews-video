# 폰스팟 디자인 시스템 (정본)

> **출처**: `CODEX_VIDEO_DESK/dashboard/server.py` 의 `INDEX_HTML <style> :root` 토큰 추출 (패널 iOS/Apple HIG 리뉴얼, PANEL_VERSION v25~v32).
> **용도**: 패널·광고 생성기(`ads/.../generator.html`)·향후 브랜드 페이지(KT/국민/진짜폰스팟)·영상(Remotion)이 **같은 디자인 언어**를 재사용.
> 새 페이지는 아래 `:root` 토큰을 복사해 `var(--…)`로 참조. 값 변경은 **server.py `:root` 가 정본** → 여기 동기화.

---

## 색상 팔레트

**배경**
- `--system-bg` `#F2F2F7` (전체 배경) · `--card-bg` `#FFFFFF` (카드/패널) · `--secondary-bg` `#F2F2F7` · `--tertiary-bg` `#FAFAFA`

**텍스트 (라벨)**
- `--label` `#1D1D1F` (본문) · `--label-secondary` `#3C3C43` · `--label-tertiary` `#86868B` (보조/뮤트) · `--label-quaternary` `#C7C7CC` (가장 흐림)

**구분선**
- `--separator` `rgba(60,60,67,.08)` · `--separator-opaque` `#ECECEE`

**브랜드 (오렌지) — 고정**
- `--accent` `#F74B0B` (메인) · `--accent-hover` `#D63E06` · `--accent-soft` `rgba(247,75,11,.10)` (선택 배경) · `--accent-tint` `rgba(247,75,11,.05)` (hover 배경)

**시맨틱 (상태 표시 전용)**
- `--success` `#34C759` · `--warning` `#FF9500` · `--danger` `#FF3B30` · (legacy) blue `#0A84FF` · green `#1B7A3D`

---

## 모서리 (radius)
`--r-sm` 6px · `--r-md` 10px (기본) · `--r-lg` 14px · `--r-xl` 18px

## 그림자 (3단계만)
- `--shadow-subtle` `0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04),0 0 0 .5px rgba(0,0,0,.04)`
- `--shadow-card` `0 4px 16px rgba(0,0,0,.06),0 1px 3px rgba(0,0,0,.05),0 0 0 .5px rgba(0,0,0,.03)`
- `--shadow-elevated` `0 12px 32px rgba(0,0,0,.13),0 4px 12px rgba(0,0,0,.07)`

## 전환 (transition)
`--t-fast` `150ms cubic-bezier(.4,0,.2,1)` (애플 표준 ease)

---

## 타이포그래피
**폰트 스택** (Apple HIG 무드, 한글 포함):
```
'Pretendard Variable','Pretendard',-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Segoe UI','Malgun Gothic',sans-serif
```
- 굵기로 위계(타이틀 700~900 / 본문 400~600 / 뮤트 `--label-tertiary`).
- 영상(Remotion)도 Pretendard + 동일 색(오렌지/검정/흰색) — `CasualCaption` 강조색 `#F74B0B` 일치.

---

## 컴포넌트 패턴 (핵심)
- **`.btn`**: `background:var(--card-bg)`, `border:none`, `border-radius:var(--r-md)`, `min-height:78px`, `padding:14px`, 좌측 정렬, `box-shadow:var(--shadow-subtle)`. hover 시 `--accent-tint`.
- **`.row` (리스트 행)**: `:hover` → `background:var(--accent-tint)`; `.active` → `background:var(--accent-soft)`. 좌측 컬러 점 + 2줄(idx + 슬러그).
- **`.foldbar` (접기 토글)**: `background:var(--secondary-bg)`, 중앙 정렬, 캐럿. 보조 영역 단계적 노출용(기본 접힘).
- **컬러 점(상태)**: 시맨틱 색(success/warning/danger)으로 상태 표시.

## legacy alias (기존 inline `var()` 호환)
`--bg`=system-bg · `--panel`=card-bg · `--ink`=label · `--muted`=label-tertiary · `--line`=separator-opaque · `--orange`=accent · `--orange-soft`=accent-soft · `--red`=danger · `--r`=r-md · (단독) `--blue` `#0A84FF` · `--green` `#1B7A3D`

---

## 재사용 원칙
1. 새 HTML 페이지(생성기·브랜드)는 위 `:root` 블록을 **그대로 복사** → `var(--accent)` 등으로 참조. 하드코딩 hex 금지.
2. **브랜드 오렌지 `#F74B0B` 고정.** 시맨틱 색은 상태 표시에만(브랜딩 X).
3. 그림자는 3단계(`subtle`/`card`/`elevated`)만. 모서리는 4단계만. 무드 통일.
4. 값 변경은 **server.py `:root` 에서** → 이 문서 동기화(정본=server.py, 이 문서=참조 인덱스).

> ※ server.py 는 165KB 대형파일 — CSS 수정 시 **Edit 도구 금지, bash-python only**(SYSTEM_MAP I단원 규칙).
