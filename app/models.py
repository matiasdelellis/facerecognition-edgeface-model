"""Face detectors (YuNet, SCRFD) and the EdgeFace recognizer, all run with ONNX.

Every detector takes a BGR image and returns a list of (box, score, kps): box is
[x1, y1, x2, y2], kps the 5 points image-left eye, image-right eye, nose,
image-left mouth corner, image-right mouth corner, as YuNet and SCRFD give them.
"""
import os

import cv2
import numpy as np
import onnxruntime as ort

MODELS_DIR = os.getenv("MODELS_DIR", "models")
THREADS = int(os.getenv("MODEL_THREADS", 1))

# Lowest detection score returned. It is also the minimum of the confidence
# range reported to the app, which filters with a higher default.
DETECTION_THRESHOLD = 0.5

# Where the 5 points land on the 112x112 crop the ArcFace-style models expect.
ARCFACE_DST = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
                        [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float64)


def session(name):
    options = ort.SessionOptions()
    options.intra_op_num_threads = THREADS
    options.inter_op_num_threads = 1
    options.log_severity_level = 3
    return ort.InferenceSession(os.path.join(MODELS_DIR, name), options, providers=["CPUExecutionProvider"])


class YuNet:
    def __init__(self):
        self.det = cv2.FaceDetectorYN.create(os.path.join(MODELS_DIR, "yunet_2023mar.onnx"), "", (320, 320),
                                             DETECTION_THRESHOLD, 0.3, 5000)

    def __call__(self, bgr):
        h, w = bgr.shape[:2]
        self.det.setInputSize((w, h))
        _, faces = self.det.detect(bgr)
        out = []
        for f in faces if faces is not None else []:
            x, y, fw, fh = map(float, f[:4])
            out.append(([x, y, x + fw, y + fh], float(f[14]), f[4:14].reshape(5, 2).astype(np.float64)))
        return out


class SCRFD:
    """SCRFD (InsightFace det_500m of buffalo_sc or det_10g of buffalo_l), decoded as
    insightface.model_zoo.scrfd does. Every image is scaled to fit size x size."""
    STRIDES = (8, 16, 32)
    ANCHORS = 2

    def __init__(self, filename, size=640):
        self.sess = session(filename)
        self.input = self.sess.get_inputs()[0].name
        self.size = size
        self.centers = {}

    def _centers(self, stride):
        if stride not in self.centers:
            n = self.size // stride
            grid = np.stack(np.mgrid[:n, :n][::-1], axis=-1).reshape(-1, 2).astype(np.float32) * stride
            self.centers[stride] = np.repeat(grid, self.ANCHORS, axis=0)
        return self.centers[stride]

    def __call__(self, bgr):
        h, w = bgr.shape[:2]
        if h > w:
            nh, nw = self.size, int(self.size * w / h)
        else:
            nh, nw = int(self.size * h / w), self.size
        scale = nh / h
        canvas = np.zeros((self.size, self.size, 3), dtype=np.uint8)
        canvas[:nh, :nw] = cv2.resize(bgr, (nw, nh))
        blob = cv2.dnn.blobFromImage(canvas, 1.0 / 128, (self.size, self.size), (127.5, 127.5, 127.5), swapRB=True)
        outs = [o[0] if o.ndim == 3 else o for o in self.sess.run(None, {self.input: blob})]

        boxes, scores, kpss = [], [], []
        for i, stride in enumerate(self.STRIDES):
            score = outs[i][:, 0]
            keep = score >= DETECTION_THRESHOLD
            if not keep.any():
                continue
            c = self._centers(stride)[keep]
            d = outs[i + 3][keep] * stride
            k = outs[i + 6][keep].reshape(-1, 5, 2) * stride
            boxes.append(np.stack([c[:, 0] - d[:, 0], c[:, 1] - d[:, 1], c[:, 0] + d[:, 2], c[:, 1] + d[:, 3]], axis=1))
            kpss.append(c[:, None, :] + k)
            scores.append(score[keep])
        if not boxes:
            return []
        boxes = np.concatenate(boxes) / scale
        kpss = np.concatenate(kpss) / scale
        scores = np.concatenate(scores)
        xywh = [[b[0], b[1], b[2] - b[0], b[3] - b[1]] for b in boxes.tolist()]
        keep = cv2.dnn.NMSBoxes(xywh, scores.tolist(), DETECTION_THRESHOLD, 0.4)
        return [(boxes[i].tolist(), float(scores[i]), kpss[i].astype(np.float64)) for i in np.asarray(keep).reshape(-1)]


def similarity_transform(src, dst):
    """Least-squares similarity (Umeyama, no reflection) mapping src points to dst, as a 2x3 matrix."""
    src_mean, dst_mean = src.mean(0), dst.mean(0)
    src_c, dst_c = src - src_mean, dst - dst_mean
    cov = dst_c.T @ src_c / len(src)
    u, s, vt = np.linalg.svd(cov)
    d = np.ones(2)
    if np.linalg.det(cov) < 0:
        d[1] = -1
    r = u @ np.diag(d) @ vt
    scale = (s * d).sum() / src_c.var(0).sum()
    t = dst_mean - scale * r @ src_mean
    return np.hstack([scale * r, t[:, None]])


def align(rgb, kps, size=112):
    m = similarity_transform(np.asarray(kps, dtype=np.float64), ARCFACE_DST * size / 112)
    return cv2.warpAffine(rgb, m, (size, size), borderValue=0.0)


def template_kps(box):
    """The 5 points where an average face would have them in a box, for a face no detector confirms."""
    x1, y1, x2, y2 = box
    side = max(x2 - x1, y2 - y1)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return (ARCFACE_DST / 112 - 0.5) * side + [cx, cy]


class EdgeFace:
    """EdgeFace-Base (Idiap) exported to ONNX: 112x112 aligned RGB in [-1, 1] -> 512-d."""
    dim = 512

    def __init__(self):
        self.sess = session("edgeface_base.onnx")
        self.input = self.sess.get_inputs()[0].name

    def __call__(self, rgb, kpss):
        if not len(kpss):
            return np.zeros((0, self.dim), dtype=np.float32)
        crops = np.stack([align(rgb, k) for k in kpss]).astype(np.float32)
        x = np.ascontiguousarray(((crops / 255.0 - 0.5) / 0.5).transpose(0, 3, 1, 2), dtype=np.float32)
        emb = self.sess.run(None, {self.input: x})[0]
        return emb / np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12)


DETECTORS = {
    "scrfd_500m": lambda: SCRFD("scrfd_500m.onnx"),
    "scrfd_10g": lambda: SCRFD("scrfd_10g.onnx"),
    "yunet": YuNet,
}
