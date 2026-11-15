"""Join parts of one or more videos into one finished video. An edit job and a montage job both end here.

jobs/<name>/join.json:
  {"shape": "wide", "fit": "pad", "captions": false, "mute_strong": false, "music": "", "music_volume": 20, "title": "",
   "parts": [{"file": "source.mp4", "start": 12.4, "end": 31.0, "volume": 100}, {"file": "sources/02.mp4"}]}
"""
import sys
from pathlib import Path

from .common import FONTS, ROOT, has_audio, job_dir, probe, read_json, run, write_json
from .render import SIZES, build_srt, clip_words, even, is_strong

SHAPES = {"wide": SIZES["16:9"], "tall": SIZES["9:16"], "square": SIZES["1:1"]}
PAGE_MB = 19.0   # the page takes files under 20 MB


def timeline(parts: list) -> list:
    """Each part with the second at which it starts in the finished video."""
    out, at = [], 0.0
    for p in parts:
        out.append({**p, "at": at})
        at += p["end"] - p["start"]
    return out


def moved_words(transcript: dict, parts: list) -> list:
    """The spoken words of the parts cut from source.mp4, at their times in the finished video."""
    out = []
    for p in timeline(parts):
        if p["src"]:
            out += [{"s": w["s"] + p["at"], "e": w["e"] + p["at"], "w": w["w"]} for w in clip_words(transcript, p["start"], p["end"])]
    return out


def esc(path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def join(job: str) -> None:
    d = job_dir(job)
    if not (d / "join.json").exists():
        sys.exit(f"join.json is missing in {d}. See CLAUDE.md, \"The join step\".")
    plan = read_json(d / "join.json")
    parts = []
    for p in plan.get("parts") or []:
        f = Path(p["file"])
        f = f if f.is_absolute() else d / f
        if not f.exists():
            sys.exit(f"No file at {f}")
        info = probe(f)
        start = max(0.0, float(p.get("start") or 0))
        end = min(float(p.get("end") or info["duration"]), info["duration"])
        if end - start < 0.1:
            sys.exit(f"Part {len(parts) + 1} ({f.name}) is empty: it runs from {start} to {end}.")
        parts.append({"f": f, "start": start, "end": end, "volume": float(p.get("volume", 100)), "info": info,
                      "src": f.resolve() == (d / "source.mp4").resolve()})
    if not parts:
        sys.exit("join.json lists no parts.")
    W, H = SHAPES.get(plan.get("shape")) or (even(parts[0]["info"]["width"]), even(parts[0]["info"]["height"]))
    box = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}" if plan.get("fit") == "crop"
           else f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
    total = sum(p["end"] - p["start"] for p in parts)

    # shortcut: the whole filter goes on the command line, which holds about 100 parts on Windows.
    # Write it to a file and pass it with -/filter_complex when a job needs more.
    cmd, graph = ["ffmpeg", "-y"], []
    for i, p in enumerate(parts):
        dur = p["end"] - p["start"]
        cmd += ["-ss", f"{p['start']:.3f}", "-t", f"{dur:.3f}", "-i", p["f"]]
        # Every part is cut to its exact length, so the captions stay in step after many parts.
        graph.append(f"[{i}:v]{box},setsar=1,fps=30,format=yuv420p,tpad=stop_mode=clone:stop_duration=1,trim=duration={dur:.3f},setpts=PTS-STARTPTS[v{i}]")
        sound = (f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={p['volume'] / 100:.2f},apad" if has_audio(p["f"])
                 else "anullsrc=r=48000:cl=stereo")
        graph.append(f"{sound},atrim=duration={dur:.3f},asetpts=PTS-STARTPTS[a{i}]")
    graph.append("".join(f"[v{i}][a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[vc][ac]")
    vout, aout = "[vc]", "[ac]"

    out_dir = d / "clips"
    out_dir.mkdir(exist_ok=True)
    words = []
    if plan.get("captions") or plan.get("mute_strong"):
        if not (d / "transcript.json").exists():
            sys.exit("Captions and muting need transcript.json. Run the transcribe step first.")
        words = moved_words(read_json(d / "transcript.json"), parts)
    if plan.get("captions") and words:
        srt = out_dir / "clip01.srt"
        srt.write_text(build_srt(words, total), encoding="utf-8")
        graph.append(f"{vout}subtitles='{esc(srt)}':fontsdir='{esc(FONTS)}':"
                     f"force_style='FontName=Montserrat SemiBold,FontSize=15,Outline=1.2,Shadow=0,MarginV=22'[vs]")
        vout = "[vs]"
    muted = [w for w in words if is_strong(w["w"])] if plan.get("mute_strong") else []
    if muted:
        graph.append(aout + ",".join(f"volume=enable='between(t,{w['s']:.2f},{w['e']:.2f})':volume=0" for w in muted) + "[am]")
        aout = "[am]"
    if plan.get("music"):
        music = Path(plan["music"])
        music = music if music.is_absolute() else ROOT / music
        if not music.exists():
            sys.exit(f"No music file at {music}")
        cmd += ["-stream_loop", "-1", "-i", music]
        graph.append(f"[{len(parts)}:a]aresample=48000,aformat=channel_layouts=stereo,volume={float(plan.get('music_volume', 20)) / 100:.2f}[mu];"
                     f"{aout}[mu]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[ax]")
        aout = "[ax]"

    out = out_dir / "clip01.mp4"
    run(cmd + ["-filter_complex", ";".join(graph), "-map", vout, "-map", aout, "-t", f"{total:.3f}",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])
    mb = out.stat().st_size / 1048576
    page = None
    if mb > PAGE_MB:
        # The finished video is too large for the page. A smaller copy goes there, and the full file stays here.
        rate = int(PAGE_MB * 8192 * 0.94 / total) - 96
        if rate >= 150:
            page = out_dir / "clip01-page.mp4"
            run(["ffmpeg", "-y", "-i", out, "-vf", "scale=trunc(iw/4)*2:trunc(ih/4)*2", "-c:v", "libx264", "-preset", "medium",
                 "-b:v", f"{rate}k", "-maxrate", f"{rate}k", "-bufsize", f"{rate * 2}k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", page])
    path = d / "rendered.json"
    old = read_json(path) if path.exists() else []
    r = {"n": 1, "file": "clips/clip01.mp4", "seconds": round(total, 1), "title": plan.get("title", ""), "muted": len(muted),
         "mb": round(mb, 1), "size": [W, H], "parts": len(parts), "version": int(old[0].get("version") or 1) + 1 if old else 1,
         **({"page_file": "clips/clip01-page.mp4", "page_mb": round(page.stat().st_size / 1048576, 1)} if page else {})}
    write_json(path, [r])
    print(f"Joined {len(parts)} parts: {r['seconds']}s, {W}x{H}, {r['mb']} MB, version {r['version']} -> {out}")
    if page:
        print(f"Copy for the page: {r['page_mb']} MB -> {page}")
    elif mb > PAGE_MB:
        print("The video is too long for a copy that fits the page's 20 MB limit. Tell the owner where the file is.")
