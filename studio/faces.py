"""Find the faces in a clip, so the frame follows the speaker and the captions stay off the face.

The detector is the small open model "Ultra-Light-Fast-Generic-Face-Detector-1MB" (MIT licence),
run with onnxruntime, which faster-whisper already installs.
"""
import re
import subprocess

from .common import ROOT

MODEL = ROOT / "assets" / "models" / "version-RFB-640.onnx"
IN_W, IN_H = 640, 480
_session = None


def available() -> bool:
    return MODEL.exists()


def _net():
    global _session
    if _session is None:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        _session = ort.InferenceSession(str(MODEL), opts, providers=["CPUExecutionProvider"])
    return _session


def _nms(boxes: list, limit: float = 0.3) -> list:
    keep = []
    for b in sorted(boxes, key=lambda b: -b[4]):
        ok = True
        for k in keep:
            iw = min(b[2], k[2]) - max(b[0], k[0])
            ih = min(b[3], k[3]) - max(b[1], k[1])
            if iw > 0 and ih > 0:
                inter = iw * ih
                if inter / ((b[2] - b[0]) * (b[3] - b[1]) + (k[2] - k[0]) * (k[3] - k[1]) - inter) > limit:
                    ok = False
                    break
        if ok:
            keep.append(b)
    return keep


