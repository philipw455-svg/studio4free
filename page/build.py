"""Builds page/studio.html from the parts in page/src.

    python page/build.py

design.css, design-consts.js, design-phone.js and design-ui.js are the owner's design, kept word for word.
head.js, core.js and app.js connect that design to the real studio: accounts, jobs, the queue and the schedule.
"""
import pathlib
import re

SRC = pathlib.Path(__file__).parent / "src"
read = lambda name: (SRC / name).read_text(encoding="utf-8")


def between(text, start, end=None):
    a = text.index(start)
    b = text.index(end, a) if end else len(text)
    return text[a:b]


def swap(text, old, new):
    if old not in text:
        raise SystemExit("build: this text is missing from the design: " + old[:70])
    return text.replace(old, new, 1)


ui = read("design-ui.js")

widgets = between(ui, "/* ---------- live bits", "/* ---------- demos")
widgets = swap(widgets, "live.forEach(f => f());", "live.forEach(f => f()); dirty();")
widgets = widgets.replace(between(widgets, "function upload(", "function seg("), "")

demos = between(ui, "/* ---------- demos", "/* ---------- the five setup steps")
demos = demos.replace(between(demos, "function channelsDemo(", "function postDemo("), "")

steps = between(ui, "/* ---------- the five setup steps", "/* ---------- screens")
steps = swap(steps, "Design preview: your files stay in this browser tab. The real app saves them to your studio.",
             "Your files are saved with your studio. Each file can be up to 20 MB.")

vstep = between(ui, "function vStep(", "function vRecap(")
cardrag = between(ui, "// Mouse users drag the clip row sideways.", "function openEditor(")
presets = between(ui, "/* ---------- saved setups", "function vStart(")
presets = re.sub(r"let PRESETS = .*\n", "let PRESETS = [];\n", presets, count=1)
presets = re.sub(r"const keepPresets = .*\n", "const keepPresets = () => { S.set.presets = PRESETS; dirty(); };\n", presets, count=1)
if "let PRESETS = [];" not in presets or "S.set.presets = PRESETS" not in presets:
    raise SystemExit("build: the saved setups block changed")

app = read("app.js")
for mark, part in (("/*__VSTEP__*/", vstep), ("/*__CARDRAG__*/", cardrag), ("/*__PRESETS__*/", presets)):
    app = swap(app, mark, part)

# No preview is on the sign-in screen, and no settings are loaded there. The preview clock waits.
phone = swap(read("design-phone.js"), "  const t = still.matches", "  if (!phones.length){ requestAnimationFrame(tick); return; }\n  const t = still.matches")

script = "\n".join([read("head.js"), read("design-consts.js"), read("core.js"), phone, widgets, demos, steps, app])
css = read("design.css") + read("extra.css")

html = """<title>Studio4Free</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
%s</style>

<div class="wrap">
  <div class="top"><div class="logo">Studio<i>4</i>Free</div><span class="save" id="save" role="status"></span><span class="badge" id="badge" hidden></span></div>
  <nav class="steps tabs" id="tabs" aria-label="Studio sections" hidden></nav>
  <div id="app"></div>
</div>
<nav class="nav" id="nav" hidden><div class="in"><button class="btn ghost" id="bk" type="button">Back</button><span class="why" id="why" role="status"></span><button class="btn pri" id="nx" type="button">Next</button></div></nav>

<script>
%s</script>
""" % (css, script)

out = pathlib.Path(__file__).parent / "studio.html"
out.write_text(html, encoding="utf-8")
print("wrote", out, len(html.encode("utf-8")), "bytes")
