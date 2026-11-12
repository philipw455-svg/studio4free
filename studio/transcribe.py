"""Step 2: turn the speech into text with a time for every word."""
import sys

from .common import clock, job_dir, write_json


def transcribe(job: str, model: str = "small", language: str | None = None) -> None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is missing. Run: pip install -r requirements.txt")
    d = job_dir(job)
    src = d / "source.mp4"
    if not src.exists():
        sys.exit(f"No source video. Run the fetch step first, or put the file at {src}")
    import subprocess
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True)
    if raw.returncode or not raw.stdout:
        sys.exit("ffmpeg could not read the sound of the source video.")
    audio = np.frombuffer(raw.stdout, np.int16).astype(np.float32) / 32768.0
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segments, info = m.transcribe(audio, language=language, word_timestamps=True, vad_filter=True)
    segs, lines = [], []
    for s in segments:
        words = [{"s": round(w.start, 2), "e": round(w.end, 2), "w": w.word.strip()} for w in (s.words or [])]
        segs.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(), "words": words})
        lines.append(f"[{clock(s.start)} | {s.start:.1f}] {s.text.strip()}")
        if len(segs) % 50 == 0:
            print(f"  heard up to {clock(s.end)} of {clock(info.duration)}", flush=True)
    write_json(d / "transcript.json", {"language": info.language, "duration": round(info.duration, 2), "segments": segs})
    (d / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {d / 'transcript.txt'} ({len(segs)} lines, language {info.language})")
