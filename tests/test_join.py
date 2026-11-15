"""The join step and the fetch step's file rules. Run with: python -B -m unittest discover -s tests"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from studio import common, fetch, join, render

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


class Words(unittest.TestCase):
    def test_words_move_to_their_time_in_the_finished_video(self):
        talk = {"segments": [{"start": 0, "end": 30, "words": [{"s": 1.0, "e": 1.4, "w": "skip"}, {"s": 10.0, "e": 10.5, "w": "keep"},
                                                               {"s": 20.2, "e": 20.6, "w": "damn"}]}]}
        parts = [{"start": 20.0, "end": 22.0, "src": True}, {"start": 0.0, "end": 5.0, "src": False}, {"start": 9.0, "end": 12.0, "src": True}]
        got = join.moved_words(talk, parts)
        self.assertEqual([w["w"] for w in got], ["damn", "keep"])
        self.assertAlmostEqual(got[0]["s"], 0.2)   # 20.2 in the source, in a part that starts the video
        self.assertAlmostEqual(got[1]["s"], 8.0)   # 2 + 5 seconds of earlier parts, then 1 second into its own part

    def test_the_page_names_a_looks_options_ovs(self):
        look = {"overlay": "Sticker", "ovs": {"bg": "#00ff00", "tilt": "Right"}}
        self.assertEqual(render.look_style(look)["opts"], render.look_style({"overlay": "Sticker", "opts": look["ovs"]})["opts"])


class FetchRules(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        patch = mock.patch.object(common, "JOBS", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_path_from_the_page_must_be_a_video_file(self):
        secret = self.tmp / "notes.txt"
        secret.write_text("private")
        with self.assertRaises(SystemExit) as e:
            fetch.fetch("j", str(secret))
        self.assertIn("not a video file", str(e.exception))

    def test_out_stays_inside_the_job_folder(self):
        for name in ("../elsewhere.mp4", "sources/01.txt"):
            with self.assertRaises(SystemExit):
                fetch.fetch("j", "C:/nothing.mp4", name)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg or ffprobe is not installed")
class RealJoin(unittest.TestCase):
    def test_join_two_sizes_one_without_sound(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        patch = mock.patch.object(common, "JOBS", tmp)
        patch.start()
        self.addCleanup(patch.stop)
        d = tmp / "m"
        (d / "sources").mkdir(parents=True)
        ff = ["ffmpeg", "-v", "error", "-y"]
        subprocess.run(ff + ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                             "-t", "2", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(d / "source.mp4")], check=True)
        subprocess.run(ff + ["-f", "lavfi", "-i", "color=c=red:size=640x640:rate=24", "-t", "1.5", "-c:v", "libx264", "-preset", "ultrafast",
                             "-pix_fmt", "yuv420p", str(d / "sources" / "02.mp4")], check=True)
        common.write_json(d / "transcript.json", {"segments": [{"start": 0, "end": 2, "words": [{"s": 0.6, "e": 0.9, "w": "Hello"}, {"s": 1.0, "e": 1.3, "w": "damn."}]}]})
        common.write_json(d / "join.json", {"shape": "tall", "fit": "crop", "captions": True, "mute_strong": True, "title": "Test",
                                            "parts": [{"file": "sources/02.mp4", "end": 1.0}, {"file": "source.mp4", "start": 0.5, "end": 1.5, "volume": 50}]})
        join.join("m")
        info = common.probe(d / "clips" / "clip01.mp4")
        self.assertEqual((info["width"], info["height"]), (1080, 1920))
        self.assertAlmostEqual(info["duration"], 2.0, delta=0.15)
        self.assertTrue(common.has_audio(d / "clips" / "clip01.mp4"))
        r = common.read_json(d / "rendered.json")[0]
        self.assertEqual((r["n"], r["file"], r["version"], r["parts"]), (1, "clips/clip01.mp4", 1, 2))
        self.assertIn("Hello", (d / "clips" / "clip01.srt").read_text(encoding="utf-8"))
        join.join("m")   # a second join replaces the file and raises the version
        self.assertEqual(common.read_json(d / "rendered.json")[0]["version"], 2)


if __name__ == "__main__":
    unittest.main()
