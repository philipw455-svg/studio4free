"""The looks, smart captions, clip versions and the doctor. Run with: python -B -m unittest discover -s tests

The pure tests need Pillow at most. The last class cuts real clips from a generated video and runs only where ffmpeg is installed.
"""
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from studio import common, doctor, faces, overlays, render

BASE = "fab63b4"   # the last commit before the look options. Its overlays are the pictures the old looks must still give.
HAS_PIL = importlib.util.find_spec("PIL") is not None
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
SIZE = (1080, 1920)
STYLE = dict(render.DEFAULT_STYLE)
SAFE = overlays.SAFE


def old_module(name: str):
    """A module of the studio as it was at BASE, or None when git cannot give it."""
    p = subprocess.run(["git", "show", f"{BASE}:studio/{name}.py"], cwd=common.ROOT, capture_output=True)
    if p.returncode:
        return None
    mod = types.ModuleType(f"studio._base_{name}")
    mod.__package__ = "studio"
    exec(compile(p.stdout.decode("utf-8"), f"{name}.py@{BASE}", "exec"), mod.__dict__)
    return mod


def changed(a, b):
    """The box in which two pictures differ, or None when they are the same."""
    from PIL import ImageChops
    most = None   # the largest difference of any channel, so a change of colour counts as much as a change of alpha
    for band in ImageChops.difference(a.convert("RGBA"), b.convert("RGBA")).split():
        most = band if most is None else ImageChops.lighter(most, band)
    return most.getbbox()


def words(*rows):
    return [{"w": w, "s": s, "e": e} for w, s, e in rows]


