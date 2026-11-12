"""Step 5: give every clip a publish time."""
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .common import job_dir, read_json, write_json


def schedule(job: str, start: str, times: str = "12:15,17:00", tz: str = "America/Chicago", order: str = "",
             flash_days: str = "Tuesday,Friday") -> None:
    d = job_dir(job)
    if not (d / "rendered.json").exists():
        sys.exit("No rendered clips yet. Run the cut step first.")
    clips = read_json(d / "rendered.json")
    if order:
        want = [int(x) for x in order.split(",")]
        by = {c["n"]: c for c in clips}
        clips = [by[n] for n in want if n in by]
    # Keep the parts of one story together and in order: Part 1 first, then the parts that follow.
    ordered, seen = [], set()
    for c in clips:
        s = c.get("series")
        if not s:
            ordered.append(c)
        elif s not in seen:
            seen.add(s)
            ordered += sorted((x for x in clips if x.get("series") == s), key=lambda x: x.get("part", 0))
    clips = ordered
    slots = [time.fromisoformat(t.strip()) for t in times.split(",")]
    zone = ZoneInfo(tz)
    day = date.fromisoformat(start)
    items, i = [], 0
    while i < len(clips):
        for s in slots:
            if i >= len(clips):
                break
            when = datetime.combine(day, s, zone)
            items.append({"clip": clips[i]["n"], "file": clips[i]["file"], "title": clips[i]["title"],
                          "seconds": clips[i]["seconds"], "publishAt": when.isoformat(), "status": "planned",
                          **{k: clips[i][k] for k in ("series", "part", "parts") if k in clips[i]}})
            i += 1
        day += timedelta(days=1)
    write_json(d / "posting.json", {"tz": tz, "times": times, "items": items})
    for it in items:
        tag = f"  (part {it['part']} of {it['parts']})" if it.get("parts") else ""
        print(f"Clip {it['clip']:>2}  {it['publishAt']}  {it['title']}{tag}")
    # The Noxi flash belongs on clips that post on a flash day, and on no other clip.
    want = {d.strip().lower() for d in flash_days.split(",") if d.strip()}
    has = {c["n"]: bool(c.get("flash")) for c in clips}
    redo = []
    for it in items:
        day = datetime.fromisoformat(it["publishAt"]).strftime("%A")
        it["flashDay"] = day.lower() in want
        if it["flashDay"] != has.get(it["clip"], False):
            redo.append((it["clip"], day, it["flashDay"]))
    write_json(d / "posting.json", {"tz": tz, "times": times, "items": items})
    for n, day, on in redo:
        print(f"Cut clip {n} again with \"flash\": {'true' if on else 'false'}. It posts on a {day}.")
