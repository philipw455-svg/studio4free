"""Film an ad template frame by frame with Playwright, then encode it with ffmpeg at 30 fps.

python -m studio film <storyboard.json> --out jobs/<name>/ad.mp4             the whole video
python -m studio film <storyboard.json> --out jobs/<name>/stills --stills 0.5,3,14   a few frames to look at first

The template draws at the output size. Every still also reports words that left the Reels safe area.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from .brain import BRANDS, Brain, brand_dir
from .common import ROOT, has_audio, probe, run

ADS = Path(__file__).resolve().parent / "ads"
FPS = 30
SIZES = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}
STYLES = {"App tour": "app-tour", "Mascot story": "mascot-story", "Hype type": "hype-type", "Sting": "sting",
          "Podcast clip with end card": "podcast-endcard"}
SFX = ROOT / "assets" / "sfx" / "whoosh.mp3"


def style_dir(style: str) -> Path:
    key = STYLES.get(style, style)
    d = ADS / key
    if not (d / "README.md").exists():
        sys.exit(f"There is no ad style '{style}'. The styles are: {', '.join(STYLES)}.")
    return d


def length(sb: dict) -> float:
    ends = [float(f["end"]) for f in sb.get("frames") or []]
    return float(sb.get("length") or 0) or (max(ends) if ends else 2.0)


def brand_data(brain: Brain, sb: dict) -> dict:
    """What a template needs from the brain: looks, fonts, the logo for the look, the cast picture, and file links."""
    base = brain.path.resolve().as_uri() + "/"
    kit = brain.kit()
    fonts = []
    for it in kit:
        if it.kind == "font" and not it.retired and it.files:
            fam = re.sub(r"^font:\s*", "", it.name, flags=re.I)
            entry = {"family": fam, "url": base + it.files[0]}
            fonts.insert(0, entry) if "display" in it.note.lower() else fonts.append(entry)
    look = (sb.get("look") or "").lower()
    logo = ""
    for it in kit:
        if it.kind == "logo" and not it.retired and it.files:
            pick = [f for f in it.files if look and look in f.lower() and f.endswith(".png")]
            logo = (pick or [f for f in it.files if f.endswith(".png")] or it.files)[0]
            break
    cast = next((it.files[0] for it in kit if it.kind == "picture" and not it.retired and it.files
                 and "lineup" in it.name.lower()), "")
    mascots = [re.sub(r"^mascot:\s*", "", it.name, flags=re.I) for it in kit if it.kind == "mascot" and not it.retired]
    files = {str(p.relative_to(brain.path)): p.resolve().as_uri() for p in (brain.path / "assets").rglob("*") if p.is_file()}
    return {"looks": brain.looks(), "fonts": fonts, "logo": logo, "cast": cast, "mascots": mascots, "base": base, "files": files}


def _page(pw, sb: dict, brain: Brain):
    w, h = SIZES.get(sb.get("shape") or "9:16", SIZES["9:16"])
    browser = pw.chromium.launch()
    page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    page.add_init_script("window.SB = %s; window.BRAND = %s;" % (json.dumps(sb), json.dumps(brand_data(brain, sb))))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((style_dir(sb["style"]) / "template.html").resolve().as_uri())
    page.evaluate("window.ready")
    if errors:
        sys.exit("The template failed: " + errors[0])
    return browser, page, (w, h)


OUTSIDE = """() => { const s = S4F.SAFE, out = [];
  for (const el of document.querySelectorAll('.words')) {
    const st = getComputedStyle(el); if (st.display === 'none' || st.visibility === 'hidden' || +st.opacity < 0.5 || !el.textContent.trim()) continue;
    const r = el.getBoundingClientRect(); if (r.width < 1) continue;
    const range = document.createRange(); range.selectNodeContents(el); const t = range.getBoundingClientRect();
    if (t.top < s.top - 20 || t.bottom > s.bottom + 20 || t.right > s.right + 1 || t.left < 0)
      out.push({text: el.textContent.trim().slice(0, 40), box: [Math.round(t.left), Math.round(t.top), Math.round(t.width), Math.round(t.height)]}); }
  return out; }"""


def stills(sb: dict, brain: Brain, out: Path, times: list[float]) -> list[Path]:
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    files = []
    with sync_playwright() as pw:
        browser, page, _ = _page(pw, sb, brain)
        for t in times:
            page.evaluate(f"window.seek({t})")
            p = out / f"still-{t:06.2f}.png"
            page.screenshot(path=str(p))
            files.append(p)
            for o in page.evaluate(OUTSIDE):
                print(f"At {t:.2f} s the words \"{o['text']}\" leave the safe area (box {o['box']}).")
        browser.close()
    return files


def _audio_args(sb: dict, seconds: float) -> tuple[list, str]:
    """ffmpeg inputs and filter for the sound choice. Returns (input args, filter text ending in [a])."""
    sound = sb.get("sound") or "Sound effects only"
    if sound == "Silent":
        return ["-f", "lavfi", "-t", f"{seconds:.3f}", "-i", "anullsrc=r=48000:cl=stereo"], "[1:a]anull[a]"
    hits = [float(f["start"]) for f in sb.get("frames") or [] if (f.get("sound") or "").strip()]
    if sound == "Beat":
        beat = sb.get("soundFile")
        if not beat or not Path(beat).exists():
            sys.exit("The sound is Beat, but the storyboard has no soundFile that exists. Add a licensed track as soundFile, "
                     "or pick 'Sound effects only' or 'Silent'.")
        args = ["-i", beat]
        filt = f"[1:a]atrim=0:{seconds:.3f},afade=t=out:st={max(0, seconds - 1.5):.3f}:d=1.5[m]"
        if not hits:
            return args, filt + ";[m]anull[a]"
        return args + ["-i", str(SFX)], filt + ";" + _sfx_mix(2, hits, seconds, "[m]")
    return ["-f", "lavfi", "-t", f"{seconds:.3f}", "-i", "anullsrc=r=48000:cl=stereo", "-i", str(SFX)], \
        _sfx_mix(2, hits, seconds, "[1:a]")


def _sfx_mix(idx: int, hits: list[float], seconds: float, bed: str) -> str:
    if not hits:
        return f"{bed}anull[a]"
    parts = [f"[{idx}:a]asplit={len(hits)}" + "".join(f"[s{i}]" for i in range(len(hits)))]
    for i, t in enumerate(hits):
        ms = int(max(0, t - 0.15) * 1000)
        parts.append(f"[s{i}]volume=0.35,adelay={ms}|{ms}[d{i}]")
    parts.append(bed + "".join(f"[d{i}]" for i in range(len(hits))) +
                 f"amix=inputs={len(hits) + 1}:normalize=0,atrim=0:{seconds:.3f}[a]")
    return ";".join(parts)


def film(sb: dict, brain: Brain, out: Path) -> Path:
    from playwright.sync_api import sync_playwright
    if STYLES.get(sb.get("style"), sb.get("style")) == "podcast-endcard":
        return podcast_endcard(sb, brain, out)
    seconds = length(sb)
    total = int(round(seconds * FPS))
    out.parent.mkdir(parents=True, exist_ok=True)
    a_in, a_filt = _audio_args(sb, seconds)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-", *a_in,
           "-filter_complex", a_filt, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with sync_playwright() as pw:
        browser, page, _ = _page(pw, sb, brain)
        for i in range(total):
            page.evaluate(f"window.seek({i / FPS})")
            enc.stdin.write(page.screenshot(type="jpeg", quality=95))
            if i and i % (FPS * 5) == 0:
                print(f"  {i // FPS} of {seconds:.0f} seconds filmed")
        browser.close()
    enc.stdin.close()
    if enc.wait():
        sys.exit("ffmpeg could not encode the video.")
    print(f"Wrote {out} ({seconds:.1f} s, {out.stat().st_size / 1e6:.1f} MB)")
    return out


def podcast_endcard(sb: dict, brain: Brain, out: Path) -> Path:
    """An existing clip with the brand's end card added after it."""
    clip, card = Path(sb.get("clip") or ""), Path(sb.get("endCardFile") or "")
    if not clip.exists():
        sys.exit("The storyboard needs 'clip': the path of the finished clip.")
    if not card.exists():
        sys.exit("The storyboard needs 'endCardFile': the path of a current end card video.")
    w, h = SIZES.get(sb.get("shape") or "9:16", SIZES["9:16"])
    fit = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},format=yuv420p"
    ins, parts = [], []
    for i, p in enumerate((clip, card)):
        ins += ["-i", str(p)]
        if not has_audio(p):
            ins += ["-f", "lavfi", "-t", f"{probe(p)['duration']:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    # Inputs: clip [audio?], card [audio?]. Work out the index of each stream.
    idx, streams = 0, []
    for p in (clip, card):
        v = idx
        a = idx if has_audio(p) else idx + 1
        streams.append((v, a))
        idx += 1 if has_audio(p) else 2
    for n, (v, a) in enumerate(streams):
        parts.append(f"[{v}:v]{fit}[v{n}];[{a}:a]aresample=48000,aformat=channel_layouts=stereo[a{n}]")
    filt = ";".join(parts) + ";[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", filt, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
         "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    print(f"Wrote {out}")
    return out


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="studio film")
    p.add_argument("storyboard")
    p.add_argument("--out", required=True)
    p.add_argument("--stills", default="", help="seconds to draw as pictures, for example 0.5,3,14; leave out to film the video")
    x = p.parse_args(argv)
    sb = json.loads(Path(x.storyboard).read_text(encoding="utf-8"))
    brain = Brain.load(brand_dir(sb.get("brand", ""), BRANDS))
    if x.stills:
        for f in stills(sb, brain, Path(x.out), [float(t) for t in x.stills.split(",")]):
            print("Drew", f)
    else:
        film(sb, brain, Path(x.out))


if __name__ == "__main__":
    main()
