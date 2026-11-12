"""Step 4: cut each chosen moment into a finished vertical clip.

Each clip gets: a 9:16 frame, a title banner, word-by-word captions,
an optional brand line, an optional zoom, and muted words.
"""
import re
import sys

from .common import FONTS, ROOT, job_dir, probe, read_json, run, write_json

SIZES = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
STRONG = {"fuck", "fucking", "fucked", "fucker", "motherfucker", "shit", "shitty", "bullshit", "bitch",
          "bitches", "asshole", "dick", "pussy", "cunt", "goddamn", "bastard"}
DEFAULT_STYLE = {
    "aspect": "9:16",
    "layout": "banner",       # banner: black title banner with the brand row, video below. plain: no banner.
    "fit": "blur",            # plain layout only. blur: whole frame over a blurred copy. crop: fill the frame.
    "focus": 0.5,             # crop only: 0 is the left edge, 1 is the right edge.
    "zoom": "Smooth",         # none | Smooth | Slow creep
    "captions": True,
    "caption_words": 3,
    "caption_upper": True,
    "font": "Montserrat Black",
    "accent": "#FFE300",      # colour of the word being spoken, and of the bar under the title
    "banner": "#0A090C",      # title banner colour
    "brand": "appnoxi.com",   # text beside the mark in the banner. Empty for none.
    "logo": "assets/brand/mark.png",  # round mark in the banner. Empty for none.
    "language": "Mute it",    # Mute it | Leave it in
}


def ass_colour(hex_colour: str, alpha: int = 0) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def srt_time(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)) % 1000:03d}"


def clean(text: str) -> str:
    return text.replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def clip_words(transcript: dict, start: float, end: float) -> list:
    out = []
    for seg in transcript["segments"]:
        if seg["end"] < start or seg["start"] > end:
            continue
        for w in seg["words"]:
            mid = (w["s"] + w["e"]) / 2
            if start <= mid <= end:
                out.append({"s": max(0.0, w["s"] - start), "e": min(end - start, w["e"] - start), "w": w["w"]})
    return out


def chunks(words: list, size: int, limit: int = 16) -> list:
    groups, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["s"] - w["e"] if i + 1 < len(words) else 9
        ends = bool(re.search(r"[.!?]$", w["w"]))
        if len(cur) >= size or gap > 0.6 or ends or sum(len(x["w"]) for x in cur) >= limit:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def is_strong(word: str) -> bool:
    return re.sub(r"[^a-z]", "", word.lower()) in STRONG


def balance(draw, text: str, font, max_w: float) -> list:
    """Wrap a title. With two lines, pick the break that makes them most even."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if not cur or draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) == 2:
        best = None
        for i in range(1, len(words)):
            a, b = " ".join(words[:i]), " ".join(words[i:])
            wa, wb = draw.textlength(a, font=font), draw.textlength(b, font=font)
            if max(wa, wb) <= max_w and (best is None or max(wa, wb) < best[0]):
                best = (max(wa, wb), [a, b])
        if best:
            lines = best[1]
    return lines


def banner_height(size: tuple) -> int:
    return even(400 * size[0] / 1080)


def make_overlay(path, size: tuple, title: str, style: dict, part_label: str = "") -> None:
    """Draw the still parts of the banner layout: banner, title, bar, brand row and bottom fade."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    k = W / 1080
    bh = banner_height(size)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    h = style["banner"].lstrip("#")
    d.rectangle([0, 0, W, bh], fill=(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255))
    top, end = H - int(230 * k), H - int(60 * k)
    for y in range(top, H):
        a = min(1.0, (y - top) / (end - top))
        d.line([(0, y), (W, y)], fill=(0, 0, 0, int(255 * a ** 1.3)))
    text = " ".join(title.upper().split())
    if text:
        for fs in (64, 58, 52, 46, 40):
            font = ImageFont.truetype(str(FONTS / "Montserrat-ExtraBold.ttf"), int(fs * k))
            lines = balance(d, text, font, W - 200 * k)
            if len(lines) <= 2:
                break
        lines = lines[:3]
        for i, line in enumerate(reversed(lines)):
            d.text((W / 2, 230 * k - i * fs * k * 1.02), line, font=font, fill=(255, 255, 255, 255), anchor="ms")
    if part_label:
        pf = ImageFont.truetype(str(FONTS / "Montserrat-ExtraBold.ttf"), int(30 * k))
        d.text((W / 2, 264 * k), part_label, font=pf, fill=style["accent"], anchor="mm")
    elif text:
        d.rounded_rectangle([W / 2 - 60 * k, 258 * k, W / 2 + 60 * k, 266 * k], radius=4 * k, fill=style["accent"])
    brand = style.get("brand") or ""
    logo = ROOT / style["logo"] if style.get("logo") else None
    mark = Image.open(logo).convert("RGBA").resize((int(60 * k), int(60 * k))) if logo and logo.exists() else None
    if brand or mark:
        bf = ImageFont.truetype(str(FONTS / "Montserrat-SemiBold.ttf"), int(37 * k))
        tw = d.textlength(brand, font=bf) if brand else 0
        gap = 14 * k if (brand and mark) else 0
        x = (W - ((mark.width if mark else 0) + gap + tw)) / 2
        cy = 350 * k
        if mark:
            img.alpha_composite(mark, (int(x), int(cy - mark.height / 2)))
            x += mark.width + gap
        if brand:
            d.text((x, cy), brand, font=bf, fill=(232, 232, 232, 255), anchor="lm")
    img.save(path)