class LookStyle(unittest.TestCase):
    def test_each_page_name_becomes_an_overlay(self):
        want = {"Poster": "poster", "Banner": "banner-safe", "Glass card": "glass", "Sticker": "sticker", "Frame": "frame",
                "Lower third": "lower", "Wide frame": "wide", "First banner": ""}
        for label, key in want.items():
            self.assertEqual(render.look_style({"overlay": label})["overlay"], key)
        for bad in ("Neon", "", None, 7, ["Poster"]):
            self.assertNotIn("overlay", render.look_style({"overlay": bad}))

    def test_a_full_look(self):
        look = {"overlay": "Glass card", "opts": {"tint": "#FF6AD5", "blur": "Strong", "round": "Square", "junk": 1},
                "capColor": "#6BC7FF", "capY": 40, "zoom": "Slow creep", "captions": "No", "language": "Leave it in",
                "brand": " studio.example ", "descTail": "x", "media": {"banner": None}, "fit": "Fill the frame"}
        self.assertEqual(render.look_style(look), {
            "overlay": "glass", "opts": {"tint": "#ff6ad5", "blur": "Strong", "round": "Square"}, "cap_colour": "#6bc7ff",
            "cap_y": 40.0, "zoom": "Slow creep", "captions": False, "language": "Leave it in", "brand": "studio.example"})

    def test_bad_values_fall_back_to_the_defaults(self):
        look = {"overlay": "Sticker", "opts": {"bg": "red", "tilt": "Sideways"}, "capColor": "#12345", "capY": "40",
                "zoom": "Fast", "captions": True, "language": "Shout", "brand": 5}
        self.assertEqual(render.look_style(look), {"overlay": "sticker", "opts": {}})
        for junk in (None, "Poster", [], 3):
            self.assertEqual(render.look_style(junk), {})
        self.assertEqual(render.look_style({"zoom": "None"}), {"zoom": "none"})
        self.assertEqual(overlays.options("frame", {"color": "#12345g", "width": "Thick"}), {"width": "Thick"})

    def test_two_options_keep_their_older_keys(self):
        self.assertEqual(render.look_style({"overlay": "Poster", "opts": {"color": "#ffffff", "size": "Medium", "hold": "1.5"}}),
                         {"overlay": "poster", "title_seconds": 1.5, "opts": {"color": "#ffffff", "size": "Medium"}})
        self.assertEqual(render.look_style({"overlay": "Poster", "opts": {"hold": 3}})["title_seconds"], 3.0)
        self.assertEqual(render.look_style({"overlay": "Banner", "opts": {"bg": "#FF8A3D", "fg": "#111111", "pos": "Bottom"}}),
                         {"overlay": "banner-safe", "banner": "#ff8a3d", "opts": {"fg": "#111111", "pos": "Bottom"}})

    def test_ink_is_the_pages_rule(self):
        self.assertEqual(overlays.ink("#f8ff7a"), (17, 17, 17, 255))
        self.assertEqual(overlays.ink("#ffffff"), (17, 17, 17, 255))
        self.assertEqual(overlays.ink("#000000"), (255, 255, 255, 255))
        self.assertEqual(overlays.ink("#ff6ad5"), (17, 17, 17, 255))   # luma 0.63
        self.assertEqual(overlays.ink("#2f4a7a"), (255, 255, 255, 255))


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class Looks(unittest.TestCase):
    TITLES = ("Why I quit my job at 30", "The week it all broke and how we got every client back", "")

    def draw(self, name, opts=None, title=TITLES[0], **more):
        return overlays.design(name, SIZE, title, {**STYLE, "opts": opts or {}, **more})

    def test_the_old_looks_draw_the_same_pictures_as_before(self):
        old = old_module("overlays")
        if old is None:
            self.skipTest(f"git cannot show commit {BASE}")
        for name in ("banner-safe", "glass", "lower", "wide", "poster"):
            for title in self.TITLES:
                for part in ("", "PART 1 OF 2"):
                    where = f"{name} / {title!r} / {part!r}"
                    try:
                        was = old.design(name, SIZE, title, STYLE, part, (1920, 1080))
                    except ValueError:
                        # The old Lower third cannot draw an empty title. It still cannot.
                        self.assertRaises(ValueError, overlays.design, name, SIZE, title, STYLE, part, (1920, 1080))
                        continue
                    now = overlays.design(name, SIZE, title, STYLE, part, (1920, 1080))
                    self.assertEqual(now["image"].tobytes(), was["image"].tobytes(), where)
                    self.assertEqual((now["video"], now["cap"], now["cue_y"]), (was["video"], was["cap"], was["cue_y"]), where)
                    if "intro" in was:
                        self.assertEqual(now["intro"]["image"].tobytes(), was["intro"]["image"].tobytes(), where)
                        self.assertEqual((now["intro"]["hold"], now["intro"]["fade"]), (was["intro"]["hold"], was["intro"]["fade"]))
                    self.assertNotIn("blur", now)

    def test_the_default_options_are_todays_poster(self):
        plain = self.draw("poster")
        same = self.draw("poster", {"color": "#ffffff", "size": "Medium", "hold": "2"})
        self.assertEqual(same["image"].tobytes(), plain["image"].tobytes())
        self.assertEqual(same["intro"]["image"].tobytes(), plain["intro"]["image"].tobytes())
        self.assertEqual(same["intro"]["hold"], plain["intro"]["hold"])

    def test_the_first_banner_is_untouched(self):
        from PIL import Image
        old = old_module("render")
        if old is None:
            self.skipTest(f"git cannot show commit {BASE}")
        with tempfile.TemporaryDirectory() as tmp:
            for i, title in enumerate(self.TITLES):
                a, b = Path(tmp) / f"a{i}.png", Path(tmp) / f"b{i}.png"
                old.make_overlay(a, SIZE, title, STYLE, "PART 1 OF 2" if i else "")
                render.make_overlay(b, SIZE, title, STYLE, "PART 1 OF 2" if i else "")
                with Image.open(a) as x, Image.open(b) as y:
                    self.assertEqual(x.tobytes(), y.tobytes())

    def test_each_option_changes_the_picture(self):
        intro = lambda look: look["intro"]["image"]
        whole = lambda look: look["image"]
        cases = [("poster", {"color": "#ff6ad5"}, intro), ("poster", {"size": "Small"}, intro), ("poster", {"size": "Large"}, intro),
                 ("banner-safe", {"bg": "#ff8a3d"}, whole), ("banner-safe", {"fg": "#f8ff7a"}, whole), ("banner-safe", {"pos": "Bottom"}, whole),
                 ("glass", {"tint": "#6bc7ff"}, whole), ("glass", {"round": "Round"}, whole), ("glass", {"round": "Square"}, whole),
                 ("sticker", {"bg": "#ff6ad5"}, whole), ("sticker", {"tilt": "None"}, whole), ("sticker", {"tilt": "Right"}, whole),
                 ("frame", {"color": "#6bc7ff"}, whole), ("frame", {"width": "Thick"}, whole)]
        for name, opts, part in cases:
            self.assertIsNotNone(changed(part(self.draw(name)), part(self.draw(name, opts))), f"{name} {opts}")
        self.assertEqual([self.draw("poster", {"hold": h})["intro"]["hold"] for h in ("1", "1.5", "2", "3")], [1.0, 1.5, 2.0, 3.0])
        self.assertEqual(self.draw("poster", title_seconds=2.5)["intro"]["hold"], 2.5)
        soft, strong = self.draw("glass", {"blur": "Soft"})["blur"], self.draw("glass", {"blur": "Strong"})["blur"]
        self.assertLess(soft["sigma"], strong["sigma"])
        x, y, w, h = strong["box"]
        self.assertEqual((strong["mask"].size, x % 2, y % 2, w % 2, h % 2), ((w, h), 0, 0, 0, 0))
        self.assertTrue(SAFE["left"] - 1 <= x and x + w <= SAFE["right"] and SAFE["top"] <= y and y + h <= SAFE["bottom"])

    def test_a_poster_title_colour_fills_every_line(self):
        look = self.draw("poster", {"color": "#ff6ad5"}, self.TITLES[1])["intro"]["image"]
        self.assertNotIn((255, 227, 0), {c[:3] for _, c in look.getcolors(1 << 24)})

    def test_new_marks_stay_inside_the_safe_zone(self):
        def inside(box, what, top=SAFE["top"], bottom=SAFE["bottom"]):
            self.assertIsNotNone(box, what)
            self.assertTrue(SAFE["left"] <= box[0] and box[2] <= SAFE["right"] and top <= box[1] and box[3] <= bottom, f"{what}: {box}")
        for title in self.TITLES[:2]:
            for tilt in ("Left", "None", "Right"):
                inside(self.draw("sticker", {"tilt": tilt}, title, brand="appnoxi.com")["image"].getbbox(), f"sticker {tilt}")
            for width in ("Thin", "Thick"):
                bare = self.draw("frame", {"width": width}, "", brand="")["image"]
                inside(changed(bare, self.draw("frame", {"width": width}, title, brand="appnoxi.com")["image"]), f"frame {width}")
                inside(changed(bare, self.draw("frame", {"width": width}, title, brand="")["image"]), "frame title", 280, 430)
            bare = self.draw("banner-safe", {"pos": "Bottom"}, "", brand="", logo="")["image"]
            inside(changed(bare, self.draw("banner-safe", {"pos": "Bottom"}, title)["image"]), "banner bottom", 1010, 1230)
        frame = self.draw("frame", {"width": "Thick"}, "")
        self.assertEqual(frame["image"].getpixel((30, 900))[3], 255)       # the side edge
        self.assertEqual(frame["image"].getpixel((540, 1900))[3], 255)     # the bottom edge
        self.assertEqual(frame["image"].getpixel((540, 900))[3], 0)        # the clip shows through
        for name in ("sticker", "frame", "poster"):
            look = self.draw(name)
            y = look["cap"]["y"] / 1920 * 100
            self.assertTrue(58 < y < 63, name)
            self.assertEqual([(b[1], b[3]) for b in look["fixed"]], [(1002, 1062)], name)   # the brand tag never moves
        self.assertTrue(29 < self.draw("banner-safe", {"pos": "Bottom"})["cap"]["y"] / 1920 * 100 < 33)

    def test_a_banner_image_takes_the_place_of_the_title(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "banner.png"
            Image.new("RGB", (540, 180), (255, 0, 255)).save(path)
            for name in ("poster", "banner-safe", "glass", "sticker", "frame"):
                look = self.draw(name, banner_image=str(path))
                self.assertEqual(look["image"].getpixel((540, 271)), (255, 0, 255, 255), name)
                self.assertEqual(look["image"].getpixel((540, 628)), (255, 0, 255, 255), name)   # 540 x 180 fills 1080 x 360
                self.assertEqual(look["free_top"], 630, name)
                self.assertIsNone(look.get("intro"), name)
                self.assertNotIn("blur", look)
                # No title is drawn: the picture is the same for any title.
                self.assertIsNone(changed(look["image"], self.draw(name, title="Other words", banner_image=str(path))["image"]), name)
            with self.assertRaises(SystemExit):
                self.draw("poster", banner_image=str(Path(tmp) / "none.png"))


class CaptionLines(unittest.TestCase):
    TALK = words(("I", 0.5, 0.6), ("quit", 0.6, 0.9), ("my", 0.9, 1.0), ("job,", 1.0, 1.4), ("and", 1.5, 1.6), ("it", 1.6, 1.7),
                 ("was", 1.7, 1.9), ("great.", 1.9, 2.3), ("Then", 2.4, 2.6), ("nothing", 3.5, 3.9), ("happened", 3.9, 4.4))

    def text(self, lines):
        return [" ".join(w["w"] for w in ln["words"]) for ln in lines]

    def test_three_words_at_most_and_breaks_at_commas_sentences_and_pauses(self):
        lines = render.caption_lines(self.TALK, 3, 99)
        self.assertEqual(self.text(lines), ["I quit my", "job,", "and it was", "great.", "Then", "nothing happened"])
        self.assertEqual(self.text(render.caption_lines(self.TALK, 7, 99)), self.text(lines))   # never more than 3
        self.assertEqual(self.text(render.caption_lines(self.TALK, 2, 99))[0], "I quit")

    def test_a_line_shows_just_before_its_first_word_and_stays_until_the_next(self):
        lines = render.caption_lines(self.TALK, 3, 99)
        for ln, nxt in zip(lines, lines[1:]):
            self.assertAlmostEqual(ln["s"], ln["words"][0]["s"] - 0.1)
            self.assertEqual(ln["e"], nxt["s"])
        self.assertAlmostEqual(lines[-1]["s"], 3.4)
        self.assertAlmostEqual(lines[-1]["e"], 4.4 + 0.35)
        self.assertEqual(render.caption_lines(words(("Hi", 0.02, 0.3)))[0]["s"], 0.0)
        self.assertEqual(render.caption_lines([]), [])

    def events(self, **kw):
        style = {**STYLE, **kw.pop("style", {})}
        ass = render.build_ass(style, SIZE, "T", kw.pop("talk", self.TALK), set(), 5.0, cue="", **kw)
        rows = []
        for line in ass.splitlines():
            if line.startswith("Dialogue: 3,"):
                f = line.split(",", 9)
                secs = lambda t: sum(float(x) * m for x, m in zip(t.split(":"), (3600, 60, 1)))
                rows.append((secs(f[1]), secs(f[2]), f[9]))
        return rows

    @unittest.skipUnless(HAS_PIL, "Pillow is not installed")
    def test_the_events_cover_each_line_without_a_gap_and_colour_the_spoken_word(self):
        look = overlays.design("poster", SIZE, "T", STYLE)
        rows = self.events(look=look)
        self.assertAlmostEqual(rows[0][0], 0.4)
        self.assertAlmostEqual(rows[-1][1], 4.75)
        for a, b in zip(rows, rows[1:]):
            self.assertAlmostEqual(a[1], b[0], places=2)
        self.assertNotIn("\\c&H", rows[0][2])                              # shown before the word is said: all white
        self.assertIn("{\\c&H0000E3FF}QUIT{\\c&HFFFFFF&}", rows[2][2])     # today's yellow, as blue-green-red
        self.assertTrue(all("\\pos(540,1163)" in r[2] for r in rows))
        pink = self.events(look=look, style={"cap_colour": "#ff6ad5"})
        self.assertIn("{\\c&H00D56AFF}QUIT", pink[2][2])
        self.assertIn("{\\c&H0000E3FF}QUIT", self.events(look=look, style={"cap_colour": "pink"})[2][2])

    def test_captions_off_draws_none(self):
        for off in (False, "No"):
            self.assertEqual(self.events(style={"captions": off}), [])
        self.assertTrue(self.events(style={"captions": True}))

    @unittest.skipUnless(HAS_PIL, "Pillow is not installed")
    def test_a_dragged_spot_stays_between_16_and_63_percent_and_inside_the_safe_zone(self):
        look = overlays.design("poster", SIZE, "T", STYLE)
        at = lambda spot: {int(r[2].split("\\pos(540,")[1].split(")")[0]) for r in self.events(look=look, spot=spot)}
        self.assertEqual(at(40), {768})
        low, high = at(99).pop(), at(1).pop()
        self.assertLessEqual(low, 0.63 * 1920)
        self.assertLessEqual(low + 60, SAFE["bottom"])
        self.assertGreaterEqual(high, 0.16 * 1920)
        self.assertGreaterEqual(high - 60, SAFE["top"])

    @unittest.skipUnless(HAS_PIL, "Pillow is not installed")
    def test_a_line_moves_off_a_face_in_the_ass_file(self):
        look = overlays.design("poster", SIZE, "T", STYLE)
        face = (340, 700, 740, 1150)
        samples = [(i * 0.25, [face] if 1.4 <= i * 0.25 <= 2.4 else []) for i in range(20)]
        ys = [(a, int(text.split("\\pos(540,")[1].split(")")[0])) for a, b, text in self.events(look=look, faces=samples)]
        self.assertEqual({y for a, y in ys if a < 1.0 or a > 2.8}, {1163})
        moved = {y for a, y in ys if 1.5 <= a <= 2.3}
        self.assertEqual(len(moved), 1)
        self.assertLess(moved.pop(), 700 - 24)


class Placement(unittest.TestCase):
    HALF, SPAN, LO, HI = 85, (240, 840), SAFE["top"] + 85, SAFE["bottom"] - 85
    FACE = (340, 700, 740, 1150)

    def place(self, samples, y=1163, t0=0.0, t1=4.0, fixed=()):
        return render.place_line(t0, t1, y, self.HALF, self.SPAN, samples, 0.25, fixed, self.LO, self.HI)

    def samples(self, box, a, b, n=20):
        return [(i * 0.25, [box] if a <= i * 0.25 <= b else []) for i in range(n)]

    def test_no_face_no_move(self):
        self.assertEqual(self.place(self.samples(self.FACE, 9, 9)), [(0.0, 4.0, 1163)])
        self.assertEqual(self.place([]), [(0.0, 4.0, 1163)])
        beside = (880, 700, 1040, 1150)   # a face beside the line, not over it
        self.assertEqual(self.place(self.samples(beside, 0, 9)), [(0.0, 4.0, 1163)])

    def test_the_line_moves_away_and_comes_back(self):
        segs = self.place(self.samples(self.FACE, 1.5, 2.5))
        self.assertEqual([s[2] for s in segs], [1163, 700 - 24 - 85, 1163])
        self.assertEqual((segs[0][0], segs[-1][1]), (0.0, 4.0))
        for a, b in zip(segs, segs[1:]):
            self.assertEqual(a[1], b[0])
        self.assertLessEqual(segs[1][0], 1.5 - 0.125)   # it has moved before the face arrives
        self.assertGreaterEqual(segs[1][1], 2.5 + 0.125)   # and comes back after the face has gone

    def test_a_short_stay_at_the_own_spot_is_skipped(self):
        self.assertEqual(self.place(self.samples(self.FACE, 0.5, 1.0), t1=1.4), [(0.0, 1.4, 591)])

    def test_the_nearest_clear_spot_can_be_below(self):
        high = (340, 300, 740, 560)
        segs = self.place(self.samples(high, 0, 9), y=500)
        self.assertEqual(segs, [(0.0, 4.0, 560 + 24 + 85)])

    def test_it_clears_the_brand_tag_too(self):
        tag = (400, 1002, 680, 1062)
        face = (340, 1080, 740, 1240)   # the nearest clear spot would sit on the tag
        segs = self.place(self.samples(face, 0, 9), fixed=[tag])
        self.assertEqual(segs, [(0.0, 4.0, 1002 - 85)])

    def test_with_no_clear_spot_it_stays(self):
        huge = (0, 200, 1080, 1400)
        self.assertEqual(self.place(self.samples(huge, 0, 9)), [(0.0, 4.0, 1163)])

    def test_it_never_leaves_the_safe_zone(self):
        for top in range(200, 1300, 37):
            for height in (120, 300, 520, 800):
                for y in (400, 760, 1163):
                    for a, b, at in self.place(self.samples((300, top, 780, top + height), 1.0, 3.0), y=y):
                        self.assertGreaterEqual(at - self.HALF, SAFE["top"])
                        self.assertLessEqual(at + self.HALF, SAFE["bottom"])
                        if at != y:   # a moved line clears the face, with the margin
                            self.assertTrue(at + self.HALF <= top - 24 or at - self.HALF >= top + height + 24)


class Versions(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for p in (mock.patch.object(common, "JOBS", self.tmp), mock.patch.object(render, "probe", return_value={"width": 1280, "height": 720, "duration": 9}),
                  mock.patch.object(render, "render_clip", side_effect=self.fake), mock.patch("sys.stdout", io.StringIO())):
            p.start()
            self.addCleanup(p.stop)
        self.d = self.tmp / "job"
        self.d.mkdir()
        (self.d / "source.mp4").write_bytes(b"")
        common.write_json(self.d / "transcript.json", {"segments": []})
        self.plan({"style": {}, "clips": [{"n": n, "start": n, "end": n + 1, "title": f"Clip {n}"} for n in (1, 2, 3)]})
        self.styles = []

    def plan(self, data):
        common.write_json(self.d / "clips.json", data)

    def fake(self, d, info, transcript, style, clip, check_faces=True):
        self.styles.append(style)
        return {"n": int(clip["n"]), "file": f"clips/clip{int(clip['n']):02d}.mp4", "seconds": 1.0, "title": clip["title"], "muted": 0, "mb": 0.1}

    def rows(self):
        return [(r["n"], r["file"], r["version"]) for r in common.read_json(self.d / "rendered.json")]

    def test_cutting_one_clip_again_keeps_the_others_and_raises_its_version(self):
        render.render("job")
        first = self.rows()
        self.assertEqual(first, [(1, "clips/clip01.mp4", 1), (2, "clips/clip02.mp4", 1), (3, "clips/clip03.mp4", 1)])
        render.render("job", [2])
        self.assertEqual(self.rows(), [(1, "clips/clip01.mp4", 1), (2, "clips/clip02.mp4", 2), (3, "clips/clip03.mp4", 1)])
        render.render("job", [2])
        render.render("job", [3, 2])
        self.assertEqual(self.rows(), [(1, "clips/clip01.mp4", 1), (2, "clips/clip02.mp4", 4), (3, "clips/clip03.mp4", 2)])

    def test_an_entry_from_before_versions_counts_as_1(self):
        common.write_json(self.d / "rendered.json", [{"n": 1, "file": "clips/clip01.mp4"}, {"n": 2, "file": "clips/clip02.mp4"}])
        render.render("job", [1])
        self.assertEqual([r.get("version") for r in common.read_json(self.d / "rendered.json")], [2, None])

    def test_a_full_cut_follows_clips_json(self):
        render.render("job")
        self.plan({"clips": [{"n": 3, "start": 3, "end": 4, "title": "c"}, {"n": 4, "start": 4, "end": 5, "title": "d"}]})
        render.render("job")
        self.assertEqual(self.rows(), [(3, "clips/clip03.mp4", 2), (4, "clips/clip04.mp4", 1)])

    def test_the_look_fills_the_style_and_a_key_written_by_hand_wins(self):
        self.plan({"style": {"brand": "by-hand.example", "title_seconds": 4, "look": {
            "overlay": "Sticker", "opts": {"bg": "#6bc7ff"}, "capColor": "#ff6ad5", "zoom": "None", "captions": "No", "brand": "from-look.example"}},
            "clips": [{"n": 1, "start": 0, "end": 1, "title": "a"}]})
        render.render("job")
        s = self.styles[-1]
        self.assertEqual((s["overlay"], s["opts"], s["cap_colour"], s["zoom"], s["captions"]), ("sticker", {"bg": "#6bc7ff"}, "#ff6ad5", "none", False))
        self.assertEqual((s["brand"], s["title_seconds"], s["accent"]), ("by-hand.example", 4, "#FFE300"))
        self.plan({"clips": [{"n": 1, "start": 0, "end": 1, "title": "a"}]})
        render.render("job")
        self.assertEqual(self.styles[-1], render.DEFAULT_STYLE)   # no look and no keys: today's defaults


class Doctor(unittest.TestCase):
    def shape(self, r):
        self.assertEqual(sorted(r), ["cannot", "missing", "ok"])
        self.assertIs(r["ok"], not r["missing"])
        self.assertEqual(len(r["cannot"]), len(r["missing"]))
        for line in r["cannot"]:
            self.assertRegex(line, r"^[A-Z][^.\n]+ cannot [^.\n]+: [^\n]+\.$")

    def test_the_shape(self):
        self.shape(doctor.check())

    def test_everything_missing(self):
        with mock.patch("shutil.which", return_value=None), mock.patch("importlib.util.find_spec", return_value=None), \
                mock.patch.object(doctor, "_has_zones", return_value=False), mock.patch.object(faces, "MODEL", Path("no-such-model.onnx")):
            r = doctor.check()
        self.shape(r)
        self.assertEqual(r["missing"], ["ffmpeg", "ffprobe", "yt-dlp", "faster-whisper", "onnxruntime", "face model", "Pillow", "tzdata"])
        self.assertEqual(r["cannot"][0], "Clips cannot be cut or re-cut: ffmpeg is missing.")

    def test_an_ffmpeg_without_libass(self):
        no_ass = mock.Mock(stdout=" T. boxblur           V->V       Blur the input.\n .. subtitles        V->V       Render text subtitles.\n")
        with mock.patch("shutil.which", return_value="ffmpeg"), mock.patch("subprocess.run", return_value=no_ass):
            self.assertIn("libass", doctor.check()["missing"])
        has_ass = mock.Mock(stdout=" .. ass               V->V       Render ASS subtitles onto input video using the libass library.\n")
        with mock.patch("shutil.which", return_value="ffmpeg"), mock.patch("subprocess.run", return_value=has_ass):
            self.assertNotIn("libass", doctor.check()["missing"])

    def test_json_output(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            doctor.doctor(True)
        self.shape(json.loads(out.getvalue()))
        with mock.patch("shutil.which", return_value=None), contextlib.redirect_stdout(io.StringIO()) as text:
            doctor.doctor(False)
        self.assertIn("- Clips cannot be cut or re-cut: ffmpeg is missing.", text.getvalue())


class NoDetector(unittest.TestCase):
    def test_a_missing_model_gives_a_reason(self):
        with mock.patch.object(faces, "MODEL", common.ROOT / "assets" / "models" / "none.onnx"):
            self.assertIn("face model is missing", faces.why_not())
        with mock.patch("importlib.util.find_spec", return_value=None):
            self.assertEqual(faces.why_not(), "onnxruntime is missing")

    def test_the_module_only_finds_boxes(self):
        # The owner had frame-following face tracking removed. Nothing in faces.py may plan a crop, a focus or a zoom.
        self.assertEqual(sorted(n for n in vars(faces) if not n.startswith("_") and callable(getattr(faces, n))), ["find", "why_not"])


@unittest.skipUnless(HAS_FFMPEG and HAS_PIL, "ffmpeg, ffprobe or Pillow is not installed")
class RealRender(unittest.TestCase):
    """Cut real clips from a generated test video: one for each look with options that are not the defaults.
    The test video is grey, so a colour found in a frame comes from the look and not from the picture."""
    SECONDS = 2.4

    @classmethod
    def setUpClass(cls):
        from PIL import Image
        cls.tmp = Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        patch = mock.patch.object(common, "JOBS", cls.tmp)
        patch.start()
        cls.addClassCleanup(patch.stop)
        cls.d = d = cls.tmp / "real"
        d.mkdir()
        ff = ["ffmpeg", "-v", "error", "-y"]
        subprocess.run(ff + ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30,hue=s=0", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                             "-t", str(cls.SECONDS), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "source.mp4")], check=True)
        subprocess.run(ff + ["-f", "lavfi", "-i", "color=c=red:size=640x360:rate=30", "-t", "0.6", "-c:v", "libx264", "-preset", "ultrafast",
                             "-pix_fmt", "yuv420p", str(d / "ending.mp4")], check=True)
        Image.new("RGB", (1080, 360), (255, 0, 255)).save(d / "banner.png")
        talk = words(("Nobody", 0.2, 0.5), ("tells", 0.5, 0.75), ("you,", 0.75, 1.0), ("so", 1.05, 1.2), ("listen", 1.2, 1.5), ("up.", 1.5, 1.8), ("Damn.", 1.9, 2.2))
        common.write_json(d / "transcript.json", {"segments": [{"start": 0.0, "end": cls.SECONDS, "words": talk}]})
        look = lambda overlay, opts=None, **more: {"look": {"overlay": overlay, "opts": opts or {}, **more}}
        styles = [
            {},                                                                                      # 1  today's default: Poster
            look("Poster", {"color": "#ff6ad5", "size": "Small", "hold": "1"}),                      # 2
            look("Banner"),                                                                          # 3
            look("Banner", {"bg": "#ff8a3d", "fg": "#111111", "pos": "Bottom"}),                     # 4
            look("Glass card"),                                                                      # 5
            look("Glass card", {"blur": "Strong"}),                                                  # 6  only the blur
            look("Glass card", {"tint": "#6bc7ff", "blur": "Soft", "round": "Square"}),              # 7
            look("Sticker", {"bg": "#6bc7ff", "tilt": "Right"}),                                     # 8
            look("Frame", {"color": "#ff8a3d", "width": "Thick"}, capColor="#ff6ad5", capY=30),      # 9
            {"banner_image": str(d / "banner.png"), "ending_video": str(d / "ending.mp4"), "captions": "No"},   # 10
        ]
        clips = [{"n": i + 1, "start": 0.0, "end": cls.SECONDS, "title": "Short title", "style": s} for i, s in enumerate(styles)]
        clips[7]["volume"] = 0
        common.write_json(d / "clips.json", {"clips": clips})
        cls.log = io.StringIO()
        with contextlib.redirect_stdout(cls.log):
            render.render("real")
        cls.rendered = common.read_json(d / "rendered.json")
        cls.frames = {}

    def frame(self, n, at=1.0):
        from PIL import Image
        if (n, at) not in self.frames:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(at), "-i", str(self.d / f"clips/clip{n:02d}.mp4"), "-frames:v", "1",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
            self.frames[(n, at)] = Image.frombytes("RGB", SIZE, raw)
        return self.frames[(n, at)]

    def apart(self, a, b, box=None):
        """How far two frames are apart inside a box: the mean difference of a pixel, 0 to 255."""
        from PIL import ImageChops, ImageStat
        diff = ImageChops.difference(a, b)
        return sum(ImageStat.Stat(diff.crop(box) if box else diff).mean) / 3

    def test_every_clip_is_a_1080_by_1920_file(self):
        self.assertEqual(len(self.rendered), 10)
        for r in self.rendered:
            info = common.probe(self.d / r["file"])
            self.assertEqual((info["width"], info["height"]), SIZE, r["file"])
            self.assertEqual(r["version"], 1)
            self.assertIn("face", r)

    def test_each_looks_options_change_the_frame(self):
        title, card, video = (60, 280, 1020, 640), (380, 295, 600, 380), (0, 700, 1080, 1000)   # card: inside the glass, above its title
        self.assertGreater(self.apart(self.frame(2), self.frame(1), title), 2)           # Poster: colour and size
        self.assertGreater(self.apart(self.frame(2, 1.9), self.frame(1, 1.9), title), 2)   # Poster: its title has gone after 1 second
        self.assertGreater(self.apart(self.frame(4), self.frame(3)), 10)                  # Banner: bar at the bottom, in orange
        self.assertGreater(self.apart(self.frame(6), self.frame(5), card), 4)             # Glass: the video behind the card is blurred
        self.assertLess(self.apart(self.frame(6), self.frame(5), video), 1)               # ... and only behind the card
        self.assertGreater(self.apart(self.frame(7), self.frame(5), card), 4)             # Glass: tint, blur and corners
        self.assertGreater(self.apart(self.frame(8), self.frame(1), title), 4)            # Sticker
        self.assertGreater(self.apart(self.frame(9), self.frame(1)), 10)                  # Frame
        r, g, b = self.frame(9).getpixel((540, 100))
        self.assertTrue(r > 200 and 100 < g < 175 and b < 110, (r, g, b))                 # the top edge is the frame's orange
        r, g, b = self.frame(4).getpixel((100, 1700))
        self.assertTrue(r > 200 and 100 < g < 175 and b < 110, (r, g, b))                 # the bar fills the bottom

    def test_the_spoken_word_takes_the_caption_colour_at_the_dragged_spot(self):
        # Clip 9 has capColor pink and capY 30 percent: "TELLS" is being said at 0.6 seconds, in a line centred at y 576.
        pink = lambda img, box: sum(1 for r, g, b in img.crop(box).getdata() if r > 215 and 70 < g < 150 and 170 < b < 250)
        at_spot, at_rest = (140, 500, 940, 650), (140, 1080, 940, 1248)
        self.assertGreater(pink(self.frame(9, 0.6), at_spot), 300)
        self.assertEqual(pink(self.frame(9, 0.6), at_rest), 0)
        yellow = lambda img, box: sum(1 for r, g, b in img.crop(box).getdata() if r > 215 and g > 190 and b < 90)
        self.assertGreater(yellow(self.frame(1, 0.6), at_rest), 300)                      # the default: yellow, under the tag

    def test_captions_off_banner_image_and_ending_video(self):
        r, g, b = self.frame(10).getpixel((540, 450))
        self.assertTrue(r > 200 and g < 60 and b > 200, (r, g, b))                        # the banner image, across the top of the safe zone
        caption = (140, 1080, 940, 1248)
        self.assertGreater(self.apart(self.frame(10, 0.6), self.frame(1, 0.6), caption), 4)   # clip 1 has a caption there, clip 10 has none
        yellow = sum(1 for r, g, b in self.frame(10, 0.6).crop(caption).getdata() if r > 215 and g > 190 and b < 90)
        self.assertEqual(yellow, 0)                                                       # no spoken word is lit either
        entry = self.rendered[9]
        self.assertAlmostEqual(entry["seconds"], self.SECONDS + 0.6, delta=0.15)
        self.assertAlmostEqual(common.probe(self.d / entry["file"])["duration"], self.SECONDS + 0.6, delta=0.2)
        r, g, b = self.frame(10, self.SECONDS + 0.3).getpixel((540, 960))
        self.assertTrue(r > 200 and g < 60 and b < 60, (r, g, b))                         # the red ending video plays last

    def test_volume_0_is_silent(self):
        def level(n):
            err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(self.d / f"clips/clip{n:02d}.mp4"), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                                 capture_output=True, text=True).stderr
            return float(err.split("mean_volume:")[1].split("dB")[0])
        self.assertGreater(level(1), -40)
        self.assertLess(level(8), -80)

    def test_faces_were_looked_for(self):
        if faces.why_not():
            self.assertTrue(all(r["faces_checked"] is False and r["face"] is None for r in self.rendered))
            self.assertEqual(self.log.getvalue().count("Faces were not checked"), 1)
        else:
            # The test picture has no face in it. Clip 10 has no captions, so nothing had to be checked there.
            self.assertEqual([r["faces_checked"] for r in self.rendered], [True] * 9 + [False])
            self.assertTrue(all(r["face"] is None for r in self.rendered))

    def test_the_extra_pass_gives_boxes_in_pixels_of_the_finished_frame(self):
        picture = "[0:v]fps=30,scale=3414:1920,crop=1080:1920:1167:0,setsar=1"
        seen = []

        def find(raw):
            seen.append(len(raw))
            # One face in every frame, and one mark too flat to be a face. Sides are parts of the 640 x 480 detector frame.
            return [[(0.1, 0.25, 0.2, 0.5, 0.99), (0.1, 0.6, 0.3, 0.62, 0.99)]] * (len(raw) // (640 * 480 * 3))

        with mock.patch.object(faces, "find", side_effect=find):
            samples = render.face_samples(self.d / "source.mp4", 0.0, self.SECONDS, picture, SIZE)
        self.assertEqual(seen[0] % (640 * 480 * 3), 0)
        self.assertIn(len(samples), (9, 10))                      # four frames a second
        self.assertEqual([t for t, _ in samples][:3], [0.0, 0.25, 0.5])
        # The 1080 x 1920 frame is shown 270 x 480 in the detector frame, so 0.1 of 640 is pixel 256 of 1080.
        self.assertEqual([[round(v) for v in box] for box in samples[0][1]], [[256, 480, 512, 960]])
        self.assertIsNone(render.face_samples(self.d / "none.mp4", 0.0, 1.0, picture, SIZE))

    def test_a_face_moves_the_caption_in_the_real_frame(self):
        d = self.tmp / "moved"
        d.mkdir()
        for name in ("source.mp4", "transcript.json"):
            shutil.copy(self.d / name, d / name)
        common.write_json(d / "clips.json", {"clips": [{"n": 1, "start": 0.0, "end": self.SECONDS, "title": "Short title"}]})
        face = (340, 700, 740, 1180)   # a face over the place where the Poster captions rest
        with mock.patch.object(render, "face_samples", return_value=[(i * 0.25, [face]) for i in range(10)]), contextlib.redirect_stdout(io.StringIO()):
            render.render("moved")
        entry = common.read_json(d / "rendered.json")[0]
        self.assertEqual((entry["face"], entry["faces_checked"]), ([36, 61], True))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.6", "-i", str(d / "clips/clip01.mp4"), "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        from PIL import Image
        img = Image.frombytes("RGB", SIZE, raw)
        yellow = lambda box: sum(1 for r, g, b in img.crop(box).getdata() if r > 215 and g > 190 and b < 90)
        self.assertEqual(yellow((140, 1080, 940, 1248)), 0)        # nothing is left on the face
        self.assertGreater(yellow((140, 532, 940, 676)), 300)      # the line sits above it, 24 pixels clear, inside the safe zone
        self.assertEqual(yellow((140, 677, 940, 890)), 0)          # (the closing line is yellow too, at y 950)

    def test_z_cutting_one_clip_again_writes_over_the_same_file(self):
        target = self.d / "clips/clip02.mp4"
        before = {p.name for p in (self.d / "clips").iterdir()}
        target.write_bytes(b"old")
        with contextlib.redirect_stdout(io.StringIO()):
            render.render("real", [2])
        after = common.read_json(self.d / "rendered.json")
        self.assertEqual([r["file"] for r in after], [r["file"] for r in self.rendered])
        self.assertEqual([r["version"] for r in after], [1, 2] + [1] * 8)
        self.assertEqual({p.name for p in (self.d / "clips").iterdir()}, before)
        self.assertGreater(target.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