def detect(source, start: float, dur: float, fps: float = 5.0, min_score: float = 0.75) -> list:
    """Sample the clip and return [(seconds into the clip, [face, ...])].
    A face is (left, top, right, bottom, score), each side as a part of the frame from 0 to 1."""
    import numpy as np
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(source), "-an",
         "-vf", f"fps={fps},scale={IN_W}:{IN_H}", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    size = IN_W * IN_H * 3
    net = _net()
    name = net.get_inputs()[0].name
    out = []
    for i in range(len(raw) // size):
        frame = np.frombuffer(raw, np.uint8, size, i * size).reshape(IN_H, IN_W, 3).astype(np.float32)
        x = ((frame - 127.0) / 128.0).transpose(2, 0, 1)[None]
        scores, boxes = net.run(None, {name: x})
        s = scores[0][:, 1]
        pick = s > min_score
        found = [(float(b[0]), float(b[1]), float(b[2]), float(b[3]), float(c)) for b, c in zip(boxes[0][pick], s[pick])]
        out.append((i / fps, _nms(found)))
    return out


def camera_cuts(source, start: float, dur: float, limit: float = 0.25) -> list:
    """Seconds into the clip at which the camera changes."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(source), "-an",
         "-vf", f"scale=480:-2,select='gt(scene,{limit})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True)
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", p.stderr)]


def _median(values: list) -> float:
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def _plausible(f: tuple, aspect: float) -> bool:
    """Drop weak hits and boxes too tall or too flat to be a face. `aspect` is the source width over its height."""
    w, h = f[2] - f[0], f[3] - f[1]
    return f[4] >= 0.9 and w >= 0.015 and 0.9 <= h / (w * aspect) <= 1.9


def _subject(shot: list, window) -> list:
    """The person a shot is about: the largest face that stays in the picture. Returns [(t, x, top, chin, width)]."""
    tracks = []
    for t, fs in shot:
        for f in fs:
            cx = (f[0] + f[2]) / 2
            if window and not (window(t)[0] <= cx <= window(t)[1]):
                continue
            near = [tr for tr in tracks if tr[-1][0] != t and abs((tr[-1][1][0] + tr[-1][1][2]) / 2 - cx) < 0.10]
            if near:
                min(near, key=lambda tr: abs((tr[-1][1][0] + tr[-1][1][2]) / 2 - cx)).append((t, f))
            else:
                tracks.append([(t, f)])
    if not tracks:
        return []

    def weight(tr):
        return _median([(f[2] - f[0]) * (f[3] - f[1]) for _, f in tr]) * min(1.0, len(tr) / max(1, len(shot)))

    best = max(tracks, key=weight)
    if _median([f[2] - f[0] for _, f in best]) < 0.05 and not window:
        # A wide shot of the whole room: keep the middle of the group in view.
        out = []
        for t, fs in shot:
            xs = [(f[0] + f[2]) / 2 for f in fs]
            out.append((t, min(0.7, max(0.3, sum(xs) / len(xs))), min(f[1] for f in fs), max(f[3] for f in fs), 0.0))
        return out
    return [(t, (f[0] + f[2]) / 2, f[1], f[3], f[2] - f[0]) for t, f in best]


def plan(samples: list, cuts: list, dur: float, zoom_at, aspect: float, r: float, win: float, limit_at,
         max_drop: float, skip: list = (), window=None) -> dict:
    """Work out, shot by shot, where the picture sits and how far down the text must go.

    The picture is not moved to suit the text. Each shot gets one fixed place, and the text moves instead.
    The owner asked for this on 12 Nov 2026: "dont move anything just use face tracking to adjust the text".

    center: the speaker's place across the source (0 left, 1 right), one fixed value for each shot.
            A shot gets a second value only when the speaker moves too far to stay in one frame.
    ay:     the height a zoom step holds still. It is the chin line, so the face stays put while the picture zooms.
    drop:   how far the text moves down in each shot to clear the chin, as a part of the window height.
    touch:  the times at which the text still reaches the face, because `max_drop` stopped it.

    zoom_at(t) is the zoom at a clip time. r is the scaled picture height over the window height.
    win is the window width as a part of the scaled picture width.
    limit_at(t) is the top of the text as a part of the window height, or None when nothing is shown.
    window(t) gives (left, right) across the source when the owner set the focus by hand."""
    bounds = [0.0] + [c for c in cuts if 0.15 < c < dur - 0.15] + [dur]
    center, ays, drops, bad, checks, last_c = [], [], [], [], 0, 0.5
    closest = max([zoom_at(t) for t, _ in samples] + [1.0])
    for a, b in zip(bounds, bounds[1:]):
        at = round(max(0.0, a - 0.02), 3)
        shot = [(t, [f for f in fs if _plausible(f, aspect)]) for t, fs in samples if a + 0.08 <= t < b - 0.08]
        pts = _subject([(t, fs) for t, fs in shot if fs], window)
        if not pts:
            center.append([at, last_c])
            ays.append([at, 0.3])
            drops.append([at, 0.0])
            continue
        raw = [p[1] for p in pts]
        xs = [_median(raw[max(0, i - 2):i + 3]) for i in range(len(raw))]
        face = _median([p[4] for p in pts])
        tight = win / closest                   # the window at the closest zoom step
        order = sorted(xs)
        lo_x, hi_x = order[int(0.05 * (len(order) - 1))], order[int(0.95 * (len(order) - 1) + 0.5)]
        if hi_x - lo_x + face <= tight:
            # The speaker stays inside one frame: put the middle of where they sit in the middle.
            last_c = (lo_x + hi_x) / 2
            center.append([at, last_c])
        else:
            # The speaker moves too far for one frame. Change the frame in one cut, never a slide.
            slack = max(0.05, tight / 2 - 0.35 * face)
            last_c = _median([x for p, x in zip(pts, xs) if p[0] <= pts[0][0] + 2.0])
            center.append([at, last_c])
            i = 0
            while i < len(pts):
                t = pts[i][0]
                if abs(xs[i] - last_c) > slack and i + 1 < len(pts) and abs(xs[i + 1] - last_c) > slack:
                    new = _median([x for p, x in zip(pts, xs) if t <= p[0] <= t + 2.5])
                    if abs(new - last_c) > 0.04:
                        center.append([round(t, 3), new])
                        last_c = new
                        while i < len(pts) and pts[i][0] < t + 1.0:
                            i += 1
                        continue
                i += 1
        ay = min(0.62, max(0.25, _median([p[3] for p in pts]) + 0.015))
        ays.append([at, round(ay, 3)])
        rows = []
        for t, _, _, chin, _ in pts:
            c = limit_at(t)
            if c is not None and not any(s0 <= t <= s1 for s0, s1 in skip):
                rz = r * zoom_at(t)
                rows.append((t, (chin + 0.015) * rz - (rz - 1) * ay + 0.012 - c))
        need = max([n for _, n in rows] + [0.0])
        drop = min(max_drop, need)
        drops.append([at, round(drop, 4)])
        for t, n in rows:
            checks += 1
            if n - drop > 0.012:
                if bad and t - bad[-1][1] <= 0.6:
                    bad[-1][1] = t
                else:
                    bad.append([t, t])
    return {"center": [[round(v, 3) for v in s] for s in center], "ay": ays, "drop": drops,
            "touch": [[round(a, 1), round(b, 1)] for a, b in bad], "checks": checks}
