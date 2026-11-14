"""Tests for the ad job helpers. Run: python -m unittest discover tests"""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from studio import brain as B
from studio.adjob import STEPS, choice_problems, context_card, open_slots
from studio.film import STYLES, brand_data, length, style_dir

CT = ZoneInfo("America/Chicago")


class SlotsTest(unittest.TestCase):
    def test_skips_used_and_past_times(self):
        after = datetime(2026, 11, 16, 10, 0, tzinfo=CT)
        taken = ["2026-11-16T18:15:00Z",  # 12:15 Central is used by a podcast clip
                 "2026-11-16T23:02:00Z"]  # 17:02 Central sits within 5 minutes of 17:00
        got = open_slots(["09:00", "12:15", "17:00"], "America/Chicago", taken, after, 2)
        self.assertEqual([g.isoformat() for g in got], ["2026-11-17T09:00:00-06:00", "2026-11-17T12:15:00-06:00"])

    def test_first_time_today_when_free(self):
        after = datetime(2026, 11, 16, 8, 0, tzinfo=CT)
        got = open_slots(["12:15"], "America/Chicago", [], after, 1)
        self.assertEqual(got[0].isoformat(), "2026-11-16T12:15:00-06:00")


class NoxiJobTest(unittest.TestCase):
    def setUp(self):
        self.brain = B.Brain.load(B.BRANDS / "noxi")

    def test_steps_are_in_order(self):
        self.assertEqual([s["n"] for s in STEPS], list(range(1, 10)))

    def test_context_card(self):
        card = context_card(self.brain, {"about": "the 24 hours before photos are deleted", "postWhen": "2026-11-18T12:15:00-06:00"})
        self.assertIn("Photos are deleted after 24 hours. (approved", card)
        self.assertIn("2026-11-20: Noxi launch day", card)
        self.assertIn("Your nights just got a glow-up", card)
        self.assertIn("Retired, never use", card)

    def test_choices(self):
        ok = {"style": "Sting", "length": "2 s", "shape": "9:16", "pace": "Hyped", "sound": "Silent",
              "look": "Mosaic", "cast": ["Nova", "Hoot"], "cta": "appnoxi.com/go"}
        self.assertEqual(choice_problems(self.brain, ok), [])
        bad = dict(ok, look="Classic", cast=["Rex"], length="30 s", cta="noxi.app")
        probs = " ".join(choice_problems(self.brain, bad))
        for word in ("Classic", "Rex", "built for 2 to 2 seconds", "noxi.app"):
            self.assertIn(word, probs)

    def test_every_style_has_a_readme(self):
        for name in STYLES:
            self.assertTrue((style_dir(name) / "README.md").exists(), name)

    def test_brand_data_for_the_templates(self):
        d = brand_data(self.brain, {"look": "Smoke"})
        self.assertEqual(d["logo"], "assets/logo/column-n-smoke.png")
        self.assertEqual([f["family"] for f in d["fonts"]], ["Cinzel", "Inter"])
        self.assertEqual(d["mascots"], ["Nova", "Luna", "Echo", "Hoot"])
        self.assertNotIn("retired", d["logo"])
        self.assertEqual(length({"frames": [{"end": 3}, {"end": 7.5}]}), 7.5)


if __name__ == "__main__":
    unittest.main()
