"""The brain check: list every problem in an ad storyboard, in plain words, with the frame number.

Run: python -m studio.brain_check <brand-id> <storyboard.json>

A storyboard is JSON: {"brand", "postAt", "shape", "look", "cast", "endCard", "frames": [...]}.
Each frame: {"n", "start", "end", "picture", "words", "sound"}, and optionally "kit" (names of kit items it shows)
and "box" ([x, y, width, height] of the words, in pixels of the output frame).
"""
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .brain import BRANDS, Brain, brand_dir

MIN_SECONDS = 2.0
# The Reels safe area on a 1080 x 1920 frame: no words in the top 240 px, the bottom 440 px or the right 190 px.
SAFE = {"top": 240, "bottom": 440, "right": 190}
MONTHS = {m: i for i, ms in enumerate([("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
                                       ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
                                       ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"),
                                       ("dec", "december")], 1) for m in ms}
DAYS = {d: i for i, ds in enumerate([("mon", "monday"), ("tue", "tues", "tuesday"), ("wed", "wednesday"),
                                     ("thu", "thur", "thurs", "thursday"), ("fri", "friday"),
                                     ("sat", "saturday"), ("sun", "sunday")]) for d in ds}
DATE = re.compile(r"(?:\b(?P<wd>[A-Za-z]{3,9})\.?,?\s+)?\b(?P<mon>[A-Za-z]{3,9})\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(?P<year>\d{4}))?")
SOON = re.compile(r"\b(coming|soon|countdown|days? left|days? to go|get ready|is almost here|launches|launching)\b", re.I)
DONE = re.compile(r"\b(out now|is here|is live|now live|available now|just launched|launched)\b", re.I)
ROMAN_CLOCK = re.compile(r"\b(XII|XI|IX|X|VIII|VII|VI|IV|V|III|II|I)\s*(?::\s*[0-9IVXL]+|\s*(?:AM|PM|A\.M\.|P\.M\.|o'clock))", re.I)


@dataclass
class Problem:
    frame: object  # the frame number, or None for the whole storyboard
    kind: str
    text: str

    def __str__(self) -> str:
        where = f"Frame {self.frame}" if self.frame is not None else "Whole ad"
        return f"{where}: {self.text}"


def has(text: str, word: str) -> bool:
    """True when the word or phrase is in the text, on word edges, ignoring case and a plural s."""
    if not word:
        return False
    if not re.match(r"[\w@#]", word[0]) or not re.match(r"[\w+]", word[-1]):
        return word.lower() in text.lower()  # emoji and other symbols
    w = re.escape(word.lower()).replace(r"\ ", r"[\s-]+")
    return re.search(rf"(?<![\w@]){w}(?:s|es)?(?![\w+])", text.lower()) is not None


def quote(s: str) -> str:
    return '"' + " / ".join(x.strip() for x in s.splitlines() if x.strip()) + '"'


def claims_in(words: str, claim_words: list[str]) -> list[str]:
    """The claim words and numbers a line uses. A number inside a link (appnoxi.com/go) or a handle does not count."""
    found = [w for w in claim_words if has(words, w)]
    plain = re.sub(r"\S+\.(com|app|io|net|org)\S*|@\w+", " ", words)
    plain = DATE.sub(lambda m: " " if MONTHS.get(m.group("mon").lower()) else m.group(0), plain)  # dates go to the date check
    for m in re.finditer(r"(?<![\w.])(\d+(?:[:.]\d+)?\+?)(?![\w])", plain):
        found.append(m.group(1))
    out = []
    for f in found:  # drop a word already inside a longer phrase that was found ("first" inside "iphone first" etc.)
        if f not in out:
            out.append(f)
    return out


def covering(token: str, facts) -> list:
    t = token.lower().rstrip("+") if token.endswith("+") and token[:-1].isdigit() else token.lower()
    return [f for f in facts if token.lower() in f.keys or t in f.keys]


def check_claims(frames, brain, problems):
    facts, words = brain.facts(), brain.claim_words()
    for fr in frames:
        text = fr.get("words") or ""
        if not text.strip():
            continue
        for bad in brain.never():
            if has(text, bad):
                problems.append(Problem(fr["n"], "claim", f'{quote(text)} says "{bad}", which facts.md lists under Never say. It is not true today.'))
        seen = set()
        for tok in claims_in(text, words):
            hits = covering(tok, facts)
            if not hits:
                problems.append(Problem(fr["n"], "claim", f'{quote(text)} makes a claim ("{tok}") that facts.md does not have. '
                                        "Add the fact with its source and get the owner's yes, or change the line."))
                continue
            if any(h.approved for h in hits):
                continue
            for h in hits:
                if h.text in seen:
                    continue
                seen.add(h.text)
                problems.append(Problem(fr["n"], "claim", f'{quote(text)} uses a fact that still needs the owner\'s yes: "{h.text}"'))


def check_avoid(frames, sb, brain, problems):
    avoid = brain.avoid()
    for fr in frames:
        for part, label in ((fr.get("words") or "", "words"), (fr.get("picture") or "", "picture"), (fr.get("sound") or "", "sound")):
            for w in avoid:
                if has(part, w):
                    problems.append(Problem(fr["n"], "avoid", f'the {label} use "{w}", which is on the avoid list in voice.md.'))
    for key in ("caption", "firstComment", "title"):
        for w in avoid:
            if has(sb.get(key) or "", w):
                problems.append(Problem(None, "avoid", f'the {key} uses "{w}", which is on the avoid list in voice.md.'))


def check_timing(frames, problems):
    for fr in frames:
        text = (fr.get("words") or "").strip()
        if not text:
            continue
        secs = float(fr["end"]) - float(fr["start"])
        if secs < MIN_SECONDS - 1e-6:
            problems.append(Problem(fr["n"], "timing", f"{quote(text)} is on screen for {secs:.1f} seconds. Each line needs at least {MIN_SECONDS:.0f}."))
        lines = [x for x in text.splitlines() if x.strip()]
        if len(lines) > 1:
            problems.append(Problem(fr["n"], "timing", f"{quote(text)} shows {len(lines)} lines at once. The rule is one line per frame."))
        if ROMAN_CLOCK.search(text):
            problems.append(Problem(fr["n"], "clock", f"{quote(text)} writes a clock time in Roman numerals. Use numbers."))


def check_kit(frames, sb, brain, problems):
    retired = [k for k in brain.kit() if k.retired]
    seen = set()  # one problem per frame and item, even when the picture and the kit list both name it
    def scan(text, frame, label):
        for item in retired:
            if (frame, item.name) in seen:
                continue
            for name in item.names():
                if has(text, name):
                    seen.add((frame, item.name))
                    note = f" ({item.note})" if item.note else ""
                    problems.append(Problem(frame, "kit", f'the {label} shows "{name}", which kit.md lists as retired: {item.name}.{note}'))
                    break
    for fr in frames:
        scan(fr.get("picture") or "", fr["n"], "picture")
        scan(" , ".join(fr.get("kit") or []), fr["n"], "kit list")
        scan(" , ".join(fr.get("assets") or []), fr["n"], "asset list")
    for key in ("endCard", "look"):
        scan(sb.get(key) or "", None, key)
    scan(" , ".join(sb.get("cast") or []), None, "cast")


def find_dates(text: str, year: int):
    """Each date written in the text: (the words, the date, the weekday it names or None)."""
    out = []
    for m in DATE.finditer(text):
        mon = MONTHS.get(m.group("mon").lower())
        if not mon:
            continue
        try:
            d = date(int(m.group("year") or year), mon, int(m.group("day")))
        except ValueError:
            continue
        wd = DAYS.get((m.group("wd") or "").lower())
        out.append((m.group(0).strip(), d, wd))
    return out


def check_dates(frames, sb, brain, problems):
    cal = brain.calendar()
    post = None
    if sb.get("postAt"):
        post = datetime.fromisoformat(sb["postAt"]).date()
        for day in cal:
            if day.kind == "quiet" and day.date == post.isoformat():
                problems.append(Problem(None, "date", f"the ad posts on {post:%a %b %d}, a quiet day in calendar.md ({day.what})."))
    year = post.year if post else date.today().year
    texts = [(fr["n"], fr.get("words") or "") for fr in frames] + [(None, sb.get("caption") or "")]
    for n, text in texts:
        if not text.strip():
            continue
        for said, d, wd in find_dates(text, year):
            if wd is not None and d.weekday() != wd:
                problems.append(Problem(n, "date", f'"{said}" names the wrong weekday. {d:%B} {d.day}, {d.year} is a {d:%A}.'))
            for day in cal:
                if any(has(text, k) for k in day.keys) and d.isoformat() != day.date:
                    real = date.fromisoformat(day.date)
                    problems.append(Problem(n, "date", f'"{said}" does not match calendar.md: {day.what} is on {real:%a %b} {real.day}.'))
        if post:
            for day in cal:
                if not any(has(text, k) for k in day.keys):
                    continue
                when = date.fromisoformat(day.date)
                if SOON.search(text) and post > when:
                    problems.append(Problem(n, "date", f"{quote(text)} says it is still coming, but the ad posts on {post:%b} {post.day}, after {day.what.split('(')[0].strip()} ({when:%b} {when.day})."))
                if DONE.search(text) and post < when:
                    problems.append(Problem(n, "date", f"{quote(text)} says it already happened, but the ad posts on {post:%b} {post.day}, before {when:%b} {when.day}."))
    if not sb.get("postAt"):
        problems.append(Problem(None, "date", "the storyboard has no postAt, so the post day was not checked against calendar.md."))


def check_safe(frames, sb, problems):
    if (sb.get("shape") or "9:16") != "9:16":
        return
    for fr in frames:
        box = fr.get("box")
        if not box or not (fr.get("words") or "").strip():
            continue
        x, y, w, h = box
        where = []
        if y < SAFE["top"]:
            where.append(f"the top {SAFE['top']} px")
        if y + h > 1920 - SAFE["bottom"]:
            where.append(f"the bottom {SAFE['bottom']} px")
        if x + w > 1080 - SAFE["right"]:
            where.append(f"the right {SAFE['right']} px")
        if where:
            problems.append(Problem(fr["n"], "safe", f"{quote(fr['words'])} reaches into {' and '.join(where)}, outside the Reels safe area."))


def check(brain: Brain, sb: dict) -> list[Problem]:
    problems: list[Problem] = []
    if sb.get("brand") and sb["brand"] != brain.id:
        problems.append(Problem(None, "brand", f"this storyboard belongs to '{sb['brand']}', not '{brain.id}'. Never mix two brands."))
    frames = sb.get("frames") or []
    if not frames:
        problems.append(Problem(None, "frames", "the storyboard has no frames."))
    check_claims(frames, brain, problems)
    check_avoid(frames, sb, brain, problems)
    check_timing(frames, problems)
    check_kit(frames, sb, brain, problems)
    check_dates(frames, sb, brain, problems)
    check_safe(frames, sb, problems)
    order = {None: -1}
    return sorted(problems, key=lambda p: (order.get(p.frame, p.frame if isinstance(p.frame, (int, float)) else 0)))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("Use: python -m studio.brain_check <brand-id> <storyboard.json>")
        return 2
    brain = Brain.load(brand_dir(argv[0], BRANDS))
    sb = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    problems = check(brain, sb)
    if not problems:
        print("The brain check found no problems.")
        return 0
    print(f"The brain check found {len(problems)} problem{'s' if len(problems) != 1 else ''}:")
    for p in problems:
        print(" -", p)
    return 1


if __name__ == "__main__":
    sys.exit(main())
