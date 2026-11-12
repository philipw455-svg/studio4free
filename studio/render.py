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
    "overlay": "poster",      # a safe-zone look from overlays.py: banner-safe, glass, lower, wide or poster. "" for the first banner.
    "title_seconds": 1.5,     # poster only: how long the opening title stays before it fades.
    "end_cue": "FOLLOW / SUBSCRIBE",  # shown in the last seconds of a clip that has no next part. "" for none.
    "layout": "banner",       # used when overlay is empty. banner: the first banner look. plain: no banner.
    "fit": "blur",            # plain layout only. blur: whole frame over a blurred copy. crop: fill the frame.
    "focus": None,            # None: follow the faces. Or 0 (left edge) to 1 (right edge), or [second, value] steps.
    "zoom": "Smooth",         # none | Smooth | Slow creep
    "zoom_steps": True,       # a new zoom level every sixth word and at each sentence. False: one gentle move.
    "cut_sound": True,        # a quiet whoosh on each cutaway
    "face_aware": True,       # frame each shot on its largest face and keep the chin above the captions
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
              cue: str = "", look: dict | None = None) -> str:
    W, H = size
    k = H / 1920
    c = (look or {}).get("cap") or {}
    font = c.get("font", style["font"])
    cap, ttl, brand = int(c.get("size", 144 if banner else 92) * k), int(60 * k), int(38 * k)
    cap_y = int(c.get("y", 1320) * k)
    cue_y = int((look or {}).get("cue_y", 1555) * k)
    outline = int(c.get("outline", 9 if banner else 7) * k)
    shadow = int(c.get("shadow", 5 if banner else 3) * k)
    boxed = bool(c.get("box"))
    banner = banner or bool(look)
    place = f"{{\\an5\\pos({W // 2},{cap_y})}}" if banner else ""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{cap},&H00FFFFFF,&H00FFFFFF,{'&H18100C0C' if boxed else '&H00000000'},{'&H18100C0C' if boxed else '&H78000000'},0,0,0,0,100,100,1,0,{3 if boxed else 1},{outline},{shadow},2,{int(100 * k)},{int(100 * k)},{int(H * 0.215)},1
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
        groups = chunks(words, int(style.get("caption_words", 3)), int(c.get("limit", 10 if banner else 16)))
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
                  f"{{\\an5\\pos({W // 2},{cue_y})\\fs{int(cap * 0.5)}\\c{ass_colour(style['accent'])}\\fad(200,0)}}{clean(cue)}")
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


ZOOM_LEVELS = [1.0, 1.13, 1.04, 1.19]
ZOOM_MOVES = {"Smooth": 0.38, "Slow creep": 1.1}   # seconds each zoom step takes


def zoom_plan(words: list, dur: float, kind: str, stepped: bool):
    """The zoom as an ffmpeg expression, and as a function of the clip time for the framing maths.
    Stepped is the zoom of the owner's first clips: a new framing every sixth word and at the start of each
    sentence. The framings cycle through ZOOM_LEVELS, and the last one keeps pushing in slowly to the end."""
    move = ZOOM_MOVES.get(kind) if stepped else None
    if not move or not words:
        if kind == "Slow creep":
            return zoom_expr(kind, dur), lambda t: 1 + 0.08 * t / dur
        if kind == "Smooth":
            return zoom_expr(kind, dur), lambda t: 1 + 0.06 * (1 - (1 - min(t / 1.4, 1)) ** 3)
        return "1", lambda t: 1.0
    keys, n, level, last = [], 0, 0, 0.0
    for i, w in enumerate(words):
        n += 1
        if i and (n >= 6 or re.search(r"[.?!]$", words[i - 1]["w"])):
            t = max(0.0, w["s"] - 0.05)
            if t - last < 0.6 or dur - t < 1.0:
                continue
            level, n, last = level + 1, 0, t
            keys.append((round(t, 2), ZOOM_LEVELS[level % 4] - ZOOM_LEVELS[(level - 1) % 4]))
    linear = kind == "Slow creep"
    end = keys[-1][0] if keys else 0.0
    terms = ["1"]
    for t, dz in keys:
        x = f"clip((t-{t:.2f})/{move}\\,0\\,1)"
        terms.append(f"{dz:+.3f}*" + (x if linear else f"(1-pow(1-{x}\\,3))"))
    terms.append(f"+0.08*clip((t-{end:.2f})/2.5\\,0\\,1)")

    def at(t: float) -> float:
        z = 1.0
        for kt, dz in keys:
            x = min(1.0, max(0.0, (t - kt) / move))
            z += dz * (x if linear else 1 - (1 - x) ** 3)
        return max(1.0, z + 0.08 * min(1.0, max(0.0, (t - end) / 2.5)))

    return "max(1\\,(" + "".join(terms) + "))", at


