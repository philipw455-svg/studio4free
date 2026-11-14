"""Build the Ad scene editor page: python page/ad-editor/build.py

Writes page/ad-editor/dist/ (git ignores it): the editor, the ad templates, and each brand's assets and brand.json.
Publish dist/index.html with every other file in dist/ as `files`, to the editor's artifact URL in CLAUDE.md.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from studio.brain import BRANDS, Brain  # noqa: E402
from studio.film import STYLES, brand_data  # noqa: E402

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "ads").mkdir(parents=True)
    shutil.copy(HERE / "editor.html", DIST / "index.html")
    ads = ROOT / "studio" / "ads"
    shutil.copy(ads / "runtime.js", DIST / "ads" / "runtime.js")
    for key in STYLES.values():
        if (ads / key / "template.html").exists():
            (DIST / "ads" / key).mkdir()
            shutil.copy(ads / key / "template.html", DIST / "ads" / key / "template.html")
    index = []
    for d in sorted(p for p in BRANDS.iterdir() if p.is_dir()):
        brain = Brain.load(d)
        out = DIST / "brand" / brain.id
        retired = {Path(f).name for k in brain.kit() if k.retired for f in k.files}  # retired files never ship
        shutil.copytree(d / "assets", out / "assets", ignore=lambda _dir, names: [n for n in names if n in retired])
        data = brand_data(brain, {})
        rel = lambda uri: uri.replace((d.resolve().as_uri() + "/"), "")  # noqa: E731
        data["fonts"] = [{"family": f["family"], "url": rel(f["url"])} for f in data["fonts"]]
        data["files"] = sorted(rel(u) for u in data["files"].values() if Path(rel(u)).name not in retired)
        data["base"] = ""
        data["links"] = brain.links()
        data["avoid"] = brain.avoid()
        data["never"] = brain.never()
        data["logos"] = {look: next((f for k in brain.kit() if k.kind == "logo" and not k.retired
                                     for f in k.files if look.lower() in f.lower()), data["logo"]) for look in data["looks"]}
        data["screens"] = next((k.files for k in brain.kit() if k.name == "App screenshots" and not k.retired), [])
        data["examples"] = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((d / "storyboards").glob("example-*.json"))]
        (out / "brand.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        index.append(brain.id)
    (DIST / "brands.json").write_text(json.dumps(index), encoding="utf-8")
    files = sorted(str(p.relative_to(DIST)) for p in DIST.rglob("*") if p.is_file() and p.name != "index.html")
    print(f"Built {DIST} with {len(files)} files for brands: {', '.join(index)}")


if __name__ == "__main__":
    main()
