# App tour (30 to 60 s)

Real app screenshots in a glowing phone frame, one serif headline per screen, and a logo end card.

- **Built from:** `template.html`, drawn by `studio/film.py` with Playwright at the output size, 30 fps.
- **Needs from the storyboard:** one frame per screen. Each frame has `words` (the headline, one line), `screen`
  (a screenshot path inside the brand folder, such as `assets/screens/home-graphite-dark.jpg`), and the last frame has `"endCard": true`.
- **Needs from the brain:** current screenshots with made-up names and placeholder photos (`kit.md`, App screenshots), a current logo, the fonts and the look colors.
- **Motion:** the phone slides up and settles on the first screen. Each new screen slides in from the right inside the phone,
  and the headline fades up with it. The end card pops the logo in, then the link.
- Never use a screenshot with a real person's photo or name. Use features that are out now, or say "coming" in the words.