def steps_at(steps, t: float) -> float:
    """The value of a number or of [second, value, glide] steps at a clip time. It mirrors focus_expr."""
    if isinstance(steps, (int, float, str)):
        return float(steps)
    rows = sorted((float(x[0]), float(x[1]), float(x[2]) if len(x) > 2 else 0.0) for x in steps)
    value = rows[0][1]
    for i, (st, v, d) in enumerate(rows):
        if i and t >= st:
            prev = rows[i - 1][1]
            value = prev + (v - prev) * min(1.0, (t - st) / d) if d > 0 else v
    return value


def cutaway_filters(d, cuts: list, first_input: int, region: tuple, base: str, out: str):
    """Stock clips laid over the speaker for about a second, each on the word it shows.
    A cutaway is {"file": "stock/4344.mp4", "at": 38.0, "seconds": 1.15, "from": 2}; `at` is seconds into the clip."""
    x, y, w, h = region
    inputs, parts, cur = [], [], base
    for i, c in enumerate(cuts):
        at, secs, frm = float(c["at"]), float(c.get("seconds", 1.15)), float(c.get("from", 0))
        path = d / c["file"]
        if not path.exists():
            path = ROOT / c["file"]
        if not path.exists():
            sys.exit(f"The cutaway file is missing: {c['file']}")
        inputs += ["-ss", f"{frm:.2f}", "-t", f"{secs + 0.2:.2f}", "-i", path]
        nxt = out if i == len(cuts) - 1 else f"ct{i}"
        grow = f"(1+0.06*t/{secs:.2f})"
        parts.append(
            f"[{first_input + i}:v]fps=30,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"scale=w='trunc({w}*{grow}/2)*2':h='trunc({h}*{grow}/2)*2':eval=frame,crop={w}:{h},setsar=1,"
            f"setpts=PTS-STARTPTS+{at:.3f}/TB[cv{i}];"
            f"[{cur}][cv{i}]overlay={x}:{y}:enable='between(t,{at:.3f},{at + secs:.3f})':eof_action=pass[{nxt}]")
        cur = nxt
    return inputs, ";".join(parts)


def zoomed(bw: int, bh: int, z: str, w: int, h: int, xoff: str, yoff: str) -> str:
    """Scale the source by the zoom `z` and show a w x h window of it. `xoff` and `yoff` say how far the
    window's left and top edges sit inside the scaled picture, in pixels. ffmpeg's crop cannot follow a
    picture that changes size, so the scaled picture is laid over a fixed canvas instead."""
    return (f"color=black:s={w}x{h}:r=30[zc];"
            f"[0:v]scale=w='trunc({bw}*{z}/2)*2':h='trunc({bh}*{z}/2)*2':eval=frame[zv];"
            f"[zc][zv]overlay=x='-({xoff})':y='-({yoff})':eval=frame:shortest=1")


def even(x: float) -> int:
    return int(x) // 2 * 2


