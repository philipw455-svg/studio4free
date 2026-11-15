"""Safe-zone overlays: five looks that keep every word clear of the apps' own buttons and text.

The safe box on a 1080 x 1920 frame is x 65..1015 and y 270..1248.
That leaves 14% at the top, 35% at the bottom and 6% at each side free.
It is the strictest set of numbers in common use for Reels, and it also covers Shorts and TikTok.

Each design returns the still picture to lay over the video, where the video goes,
and how the captions look.
"""
from .common import FONTS, ROOT

SAFE = {"left": 65, "right": 1015, "top": 270, "bottom": 1248}
NAMES = {
    "banner-safe": "Banner",
    "glass": "Glass card",
    "lower": "Lower third",
    "wide": "Wide frame",
    "poster": "Poster",
}


def _rgb(hex_colour: str, alpha: int = 255) -> tuple:
    h = hex_colour.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def _font(name: str, size: float):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONTS / name), int(size))


def _wrap(draw, text: str, font, max_w: float) -> list:
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


def _fit(draw, text: str, file: str, sizes: tuple, max_w: float, max_lines: int = 2):
    """Pick the largest size at which the title fits in max_lines lines."""
    for fs in sizes:
        font = _font(file, fs)
        lines = _wrap(draw, text, font, max_w)
        if len(lines) <= max_lines:
            break
    return font, fs, lines[:max_lines + 1]


def _scrim(img, y0: int, y1: int, a0: int, a1: int) -> None:
    """Lay a black fade over rows y0..y1, from alpha a0 to alpha a1."""
    from PIL import Image
    W = img.size[0]
    lo, hi = min(y0, y1), max(y0, y1)
    strip = Image.new("RGBA", (W, hi - lo), (0, 0, 0, 0))
    px = strip.load()
    for y in range(hi - lo):
        t = y / max(1, hi - lo - 1)
        a = int(a0 + (a1 - a0) * t)
        for x in range(W):
            px[x, y] = (0, 0, 0, a)
    img.alpha_composite(strip, (0, lo))


def _mark(style: dict, size: int):
    from PIL import Image
    logo = ROOT / style["logo"] if style.get("logo") else None
    if logo and logo.exists():
        return Image.open(logo).convert("RGBA").resize((size, size))
    return None


def _brand_row(img, draw, style: dict, cx: float, cy: float, k: float, text: str, colour=(236, 236, 236, 255),
               align: str = "center", size: int = 36, mark_size: int = 56) -> None:
    mark = _mark(style, int(mark_size * k))
    font = _font("Montserrat-SemiBold.ttf", size * k)
    tw = draw.textlength(text, font=font) if text else 0
    gap = 14 * k if (text and mark) else 0
    total = (mark.width if mark else 0) + gap + tw
    x = cx - total / 2 if align == "center" else cx
    if mark:
        img.alpha_composite(mark, (int(x), int(cy - mark.height / 2)))
        x += mark.width + gap
    if text:
        draw.text((x, cy), text, font=font, fill=colour, anchor="lm")
    return total


def flash_card(size: tuple, style: dict):
    """A brand card for the last two seconds of a clip.

    It sits at the top of the safe zone, where the opening title was, so it stays clear of the captions.
    """
    from PIL import Image, ImageDraw
    W, H = size
    k = W / 1080
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ink = (12, 12, 12, 255)
    x0, y0, x1, y1 = 65 * k, 290 * k, 1015 * k, 606 * k
    d.rounded_rectangle([x0, y0, x1, y1], radius=36 * k, fill=_rgb(style["accent"]))
    title = " ".join(str(style.get("flash_title", "Remember the night")).upper().split())
    font, fs, lines = _fit(d, title, "Anton-Regular.ttf", (104 * k, 92 * k, 80 * k, 68 * k), (x1 - x0) - 100 * k, 1)
    d.text((W / 2, 424 * k), lines[0], font=font, fill=ink, anchor="ms")
    _brand_row(img, d, style, W / 2, 486 * k, k, style.get("brand") or "", colour=ink, size=40, mark_size=60)
    sub = str(style.get("flash_sub", "The group photo app for nights out"))
    if sub:
        d.text((W / 2, 556 * k), sub, font=_font("Montserrat-SemiBold.ttf", 29 * k), fill=(34, 34, 34, 255), anchor="mm")
    return img


