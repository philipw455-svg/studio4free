"""Step 1: get the source video into the job folder as source.mp4."""
import shutil
import sys
import urllib.request
from pathlib import Path

from .common import job_dir, probe, run, write_json

YT_HOSTS = ("youtube.com", "youtu.be")

BLOCKED = """YouTube refused this download and asked for a sign-in check.
YouTube does this to cloud servers. Do not try to get around the check.
Run this same fetch step on a home computer, or put the video file in the job folder as source.mp4."""


def channel_of(link: str) -> dict:
    """Ask YouTube's public oEmbed service who published a video. This works from cloud servers too."""
    import json
    import urllib.parse
    try:
        url = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(link, safe="")
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "clip-studio/1.0"}), timeout=20) as r:
            j = json.loads(r.read())
        handle = j.get("author_url", "").replace("https://www.", "").replace("https://", "")
        return {"channel": j.get("author_name", ""), "credit": handle, "videoTitle": j.get("title", "")}
    except Exception:
        return {}


def fetch(job: str, source: str) -> Path:
    d = job_dir(job)
    out = d / "source.mp4"
    who = channel_of(source) if any(h in source for h in YT_HOSTS) else {}
    if who:
        write_json(d / "channel.json", who)
        print(f"Source channel: {who['channel']} ({who['credit']})")
    if any(h in source for h in YT_HOSTS):
        if not shutil.which("yt-dlp"):
            sys.exit("yt-dlp is missing. Run: pip install -r requirements.txt")
        import subprocess
        p = subprocess.run(
            ["yt-dlp", "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
             "--merge-output-format", "mp4", "-o", str(out), source],
            capture_output=True, text=True)
        if p.returncode:
            err = (p.stderr or "").strip()
            if "confirm you" in err and "not a bot" in err:
                sys.exit(BLOCKED)
            sys.exit("The download failed:\n" + "\n".join(err.splitlines()[-6:]))
    elif source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "clip-studio/1.0"})
        with urllib.request.urlopen(req) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
    else:
        src = Path(source).expanduser()
        if not src.exists():
            sys.exit(f"No file at {src}")
        if src.suffix.lower() == ".mp4":
            shutil.copyfile(src, out)
        else:
            run(["ffmpeg", "-y", "-i", src, "-c:v", "libx264", "-crf", "18", "-c:a", "aac", out])
    info = probe(out)
    write_json(d / "source.json", {"source": source, **who, **info})
    print(f"Saved {out} ({info['width']}x{info['height']}, {info['duration']:.0f} seconds)")
    return out