def build_ass(style: dict, size: tuple, title: str, words: list, mutes: set, dur: float, banner: bool = False,
              cue: str = "") -> str:
    W, H = size
    k = H / 1920
    font = style["font"]
    cap, ttl, brand = int((144 if banner else 92) * k), int(60 * k), int(38 * k)
    place = f"{{\\an5\\pos({W // 2},{int(H * 0.6875)})}}" if banner else ""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{cap},&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,0,0,0,0,100,100,1,0,1,{max(3, int((9 if banner else 7) * k))},{max(1, int((5 if banner else 3) * k))},2,{int(50 * k)},{int(50 * k)},{int(H * 0.215)},1
Style: Title,{font},{ttl},&H00FFFFFF,&H00FFFFFF,{ass_colour(style['banner'])},{ass_colour(style['banner'])},0,0,0,0,100,100,1,0,3,{int(22 * k)},0,8,{int(80 * k)},{int(80 * k)},{int(H * 0.105)},1
Style: Brand,{font},{brand},&H30FFFFFF,&H00FFFFFF,&H50000000,&H00000000,0,0,0,0,100,100,2,0,1,{max(2, int(3 * k))},0,2,{int(60 * k)},{int(60 * k)},{int(H * 0.075)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    if title and not banner:
        ev.append(f"Dialogue: 2,{ass_time(0)},{ass_time(dur)},Title,,0,0,0,,{clean(title)}")
    if style.get("brand") and not banner:
        ev.append(f"Dialogue: 1,{ass_time(0)},{ass_time(dur)},Brand,,0,0,0,,{clean(style['brand'])}")
    if style.get("captions", True):
        acc = ass_colour(style["accent"])
        groups = chunks(words, int(style.get("caption_words", 3)), 10 if banner else 16)
        for g, grp in enumerate(groups):
            nxt = groups[g + 1][0]["s"] if g + 1 < len(groups) else dur
            for i, w in enumerate(grp):
                t0 = w["s"]
                t1 = grp[i + 1]["s"] if i + 1 < len(grp) else min(nxt, w["e"] + 0.25)
                if t1 - t0 < 0.04:
                    continue
                parts = []
                for j, x in enumerate(grp):
                    txt = clean(x["w"])
                    if id(x) in mutes:
                        txt = txt[0] + "*" * max(1, len(re.sub(r"\W", "", txt)) - 1)
                    if style.get("caption_upper", True):
                        txt = txt.upper()
                    parts.append(f"{{\\c{acc}}}{txt}{{\\c&HFFFFFF&}}" if j == i else txt)
                pop = "{\\fscx108\\fscy108\\t(0,90,\\fscx100\\fscy100)}" if i == 0 else ""
                ev.append(f"Dialogue: 3,{ass_time(t0)},{ass_time(t1)},Cap,,0,0,0,,{place}{pop}{' '.join(parts)}")
    if cue:
        t0 = max(0.0, dur - 2.6)
        ev.append(f"Dialogue: 4,{ass_time(t0)},{ass_time(dur)},Cap,,0,0,0,,"
                  f"{{\\an5\\pos({W // 2},{int(H * 0.81)})\\fs{int(cap * 0.5)}\\c{ass_colour(style['accent'])}\\fad(200,0)}}{clean(cue)}")
    return head + "\n".join(ev) + "\n"


def build_srt(words: list, dur: float) -> str:
    rows = []
    for n, grp in enumerate(chunks(words, 7), 1):
        rows.append(f"{n}\n{srt_time(grp[0]['s'])} --> {srt_time(min(dur, grp[-1]['e']))}\n{' '.join(w['w'] for w in grp)}\n")
    return "\n".join(rows)


def zoom_expr(kind: str, dur: float) -> str:
    if kind == "Slow creep":
        return f"(1+0.08*t/{dur:.3f})"
    if kind == "Smooth":
        return "(1+0.06*(1-pow(1-min(t/1.4\\,1)\\,3)))"
    return "1"


def even(x: float) -> int:
    return int(x) // 2 * 2


def render_clip(d, src_info: dict, transcript: dict, style: dict, clip: dict) -> dict:
    W, H = SIZES.get(style["aspect"], SIZES["9:16"])
    start, end = float(clip["start"]), float(clip["end"])
    dur = round(end - start, 3)
    if dur <= 0:
        sys.exit(f"Clip {clip.get('n')} ends before it starts.")
    n = int(clip["n"])
    words = clip_words(transcript, start, end)
    asked = {re.sub(r"[^a-z]", "", str(x).lower()) for x in clip.get("mute", [])}
    mutes = set()
    for w in words:
        plain = re.sub(r"[^a-z]", "", w["w"].lower())
        if plain in asked or (style.get("language") == "Mute it" and is_strong(w["w"])):
            mutes.add(id(w))
    out_dir = d / "clips"
    out_dir.mkdir(exist_ok=True)
    stem = f"clip{n:02d}"
    ass = out_dir / f"{stem}.ass"
    banner = style.get("layout", "banner") == "banner" and H > W
    part, parts = int(clip.get("part") or 0), int(clip.get("parts") or 0)
    multi = parts > 1 and 1 <= part <= parts
    cue = f"FOLLOW FOR PART {part + 1}" if multi and part < parts else ""
    ass.write_text(build_ass(style, (W, H), clip.get("title", ""), words, mutes, dur, banner, cue), encoding="utf-8")
    (out_dir / f"{stem}.srt").write_text(build_srt(words, dur), encoding="utf-8")

    z = zoom_expr(clip.get("zoom", style.get("zoom", "none")), dur)
    sw, sh = src_info["width"], src_info["height"]
    extra = []
    if banner:
        png = out_dir / f"{stem}-overlay.png"
        make_overlay(png, (W, H), clip.get("title", ""), style, f"PART {part} OF {parts}" if multi else "")
        extra = ["-i", png]
        bh = banner_height((W, H))
        rh = H - bh
        cover = max(W / sw, rh / sh)
        bw, bh2 = even(sw * cover + 1), even(sh * cover + 1)
        focus = float(clip.get("focus", style.get("focus", 0.5)))
        video = (f"[0:v]scale=w='trunc({bw}*{z}/2)*2':h='trunc({bh2}*{z}/2)*2':eval=frame,"
                 f"crop={W}:{rh}:(iw-{W})*{focus:.3f}:(ih-{rh})/2,pad={W}:{H}:0:{bh}:black,setsar=1[vb];"
                 f"[vb][1:v]overlay=0:0[v0]")
    elif style.get("fit") == "crop" or sw / sh <= W / H + 0.01:
        cover = max(W / sw, H / sh)
        bw, bh = even(sw * cover + 1), even(sh * cover + 1)
        focus = float(clip.get("focus", style.get("focus", 0.5)))
        video = (f"[0:v]scale=w='trunc({bw}*{z}/2)*2':h='trunc({bh}*{z}/2)*2':eval=frame,"
                 f"crop={W}:{H}:(iw-{W})*{focus:.3f}:(ih-{H})/2,setsar=1[v0]")
    else:
        fh = even(W * sh / sw)
        video = (f"[0:v]split=2[a][b];"
                 f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:4,eq=brightness=-0.22:saturation=0.8[bg];"
                 f"[b]scale=w='trunc({W}*{z}/2)*2':h='trunc({fh}*{z}/2)*2':eval=frame,crop={W}:{fh}:(iw-{W})/2:(ih-{fh})/2[fg];"
                 f"[bg][fg]overlay=0:(H-h)/2,setsar=1[v0]")
    esc = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    fonts = str(FONTS).replace("\\", "/").replace(":", "\\:")
    video += f";[v0]ass='{esc}':fontsdir='{fonts}',fps=30,format=yuv420p[v]"
    af = [f"volume=enable='between(t,{w['s']:.2f},{w['e']:.2f})':volume=0" for w in words if id(w) in mutes]
    audio = "[0:a]" + ",".join(af + ["aresample=48000"]) + "[a]"
    out = out_dir / f"{stem}.mp4"
    run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", d / "source.mp4", *extra,
         "-filter_complex", video + ";" + audio, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "3500k", "-bufsize", "7000k", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", out])
    ass.unlink()
    if banner:
        png.unlink()
    return {"n": n, "file": f"clips/{out.name}", "srt": f"clips/{stem}.srt", "seconds": round(dur, 1),
            "title": clip.get("title", ""), "muted": len(mutes), "mb": round(out.stat().st_size / 1048576, 1),
            **({"series": clip.get("series", ""), "part": part, "parts": parts} if multi else {})}


def render(job: str, only: list | None = None) -> None:
    d = job_dir(job)
    for need in ("source.mp4", "transcript.json", "clips.json"):
        if not (d / need).exists():
            sys.exit(f"{need} is missing in {d}. See CLAUDE.md for the step that makes it.")
    plan = read_json(d / "clips.json")
    style = {**DEFAULT_STYLE, **plan.get("style", {})}
    transcript = read_json(d / "transcript.json")
    info = probe(d / "source.mp4")
    done = []
    for clip in plan["clips"]:
        if only and int(clip["n"]) not in only:
            continue
        r = render_clip(d, info, transcript, style, clip)
        done.append(r)
        print(f"Clip {r['n']}: {r['seconds']}s, {r['mb']} MB, {r['muted']} muted words -> {d / r['file']}", flush=True)
    write_json(d / "rendered.json", done)
