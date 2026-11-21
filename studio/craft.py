"""The craft check: does each clip open on a hook, tell one clear story, keep an even pace and avoid AI slop?

The owner asked on 20 Nov 2026 for "an immediate opening hook, simple camera motion, clear narrative structure,
and consistent high-quality pacing that avoids generic AI slop".

    python -m studio craft --job <name> [--only 2,5]

It reads clips.json and transcript.json, and posting.json when it is there, and prints every problem in plain words.
Run it before every cut and fix what it finds. It never changes a file.
"""
import re

from . import pace
from .common import ROOT, job_dir, read_json

# Words and phrases that make a title or a description read as generic, machine-made filler.
SLOP = [
    "you won't believe", "you wont believe", "wait for it", "watch till the end", "watch until the end", "must watch", "must-watch",
    "this changed everything", "changed my life", "life-changing", "life changing", "game changer", "game-changer",
    "mind-blowing", "mind blowing", "jaw-dropping", "jaw dropping", "insane", "unbelievable", "shocking", "shocked",
    "nobody talks about", "no one talks about", "the truth about", "here's why", "heres why", "let that sink in",
    "the secret", "secret to", "revealed", "exposed", "gone wrong", "goes viral", "broke the internet",
    "delve", "unlock", "unleash", "elevate", "journey", "dive into", "deep dive", "in today's", "in this video",
    "masterclass", "a must", "level up", "next level", "hits different", "real talk", "powerful message", "words to live by",
]
GENERIC_TAGS = {"#viral", "#fyp", "#foryou", "#foryoupage", "#trending", "#explore", "#explorepage", "#reels", "#viralvideo", "#motivation"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
STOP = {"the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "is", "it", "his", "her", "he", "she", "you", "your",
        "my", "i", "we", "they", "this", "that", "with", "at", "be", "was", "are", "why", "how", "what", "who", "can't", "dont",
        "don't", "not", "no", "from", "about", "part", "1", "2", "3", "of", "vs", "vs."}

MAX_SECONDS = 90.0       # the owner's rule of 12 Nov 2026, counted without the flash and the ending video
MIN_RATE = 1.6           # words a second: a story slower than this drags
OPEN_SECONDS = 3.0       # the opening: it must carry words, and no cutaway may cover it
CUT_EVERY = 15.0         # at most one cutaway in each stretch of this many seconds


def plain(word: str) -> str:
    return re.sub(r"[^a-z0-9']", "", word.lower())


def slop_in(text: str) -> list:
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    return [p for p in SLOP if re.search(r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", low)]


def text_problems(where: str, text: str, words: list, title: bool) -> list:
    out = []
    found = slop_in(text)
    if found:
        out.append(f"The {where} uses generic words: {', '.join(found)}. Say what happens in the clip instead.")
    if "—" in text:
        out.append(f"The {where} has a long dash. Use a period or a comma.")
    if EMOJI.search(text):
        out.append(f"The {where} has an emoji. Leave it out.")
    if title:
        if len(text) > 40:
            out.append(f"The {where} has {len(text)} characters. Keep it to 40 or fewer, so it fits two lines.")
        if text.rstrip().endswith("!") or text.count("?") > 1:
            out.append(f"The {where} shouts. Drop the exclamation mark.")
        said = {plain(w["w"]) for w in words}
        own = [plain(x) for x in text.split() if plain(x) and plain(x) not in STOP]
        if own and not any(x in said or x.rstrip("s") in said for x in own):
            out.append(f"No word of the {where} is spoken in the clip. Build it from the speaker's own words.")
    else:
        tags = [t.lower() for t in re.findall(r"#\w+", text)]
        if len(tags) > 5:
            out.append(f"The {where} has {len(tags)} hashtags. Keep 3 to 5 that name the show, the people and the topic.")
        generic = sorted(set(tags) & GENERIC_TAGS)
        if generic:
            out.append(f"The {where} has generic hashtags: {', '.join(generic)}. Use hashtags that name the show, the people and the topic.")
        if "credit:" not in text.lower():
            out.append(f"The {where} has no credit line. Every post needs it.")
    return out


def stock_index() -> dict:
    path = ROOT / "assets" / "stock.json"
    return read_json(path).get("clips", {}) if path.exists() else {}


def problems(clip: dict, transcript: dict, style: dict, posting: dict | None = None, stock: dict | None = None) -> list:
    """Every craft problem of one clip, as plain sentences. An empty list means the clip passes."""
    out = []
    try:
        hook = pace.hook_span(clip)
    except ValueError as e:
        return [str(e)]
    start, end = float(clip["start"]), float(clip["end"])
    story = pace.words_in(transcript, start, end)
    pieces = pace.plan(clip, transcript, style)
    length = sum(e - s for s, e in pieces)
    timeline = pace.remap(transcript, pieces)["segments"][0]["words"]
    if not story:
        return ["The clip has no words. Check its start and end against the transcript."]

    # 1. The hook: the first seconds must give a reason to stay.
    if hook is None and clip.get("hook") != "start":
        out.append('The clip has no hook. Set "hook" to the strongest 1.5 to 4 seconds of the moment, '
                   'or set "hook": "start" when the first line is already the strongest line.')
    if hook:
        for w in pace.words_in(transcript, hook[0] - 1, hook[1] + 1):
            if w["s"] < hook[0] - 0.02 < w["e"] - 0.05 or w["s"] + 0.05 < hook[1] + 0.02 < w["e"]:
                out.append(f'The hook cuts through the word "{w["w"]}". Start and end it between words.')
                break
        said = pace.words_in(transcript, *hook)
        if said and not pace.ends_a_sentence(said[-1]["w"]) and len(said) < 4:
            out.append("The hook is a fragment. Pick a line that makes sense on its own.")
    if timeline and timeline[0]["s"] > 0.35:
        out.append(f"The first word comes {timeline[0]['s']:.2f} seconds in. Start the clip on the first word.")
    if len([w for w in timeline if w["s"] < OPEN_SECONDS]) < 4:
        out.append(f"The first {OPEN_SECONDS:.0f} seconds carry fewer than 4 words. Open on speech, not on silence or a slow line.")

    # 2. The story: it starts at the start of a thought, builds, and ends on its payoff.
    before = [w for w in pace.words_in(transcript, start - 3, start) if w["e"] <= start + 0.02]
    if before and not pace.ends_a_sentence(before[-1]["w"]) and story[0]["s"] - before[-1]["e"] < 0.6:
        out.append(f'The story starts in the middle of a sentence (after "{before[-1]["w"]}"). Start at the start of a thought.')
    if not pace.ends_a_sentence(story[-1]["w"]):
        out.append(f'The story ends on "{story[-1]["w"]}", not on a finished sentence. End on the payoff line.')
    payoff = str(clip.get("payoff") or "").strip()
    if not payoff:
        out.append('The clip names no payoff. Write the line the story builds to as "payoff".')
    else:
        key = [plain(x) for x in payoff.split() if plain(x)][:4]
        tail = [plain(w["w"]) for w in story if w["s"] >= start + (end - start) * 0.55]
        joined = " ".join(tail)
        if key and " ".join(key) not in joined:
            out.append("The payoff line is not in the last part of the story. Move the end, or name the real payoff.")

    # 3. The pace: even, with no dead air, inside the 90 second rule.
    if length > MAX_SECONDS:
        out.append(f"The clip runs {length:.1f} seconds. No clip may run over {MAX_SECONDS:.0f}: split it into parts.")
    story_seconds = sum(e - s for s, e in (pieces[1:] if hook else pieces))   # the story after its pauses are cut
    rate = len(story) / max(0.1, story_seconds)
    if rate < MIN_RATE:
        out.append(f"The story runs at {rate:.1f} words a second. Under {MIN_RATE} it drags: tighten the start or the end.")
    ums = [w["w"] for w in timeline if pace.is_filler(w["w"])]
    if ums:
        out.append(f'{len(ums)} filler sound(s) stay in the clip ({", ".join(sorted(set(ums)))}). Turn on cut_fillers.')
    if timeline and length - timeline[-1]["e"] > 0.6:
        out.append(f"The clip runs {length - timeline[-1]['e']:.1f} seconds past its last word. Turn on cut_dead, or end it sooner.")
    left = [round(b["s"] - a["e"], 2) for a, b in zip(timeline, timeline[1:]) if b["s"] - a["e"] > 1.0]
    if left:
        out.append(f"{len(left)} pause(s) over 1 second stay in the clip. Turn on trim_pauses, or cut them in the plan.")
    if length < 12:
        out.append(f"The clip runs only {length:.1f} seconds. A story needs room for a setup and a payoff.")

    # 4. The camera: simple, never busy.
    every, gap = int(style.get("zoom_every", 0) or 0), float(style.get("zoom_gap", 0) or 0)
    levels = style.get("zoom_levels") or []
    if every or gap < 3 or len(levels) > 2:
        out.append("The zoom is busy: use zoom_every 0, zoom_gap 4 and two zoom_levels, as the defaults do.")
    glides = [s for s in (clip.get("focus") if isinstance(clip.get("focus"), list) else []) if len(s) > 2]
    if len(glides) > 1:
        out.append(f"The frame glides {len(glides)} times. Use a glide only where the source camera itself moves.")

    # 5. Cutaways: few, literal, never in the opening, never generic.
    cuts = sorted(clip.get("cutaways") or [], key=lambda c: float(c["at"]))
    stock = stock_index() if stock is None else stock
    for c in cuts:
        at = float(c["at"])
        if at < OPEN_SECONDS:
            out.append(f"A cutaway starts at {at:.1f} seconds. Keep the first {OPEN_SECONDS:.0f} seconds on the speaker.")
        if not str(c.get("word") or "").strip():
            out.append(f"The cutaway at {at:.1f} seconds names no spoken word. Every cutaway must show a word that is said.")
        name = re.sub(r"\.mp4$", "", str(c.get("file", "")).split("/")[-1])
        if stock and name not in stock:
            out.append(f"The cutaway {c.get('file')} is not in assets/stock.json. Look at it and add what it shows.")
    if len(cuts) > max(1, int(length // CUT_EVERY)):
        out.append(f"The clip has {len(cuts)} cutaways in {length:.0f} seconds. Keep at most one in every {CUT_EVERY:.0f} seconds.")

    # 6. The words on screen and in the post.
    if clip.get("title"):
        out += text_problems("on-screen title", str(clip["title"]), story, True)
    post = posting or {}
    if post.get("title"):
        out += text_problems("post title", str(post["title"]), story, True)
    if post.get("description") or clip.get("description"):
        out += text_problems("description", str(post.get("description") or clip.get("description")), story, False)
    return out


def check(job: str, only: list | None = None) -> int:
    from .render import DEFAULT_STYLE, look_style
    d = job_dir(job)
    plan = read_json(d / "clips.json")
    given = plan.get("style", {})
    style = {**DEFAULT_STYLE, **look_style(given.get("look")), **given}
    transcript = read_json(d / "transcript.json")
    posting = {}
    if (d / "posting.json").exists():
        items = read_json(d / "posting.json")
        items = items.get("items", items) if isinstance(items, dict) else items
        posting = {int(x["n"]): x for x in items if isinstance(x, dict) and "n" in x}
    stock, total = stock_index(), 0
    for clip in plan["clips"]:
        n = int(clip["n"])
        if only and n not in only:
            continue
        own = {**style, **look_style((clip.get("style") or {}).get("look")), **(clip.get("style") or {})}
        found = problems(clip, transcript, own, posting.get(n), stock)
        total += len(found)
        if found:
            print(f"Clip {n}: {len(found)} problem(s)", flush=True)
            for line in found:
                print(f"  - {line}", flush=True)
        else:
            print(f"Clip {n}: no craft problems.", flush=True)
    return total
