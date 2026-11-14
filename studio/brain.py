"""The brand brain: one folder per brand in brands/<brand-id>/, read by every ad session.

The page keeps the same data in its database (`brands/{brand-id}`). `pack` and `unpack` move it between the two.
"""
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .common import ROOT

BRANDS = ROOT / "brands"
FILES = ["profile.md", "facts.md", "rules.md", "voice.md", "kit.md", "calendar.md", "history.md", "results.md"]
ID = re.compile(r"^[a-z]+(-[a-z]+)*$")


def brand_dir(brand: str, root: Path = BRANDS) -> Path:
    if not ID.match(brand or ""):
        sys.exit(f"'{brand}' is not a brand id. Use lower case letters and dashes only, like 'noxi'.")
    d = root / brand
    if not d.is_dir():
        sys.exit(f"There is no brain for '{brand}'. Make the folder {d} first.")
    return d


def section(text: str, title: str) -> str:
    """The text under a '## title' heading, up to the next '## '."""
    m = re.search(rf"^##\s+{re.escape(title)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1) if m else ""


def bullets(text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^\s*-\s+(.*)$", text, re.M)]


def split_list(text: str) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


@dataclass
class Fact:
    text: str
    keys: list
    source: str = ""
    date: str = ""
    approved: bool = False


@dataclass
class KitItem:
    name: str
    status: str = "current"
    kind: str = ""
    files: list = field(default_factory=list)
    aliases: list = field(default_factory=list)
    note: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def retired(self) -> bool:
        return self.status.lower().startswith("retired")

    def names(self) -> list[str]:
        """Every name that points at this item: its title, other names and file names."""
        base = re.sub(r"^(look|font|mascot):\s*", "", self.name, flags=re.I)
        out = [base] + self.aliases + [Path(f.replace("repo:", "")).name for f in self.files]
        return [n for n in out if n]


@dataclass
class Day:
    date: str
    kind: str
    what: str
    keys: list


@dataclass
class Brain:
    id: str
    path: Path
    text: dict

    @classmethod
    def load(cls, path: Path) -> "Brain":
        path = Path(path)
        text = {f: (path / f).read_text(encoding="utf-8") if (path / f).exists() else "" for f in FILES}
        return cls(path.name, path, text)

    def facts(self) -> list[Fact]:
        out = []
        for b in bullets(section(self.text["facts.md"], "Facts")):
            parts = [p.strip() for p in b.split(" · ")]
            f = Fact(parts[0], [])
            for p in parts[1:]:
                k, _, v = p.partition(":")
                k = k.strip().lower()
                if k == "keys":
                    f.keys = [x.lower() for x in split_list(v)]
                elif k == "source":
                    f.source = v.strip()
                elif k == "status":
                    f.approved = v.strip().lower() == "approved"
                elif re.match(r"^\d{4}-\d\d-\d\d$", p):
                    f.date = p
            out.append(f)
        return out

    def avoid(self) -> list[str]:
        words = []
        for b in bullets(section(self.text["voice.md"], "Words to avoid")):
            if not b.lower().startswith("source:"):
                words += split_list(b)
        return words

    def claim_words(self) -> list[str]:
        words = []
        for b in bullets(section(self.text["rules.md"], "Claim words")):
            words += [w.lower() for w in split_list(b)]
        return words

    def kit(self) -> list[KitItem]:
        items = []
        for m in re.finditer(r"^##\s+(.+?)\s*$(.*?)(?=^##\s|\Z)", self.text["kit.md"], re.M | re.S):
            it = KitItem(m.group(1))
            for b in bullets(m.group(2)):
                k, _, v = b.partition(":")
                k, v = k.strip().lower(), v.strip()
                if k == "status":
                    it.status = v
                elif k == "kind":
                    it.kind = v
                elif k == "files":
                    it.files = split_list(v)
                elif k == "also called":
                    it.aliases = split_list(v)
                elif k == "note":
                    it.note = v
                else:
                    it.extra[k] = v
            items.append(it)
        return items

    def looks(self) -> dict:
        """{'Graphite': {'dark': {'ground': '#131517', ...}, 'light': {...}}} for the current looks."""
        out = {}
        for it in self.kit():
            if it.kind != "look" or it.retired:
                continue
            name = re.sub(r"^look:\s*", "", it.name, flags=re.I)
            out[name] = {mode: dict(x.split(" ", 1) for x in split_list(it.extra[mode]))
                         for mode in ("dark", "light") if mode in it.extra}
        return out

    def calendar(self) -> list[Day]:
        days = []
        for b in bullets(section(self.text["calendar.md"], "Dates")):
            parts = [p.strip() for p in b.split(" · ")]
            if len(parts) < 3 or not re.match(r"^\d{4}-\d\d-\d\d$", parts[0]):
                continue
            keys = []
            for p in parts[3:]:
                if p.lower().startswith("keys:"):
                    keys = [k.lower() for k in split_list(p[5:])]
            days.append(Day(parts[0], parts[1].lower(), parts[2], keys))
        return days

    def links(self) -> list[str]:
        return [b.split(" · ")[0].strip() for b in bullets(section(self.text["profile.md"], "Links"))]

    def history(self) -> list[dict]:
        return table(self.text["history.md"])


def table(text: str) -> list[dict]:
    rows = [r for r in text.splitlines() if r.strip().startswith("|")]
    if len(rows) < 2:
        return []
    head = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    out = []
    for r in rows[2:]:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        out.append(dict(zip(head, cells)))
    return out


def add_row(path: Path, cells: list[str]) -> None:
    """Add one row to the table in a history.md or results.md file."""
    clean = [str(c).replace("|", "/").replace("\n", " ").strip() for c in cells]
    text = path.read_text(encoding="utf-8").rstrip("\n")
    path.write_text(text + "\n| " + " | ".join(clean) + " |\n", encoding="utf-8")


def pack(brand: str, root: Path = BRANDS) -> dict:
    """The brain as one page database document. Write it with ArtifactData to brands/{brand-id}."""
    d = brand_dir(brand, root)
    assets = sorted(str(p.relative_to(d)) for p in (d / "assets").rglob("*") if p.is_file()) if (d / "assets").exists() else []
    return {"id": brand, "files": {f: (d / f).read_text(encoding="utf-8") for f in FILES if (d / f).exists()}, "assets": assets}


def unpack(doc: dict, root: Path = BRANDS) -> Path:
    """Write the files of a page database document back into the brand folder."""
    brand = doc.get("id", "")
    if not ID.match(brand):
        sys.exit(f"The document has no usable brand id: '{brand}'.")
    d = root / brand
    d.mkdir(parents=True, exist_ok=True)
    for name, text in (doc.get("files") or {}).items():
        if name in FILES:
            (d / name).write_text(text, encoding="utf-8")
    return d


def show(brand: str) -> None:
    """Print the whole brain, so a session reads every file before it works on an ad."""
    d = brand_dir(brand)
    for f in FILES:
        p = d / f
        print(f"===== {p.relative_to(ROOT)} =====")
        print(p.read_text(encoding="utf-8") if p.exists() else "(missing)")
    print("===== assets =====")
    for p in sorted((d / "assets").rglob("*")):
        if p.is_file():
            print(p.relative_to(d))


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="studio brain")
    p.add_argument("action", choices=["show", "pack", "unpack", "history", "result"])
    p.add_argument("--brand", required=True)
    p.add_argument("--file", help="pack: where to write the JSON; unpack: the JSON to read")
    p.add_argument("--row", nargs="*", default=[], help="history or result: the cells of the new row, in the table's order")
    x = p.parse_args(argv)
    if x.action == "show":
        show(x.brand)
    elif x.action == "pack":
        doc = pack(x.brand)
        out = Path(x.file or f"brands/{x.brand}/.brain.json")
        out.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {out}. Send it to the page with ArtifactData set, collection brands, id {x.brand}.")
    elif x.action == "unpack":
        print("Wrote", unpack(json.loads(Path(x.file).read_text(encoding="utf-8"))))
    else:
        path = brand_dir(x.brand) / ("history.md" if x.action == "history" else "results.md")
        add_row(path, x.row)
        print("Added a row to", path.relative_to(ROOT))
