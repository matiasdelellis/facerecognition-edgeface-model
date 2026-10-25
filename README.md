# facerecognition-edgeface-model

External model for the Nextcloud [Face Recognition](https://github.com/matiasdelellis/facerecognition)
app that detects faces with **SCRFD** (or YuNet) and describes them with **EdgeFace-Base**, all run
with ONNX Runtime and OpenCV on CPU. It speaks the same HTTP API as
[facerecognition-external-model](https://github.com/matiasdelellis/facerecognition-external-model)
(`/open`, `/detect`, `/compute`, `/health`, `/welcome`), so the app uses it as model 5.

Its descriptors are 512 floats compared with the **cosine** distance, and they cannot be compared
with the dlib ones. `/open` reports it, so the app needs the version that reads that report: it
then uses the cosine distance and the thresholds of this model, and refuses to mix these
descriptors with the faces already analyzed with dlib (run `occ face:reset --model` first).

## Why

Measured on a test suite of 2162 photos with ~5600 faces of 66 people
(see `bench/` in facerecognition-external-model):

| Detector + recognizer | Time per photo* | Faces in another person's cluster | Mixed clusters | Faces in usable clusters |
|---|---|---|---|---|
| dlib CNN + ResNet (model 4) | ~12 s | 3.1% | 20 | 63% |
| **SCRFD-500M + EdgeFace** (default) | ~0.09 s | 0% | 0 | 92% |
| SCRFD-10G + EdgeFace | ~0.32 s | 0.02% | 1 | 94% |
| YuNet + EdgeFace | ~0.25 s | 0.07% | 3 | 91% |

\* 1 thread, ~2.7 MP and 3.7 faces per photo. Clustering only faces of 40 px or more over the
default confidence of each detector, at the default threshold of each model; usable clusters have
5 faces or more and a majority of one person.

With the same recognizer, the detector changes the quality of the descriptors, probably because
the 5 points of YuNet align the faces worse than those of SCRFD (not verified).

The tests, the conclusions and the decisions behind this model and its defaults are in
[doc/report.md](doc/report.md).

## Run

```sh
cp .env.example .env    # set a real API_KEY
make compose-up         # builds the image (downloads and exports the weights) and runs it on :8080
API_BASE=http://localhost:8080 API_KEY=... make smoke
```

Then configure the app as with any external model:

```sh
occ face:setup --external_model_url http://host:8080 --external_model_api_key ... -m 5
```

## Configuration

| Variable | Default | |
|---|---|---|
| `API_KEY` | `some-super-secret-api-key` | Shared secret of the `x-api-key` header. Without it, `api.key` in the working directory is read. |
| `DETECTOR` | `scrfd_500m` | `scrfd_500m`, `scrfd_10g` (finds more small faces, ~4x slower) or `yunet`. |
| `GUNICORN_WORKERS` | `1` | Processes, one per core. |
| `MODEL_THREADS` | `1` | Threads each process gives to the models. |
| `REQ_TIMEOUT` | `300` | Per request timeout, in seconds. |

The detectors work differently with the size of the image:

- **YuNet** runs on the whole image, so time and memory grow with its area, as with dlib: the
  analysis area configured in the app keeps controlling them.
- **SCRFD** scales every image to 640 px, so it takes the same time for any size, and faces that
  become smaller than ~10 px at that scale are lost.
- **EdgeFace** works on a 112x112 aligned crop of each face: its cost is per face, whatever the
  size of the image.

## What `/open` reports

```json
"model": {
  "descriptor": "edgeface_base",
  "distance": "cosine",
  "sensitivity": {"min": 0.3, "default": 0.5, "max": 0.7},
  "link_suggestion_sensitivity": 0.6,
  "confidence": {"min": 0.5, "default": 0.55, "max": 1.0},
  "min_face_size": {"min": 0, "default": 30, "max": 250}
}
```

- The clustering threshold 0.5 (cosine similarity 0.5) is where the test suite, with SCRFD-500M,
  gets no cluster with two people while keeping 92% of the faces in clusters of 5 or more.
- `detection_confidence` is the score of the detector. The default minimum (0.55 for SCRFD-500M,
  0.6 for SCRFD-10G, 0.65 for YuNet) keeps ~99% of the real faces of 40 px or more and drops most
  of the blurred, tiny or turned ones and the false positives.
- `min_face_size` is the default minimum side of a face to group it, that the app uses unless the
  administrator chose another one. Over the default confidence, below 30 px a quarter of the faces
  of SCRFD-500M are blurred or not recognizable, and from 30 px they are as good as bigger ones, so
  it suggests 30 px. SCRFD-10G and YuNet mix people more with small faces, and suggest 40 px.
- `landmarks` are 5 points in the order of the dlib 5 point model (image-right eye twice,
  image-left eye twice, nose): the detectors give the center of each eye, not its corners.

## Licenses of the weights

The weights are downloaded while building the image and are not part of this repository.

| Model | Weights | License |
|---|---|---|
| YuNet | OpenCV Zoo `face_detection_yunet_2023mar` | MIT |
| SCRFD-500M | InsightFace `buffalo_sc` | Non-commercial research use only |
| SCRFD-10G | InsightFace `buffalo_l` | Non-commercial research use only |
| EdgeFace-Base | Idiap `EdgeFace-Base` | CC BY-NC-SA 4.0 (non-commercial) |

EdgeFace is non-commercial, so an image built with it must not be used commercially or
redistributed under other terms.
