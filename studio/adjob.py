"""Ad jobs: the steps, the owner's choices, the "What I know" card, the shared post calendar, and the learn step.

An ad job is a page database document `jobs/{id}` with `kind: "ad"`. CLAUDE.md lists every field.
python -m studio ad context --brand noxi --job ad.json      the "What I know" card for a brief
python -m studio ad slots --times 12:15,17:00 --count 3      the next open post times, shared with the podcast clips
python -m studio ad learn --brand noxi --job ad.json         add the ad to history.md (and results.md when it has results)
"""
import json
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .brain import BRANDS, Brain, add_row, brand_dir
from .brain_check import has as has_words

# The steps, in order. `status` is what the job says while it waits; `who` is who acts next.
STEPS = [
    {"n": 1, "name": "Brief", "status": "brief", "who": "owner", "saves": "brief"},
    {"n": 2, "name": "Context", "status": "context", "who": "owner", "saves": "context"},
    {"n": 3, "name": "Hooks", "status": "hooks", "who": "owner", "saves": "hooks, hookPick"},
    {"n": 4, "name": "Choices", "status": "choices", "who": "owner", "saves": "choices"},
    {"n": 5, "name": "Storyboard", "status": "storyboard", "who": "owner", "saves": "storyboard, check, storyboardOk"},
    {"n": 6, "name": "Render", "status": "rendering", "who": "claude", "saves": "render"},
    {"n": 7, "name": "Review", "status": "review", "who": "owner", "saves": "notes"},
    {"n": 8, "name": "Post", "status": "post", "who": "owner", "saves": "post"},
    {"n": 9, "name": "Learn", "status": "scheduled", "who": "claude", "saves": "learn"},
]
STATUSES = [s["status"] for s in STEPS] + ["sent", "scheduling", "learned", "blocked"]

CHOICES = {
    "style": ["App tour", "Mascot story", "Hype type", "Sting", "Podcast clip with end card"],
    "length": ["2 s", "15 s", "30 s", "60 s"],
    "shape": ["9:16", "1:1", "16:9"],
    "look": "the brand's current looks in kit.md",
    "pace": ["Calm", "Normal", "Hyped"],
    "sound": ["Beat", "Sound effects only", "Silent"],
    "cast": "mascots in kit.md, or none",
    "endCard": "a current end card in kit.md, or a new one",
    "cta": "a link in profile.md",
}
# The length each style is built for, in seconds. A choice outside it is allowed but reported.
STYLE_LENGTH = {"App tour": (30, 60), "Mascot story": (14, 16), "Hype type": (30, 30), "Sting": (2, 2)}


def choice_problems(brain: Brain, choices: dict) -> list[str]:
    """Plain sentences for every choice that is missing or not allowed for this brand."""
    out = []
    for key in ("style", "length", "shape", "pace", "sound"):
        v = choices.get(key)
        if not v:
            out.append(f"Pick a {key}.")
        elif v not in CHOICES[key]:
            out.append(f"'{v}' is not a {key} option. The options are: {', '.join(CHOICES[key])}.")
    looks = list(brain.looks())
    if choices.get("look") and choices["look"] not in looks:
        out.append(f"'{choices['look']}' is not a current look of this brand. The looks are: {', '.join(looks)}.")
    kit = {k.name.split(":")[-1].strip(): k for k in brain.kit()}
    for name in choices.get("cast") or []:
        k = kit.get(name)
        if not k or k.kind != "mascot":
            out.append(f"'{name}' is not a mascot in kit.md.")
        elif k.retired:
            out.append(f"'{name}' is retired in kit.md.")
    links = brain.links()
    if choices.get("cta") and choices["cta"] not in links:
        out.append(f"'{choices['cta']}' is not a link in profile.md. The links are: {', '.join(links)}.")
    span = STYLE_LENGTH.get(choices.get("style"))
    secs = int(re.sub(r"\D", "", choices.get("length") or "0") or 0)
    if span and secs and not span[0] <= secs <= span[1]:
        out.append(f"{choices['style']} is built for {span[0]} to {span[1]} seconds, and {secs} seconds was picked.")
    return out


def context_card(brain: Brain, brief: dict, around: int = 14) -> str:
    """The "What I know" card: the facts that apply, the dates near the post time, and the last 5 ads."""
    text = " ".join(str(brief.get(k) or "") for k in ("about", "notes", "audience", "action"))
    facts = brain.facts()
    apply = [f for f in facts if f.keys and any(has_words(text, k) for k in f.keys)] or [f for f in facts if f.keys]
    lines = ["What I know", "", "Facts that apply:"]
    for f in apply:
        mark = "approved" if f.approved else "needs your yes"
        lines.append(f"- {f.text} ({mark}; {f.source})")
    when = brief.get("postWhen") or ""
    try:
        post = datetime.fromisoformat(when).date()
    except ValueError:
        post = None
    lines += ["", f"Dates near the post time ({when or 'no post time yet'}):"]
    near = [d for d in brain.calendar() if post and abs((date.fromisoformat(d.date) - post).days) <= around]
    lines += [f"- {d.date}: {d.what} ({d.kind})" for d in near] or ["- none within two weeks" if post else "- set a post time to see them"]
    lines += ["", "The last 5 ads:"]
    rows = brain.history()[-5:]
    lines += [f"- {r.get('date')}: {r.get('style')}, \"{r.get('hook')}\", {r.get('length')}, {r.get('posted')}" for r in rows] or ["- none yet"]
    retired = [k.name for k in brain.kit() if k.retired]
    if retired:
        lines += ["", "Retired, never use: " + "; ".join(retired) + "."]
    return "\n".join(lines)


