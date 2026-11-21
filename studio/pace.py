"""The hook and the pace of a clip: which stretches of the source it plays, in which order.

The owner asked on 20 Nov 2026 for "an immediate opening hook, simple camera motion, clear narrative structure,
and consistent high-quality pacing that avoids generic AI slop".

A clip in clips.json can open on a hook: the strongest line of the moment, 1.5 to 4 seconds, played first.
Then the story plays from its own start:

    {"n": 1, "start": 205.2, "end": 239.5, "hook": {"start": 231.0, "end": 233.4}}

The hook is a stretch of the source, in source seconds. It is usually the payoff or the boldest line, so the
viewer hears it twice: once as the promise, once in its place. It may also come from outside the clip.

Inside the story, a pause between two words that runs longer than `trim_pauses` seconds is cut down to
`keep_pause` seconds. That keeps the pace even and drops dead air. `"trim_pauses": 0` turns it off.
With `cut_fillers`, every "um" and "uh" is cut out the same way. With `cut_dead`, the silence before the first word
and after the last word of the clip is cut off.

When a clip has a hook or a pause to cut, its pieces are joined into one file in `work/pace/`, and the
transcript is moved onto the new timeline. The rest of the renderer then treats that file as the source,
so every clip time (focus, anchor, lift, cutaways, capY) counts from the first frame of the finished clip.
"""
import hashlib
import json
import re

from .common import run

MIN_HOOK, MAX_HOOK = 1.2, 4.0   # seconds a hook may run
# Sounds that carry no meaning. The owner, 20 Nov 2026: "it also needs to cut deadspace and ums".
# Words such as "like" and "you know" stay: cutting them can change what the speaker means.
FILLERS = {"um", "umm", "uhm", "uh", "uhh", "er", "erm", "ah", "ahh", "hmm", "hm", "mm", "mmm", "eh"}
LEAD, TAIL = 0.08, 0.3           # air kept before the first word and after the last word of a clip
PAD = 0.12                      # air kept after the last word and before the next one, at a cut inside a pause


def words_in(transcript: dict, start: float, end: float) -> list:
    """The words whose middle lies between two source times, in source seconds, in order."""
    out = []
    for seg in transcript.get("segments", []):
        if seg.get("end", 0) < start or seg.get("start", 0) > end:
            continue
        for w in seg.get("words", []):
            if start <= (w["s"] + w["e"]) / 2 <= end:
                out.append(w)
    return sorted(out, key=lambda w: w["s"])


def hook_span(clip: dict):
    """The hook of a clip as (start, end) in source seconds, or None. It stops on a bad hook."""
    h = clip.get("hook")
    if not h or h == "start":   # "start": the first line of the story is already its strongest line
        return None
    if isinstance(h, (list, tuple)):
        s, e = float(h[0]), float(h[1])
    else:
        s, e = float(h["start"]), float(h["end"])
    if not MIN_HOOK <= e - s <= MAX_HOOK + 0.05:
        raise ValueError(f"Clip {clip.get('n')}: the hook runs {e - s:.2f} seconds. A hook runs {MIN_HOOK} to {MAX_HOOK} seconds.")
    return round(s, 3), round(e, 3)


def is_filler(word: str) -> bool:
    return re.sub(r"[^a-z]", "", word.lower()) in FILLERS


def story_pieces(words: list, start: float, end: float, trim: float, keep: float,
                 fillers: bool = False, dead: bool = False) -> list:
    """The clip from start to end, split where a pause between two words runs longer than trim seconds,
    and, with fillers, around every "um" and "uh". Each cut leaves keep seconds of air between the two words around it.
    With dead, the silence before the first word and after the last word is cut too."""
    keep = max(2 * PAD, keep)
    kept = [w for w in words if not (fillers and is_filler(w["w"]))]
    if dead and kept:
        start = max(start, kept[0]["s"] - LEAD)
        end = min(end, kept[-1]["e"] + TAIL)
    pieces, a = [], start
    for w, nxt in zip(kept, kept[1:]):
        gap = nxt["s"] - w["e"]
        ums = [x for x in words if fillers and is_filler(x["w"]) and w["e"] <= x["s"] < nxt["s"]] if fillers else []
        if ((trim and trim > 0 and gap > trim) or ums) and w["e"] >= start and nxt["s"] <= end:
            cut_from = w["e"] + keep / 2
            cut_to = nxt["s"] - keep / 2
            if ums:
                # The cut must take the whole um, even when the speaker leaves almost no air around it.
                cut_from = min(cut_from, ums[0]["s"] - 0.02)
                cut_to = max(cut_to, ums[-1]["e"] + 0.02)
            if cut_to - cut_from > 0.05:
                pieces.append((round(a, 3), round(cut_from, 3)))
                a = cut_to
    pieces.append((round(a, 3), round(end, 3)))
    return [p for p in pieces if p[1] - p[0] > 0.04]


