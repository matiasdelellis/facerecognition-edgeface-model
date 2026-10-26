import json
import os
from functools import wraps

import cv2
import numpy
from flask import Flask, abort, request

from app.license import accepted as license_accepted
from app.license import require as require_license

require_license()

from app.models import DETECTION_THRESHOLD, DETECTORS, MODELS_DIR, EdgeFace, template_kps  # noqa: E402

# Info
PACKAGE_VERSION = "0.1.0"

MAX_IMG_SIZE = 3840 * 2160

DETECTOR_NAME = os.getenv("DETECTOR", "scrfd_500m")
if DETECTOR_NAME not in DETECTORS:
    raise SystemExit(f"Unknown DETECTOR={DETECTOR_NAME!r}, use one of {sorted(DETECTORS)}")

# Default minimum confidence of each detector, calibrated so that it keeps ~99%
# of the real faces of at least 40 px while dropping most of the blurred, tiny
# or turned faces and the false positives. Each detector scores on its own scale.
DEFAULT_CONFIDENCE = {"scrfd_500m": 0.55, "scrfd_10g": 0.6, "yunet": 0.65}

# Default minimum side, in pixels of the original image, of a face to group it.
# Over the default confidence, below 30 px a quarter of the faces of SCRFD-500M
# are blurred or not recognizable, and from 30 px they are as good as bigger
# ones. SCRFD-10G and YuNet mix people more with small faces, so they keep the
# 40 px the app always used.
DEFAULT_MIN_FACE_SIZE = {"scrfd_500m": 30, "scrfd_10g": 40, "yunet": 40}

# What the descriptors are and how to compare them, and the scale of the
# detection confidence, reported by /open so the Nextcloud app never mixes the
# descriptors of two models and uses the right metric and thresholds. The
# cosine distance 0.5 (cosine similarity 0.5) groups without mixing people.
MODEL_PROFILE = {
    "descriptor": "edgeface_base",
    "distance": "cosine",
    "sensitivity": {"min": 0.3, "default": 0.5, "max": 0.7},
    "link_suggestion_sensitivity": 0.6,
    "confidence": {"min": DETECTION_THRESHOLD, "default": DEFAULT_CONFIDENCE[DETECTOR_NAME], "max": 1.0},
    "min_face_size": {"min": 0, "default": DEFAULT_MIN_FACE_SIZE[DETECTOR_NAME], "max": 250},
}

# Model files
MODEL_FILES = {"scrfd_500m": "scrfd_500m.onnx", "scrfd_10g": "scrfd_10g.onnx", "yunet": "yunet_2023mar.onnx"}
RECOGNIZER_FILE = "edgeface_base.onnx"

DETECTOR = None
RECOGNIZER = None

app = Flask(__name__)


def open_models():
    global DETECTOR, RECOGNIZER
    if RECOGNIZER is not None:
        return
    DETECTOR = DETECTORS[DETECTOR_NAME]()
    RECOGNIZER = EdgeFace()


def require_appkey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if "API_KEY" in os.environ:
            key = os.environ.get("API_KEY")
        else:
            with open("api.key", "r") as apikey:
                key = apikey.read().replace("\n", "")
        if request.headers.get("x-api-key") and request.headers.get("x-api-key") == key:
            return view_function(*args, **kwargs)
        abort(401)

    return decorated_function


def read_image():
    """The uploaded image as BGR. EXIF orientation is ignored, as dlib does: the
    app sends an already oriented copy and expects the coordinates in it."""
    data = numpy.frombuffer(request.files["file"].read(), dtype=numpy.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
    if bgr is None:
        abort(400)
    if bgr.shape[0] * bgr.shape[1] > MAX_IMG_SIZE:
        abort(412)
    return bgr


def face_json(box, score, kps, descriptor, width, height):
    left, top = max(0, int(round(box[0]))), max(0, int(round(box[1])))
    right, bottom = min(width - 1, int(round(box[2]))), min(height - 1, int(round(box[3])))
    return {
        "detection_confidence": score,
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "landmarks": dlib_landmarks(kps),
        "descriptor": descriptor.tolist(),
    }


def dlib_landmarks(kps):
    """The 5 points in the order of the dlib 5 point model, that the app reads:
    0-1 image-right eye, 2-3 image-left eye, 4 nose. The eye centers stand for
    both corners of each eye."""
    left_eye, right_eye, nose = kps[0], kps[1], kps[2]
    return [{"x": int(round(p[0])), "y": int(round(p[1]))} for p in (right_eye, right_eye, left_eye, left_eye, nose)]


def iou(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


# Endpoints
@app.route("/detect", methods=["POST"])
@require_appkey
def detect_faces():
    # The app sends fast=1 on its first pass, on a smaller image. The detectors
    # are fast enough, so both passes use the same one.
    filename = os.path.basename(request.files["file"].filename)
    bgr = read_image()
    open_models()

    dets = DETECTOR(bgr)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    descriptors = RECOGNIZER(rgb, [kps for _, _, kps in dets])
    height, width = bgr.shape[:2]
    faces = [face_json(box, score, kps, d, width, height) for (box, score, kps), d in zip(dets, descriptors)]

    return {"filename": filename, "faces-count": len(faces), "faces": faces}


@app.route("/compute", methods=["POST"])
@require_appkey
def compute():
    face = json.loads(request.form.get("face"))
    filename = os.path.basename(request.files["file"].filename)
    bgr = read_image()
    open_models()

    # The landmarks of the detection that matches the rect, or those of an
    # average face in it when no detection does.
    box = [face["left"], face["top"], face["right"], face["bottom"]]
    matches = [(iou(box, d[0]), d) for d in DETECTOR(bgr)]
    best = max(matches, key=lambda m: m[0], default=(0.0, None))
    kps = best[1][2] if best[0] >= 0.3 else template_kps(box)

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    face["landmarks"] = dlib_landmarks(kps)
    face["descriptor"] = RECOGNIZER(rgb, [kps])[0].tolist()

    return {"filename": filename, "face": face}


@app.route("/open")
@require_appkey
def open_model():
    open_models()
    return {"preferred_mimetype": "image/jpeg", "maximum_area": MAX_IMG_SIZE, "model": MODEL_PROFILE}


@app.route("/health")
def health():
    return "ok"


@app.route("/welcome")
def welcome():
    missing = [f for f in (MODEL_FILES[DETECTOR_NAME], RECOGNIZER_FILE)
               if not os.path.exists(os.path.join(MODELS_DIR, f))]
    if missing:
        return {"facerecognition-external-model": "Neural network files are missing: " + ", ".join(missing),
                "version": PACKAGE_VERSION}
    return {"facerecognition-external-model": "welcome", "version": PACKAGE_VERSION,
            "model": {"detector": DETECTOR_NAME, "recognizer": "edgeface_base"},
            "license": {
                "commercial_use": False,
                "accepted": license_accepted(),
                "notice": "NOTICE.md",
                "weights": {
                    "edgeface_base": "CC BY-NC-SA 4.0",
                    "scrfd": "InsightFace non-commercial research use only",
                    "yunet": "MIT",
                },
            }}
