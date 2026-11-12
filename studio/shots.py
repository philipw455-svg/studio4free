"""A helper for setting each clip's frame by hand: where the camera cuts are, and one picture of every shot."""
import re
import subprocess

from .common import job_dir, read_json


def camera_cuts(source, start: float, dur: float, limit: float = 0.12) -> list:
    """Seconds into the clip at which the camera changes."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(source), "-an",
         "-vf", f"scale=480:-2,select='gt(scene,{limit})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True)
    return [round(float(x), 3) for x in re.findall(r"pts_time:([0-9.]+)", p.stderr)]


def shots(job: str, only: list | None = None) -> None:
    """Print the camera cuts of each clip and save a sheet with one frame per shot, ruled every tenth of the width and of the height.
    Read where the speaker sits from the sheet, then write `focus` steps on the clip in clips.json.
    A speaker at x of the width needs focus (x - 0.158) / 0.684 on a 16:9 source that fills a 9:16 frame."""
    d = job_dir(job)
    out_dir = d / "shots"
    out_dir.mkdir(exist_ok=True)
    for clip in read_json(d / "clips.json")["clips"]:
        n = int(clip["n"])
        if only and n not in only:
            continue
        start, dur = float(clip["start"]), float(clip["end"]) - float(clip["start"])
        bounds = [0.0] + camera_cuts(d / "source.mp4", start, dur) + [dur]
        inputs, labels = [], []
        for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
            inputs += ["-ss", f"{start + (a + b) / 2:.3f}", "-i", str(d / "source.mp4")]
            labels.append(f"[{i}:v]trim=end_frame=1,scale=480:-2,drawgrid=w=48:h=27:t=1:c=yellow@0.55,"
                          f"drawtext=text='{a:.2f}':x=6:y=6:fontsize=22:fontcolor=white:box=1:boxcolor=black[s{i}]")
        cols = min(5, len(labels))
        sheet = out_dir / f"clip{n:02d}.jpg"
        graph = ";".join(labels) + ";" + "".join(f"[s{i}]" for i in range(len(labels))) + (
            f"xstack=inputs={len(labels)}:layout=" + "|".join(f"{(i % cols) * 480}_{(i // cols) * 270}" for i in range(len(labels)))
            if len(labels) > 1 else "null") + "[v]"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-frames:v", "1", str(sheet)])
        print(f"Clip {n}: {len(labels)} shots, starting at " + ", ".join(f"{a:.2f}" for a in bounds[:-1]) + f" -> {sheet}", flush=True)
