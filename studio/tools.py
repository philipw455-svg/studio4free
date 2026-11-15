"""Small helpers for the hand work on a clip: read the words, fix misheard ones, and look at a rendered clip."""
import re
import shutil
import subprocess
import sys

from .common import job_dir, read_json, write_json


def words(job: str, start: float, end: float) -> None:
    """Print every word between two source times as word@seconds, to set cut points and to find words to fix."""
    t = read_json(job_dir(job) / "transcript.json")
    row = [f"{w['w']}@{w['s']:.2f}" for s in t["segments"] for w in s["words"] if start - 1.0 <= w["s"] <= end + 1.0]
    print(" ".join(row))


def fix(job: str, edits: list) -> None:
    """Correct misheard words in transcript.json. Each edit is "seconds|old|new": the word that starts at that source time.
    An empty new deletes the word. The first run keeps the untouched transcript as transcript.orig.json.
    It also joins number parts the transcriber split, such as "$100" and ",000"."""
    d = job_dir(job)
    path = d / "transcript.json"
    if not (d / "transcript.orig.json").exists():
        shutil.copyfile(path, d / "transcript.orig.json")
    t = read_json(path)
    missed = 0
    for spec in edits:
        at, old, new = spec.split("|")
        hit = False
        for seg in t["segments"]:
            for i, w in enumerate(seg["words"]):
                if abs(w["s"] - float(at)) < 0.02 and w["w"] == old:
                    hit = True
                    if new:
                        w["w"] = new
                    else:
                        del seg["words"][i]
                    break
            if hit:
                break
        if not hit:
            missed += 1
            print(f"Not found: {spec}")
    joined = 0
    for seg in t["segments"]:
        ws, i = seg["words"], 1
        while i < len(ws):
            if re.match(r"^(,\d|-\w)", ws[i]["w"]):
                ws[i - 1]["w"] += ws[i]["w"]
                ws[i - 1]["e"] = ws[i]["e"]
                del ws[i]
                joined += 1
            else:
                i += 1
    write_json(path, t)
    print(f"Fixed {len(edits) - missed} of {len(edits)} words. Joined {joined} split numbers.")
    if missed:
        sys.exit(1)


def sheet(job: str, only: list | None = None, frames: int = 20) -> None:
    """Save a sheet of evenly spaced frames of each rendered clip in jobs/<name>/sheets/, to check it by eye."""
    d = job_dir(job)
    out_dir = d / "sheets"
    out_dir.mkdir(exist_ok=True)
    for clip in sorted((d / "clips").glob("clip[0-9][0-9].mp4")):
        n = int(clip.stem[4:])
        if only and n not in only:
            continue
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
                                   capture_output=True, text=True).stdout.strip())
        inputs, labels = [], []
        for i in range(frames):
            at = 0.4 + (dur - 0.8) * i / (frames - 1)
            inputs += ["-ss", f"{at:.2f}", "-i", str(clip)]
            labels.append(f"[{i}:v]trim=end_frame=1,scale=240:-2,"
                          f"drawtext=text='{at:.1f}':x=4:y=4:fontsize=18:fontcolor=white:box=1:boxcolor=black[s{i}]")
        cols = 10
        layout = "|".join(f"{(i % cols) * 240}_{(i // cols) * 426}" for i in range(frames))
        graph = ";".join(labels) + ";" + "".join(f"[s{i}]" for i in range(frames)) + f"xstack=inputs={frames}:layout={layout}[v]"
        target = out_dir / f"clip{n:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-frames:v", "1", str(target)])
        print(f"Clip {n}: {dur:.1f}s -> {target}", flush=True)
