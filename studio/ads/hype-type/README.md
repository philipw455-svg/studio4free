# Hype type (30 s)

Words on panels in 3D space and a moving camera, with cuts on the beat.

- **Built from:** `template.html`, drawn by `studio/film.py` with Playwright at the output size, 30 fps. The 3D is CSS perspective.
- **Needs from the storyboard:** frames with `words` (one line each, at least 2 s). `bpm` (beats per minute of the track) snaps every
  camera move to the beat. Optional per frame: `screen` (a screenshot that hangs beside the words).
- **Sound:** "Beat" needs `soundFile`, a licensed track on disk. The template does not pick music.
- **Motion:** the panels hang at different depths and angles. The camera glides from one panel to the next, arriving on a beat,
  then holds with a slow drift. The last panel holds the logo and the link.
- Panels that are not in front show at 30% or less. The filmer's safe-area check skips words drawn at under 50%, because nobody reads them.
