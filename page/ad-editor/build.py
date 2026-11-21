"""Build the Ad Maker page: python page/ad-editor/build.py

Writes page/ad-editor/dist/ (git ignores it): index.html and brands.json, the brands with their Never say and avoid lists,
which the page uses to warn while the owner types. Publish dist/index.html with brands.json as `files`, to the URL in CLAUDE.md.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from studio.brain import BRANDS, Brain  # noqa: E402

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copy(HERE / "editor.html", DIST / "index.html")
    brands = []
    for d in sorted(p for p in BRANDS.iterdir() if p.is_dir()):
        brain = Brain.load(d)
        brands.append({"id": brain.id, "name": brain.id.capitalize(), "never": brain.never(), "avoid": brain.avoid(), "links": brain.links()})
    (DIST / "brands.json").write_text(json.dumps(brands, ensure_ascii=False), encoding="utf-8")
    print(f"Built {DIST} for brands: {', '.join(b['id'] for b in brands)}")


if __name__ == "__main__":
    main()
