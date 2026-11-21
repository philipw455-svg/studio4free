import tempfile
import unittest
from pathlib import Path

from studio import film


class CustomSceneTest(unittest.TestCase):
    def test_custom_scene_gets_the_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "scene.html"
            src.write_text('<script src="s4f:runtime"></script>', encoding="utf-8")
            out = film.template_file({"style": "Custom", "template": str(src)})
            self.assertIn((film.ADS / "runtime.js").resolve().as_uri(), out.read_text(encoding="utf-8"))
            self.assertEqual(src.read_text(encoding="utf-8"), '<script src="s4f:runtime"></script>')

    def test_a_style_uses_its_template(self):
        self.assertEqual(film.template_file({"style": "Sting"}).name, "template.html")


if __name__ == "__main__":
    unittest.main()
