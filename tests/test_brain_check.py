"""Tests for the brand brain and the brain check. Run: python -m unittest discover tests"""
import json
import tempfile
import unittest
from pathlib import Path

from studio import brain as B
from studio.brain_check import check, claims_in, find_dates, has

FILES = {
    "profile.md": "# Test\n\n## Links\n- test.app/go · bio page\n- test.app · site\n",
    "facts.md": "# Facts\n\n## Facts\n"
                "- It is free. · keys: free · source: site · 2026-11-01 · status: approved\n"
                "- Launch is Nov 20. · keys: launch, nov 20, 20 · source: site · 2026-11-01 · status: needs Philip's yes\n"
                "- iPhone only for now. · keys: iphone · source: site · 2026-11-01 · status: approved\n",
    "rules.md": "# Rules\n\n## Claim words\n- free, iphone, android, launch, only\n",
    "voice.md": "# Voice\n\n## Words to avoid\n- drink, beer, happy hour\n- 🍺, 🥂\n- source: the owner\n",
    "kit.md": "# Kit\n\n## Round logo\n- status: current\n- kind: logo\n- files: assets/logo/round.png\n\n"
              "## Old star logo\n- status: retired\n- kind: logo\n- files: assets/retired/star.png\n- also called: star logo, NO/XI\n- note: replaced\n\n"
              "## Look: Graphite\n- status: current\n- kind: look\n- dark: ground #131517, text #E6E8EA\n",
    "calendar.md": "# Calendar\n\n## Dates\n- 2026-11-20 · launch · Launch day · keys: launch, launch day\n- 2026-11-22 · quiet · A quiet Sunday · keys:\n",
    "history.md": "# History\n\n| date | style | hook | length | posted | file |\n|---|---|---|---|---|---|\n",
    "results.md": "# Results\n\n| date | ad | where | views | likes | comments | shares | learned |\n|---|---|---|---|---|---|---|---|\n",
}


def frame(n, start, end, words="", picture="", **kw):
    return {"n": n, "start": start, "end": end, "words": words, "picture": picture, **kw}


class BrainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        d = self.root / "test"
        (d / "assets").mkdir(parents=True)
        for name, text in FILES.items():
            (d / name).write_text(text, encoding="utf-8")
        self.brain = B.Brain.load(d)

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, frames, **sb):
        return check(self.brain, {"brand": "test", "postAt": "2026-11-15T12:00:00-06:00", "frames": frames, **sb})

    def kinds(self, problems):
        return [(p.frame, p.kind) for p in problems]

    # ---- reading the brain ----
    def test_reads_facts(self):
        facts = self.brain.facts()
        self.assertEqual(len(facts), 3)
        self.assertTrue(facts[0].approved)
        self.assertFalse(facts[1].approved)
        self.assertEqual(facts[1].keys, ["launch", "nov 20", "20"])

    def test_reads_kit_looks_links_and_avoid_list(self):
        retired = [k.name for k in self.brain.kit() if k.retired]
        self.assertEqual(retired, ["Old star logo"])
        self.assertEqual(self.brain.looks()["Graphite"]["dark"]["ground"], "#131517")
        self.assertEqual(self.brain.links(), ["test.app/go", "test.app"])
        self.assertIn("🥂", self.brain.avoid())
        self.assertNotIn("source: the owner", self.brain.avoid())

    def test_brand_id_must_be_letters_and_dashes(self):
        with self.assertRaises(SystemExit):
            B.brand_dir("Noxi_2", self.root)
        self.assertEqual(B.brand_dir("test", self.root), self.root / "test")

    def test_history_rows_and_pack_unpack(self):
        B.add_row(self.root / "test" / "history.md", ["2026-11-14", "Sting", "Want the photos?", "2 s", "not yet", "a|b.mp4"])
        rows = B.Brain.load(self.root / "test").history()
        self.assertEqual(rows[0]["hook"], "Want the photos?")
        self.assertEqual(rows[0]["file"], "a/b.mp4")
        doc = B.pack("test", self.root)
        doc["id"] = "copy"
        B.unpack(doc, self.root)
        self.assertEqual((self.root / "copy" / "facts.md").read_text(encoding="utf-8"), FILES["facts.md"])

    # ---- the five checks the prompt asks for ----
    def test_clean_storyboard_has_no_problems(self):
        self.assertEqual(self.run_check([frame(1, 0, 2.5, "Free on iPhone")]), [])

    def test_claim_not_in_facts(self):
        p = self.run_check([frame(1, 0, 3, "Now on Android")])
        self.assertEqual(self.kinds(p), [(1, "claim")])
        self.assertIn("android", p[0].text)
        self.assertIn("facts.md does not have", p[0].text)

    def test_number_is_a_claim_but_a_link_is_not(self):
        self.assertEqual(claims_in("Get it at test.app/go", []), [])
        p = self.run_check([frame(1, 0, 3, "Over 500 crews")])
        self.assertEqual(self.kinds(p), [(1, "claim")])

    def test_fact_waiting_for_yes(self):
        p = self.run_check([frame(1, 0, 3, "Launch is Nov 20")])
        self.assertEqual(self.kinds(p), [(1, "claim")])
        self.assertIn("still needs the owner's yes", p[0].text)

    def test_avoid_words_in_words_picture_and_emoji(self):
        p = self.run_check([frame(1, 0, 3, "Happy hour with the crew 🥂"), frame(2, 3, 6, "Your crew", picture="Two beers on a table")])
        self.assertEqual(sorted(self.kinds(p)), [(1, "avoid"), (1, "avoid"), (2, "avoid")])
        self.assertFalse(has("drinkable water? no: undrinkable", "drink"))

    def test_line_under_two_seconds(self):
        p = self.run_check([frame(1, 0, 1.5, "Your crew"), frame(2, 1.5, 2.0, "", picture="a flash")])
        self.assertEqual(self.kinds(p), [(1, "timing")])
        self.assertIn("1.5 seconds", p[0].text)

    def test_retired_kit_item(self):
        p = self.run_check([frame(1, 0, 3, "Your crew", picture="End card with the star logo")], endCard="star.png")
        self.assertEqual(sorted(self.kinds(p), key=str), sorted([(1, "kit"), (None, "kit")], key=str))

    def test_date_conflicts(self):
        p = self.run_check([frame(1, 0, 3, "Launch day is Nov 21")])
        self.assertIn((1, "date"), self.kinds(p))
        p = self.run_check([frame(1, 0, 3, "Free on Fri Nov 21")])
        self.assertEqual(self.kinds(p), [(1, "date")])
        self.assertIn("wrong weekday", p[0].text)
        p = self.run_check([frame(1, 0, 3, "Launch is coming")], postAt="2026-11-21T12:00:00-06:00")
        self.assertIn("still coming", " ".join(x.text for x in p))
        p = self.run_check([frame(1, 0, 3, "Free")], postAt="2026-11-22T09:00:00-06:00")
        self.assertEqual(self.kinds(p), [(None, "date")])

    def test_find_dates_reads_weekday_and_year(self):
        (said, d, wd), = find_dates("See you Fri Nov 20, 2026", 2026)
        self.assertEqual((d.isoformat(), wd), ("2026-11-20", 4))

    # ---- the extra checks from rules.md ----
    def test_two_lines_roman_clock_and_safe_area(self):
        p = self.run_check([frame(1, 0, 3, "Your crew\nYour night"), frame(2, 3, 6, "Out till IV AM"),
                            frame(3, 6, 9, "Your crew", box=[100, 100, 400, 80]), frame(4, 9, 12, "Your crew", box=[300, 800, 500, 80])])
        self.assertEqual(self.kinds(p), [(1, "timing"), (2, "clock"), (3, "safe")])

    def test_never_mixes_brands(self):
        p = check(self.brain, {"brand": "other", "postAt": "2026-11-15T12:00:00-06:00", "frames": [frame(1, 0, 3, "Your crew")]})
        self.assertEqual(self.kinds(p), [(None, "brand")])


class NoxiNeverSayTest(unittest.TestCase):
    def test_android_is_not_out(self):
        brain = B.Brain.load(B.BRANDS / "noxi")
        p = check(brain, {"brand": "noxi", "postAt": "2026-11-21T12:00:00-06:00",
                          "frames": [frame(1, 0, 3, "Free on iPhone + Android")]})
        self.assertTrue(any("Never say" in x.text for x in p))
        p = check(brain, {"brand": "noxi", "postAt": "2026-11-21T12:00:00-06:00", "frames": [frame(1, 0, 3, "Free on iPhone")]})
        self.assertEqual([x.text for x in p if x.kind == "claim" and "yes" not in x.text], [])


class NoxiSeedTest(unittest.TestCase):
    """The real Noxi brain parses, and the build 22 storyboard gets the problems we know it has."""

    def test_noxi_brain(self):
        brain = B.Brain.load(B.BRANDS / "noxi")
        self.assertTrue(any(k.retired and "NO/XI" in k.name for k in brain.kit()))
        self.assertEqual(sorted(brain.looks()), ["Bone", "Graphite", "Mosaic", "Smoke"])
        self.assertEqual(brain.links()[0], "appnoxi.com/go")
        sb = json.loads((B.BRANDS / "noxi" / "storyboards" / "2026-11-14-build22.json").read_text(encoding="utf-8"))
        kinds = {p.kind for p in check(brain, sb)}
        self.assertTrue({"timing", "kit", "safe", "claim"} <= kinds)


if __name__ == "__main__":
    unittest.main()