def plan(clip: dict, transcript: dict, style: dict) -> list:
    """The stretches of the source the clip plays, in order, as [(start, end)] in source seconds."""
    start, end = float(clip["start"]), float(clip["end"])
    trim = float(clip.get("trim_pauses", style.get("trim_pauses", 0)) or 0)
    keep = float(clip.get("keep_pause", style.get("keep_pause", 0.3)))
    fillers = bool(clip.get("cut_fillers", style.get("cut_fillers", False)))
    dead = bool(clip.get("cut_dead", style.get("cut_dead", False)))
    pieces = story_pieces(words_in(transcript, start, end), start, end, trim, keep, fillers, dead)
    hook = hook_span(clip)
    return ([hook] if hook else []) + pieces


def remap(transcript: dict, pieces: list) -> dict:
    """The transcript on the timeline of the joined pieces. A word that a cut splits keeps the piece that holds its middle.
    A word that plays twice (in the hook and in the story) appears twice."""
    out, at = [], 0.0
    for s, e in pieces:
        for w in words_in(transcript, s, e):
            out.append({**w, "s": round(max(s, w["s"]) - s + at, 3), "e": round(min(e, w["e"]) - s + at, 3)})
        at += e - s
    return {"segments": [{"start": 0.0, "end": round(at, 3), "words": out}]}


def build(d, n: int, source, pieces: list) -> tuple:
    """Join the pieces into one file. Returns (path, seconds). A file made from the same pieces is used again."""
    key = hashlib.sha1(json.dumps([str(source), pieces]).encode()).hexdigest()[:10]
    folder = d / "work" / "pace"
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"clip{n:02d}-{key}.mp4"
    total = round(sum(e - s for s, e in pieces), 3)
    if out.exists() and out.stat().st_size > 0:
        return out, total
    for old in folder.glob(f"clip{n:02d}-*.mp4"):
        old.unlink()
    inputs, parts = [], []
    for i, (s, e) in enumerate(pieces):
        # Each piece is its own input, so a hook from far away in the source decodes only its own seconds.
        inputs += ["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", source]
        parts.append(f"[{i}:v]setpts=PTS-STARTPTS,fps=30[v{i}];"
                     f"[{i}:a]asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.01,"
                     f"afade=t=out:st={max(0.0, e - s - 0.012):.3f}:d=0.012[a{i}]")
    graph = ";".join(parts) + ";" + "".join(f"[v{i}][a{i}]" for i in range(len(pieces))) + f"concat=n={len(pieces)}:v=1:a=1[v][a]"
    # A high-quality middle file: the cut renders from it, so it must not lose detail.
    run(["ffmpeg", "-y", "-v", "error", *inputs,
         "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", out])
    return out, total


def prepare(d, clip: dict, transcript: dict, style: dict) -> tuple:
    """What the renderer plays for a clip: (source file, start, end, transcript).
    A clip with no hook and no pause to cut plays the source itself, as before."""
    pieces = plan(clip, transcript, style)
    if not pieces:
        return d / "source.mp4", float(clip["start"]), float(clip["end"]), transcript
    if len(pieces) == 1:
        # One stretch, perhaps with its dead air cut off at the ends: the source itself plays, from the new start to the new end.
        return d / "source.mp4", pieces[0][0], pieces[0][1], transcript
    path, total = build(d, int(clip["n"]), d / "source.mp4", pieces)
    return path, 0.0, total, remap(transcript, pieces)


def describe(pieces: list) -> str:
    return " + ".join(f"{s:.2f}-{e:.2f}" for s, e in pieces)


def ends_a_sentence(word: str) -> bool:
    return bool(re.search(r"[.?!][\"')\]]*$", word.strip()))
