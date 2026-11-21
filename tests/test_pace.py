"""The hook, the pace, the simple camera and the craft check (the owner's request of 20 Nov 2026)."""
import contextlib
import io
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from studio import common, craft, pace, render


def w(text, s, e):
    return {"w": text, "s": s, "e": e}


def transcript(words):
    return {"segments": [{"start": 0.0, "end": 200.0, "words": words}]}


TALK = [w("So", 10.0, 10.2), w("I", 10.25, 10.35), w("walked", 10.4, 10.8), w("in.", 10.8, 11.1),
        # a 1.9 second pause
        w("And", 13.0, 13.2), w("there", 13.25, 13.5), w("he", 13.55, 13.7), w("was,", 13.7, 14.0),
        w("eating", 14.1, 14.5), w("my", 14.55, 14.7), w("eggs.", 14.7, 15.2)]


class Pieces(unittest.TestCase):
    def test_a_long_pause_is_cut_short(self):
        p = pace.story_pieces(TALK, 10.0, 15.3, 0.7, 0.3)
        self.assertEqual(len(p), 2)
        kept = p[1][0] - 11.1 + 13.0 - p[0][1]    # air left on both sides of the cut
        self.assertAlmostEqual(13.0 - p[1][0] + p[0][1] - 11.1, 0.3, places=2)
        self.assertGreater(kept, 0)

    def test_short_pauses_stay(self):
        self.assertEqual(pace.story_pieces(TALK, 10.0, 15.3, 2.5, 0.3), [(10.0, 15.3)])

    def test_trim_off_keeps_the_clip_whole(self):
        self.assertEqual(pace.story_pieces(TALK, 10.0, 15.3, 0, 0.3), [(10.0, 15.3)])

    def test_an_um_is_cut_out(self):
        talk = [w("I", 1.0, 1.1), w("was,", 1.15, 1.4), w("um,", 1.5, 1.9), w("there.", 2.0, 2.4)]
        p = pace.story_pieces(talk, 1.0, 2.5, 0.7, 0.3, fillers=True)
        self.assertEqual(len(p), 2)
        self.assertLessEqual(p[0][1], 1.5)       # the cut starts before the um
        self.assertGreaterEqual(p[1][0], 1.9)    # and ends after it
        words = pace.remap(transcript(talk), p)["segments"][0]["words"]
        self.assertNotIn("um,", [x["w"] for x in words])

    def test_an_um_stays_when_cut_fillers_is_off(self):
        talk = [w("I", 1.0, 1.1), w("was,", 1.15, 1.4), w("um,", 1.5, 1.9), w("there.", 2.0, 2.4)]
        self.assertEqual(pace.story_pieces(talk, 1.0, 2.5, 0.7, 0.3), [(1.0, 2.5)])

    def test_dead_air_at_both_ends_is_cut(self):
        p = pace.story_pieces(TALK, 8.0, 18.0, 0, 0.3, dead=True)
        self.assertAlmostEqual(p[0][0], 10.0 - pace.LEAD)
        self.assertAlmostEqual(p[-1][1], 15.2 + pace.TAIL)

    def test_a_clip_that_only_loses_its_ends_plays_the_source_itself(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        src, s, e, _ = pace.prepare(d, {"n": 1, "start": 9.0, "end": 11.1}, transcript(TALK), {"cut_dead": True})
        self.assertEqual(src, d / "source.mp4")
        self.assertAlmostEqual(s, 10.0 - pace.LEAD)

    def test_the_hook_plays_first(self):
        clip = {"n": 1, "start": 10.0, "end": 15.3, "hook": {"start": 13.0, "end": 15.2}}
        p = pace.plan(clip, transcript(TALK), {"trim_pauses": 0.7})
        self.assertEqual(p[0], (13.0, 15.2))
        self.assertEqual(p[1][0], 10.0)

    def test_a_hook_too_long_or_too_short_stops(self):
        for h in ({"start": 10.0, "end": 15.3}, [13.0, 13.5]):
            with self.assertRaises(ValueError):
                pace.hook_span({"n": 1, "hook": h})

    def test_hook_start_means_no_repeat(self):
        self.assertIsNone(pace.hook_span({"n": 1, "hook": "start"}))

    def test_remap_puts_the_hook_words_first_and_shifts_the_story(self):
        pieces = [(13.0, 15.2), (10.0, 11.25), (12.85, 15.3)]
        out = pace.remap(transcript(TALK), pieces)["segments"][0]["words"]
        self.assertEqual([x["w"] for x in out[:4]], ["And", "there", "he", "was,"])
        self.assertAlmostEqual(out[0]["s"], 0.0)
        so = next(x for x in out if x["w"] == "So")
        self.assertAlmostEqual(so["s"], 2.2, places=2)        # right after the 2.2 second hook
        second_and = [x for x in out if x["w"] == "And"][1]
        self.assertAlmostEqual(second_and["s"], 2.2 + 1.25 + 0.15, places=2)
        self.assertEqual(len(out), len(TALK) + 7)


class SimpleCamera(unittest.TestCase):
    words = [w(x, i * 0.4, i * 0.4 + 0.35) for i, x in enumerate(
        "one two three four five six seven eight nine ten. eleven twelve. thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty.".split())]

    def steps(self, **kw):
        z, at = render.zoom_plan(self.words, 9.0, "Smooth", True, 0.5, 4.0, **kw)
        return z.count("(3-2*")   # each smooth step eases with one smoothstep term

    def test_the_first_clips_step_every_sixth_word(self):
        self.assertGreaterEqual(self.steps(), 3)

    def test_the_new_default_steps_only_at_sentences_with_a_gap(self):
        d = render.DEFAULT_STYLE
        n = self.steps(every=d["zoom_every"], gap=d["zoom_gap"], levels=d["zoom_levels"])
        self.assertLessEqual(n, 2)
        self.assertLess(n, self.steps())

    def test_two_levels_never_go_past_the_top_one(self):
        z, at = render.zoom_plan(self.words, 9.0, "Smooth", True, 0.5, 4.0, 0, 0.0, [1.0, 1.12])
        self.assertLessEqual(max(at(t / 10) for t in range(0, 70)), 1.0 + 0.06 + 0.001)


class Craft(unittest.TestCase):
    style = {**render.DEFAULT_STYLE}

    def good(self, **more):
        return {"n": 1, "start": 10.0, "end": 15.3, "hook": {"start": 13.0, "end": 15.2}, "payoff": "eating my eggs.",
                "title": "He was eating my eggs", **more}

    def long_talk(self):
        # 14 seconds of steady talk, so the length and pace checks pass
        words = [w(f"word{i}" + ("." if i % 7 == 6 else ""), 10 + i * 0.4, 10 + i * 0.4 + 0.35) for i in range(36)]
        words[-1]["w"] = "eggs."
        words[-2]["w"] = "my"
        words[-3]["w"] = "eating"
        return transcript(words)

    def test_a_good_clip_passes(self):
        t = self.long_talk()
        clip = self.good(start=10.0, end=24.4, hook={"start": 21.6, "end": 24.35}, payoff="eating my eggs.", title="Eating my eggs")
        self.assertEqual(craft.problems(clip, t, self.style, stock={}), [])

    def test_no_hook_no_payoff_and_a_flat_end_are_named(self):
        t = self.long_talk()
        clip = {"n": 1, "start": 10.0, "end": 23.0, "title": "Eating my eggs"}
        found = " ".join(craft.problems(clip, t, self.style, stock={}))
        self.assertIn("no hook", found)
        self.assertIn("payoff", found)
        self.assertIn("finished sentence", found)

    def test_slop_words_in_a_title_and_a_description(self):
        t = self.long_talk()
        clip = self.good(start=10.0, end=24.4, hook={"start": 21.6, "end": 24.35}, title="You won't believe his eggs!")
        post = {"description": "This changed everything — #viral #fyp", "title": "Eggs"}
        found = " ".join(craft.problems(clip, t, self.style, post, stock={}))
        for bit in ("you won't believe", "exclamation", "this changed everything", "long dash", "#viral", "credit line"):
            self.assertIn(bit, found.lower())

    def test_a_cutaway_in_the_opening_and_an_unknown_stock_clip(self):
        t = self.long_talk()
        clip = self.good(start=10.0, end=24.4, hook={"start": 21.6, "end": 24.35}, title="Eating my eggs",
                         cutaways=[{"file": "stock/999.mp4", "at": 1.0, "seconds": 1, "word": "eggs"}])
        found = " ".join(craft.problems(clip, t, self.style, stock={"4344": "a club"}))
        self.assertIn("first 3 seconds", found)
        self.assertIn("not in assets/stock.json", found)

    def test_a_busy_camera_is_named(self):
        t = self.long_talk()
        clip = self.good(start=10.0, end=24.4, hook={"start": 21.6, "end": 24.35}, title="Eating my eggs")
        found = " ".join(craft.problems(clip, t, {**self.style, "zoom_every": 6, "zoom_gap": 0}, stock={}))
        self.assertIn("zoom is busy", found)

    def test_a_title_with_no_spoken_word(self):
        t = self.long_talk()
        clip = self.good(start=10.0, end=24.4, hook={"start": 21.6, "end": 24.35}, title="Breakfast betrayal")
        self.assertIn("No word of the on-screen title", " ".join(craft.problems(clip, t, self.style, stock={})))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is not installed")
class RealHook(unittest.TestCase):
    """A real cut with a hook and a trimmed pause: the clip is shorter than its span, and the hook plays first."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        patch = mock.patch.object(common, "JOBS", cls.tmp)
        patch.start()
        cls.addClassCleanup(patch.stop)
        cls.d = d = cls.tmp / "hook"
        d.mkdir()
        # A source whose picture is black for 12 seconds and white after, so a frame shows which part plays.
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:size=1280x720:rate=30:d=12",
                        "-f", "lavfi", "-i", "color=c=white:size=1280x720:rate=30:d=8", "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:d=20",
                        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "source.mp4")], check=True)
        talk = TALK[:4] + [w("um,", 11.6, 12.0)] + TALK[4:] + [w("Then", 16.0, 16.3), w("white.", 16.3, 16.8)]
        common.write_json(d / "transcript.json", transcript(talk))
        common.write_json(d / "clips.json", {"style": {"captions": "No"}, "clips": [
            {"n": 1, "start": 10.0, "end": 15.3, "title": "Eggs", "hook": {"start": 16.0, "end": 17.8}}]})
        with contextlib.redirect_stdout(io.StringIO()):
            render.render("hook")
        cls.r = common.read_json(d / "rendered.json")[0]

    def frame_level(self, at):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(at), "-i", str(self.d / "clips/clip01.mp4"), "-frames:v", "1",
                              "-vf", "crop=200:200:440:1400,scale=1:1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, check=True).stdout
        return raw[0]

    def test_the_clip_is_the_hook_plus_the_trimmed_story(self):
        # 1.8 s of hook, then the story from 10.0 to 15.3, less the pause and the um between "in." (11.1) and "And" (13.0),
        # of which 0.3 seconds stay.
        self.assertTrue(self.r.get("hook"))
        self.assertIn("pieces", self.r)
        expect = 1.8 + (15.3 - 10.0) - (13.0 - 11.1 - 0.3)   # the dead-air cut only shortens: 10.0 and 15.3 already hug the words
        self.assertAlmostEqual(self.r["seconds"], expect, delta=0.25)

    def test_the_hook_plays_first(self):
        self.assertGreater(self.frame_level(0.5), 150)    # the white part of the source: the hook
        self.assertLess(self.frame_level(3.0), 100)       # then the black part: the story


if __name__ == "__main__":
    unittest.main()
