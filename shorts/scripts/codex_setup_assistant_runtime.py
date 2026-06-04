# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
DESK = ROOT / "CODEX_VIDEO_DESK"
RUNTIME = Path(os.environ.get("PHONESPOT_LOCAL_RUNTIME", Path.home() / "AppData" / "Local" / "PhoneSpotCodexVideo"))
PORT = "4901"


def run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print("")
    print("[run] " + " ".join(command))
    result = subprocess.run(command, cwd=str(cwd) if cwd else None, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode:
        raise RuntimeError(f"command failed: {' '.join(command)}")
    return result


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def winget_exists() -> bool:
    return command_exists("winget")


def install_with_winget(package_id: str, label: str) -> bool:
    if not winget_exists():
        print(f"[MISS] winget not available. Cannot auto install {label}.")
        return False
    print(f"[install] {label} via winget")
    result = run([
        "winget", "install", "--id", package_id,
        "--accept-source-agreements", "--accept-package-agreements",
        "--silent"
    ], check=False)
    return result.returncode == 0


def ensure_node() -> None:
    if command_exists("node") and command_exists("npm"):
        run(["node", "-v"], check=False)
        run(["npm", "-v"], check=False)
        print("[OK] Node.js/npm ready")
        return
    ok = install_with_winget("OpenJS.NodeJS.LTS", "Node.js LTS")
    if not ok or not command_exists("node") or not command_exists("npm"):
        raise RuntimeError("Node.js/npm missing. Install Node.js LTS, reopen this setup, and run again.")
    print("[OK] Node.js/npm installed")


def ensure_python() -> None:
    if command_exists("python"):
        run(["python", "--version"], check=False)
        print("[OK] Python ready")
        return
    ok = install_with_winget("Python.Python.3.12", "Python 3")
    if not ok or not command_exists("python"):
        raise RuntimeError("Python missing. Install Python 3, reopen this setup, and run again.")
    print("[OK] Python installed")


def ensure_ffmpeg() -> None:
    if command_exists("ffmpeg"):
        run(["ffmpeg", "-version"], check=False)
        print("[OK] FFmpeg ready")
        return
    ok = install_with_winget("Gyan.FFmpeg", "FFmpeg")
    if not ok:
        print("[WARN] FFmpeg auto install failed. Remotion may still use bundled ffmpeg, but system FFmpeg is recommended.")
        return
    print("[OK] FFmpeg installed")


def ensure_edge_tts() -> None:
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=False)
    run([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "edge-tts"])
    print("[OK] edge-tts ready")


def ensure_npm_dependencies() -> None:
    if not (SHORTS / "package.json").exists():
        raise RuntimeError(f"package.json not found: {SHORTS / 'package.json'}")
    run(["npm", "install", "--no-audit", "--no-fund"], cwd=SHORTS)
    print("[OK] npm dependencies ready")


def ensure_runtime_dirs() -> None:
    for path in [
        RUNTIME,
        RUNTIME / "temp" / "_raw",
        RUNTIME / "logs",
        DESK / "RESULTS",
        DESK / "ILLUSTRATION_DROP",
        DESK / "TEMP" / "panel_logs",
    ]:
        path.mkdir(parents=True, exist_ok=True)
        print(f"[OK] dir: {path}")


def ensure_panel_shortcuts() -> None:
    script = DESK / "dashboard" / "create_desktop_shortcuts.ps1"
    if script.exists():
        run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=False)
    else:
        print("[WARN] shortcut script missing")


def smoke_test() -> None:
    print("")
    print("----- smoke test -----")
    run([sys.executable, str(SHORTS / "scripts" / "list_slugs.py")], cwd=SHORTS, check=False)
    if not (DESK / "00_PHONE_SPOT_PANEL.bat").exists():
        raise RuntimeError("00_PHONE_SPOT_PANEL.bat missing")
    if not (DESK / "dashboard" / "start_hidden.ps1").exists():
        raise RuntimeError("dashboard/start_hidden.ps1 missing")
    print(f"[OK] panel URL will be http://localhost:{PORT}/")


def main() -> int:
    print("=" * 60)
    print(" PhoneSpot Assistant PC Full Setup")
    print("=" * 60)
    print(f"Project: {ROOT}")
    print("")
    print("This PC will render videos locally.")
    print("Codex is not required on this assistant PC.")
    print("")
    try:
        ensure_runtime_dirs()
        ensure_node()
        ensure_python()
        ensure_ffmpeg()
        ensure_edge_tts()
        ensure_npm_dependencies()
        ensure_panel_shortcuts()
        smoke_test()
    except Exception as exc:
        print("")
        print(f"[ERROR] {exc}")
        print("")
        print("If Node.js or Python was installed just now, close this window,")
        print("open a new window, and run 00_SETUP_ASSISTANT_PC.bat again.")
        return 1
    print("")
    print("[OK] Assistant PC setup complete.")
    print("Next: run 00_PHONE_SPOT_PANEL.bat from CODEX_VIDEO_DESK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
