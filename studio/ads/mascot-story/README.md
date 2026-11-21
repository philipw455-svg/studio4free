# Mascot story (14 to 16 s)

A short story with the mascots, told in comic panels. One line per frame. Ends on the mascot end card.

- **Built from:** `template.html`, drawn by `studio/film.py` with Playwright at the output size, 30 fps.
- **Needs from the storyboard:** frames with `words` (the caption, one line, at least 2 s) and `mascots` (the names in the panel,
  such as `["Luna", "Echo"]`). The last frame has `"endCard": true`. Optional `bg` per frame: `"night"` or `"day"`.
- **Needs from the brain:** the mascots in `kit.md` and their art. Today the only art is `assets/mascots/lineup-from-endcard.png`,
  cut from the old end card, so each panel crops one mascot out of that row. Separate art for each mascot (transparent PNGs in
  `assets/mascots/<name>.png`) will be used first when it exists.
- **Motion:** each panel drops in with a small tilt and a bounce. The caption box types on. A halftone of the accent color moves behind.
- No drinks in any panel. No real people.
