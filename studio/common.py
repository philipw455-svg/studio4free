"""Shared helpers: job folders, JSON files, running commands."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "jobs"
FONTS = ROOT / "assets" / "fonts"


def job_dir(name: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-")
    if not safe:
        sys.exit("The job needs a name made of letters or digits.")
    d = JOBS / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(cmd, **kw):
    """Run a command and stop with its last lines if it fails."""
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if p.returncode:
        tail = "\n".join((p.stderr or p.stdout).strip().splitlines()[-12:])
        sys.exit(f"Command failed: {cmd[0]}\n{tail}")
    return p.stdout


def probe(path: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height:format=duration", "-of", "json", path])
    j = json.loads(out)
    s = (j.get("streams") or [{}])[0]
    return {"width": int(s.get("width", 0)), "height": int(s.get("height", 0)),
            "duration": float(j.get("format", {}).get("duration", 0) or 0)}


def clock(t: float) -> str:
    t = max(0.0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:04.1f}" if h else f"{m:02d}:{s:04.1f}"
