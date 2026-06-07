# -*- coding: utf-8 -*-
"""
PhoneSpot 작업 큐  <->  Google Sheets 동기화 브리지

이 파일은 기존 코드(server.py, codex_work_queue.py, Code.gs)를 전혀 건드리지 않는
"추가 파일" 입니다. 단독으로 실행되며, 시트를 작업 큐의 "마스터"로 만들어
원격에 있는 여러 PC 가 같은 큐를 공유하게 합니다.

필드 소유권 (codex_work_queue.py 의 모델 그대로):
  - 파생 필드(각 PC 가 로컬 파일 스캔으로 계산) -> 시트로 PUSH (공유 표시용)
      date, title, cardnews_status, render_status,
      illustration_request_status, result_folder
  - 협업 필드(사람이 시트에서 편집, PRESERVE_COLUMNS) -> 시트에서 PULL (마스터)
      assignee, review_status, publish_youtube/instagram/tiktok, notes
  => 필드마다 쓰는 주체가 하나라 동시 편집 충돌이 구조적으로 없음.

사용:
  python sheets_sync.py status     # 설정/연결 확인 (쓰기 없음)
  python sheets_sync.py push       # 로컬 파생 상태를 시트로 올림
  python sheets_sync.py pull       # 시트의 협업 필드를 로컬 JSON 에 반영
  python sheets_sync.py sync       # push 후 pull (기본 권장)
  python sheets_sync.py migrate    # 최초 1회: 로컬의 모든 필드를 시트에 씨딩

엔드포인트 미설정 시 어떤 명령도 아무것도 바꾸지 않고 안내만 출력하고 종료합니다.
(그래서 설정 전에 실수로 실행해도 무해합니다.)
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESK = HERE.parent
QUEUE = DESK / "WORK_QUEUE"
QUEUE_JSON = QUEUE / "phonespot_work_queue.json"
ENDPOINT_FILE = HERE / "sheets_endpoint.txt"

# 파생 필드: 로컬 JSON 키 -> 시트 헤더
DERIVED_MAP = {
    "date": "날짜",
    "title": "제목",
    "cardnews_status": "카드뉴스 상태",
    "render_status": "영상 상태",
    "illustration_request_status": "필요 일러스트",
    "result_folder": "결과",
}

# 협업 필드: 시트 헤더 -> 로컬 JSON 키
COORDINATION_MAP = {
    "담당자": "assignee",
    "검수": "review_status",
    "유튜브": "publish_youtube",
    "인스타": "publish_instagram",
    "틱톡": "publish_tiktok",
    "메모": "notes",
}
# 역방향 (migrate 용): 로컬 JSON 키 -> 시트 헤더
COORDINATION_MAP_REV = {v: k for k, v in COORDINATION_MAP.items()}


def log(msg: str) -> None:
    print(f"[sheets_sync] {msg}")


def read_endpoint() -> tuple[str, str] | None:
    """sheets_endpoint.txt 에서 (url, token) 읽기. 없으면 None."""
    if not ENDPOINT_FILE.exists():
        return None
    lines = []
    for raw in ENDPOINT_FILE.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    if not lines:
        return None
    url = lines[0]
    token = lines[1] if len(lines) > 1 else ""
    if not url.lower().startswith("http"):
        return None
    return url, token


def load_local() -> dict:
    if not QUEUE_JSON.exists():
        return {"version": 1, "rows": []}
    try:
        data = json.loads(QUEUE_JSON.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {"version": 1, "rows": []}
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        return {"version": 1, "rows": []}
    return data


def save_local(data: dict) -> None:
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    QUEUE.mkdir(parents=True, exist_ok=True)
    QUEUE_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    # 가능하면 tsv/csv/md 도 같이 갱신 (codex_work_queue 의 작성기 재사용).
    try:
        scripts_dir = DESK.parent / "shorts" / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import codex_work_queue as cwq  # type: ignore
        rows = data.get("rows", [])
        cwq.write_csv(QUEUE / "phonespot_work_queue.csv", rows)
        cwq.write_tsv(QUEUE / "phonespot_work_queue.tsv", rows)
        cwq.write_markdown(QUEUE / "phonespot_work_queue.md", rows)
    except Exception as exc:  # 보조 포맷 실패는 치명적이지 않음
        log(f"(참고) tsv/csv/md 보조 갱신 생략: {exc}")


def http_json(url: str, payload: dict, timeout: int = 30) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    text = text.strip()
    if not text.startswith("{") and not text.startswith("["):
        raise RuntimeError(
            "JSON 이 아닌 응답을 받았습니다. 웹앱 배포 권한이 '링크가 있는 모든 사용자'인지, "
            "URL 이 .../exec 인지 확인하세요. 응답 앞부분: " + text[:120]
        )
    return json.loads(text)


def fetch_sheet_rows(url: str, token: str) -> list[dict]:
    resp = http_json(url, {"op": "pull", "token": token})
    if not resp.get("ok"):
        raise RuntimeError(f"시트 읽기 실패: {resp.get('error')}")
    return resp.get("rows", [])


def push_rows(url: str, token: str, items: list[dict], op: str = "push") -> int:
    resp = http_json(url, {"op": op, "token": token, "items": items})
    if not resp.get("ok"):
        raise RuntimeError(f"시트 쓰기 실패: {resp.get('error')}")
    return int(resp.get("changed", 0))


def build_push_items(rows: list[dict], include_coordination: bool) -> list[dict]:
    items = []
    for row in rows:
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        fields = {}
        for json_key, header in DERIVED_MAP.items():
            fields[header] = row.get(json_key, "")
        if include_coordination:
            for json_key, header in COORDINATION_MAP_REV.items():
                fields[header] = row.get(json_key, "")
        items.append({"slug": slug, "fields": fields})
    return items


def cmd_status(url: str, token: str) -> int:
    log(f"엔드포인트: {url}")
    log(f"토큰: {'설정됨' if token else '(없음 - 보안상 설정 권장)'}")
    try:
        rows = fetch_sheet_rows(url, token)
        log(f"연결 OK. 시트 행 수: {len(rows)}")
        local = load_local().get("rows", [])
        log(f"로컬 큐 행 수: {len(local)}")
        return 0
    except Exception as exc:
        log(f"연결 실패: {exc}")
        return 1


def cmd_push(url: str, token: str) -> int:
    rows = load_local().get("rows", [])
    items = build_push_items(rows, include_coordination=False)
    changed = push_rows(url, token, items, op="push")
    log(f"파생 상태 {changed}행을 시트로 올렸습니다.")
    return 0


def cmd_migrate(url: str, token: str) -> int:
    rows = load_local().get("rows", [])
    items = build_push_items(rows, include_coordination=True)
    changed = push_rows(url, token, items, op="migrate")
    log(f"최초 씨딩: {changed}행(협업 필드 포함)을 시트에 기록했습니다.")
    return 0


def cmd_pull(url: str, token: str) -> int:
    sheet_rows = fetch_sheet_rows(url, token)
    by_slug = {str(r.get("슬러그") or "").strip(): r for r in sheet_rows if r.get("슬러그")}
    data = load_local()
    rows = data.get("rows", [])
    applied = 0
    for row in rows:
        slug = str(row.get("slug") or "").strip()
        if not slug or slug not in by_slug:
            continue
        sheet_row = by_slug[slug]
        touched = False
        for header, json_key in COORDINATION_MAP.items():
            if header in sheet_row:
                value = sheet_row.get(header)
                value = "" if value is None else str(value)
                if row.get(json_key, "") != value:
                    row[json_key] = value
                    touched = True
        if touched:
            applied += 1
    save_local(data)
    log(f"시트의 협업 필드를 로컬 {applied}행에 반영했습니다.")
    return 0


def cmd_sync(url: str, token: str) -> int:
    rc = cmd_push(url, token)
    if rc != 0:
        return rc
    return cmd_pull(url, token)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "sync").strip().lower()
    ep = read_endpoint()
    if ep is None:
        log("엔드포인트가 설정되지 않았습니다. 아무것도 바꾸지 않고 종료합니다.")
        log(f"설정 파일: {ENDPOINT_FILE}")
        log("sheets_endpoint.example.txt 를 복사해 sheets_endpoint.txt 로 만들고 URL/토큰을 채우세요.")
        return 0
    url, token = ep
    try:
        if cmd == "status":
            return cmd_status(url, token)
        if cmd == "push":
            return cmd_push(url, token)
        if cmd == "pull":
            return cmd_pull(url, token)
        if cmd == "migrate":
            return cmd_migrate(url, token)
        if cmd == "sync":
            return cmd_sync(url, token)
        log(f"알 수 없는 명령: {cmd} (status|push|pull|sync|migrate)")
        return 2
    except urllib.error.URLError as exc:
        log(f"네트워크 오류: {exc}")
        return 1
    except Exception as exc:
        log(f"오류: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
