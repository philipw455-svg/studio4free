# Podcast clip with end card

An existing clip, with the brand's end card added after it.

- **Built with ffmpeg only**, by `studio/film.py` (`podcast_endcard`). No template page.
- **Needs from the storyboard:** `clip` (the path of the finished clip, such as `jobs/<job>/clips/clip03.mp4`) and `endCardFile`
  (the path of a current end card video from `kit.md`). Both are scaled to the shape and joined, sound and all.
- The clip keeps its own captions, credit and look. The clipping job's rules still apply to it, including the credit line.
- Never use a retired end card. Noxi's old end card (`assets/brand/endcard.mp4`) is retired, because it shows the old logo.