def focus_expr(focus) -> str:
    """Where the crop sits, 0 (left) to 1 (right). One number, or steps for a video that changes camera.
    [[0, 0.5], [8.9, 0.47]] means 0.5 from the start and 0.47 from second 8.9 of the clip.
    A third number glides to the new value over that many seconds, for a speaker who moves: [52.6, 0.4, 1.4]."""
    if isinstance(focus, (int, float, str)):
        return f"{float(focus):.3f}"
    steps = sorted((float(x[0]), float(x[1]), float(x[2]) if len(x) > 2 else 0.0) for x in focus)
    parts = [f"{steps[0][1]:.3f}"]
    for i in range(1, len(steps)):
        t, v, d = steps[i]
        prev = steps[i - 1][1]
        parts.append(f"({prev:.3f}+({v - prev:.3f})*clip((t-{t:.3f})/{d:.3f}\\,0\\,1))" if d > 0 else f"{v:.3f}")
    expr = parts[-1]
    for i in range(len(steps) - 2, -1, -1):
        expr = f"if(lt(t\\,{steps[i + 1][0]:.3f})\\,{parts[i]}\\,{expr})"
    return expr


def render_clip(d, src_info: dict, transcript: dict, style: dict, clip: dict) -> dict:
    style = {**style, **clip.get("style", {})}
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
    safe = style.get("overlay") if H > W else ""
    banner = not safe and style.get("layout", "banner") == "banner" and H > W
    part, parts = int(clip.get("part") or 0), int(clip.get("parts") or 0)
    multi = parts > 1 and 1 <= part <= parts
    # The closing line: only a story with a next part asks for that part. Every other clip asks for a follow.
    cue = f"FOLLOW FOR PART {part + 1}" if multi and part < parts else str(style.get("end_cue", "FOLLOW / SUBSCRIBE"))
    sw, sh = src_info["width"], src_info["height"]
    look = None
    if safe:
        from .overlays import design
        look = design(safe, (W, H), clip.get("title", ""), style, f"PART {part} OF {parts}" if multi else "", (sw, sh))
    ass.write_text(build_ass(style, (W, H), clip.get("title", ""), words, mutes, dur, banner, cue, look), encoding="utf-8")
    (out_dir / f"{stem}.srt").write_text(build_srt(words, dur), encoding="utf-8")

    kind = clip.get("zoom", style.get("zoom", "none"))
    stepped = bool(style.get("zoom_steps", True)) and kind in ZOOM_MOVES
    z, zoom_at = zoom_plan(words, dur, kind, stepped)
    region = (0, 0, W, H)          # where the source picture sits in the frame
    extra, temps = [], []
    cuts = sorted(clip.get("cutaways") or [], key=lambda c: float(c["at"]))
    framing = {}

    def window(bw: int, bh2: int, w: int, h: int, top: int) -> str:
        """The speaker's part of the picture, as the filter that cuts it out. With the face model, each shot
        is framed on its largest face and the chin is kept above the captions. `focus` on a clip sets the
        place across by hand."""
        manual = clip.get("focus", style.get("focus"))
        ay, zz, xoff = ("0.300" if stepped else "0.500"), z, None
        from . import faces
        if style.get("face_aware", True) and faces.available():
            c = (look or {}).get("cap") or {}
            k = H / 1920
            size = c.get("size", 144 if banner else 92) * k
            edge = c.get("outline", 9 if banner else 7) * k
            cap_top = (c.get("y", 1320) * k if (banner or look) else H * 0.785 - size * 0.6) - size * 0.62 - edge
            cue_top = (look or {}).get("cue_y", 1555) * k - size * 0.31 - edge
            shown = bool(style.get("captions", True))

            def limit_at(t: float):
                tops = ([cap_top] if shown else []) + ([cue_top] if cue and t >= dur - 2.7 else [])
                return (min(tops) - top) / h if tops else None

            def by_hand(t: float):
                zt = zoom_at(t)
                mid = steps_at(manual, t) * (1 - w / (bw * zt)) + w / (2 * bw * zt)
                return mid - w / (2 * bw * zt), mid + w / (2 * bw * zt)

            src = d / "source.mp4"
            plan = faces.plan(faces.detect(src, start, dur), faces.camera_cuts(src, start, dur), dur, zoom_at,
                              sw / sh, bh2 / h, w / bw, limit_at,
                              [(float(x["at"]), float(x["at"]) + float(x.get("seconds", 1.15))) for x in cuts],
                              by_hand if manual is not None else None)
            framing.update(plan)
            ay = focus_expr(plan["ay"])
            if any(row[1] != 1.0 for row in plan["z0"] + plan["amp"]):
                zz = f"({focus_expr(plan['z0'])})*(1+(({z})-1)*({focus_expr(plan['amp'])}))"
            if manual is None:
                xoff = f"clip(({focus_expr(plan['center'])})*{bw}*{zz}-{w / 2:.0f}\\,0\\,{bw}*{zz}-{w})"
        if xoff is None:
            xoff = f"({bw}*{zz}-{w})*({focus_expr(manual if manual is not None else 0.5)})"
        return zoomed(bw, bh2, zz, w, h, xoff, f"({bh2}*{zz}-{h})*({ay})")

    if look:
        png = out_dir / f"{stem}-overlay.png"
        look["image"].save(png)
        extra = ["-i", png]
        v = look["video"]
        if v[0] == "wide":
            _, vx, vt, vw, vh, bg = v
            region = (vx, vt, vw, vh)
            sc = max(vw / sw, vh / sh)
            bw, bh2 = even(sw * sc + 1), even(sh * sc + 1)
            video = (zoomed(bw, bh2, z, vw, vh, f"({bw}*{z}-{vw})/2", f"({bh2}*{z}-{vh})/2")
                     + f",pad={W}:{H}:{vx}:{vt}:0x{bg.lstrip('#')},setsar=1[vb];"
                     f"[vb][1:v]overlay=0:0[v0]")
        else:
            top, rh = (v[1], v[2]) if v[0] == "region" else (0, H)
            region = (0, top, W, rh)
            cover = max(W / sw, rh / sh)
            bw, bh2 = even(sw * cover + 1), even(sh * cover + 1)
            video = (window(bw, bh2, W, rh, top) + f",pad={W}:{H}:0:{top}:black,setsar=1[vb];"
                     f"[vb][1:v]overlay=0:0[v0]")
        idx = 2
        if look.get("intro"):
            # The opening title: shown for a moment, then faded out.
            ip = out_dir / f"{stem}-intro.png"
            look["intro"]["image"].save(ip)
            temps.append(ip)
            extra += ["-loop", "1", "-framerate", "30", "-t", f"{dur:.3f}", "-i", ip]
            hold, fade = look["intro"]["hold"], look["intro"]["fade"]
            video = (video[:-4] + f"[s{idx}];[{idx}:v]format=rgba,fade=t=out:st={hold}:d={fade}:alpha=1[in{idx}];"
                     f"[s{idx}][in{idx}]overlay=0:0:eof_action=pass[v0]")
            idx += 1
        if look.get("tag"):
            # The brand tag: starts under the title, then slides to its resting place.
            g = look["tag"]
            tp = out_dir / f"{stem}-tag.png"
            g["image"].save(tp)
            temps.append(tp)
            extra += ["-i", tp]
            p = f"(clip((t-{g['at']})/{g['move']}\\,0\\,1))"
            e = f"({p}*{p}*(3-2*{p}))"
            (x0, y0), (x1, y1) = g["from"], g["to"]
            video = (video[:-4] + f"[s{idx}];[s{idx}][{idx}:v]overlay=x='{x0}+({x1 - x0})*{e}':y='{y0}+({y1 - y0})*{e}':eval=frame[v0]")
    elif banner:
        png = out_dir / f"{stem}-overlay.png"
        make_overlay(png, (W, H), clip.get("title", ""), style, f"PART {part} OF {parts}" if multi else "")
        extra = ["-i", png]
        bh = banner_height((W, H))
        rh = H - bh
        region = (0, bh, W, rh)
        cover = max(W / sw, rh / sh)
        bw, bh2 = even(sw * cover + 1), even(sh * cover + 1)
        video = (window(bw, bh2, W, rh, bh) + f",pad={W}:{H}:0:{bh}:black,setsar=1[vb];"
                 f"[vb][1:v]overlay=0:0[v0]")
    elif style.get("fit") == "crop" or sw / sh <= W / H + 0.01:
        cover = max(W / sw, H / sh)
        bw, bh = even(sw * cover + 1), even(sh * cover + 1)
        video = window(bw, bh, W, H, 0) + ",setsar=1[v0]"
    else:
        fh = even(W * sh / sw)
        video = (zoomed(W, fh, z, W, fh, f"({W}*{z}-{W})/2", f"({fh}*{z}-{fh})/2") + "[fg];"
                 f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=28:4,eq=brightness=-0.22:saturation=0.8[bg];"
                 f"[bg][fg]overlay=0:(H-h)/2,setsar=1[v0]")
    if cuts:
        cut_in, chain = cutaway_filters(d, cuts, 1 + extra.count("-i"), region, "vraw", "vcut")
        extra += cut_in
        if "[vb];[vb]" in video:
            video = video.replace("[vb];[vb]", f"[vraw];{chain};[vcut]", 1)
        else:
            video = video[:-4] + f"[vraw];{chain};[vcut]null[v0]"
    esc = str(ass).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    fonts = str(FONTS).replace("\\", "/").replace(":", "\\:")
    video += f";[v0]ass='{esc}':fontsdir='{fonts}',fps=30,format=yuv420p[v]"
    af = [f"volume=enable='between(t,{w['s']:.2f},{w['e']:.2f})':volume=0" for w in words if id(w) in mutes]
    audio = "[0:a]" + ",".join(af + ["aresample=48000"]) + "[a]"
    whoosh = ROOT / "assets" / "sfx" / "whoosh.mp3"
    if cuts and style.get("cut_sound", True) and whoosh.exists():
        wi = 1 + extra.count("-i")
        extra += ["-i", whoosh]
        audio = (audio[:-3] + "[a0];" + f"[{wi}:a]asplit={len(cuts)}" + "".join(f"[w{i}]" for i in range(len(cuts))) + ";"
                 + ";".join(f"[w{i}]adelay={int(float(c['at']) * 1000)}:all=1,volume=0.22,aresample=48000[x{i}]"
                            for i, c in enumerate(cuts))
                 + ";[a0]" + "".join(f"[x{i}]" for i in range(len(cuts)))
                 + f"amix=inputs={len(cuts) + 1}:duration=first:normalize=0[a]")
    out = out_dir / f"{stem}.mp4"
    run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", d / "source.mp4", *extra,
         "-filter_complex", video + ";" + audio, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "3500k", "-bufsize", "7000k", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", out])
    ass.unlink()
    if banner or look:
        png.unlink()
    for tmp in temps:
        tmp.unlink()
    return {"n": n, "file": f"clips/{out.name}", "srt": f"clips/{stem}.srt", "seconds": round(dur, 1),
            "title": clip.get("title", ""), "muted": len(mutes), "mb": round(out.stat().st_size / 1048576, 1),
            **({"faces": {"checks": framing["checks"], "touch": framing["touch"]}} if framing else {}),
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
        if "faces" in r:
            touch = r["faces"]["touch"]
            print("  Captions: clear of the face in all " + str(r["faces"]["checks"]) + " checks." if not touch else
                  "  Captions touch a face at " + ", ".join(f"{a}-{b}s" for a, b in touch) + ". Look at those frames.",
                  flush=True)
    write_json(d / "rendered.json", done)
