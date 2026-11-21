# studio4free

Studio4Free makes finished video for creators and schedules it in Buffer. It has four paths:
YouTube video to clips, your own video to clips, unedited video to edited video, and game clips to montage.

- `page/studio.html` is the phone-first page. It is built from `page/src/` with `python page/build.py`.
  You sign in with a studio number and set up your studio in five steps: Channels, Style, Motion, Brand and Times.
  Then you start a job on one of the four paths, pick moments, change clips and see the queue and the schedule.
- `studio/` is the program a Claude Code session runs: fetch, transcribe, cut, check, schedule, post.
- `app/` is a small Windows launcher that opens the page in its own window.
- `tests/` holds the tests. Run them with `python -B -m unittest discover -s tests`.
- `CLAUDE.md` tells any Claude Code session how to run a job from start to finish.
- `brands/<brand-id>/` is a brand's brain for ad jobs, and `studio/ads/` holds the ad styles. See "Business automation" in `CLAUDE.md`.

## Setup

```
pip install -r requirements.txt
python -m studio doctor
```

`doctor` names what is missing, and what cannot run without it. `doctor --json` prints the same as one line.
ffmpeg and ffprobe are not Python packages. Both must be on the PATH, and ffmpeg must have libass.
On Windows, `winget install Gyan.FFmpeg` installs both. Open a new terminal after it.

## Commands

```
python -m studio fetch "https://youtu.be/..." --job demo    # get the video as jobs/demo/source.mp4
python -m studio transcribe --job demo                      # the words, each with its time
python -m studio words --job demo --start 205 --end 240     # print the words between two times
python -m studio fix --job demo "4450.22|old|new"           # correct a misheard word
# write jobs/demo/clips.json (each clip with a hook and a payoff), then:
python -m studio shots --job demo                           # one frame of every camera shot, to set the frame by hand
python -m studio craft --job demo                           # check the hook, the story, the pace, the camera and the words for slop
python -m studio cut --job demo                             # render the clips. --only 2,5 cuts those again over the same files
python -m studio sheet --job demo                           # frames of every finished clip, to check by eye
python -m studio join --job demo                            # an edit or a montage: join the parts in join.json into one video
python -m studio texts --job demo                           # words and titles for the rules check
python -m studio schedule --job demo --start 2026-11-20     # give each clip a publish time
python -m studio channels                                   # the Buffer channels: id, service and name
python -m studio post --job demo --draft                    # create the Buffer posts from posting.json
python -m studio queue                                      # every Buffer post with its status
```

`channels`, `post` and `queue` take `--buffer=<label>` for a studio with its own Buffer login.

## What a clip looks like

A clip is a 1080 x 1920 video in one of five looks: Poster, Banner, Glass card, Sticker or Frame. Each look has its own options.
Three older looks still render: Lower third, Wide frame and First banner.
Captions are always smart. A line holds at most 3 words and breaks at natural pauses. Each word lights up as it is said.
A caption moves aside while it would cover a face, then goes back. The face check only places captions. It never moves, crops or zooms the picture.

## The Windows launcher

`app/build.cmd` builds `app/Studio4Free.exe`. It is a small Windows launcher that opens the page in its own window.
The build needs Python with Pillow, and the C# compiler that ships with Windows.
On the page, you sign in with your 8-digit studio number. There is no password, so keep the number safe.

## Licences

The fonts are Montserrat and Anton, under the SIL Open Font License (`assets/fonts`).
The face model `assets/models/version-RFB-640.onnx` is Ultra-Light-Fast-Generic-Face-Detector-1MB, under the MIT licence.
