"""Rules check helper: collect what each clip says and shows, ready to compare with the platform rules."""
import sys

from .common import ROOT, job_dir, read_json, write_json
from .render import clip_words


def texts(job: str) -> None:
    d = job_dir(job)
    for need in ("transcript.json", "clips.json"):
        if not (d / need).exists():
            sys.exit(f"{need} is missing in {d}.")
    transcript, plan = read_json(d / "transcript.json"), read_json(d / "clips.json")
    posting = {}
    if (d / "posting.json").exists():
        posting = {it["clip"]: it for it in read_json(d / "posting.json")["items"]}
    out = []
    for c in plan["clips"]:
        words = clip_words(transcript, float(c["start"]), float(c["end"]))
        p = posting.get(int(c["n"]), {})
        out.append({"n": int(c["n"]), "onScreenTitle": c.get("title", ""), "postTitle": p.get("title", ""),
                    "description": p.get("description", ""), "muted": c.get("mute", []),
                    "spoken": " ".join(w["w"] for w in words)})
    write_json(d / "clip_texts.json", out)
    src = read_json(ROOT / "rules" / "sources.json")
    print(f"Wrote {d / 'clip_texts.json'} ({len(out)} clips).")
    print("Read these official pages now, then compare every clip with them:")
    for site in ("youtube", "instagram", "tiktok"):
        for s in src[site]:
            print(f"  {s['title']}: {s['url']}")
