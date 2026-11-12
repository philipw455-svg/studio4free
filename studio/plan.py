"""Step 5: give every clip a publish time."""
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .common import job_dir, read_json, write_json


def schedule(job: str, start: str, times: str = "12:15,17:00", tz: str = "America/Chicago", order: str = "") -> None:
    d = job_dir(job)
    if not (d / "rendered.json").exists():
        sys.exit("No rendered clips yet. Run the cut step first.")
    clips = read_json(d / "rendered.json")
    if order:
        want = [int(x) for x in order.split(",")]
        by = {c["n"]: c for c in clips}
        clips = [by[n] for n in want if n in by]
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
                          "seconds": clips[i]["seconds"], "publishAt": when.isoformat(), "status": "planned"})
            i += 1
        day += timedelta(days=1)
    write_json(d / "posting.json", {"tz": tz, "times": times, "items": items})
    for it in items:
        print(f"Clip {it['clip']:>2}  {it['publishAt']}  {it['title']}")