def design(name: str, size: tuple, title: str, style: dict, part_label: str = "", source: tuple = (16, 9)) -> dict:
    from PIL import Image, ImageDraw
    W, H = size
    k = W / 1080
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    text = " ".join(title.upper().split())
    accent = _rgb(style["accent"])
    brand = style.get("brand") or ""
    tag = "  ·  ".join(x for x in (part_label, brand) if x)
    white = (255, 255, 255, 255)
    cap = {"font": "Montserrat Black", "size": 138, "y": 1150, "outline": 9, "shadow": 5, "box": False, "limit": 10}
    video = ("full",)
    cue_y = 1010

    if name == "banner-safe":
        # A black banner holds the title and the brand row. The video fills the frame below it.
        bh = int(560 * k)
        d.rectangle([0, 0, W, bh], fill=_rgb(style["banner"]))
        font, fs, lines = _fit(d, text, "Montserrat-ExtraBold.ttf", (64 * k, 58 * k, 52 * k, 46 * k), W - 200 * k)
        for i, line in enumerate(reversed(lines[:2])):
            d.text((W / 2, 420 * k - i * fs * 1.04), line, font=font, fill=white, anchor="ms")
        d.rounded_rectangle([W / 2 - 60 * k, 446 * k, W / 2 + 60 * k, 454 * k], radius=4 * k, fill=accent)
        _brand_row(img, d, style, W / 2, 506 * k, k, tag)
        _scrim(img, H - int(230 * k), H - int(60 * k), 0, 255)
        d.rectangle([0, H - int(60 * k), W, H], fill=(0, 0, 0, 255))
        video = ("region", bh, H - bh)
        cap.update(y=1150)

    elif name == "glass":
        # A see-through dark card floats over the video. It holds the title and the brand row.
        _scrim(img, 0, int(640 * k), 110, 0)
        _scrim(img, int(900 * k), int(1320 * k), 0, 120)
        _scrim(img, int(1320 * k), H, 120, 120)
        x0, y0, x1, y1 = 65 * k, 280 * k, 1015 * k, 556 * k
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([x0, y0, x1, y1], radius=40 * k, fill=(20, 16, 44, 150), outline=(255, 255, 255, 100), width=max(2, int(2 * k)))
        cd.line([(x0 + 44 * k, y0 + 2 * k), (x1 - 44 * k, y0 + 2 * k)], fill=(255, 255, 255, 170), width=max(2, int(2 * k)))
        img.alpha_composite(card)
        font, fs, lines = _fit(d, text, "Montserrat-ExtraBold.ttf", (56 * k, 50 * k, 44 * k), (x1 - x0) - 90 * k)
        for i, line in enumerate(reversed(lines[:2])):
            d.text((W / 2, 440 * k - i * fs * 1.08), line, font=font, fill=white, anchor="ms")
        _brand_row(img, d, style, W / 2, 500 * k, k, tag, size=32, mark_size=48)
        cap.update(y=1140, size=132)

    elif name == "lower":
        # The video stays clear at the top. A small brand pill sits above, and the title sits low on the left.
        _scrim(img, 0, int(520 * k), 90, 0)
        _scrim(img, int(820 * k), int(1300 * k), 0, 150)
        _scrim(img, int(1300 * k), H, 150, 150)
        pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill)
        bf = _font("Montserrat-SemiBold.ttf", 32 * k)
        tw = d.textlength(tag, font=bf) + (48 * k + 14 * k if _mark(style, 8) else 0)
        px0, px1 = W / 2 - tw / 2 - 26 * k, W / 2 + tw / 2 + 26 * k
        pd.rounded_rectangle([px0, 280 * k, px1, 352 * k], radius=36 * k, fill=(14, 12, 28, 170), outline=(255, 255, 255, 90), width=max(2, int(2 * k)))
        img.alpha_composite(pill)
        d = ImageDraw.Draw(img)
        _brand_row(img, d, style, W / 2, 316 * k, k, tag, size=32, mark_size=48)
        font, fs, lines = _fit(d, text, "Montserrat-ExtraBold.ttf", (50 * k, 46 * k, 42 * k), 760 * k)
        lines = lines[:2]
        base = 1232 * k
        top = base - len(lines) * fs * 1.1 + fs * 0.25
        d.rounded_rectangle([65 * k, top, 77 * k, base + 6 * k], radius=6 * k, fill=accent)
        for i, line in enumerate(reversed(lines)):
            d.text((100 * k, base - i * fs * 1.1), line, font=font, fill=white, anchor="ls")
        cap.update(y=980, size=124)
        cue_y = 850

    elif name == "wide":
        # The whole camera shot shows in a rounded frame. The title sits above it and the captions sit below it.
        bg = _rgb(style["banner"])
        inset = int(40 * k)
        vw = W - 2 * inset
        vh = int(min(vw * source[1] / source[0], 700 * k)) // 2 * 2
        vt = int(500 * k)
        frame = Image.new("RGBA", (W, H), bg)
        hole = Image.new("L", (W, H), 255)
        ImageDraw.Draw(hole).rounded_rectangle([inset, vt, inset + vw, vt + vh], radius=int(30 * k), fill=0)
        frame.putalpha(hole)
        img.alpha_composite(frame)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([inset, vt, inset + vw, vt + vh], radius=int(30 * k), outline=(255, 255, 255, 60), width=max(2, int(2 * k)))
        _brand_row(img, d, style, W / 2, 302 * k, k, tag, size=32, mark_size=48)
        font, fs, lines = _fit(d, text, "Montserrat-ExtraBold.ttf", (60 * k, 54 * k, 48 * k, 42 * k), W - 180 * k)
        for i, line in enumerate(reversed(lines[:2])):
            d.text((W / 2, 462 * k - i * fs * 1.04), line, font=font, fill=white, anchor="ms")
        video = ("wide", inset, vt, vw, vh, style["banner"])
        cap.update(y=min(1180, int((vt + vh) / k) + 110), size=132, outline=0, shadow=0)
        cue_y = int((vt + vh) / k) - 70

    elif name == "poster":
        # A loud title in tall letters opens the clip, top left, then fades after 2 seconds.
        # The yellow brand tag never moves. It sits in the middle, and the captions sit under it.
        # The owner asked for this on 12 Nov 2026: "move the caption under the app noxi, dont move app noxis banner".
        _scrim(img, int(940 * k), int(1320 * k), 0, 90)
        _scrim(img, int(1320 * k), H, 90, 90)
        intro = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        di = ImageDraw.Draw(intro)
        _scrim(intro, 0, int(760 * k), 205, 0)
        font, fs, lines = _fit(di, text, "Anton-Regular.ttf", (112 * k, 100 * k, 88 * k, 76 * k), 900 * k)
        lines = lines[:2]
        first = 300 * k + fs * 0.86
        for i, line in enumerate(lines):
            last = i == len(lines) - 1
            di.text((70 * k, first + i * fs * 1.08), line, font=font, fill=accent if last else white, anchor="ls")
        ty = first + (max(1, len(lines)) - 1) * fs * 1.08 + 34 * k
        bf = _font("Montserrat-ExtraBold.ttf", 30 * k)
        mark = _mark(style, int(44 * k))
        tw = d.textlength(tag, font=bf)
        tag_w, tag_h = int(tw + 44 * k + (mark.width + 12 * k if mark else 0)), int(60 * k)
        chip = Image.new("RGBA", (tag_w, tag_h), (0, 0, 0, 0))
        dc = ImageDraw.Draw(chip)
        dc.rounded_rectangle([0, 0, tag_w - 1, tag_h - 1], radius=12 * k, fill=accent)
        x = 22 * k
        if mark:
            chip.alpha_composite(mark, (int(x), int(8 * k)))
            x += mark.width + 12 * k
        dc.text((x, tag_h / 2), tag, font=bf, fill=(12, 12, 12, 255), anchor="lm")
        # From the top: the tag at 1002 to 1062, then the caption box down to the safe-zone edge at 1248.
        if tag:
            img.alpha_composite(chip, (int((W - tag_w) / 2), int(1002 * k)))
        # One line only: a caption that wraps onto a second line would rise over the tag.
        cap.update(y=1163, size=112, box=True, outline=16, shadow=0, line_px=850)
        cue_y = 950
        hold = float(style.get("title_seconds", 2.0))
        return {"image": img, "video": video, "cap": cap, "cue_y": cue_y, "intro": {"image": intro, "hold": hold, "fade": 0.4}}

    else:
        raise ValueError(f"Unknown overlay: {name}")

    return {"image": img, "video": video, "cap": cap, "cue_y": cue_y}