def open_slots(times: list[str], tz: str, taken: list[str], after: datetime, count: int = 1, days: int = 60) -> list[datetime]:
    """The next post times that nothing uses yet. Podcast clips and ads share these times.

    times: the day's post times, "HH:MM". taken: the times already used (ISO, any zone), such as every Buffer post's dueAt.
    A time counts as used when a post sits within 5 minutes of it.
    """
    zone = ZoneInfo(tz)
    used = [datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(zone) for t in taken if t]
    slots = sorted(time.fromisoformat(t.strip()) for t in times if t.strip())
    out = []
    day = after.astimezone(zone).date()
    for _ in range(days):
        for s in slots:
            when = datetime.combine(day, s, zone)
            if when <= after:
                continue
            if any(abs((when - u).total_seconds()) < 300 for u in used):
                continue
            out.append(when)
            if len(out) >= count:
                return out
        day += timedelta(days=1)
    return out


def learn(brain: Brain, job: dict) -> list[str]:
    """Write the ad into history.md, and its results into results.md when the job has them. Returns what was added."""
    sb = (job.get("storyboard") or {})
    ch = job.get("choices") or {}
    post = job.get("post") or {}
    hook = (job.get("hookPick") or {}).get("line") or (sb.get("frames") or [{}])[0].get("words", "")
    when = (post.get("publishAt") or "")[:10] or date.today().isoformat()
    where = ", ".join(post.get("services") or []) or "not posted"
    added = []
    add_row(brain.path / "history.md", [when, ch.get("style", ""), hook, ch.get("length", ""), where, (job.get("render") or {}).get("file", "")])
    added.append("history.md")
    res = job.get("learn") or {}
    if res.get("metrics"):
        m = res["metrics"]
        add_row(brain.path / "results.md", [when, job.get("name", ""), where, m.get("views", ""), m.get("likes", ""),
                                            m.get("comments", ""), m.get("shares", ""), res.get("line", "")])
        added.append("results.md")
    return added


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="studio ad")
    sub = p.add_subparsers(dest="action", required=True)
    a = sub.add_parser("context", help="print the What I know card for a brief")
    a.add_argument("--brand", required=True)
    a.add_argument("--job", required=True, help="the job document as JSON (from the page)")
    a = sub.add_parser("choices", help="check the owner's choices against the brain")
    a.add_argument("--brand", required=True)
    a.add_argument("--job", required=True)
    a = sub.add_parser("slots", help="the next open post times, shared with podcast clips")
    a.add_argument("--times", required=True, help="the day's post times from settings, such as 09:00,12:15,17:00")
    a.add_argument("--tz", default="America/Chicago")
    a.add_argument("--count", type=int, default=3)
    a.add_argument("--after", default="", help="ISO time; default now")
    a.add_argument("--taken", default="", help="a JSON file with a list of used times; default: ask Buffer")
    a = sub.add_parser("learn", help="add the posted ad to history.md and results.md")
    a.add_argument("--brand", required=True)
    a.add_argument("--job", required=True)
    x = p.parse_args(argv)

    if x.action == "slots":
        if x.taken:
            taken = json.loads(Path(x.taken).read_text(encoding="utf-8"))
        else:
            from .buffer import queue
            taken = [q.get("dueAt") for q in queue() if q.get("status") in ("scheduled", "draft", "sending")]
        after = datetime.fromisoformat(x.after) if x.after else datetime.now(ZoneInfo(x.tz))
        for s in open_slots(x.times.split(","), x.tz, taken, after, x.count):
            print(s.isoformat(), s.strftime("(%a %b %d, %I:%M %p)"))
        return
    brain = Brain.load(brand_dir(x.brand, BRANDS))
    job = json.loads(Path(x.job).read_text(encoding="utf-8"))
    if job.get("brand") and job["brand"] != x.brand:
        sys.exit(f"This job belongs to '{job['brand']}', not '{x.brand}'. Never mix two brands.")
    if x.action == "context":
        print(context_card(brain, job.get("brief") or {}))
    elif x.action == "choices":
        probs = choice_problems(brain, job.get("choices") or {})
        print("\n".join("- " + s for s in probs) if probs else "The choices fit the brain.")
    elif x.action == "learn":
        print("Added to", ", ".join(learn(brain, job)))
