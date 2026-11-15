"""Check that everything the studio needs is installed, and say in plain words what cannot run without it."""
import importlib.util
import json
import shutil
import subprocess

from . import faces


def _has_ass() -> bool:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return any(line.split()[1:2] == ["ass"] for line in out.splitlines())


def _has_zones() -> bool:
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("America/Chicago")
        return True
    except Exception:
        return False


def check() -> dict:
    """{"ok": true or false, "missing": [names], "cannot": [one plain sentence for each feature that cannot run]}"""
    mod = lambda name: importlib.util.find_spec(name) is not None
    ffmpeg = shutil.which("ffmpeg") is not None
    rows = [
        ("ffmpeg", ffmpeg, "Clips cannot be cut or re-cut: ffmpeg is missing."),
        ("ffprobe", shutil.which("ffprobe") is not None, "Videos cannot be measured, so no clip can be cut: ffprobe is missing."),
        # Without ffmpeg there is nothing to ask about its filters, so only ffmpeg is listed then.
        ("libass", not ffmpeg or _has_ass(), "Captions cannot be drawn on clips: this ffmpeg has no ass subtitle filter (libass)."),
        ("yt-dlp", shutil.which("yt-dlp") is not None, "YouTube videos cannot be downloaded: yt-dlp is missing."),
        ("faster-whisper", mod("faster_whisper"), "Videos cannot be transcribed, so there are no words to choose clips from: faster-whisper is missing."),
        ("onnxruntime", mod("onnxruntime") and mod("numpy"), "Captions cannot be kept off faces: onnxruntime or numpy is missing."),
        ("face model", faces.MODEL.exists(), "Captions cannot be kept off faces: the face model file is missing."),
        ("Pillow", mod("PIL"), "Titles, overlays and brand tags cannot be drawn: Pillow is missing."),
        ("tzdata", _has_zones(), "Post times cannot be planned: the time zone data (tzdata) is missing."),
    ]
    missing = [name for name, ok, _ in rows if not ok]
    return {"ok": not missing, "missing": missing, "cannot": [why for _, ok, why in rows if not ok]}


def doctor(as_json: bool = False) -> None:
    r = check()
    if as_json:
        print(json.dumps(r))
    elif r["ok"]:
        print("Everything the studio needs is installed.")
    else:
        print("Missing: " + ", ".join(r["missing"]))
        for line in r["cannot"]:
            print("- " + line)
