# AGENTS.md

## What this repo is

A Flask service with the HTTP API of facerecognition-external-model (the "external model" of the
Nextcloud Face Recognition app), running SCRFD (500M by default, or 10G) or YuNet + EdgeFace-Base with ONNX Runtime.

## Layout

- `app/server.py` — endpoints, auth (`x-api-key`, `API_KEY` env or `api.key`), the model profile
  reported by `/open` (`MODEL_PROFILE`) and the conversion to the JSON the app expects.
- `app/models.py` — detectors (`SCRFD`, `YuNet`, decoded like `insightface.model_zoo.scrfd`), the
  5 point ArcFace alignment (Umeyama, like `insightface.utils.face_align.norm_crop`) and `EdgeFace`.
- `app/gunicorn.py` — gunicorn config.
- `docker/Dockerfile` — stage 1 downloads the weights (`docker/download.sh`, sha256 checked) and
  exports EdgeFace to ONNX with torch (`docker/export_edgeface.py`, checks torch vs onnxruntime);
  stage 2 is the service, without torch.
- `test/api_smoke.py` — stdlib-only smoke test of every endpoint (`make smoke`).
- `doc/report.md` — the tests, conclusions and decisions behind the model and its defaults. Update
  it when a default changes.

## Rules

- The descriptors must stay those of the benchmark (`bench/` in facerecognition-external-model):
  same alignment, same normalization. Changing them requires a new `descriptor` id in
  `MODEL_PROFILE`, since the app refuses to compare descriptors with different ids.
- `.env` and `api.key` are gitignored; never commit a real key.
- No weights in the repo: they are downloaded at build time (non-commercial licenses).
