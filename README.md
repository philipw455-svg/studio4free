# studio4free

Studio4Free turns a long YouTube video into short vertical clips and schedules them in Buffer.

- `page/studio.html` is the phone-first page where jobs, clips and the schedule live.
- `studio/` is the program a Claude Code session runs: fetch, transcribe, cut, schedule, post.
- `CLAUDE.md` tells any Claude Code session how to run a job from start to finish.

```
pip install -r requirements.txt
python -m studio fetch "https://youtu.be/..." --job demo
python -m studio transcribe --job demo
# write jobs/demo/clips.json, then:
python -m studio cut --job demo
python -m studio schedule --job demo --start 2026-11-20
```

The fonts are Montserrat and Anton, under the SIL Open Font License (`assets/fonts`).
