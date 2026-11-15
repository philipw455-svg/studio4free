"""Find the face boxes in finished frames, so a caption line can step aside while it would cover a face.

This module only finds boxes. It never moves, crops or zooms the picture: the frame is set by hand.
The owner had frame-following face tracking removed on 12 Nov 2026. Do not add it back.

The detector is the small open model "Ultra-Light-Fast-Generic-Face-Detector-1MB" (MIT licence), run with onnxruntime.
"""
import importlib.util

from .common import ROOT

MODEL = ROOT / "assets" / "models" / "version-RFB-640.onnx"
IN_W, IN_H = 640, 480
_session = None


def why_not() -> str:
    """Empty when faces can be found. Otherwise the plain reason they cannot."""
    for mod in ("onnxruntime", "numpy"):
        if importlib.util.find_spec(mod) is None:
            return f"{mod} is missing"
    return "" if MODEL.exists() else f"the face model is missing ({MODEL.relative_to(ROOT).as_posix()})"


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


def find(raw: bytes, min_score: float = 0.85) -> list:
    """The faces in each 640 x 480 rgb24 frame of `raw`, one list for each frame.
    A face is (left, top, right, bottom, score), each side as a part of that 640 x 480 frame from 0 to 1."""
    import numpy as np
    size = IN_W * IN_H * 3
    net = _net()
    name = net.get_inputs()[0].name
    out = []
    for i in range(len(raw) // size):
        frame = np.frombuffer(raw, np.uint8, size, i * size).reshape(IN_H, IN_W, 3).astype(np.float32)
        scores, boxes = net.run(None, {name: ((frame - 127.0) / 128.0).transpose(2, 0, 1)[None]})
        s = scores[0][:, 1]
        pick = s > min_score
        out.append(_nms([(float(b[0]), float(b[1]), float(b[2]), float(b[3]), float(c)) for b, c in zip(boxes[0][pick], s[pick])]))
    return out
