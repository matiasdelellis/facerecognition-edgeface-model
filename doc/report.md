# Choosing the model: tests, conclusions and decisions

This report explains why this service detects faces with SCRFD and describes them with
EdgeFace-Base, how its defaults were chosen, and what changed in the Nextcloud app to use it. Every
number comes from the benchmark in
[`bench/`](https://github.com/matiasdelellis/facerecognition-external-model/tree/master/bench) of
facerecognition-external-model, which documents how to run it.

## Summary

- dlib model 4, the default of the app, puts **3.1% of the faces in the cluster of another person**
  (20 mixed clusters) and leaves only 63% of them in clusters worth naming, at ~12 s per photo.
- **SCRFD-500M + EdgeFace-Base** mixes nobody at the default threshold, leaves 92% of the faces in
  clusters worth naming, and takes ~0.09 s per photo on one CPU thread. It is the default.
- SCRFD-10G finds more small faces (94%, ~0.32 s per photo) and is an option. YuNet, chosen first
  for its MIT license, mixes more people with the same recognizer and gives no license advantage,
  since EdgeFace is non-commercial anyway; it stays as an option.
- The detector runs on a 640 px input: the whole image is slower, uses more memory, loses big
  faces and lets false positives through.
- The service reports a **model profile** in `/open` (descriptor, distance, thresholds, confidence
  scale, minimum face size). The app uses it to compare with the cosine distance, to adapt its
  settings, and to refuse mixing descriptors of different models.
- Images do not need to be enlarged: the app gained a mode that uses the analysis area only as a
  maximum, which halves the analysis time with the same results.

## The test set

2162 photos of the cast of The Big Bang Theory (press and event photos, median 2.7 MP, from
0.2 to 11.6 MP), whose captions name the people in them. They are not distributed.

Every face found by any of the detectors was merged into one list and labeled, with clustering
proposals reviewed by hand:

| Label | Faces | Meaning |
|---|---|---|
| a name | 5593 (66 people) | Scored: it must be grouped with its person. |
| `desconocido` | 1295 | A real face of someone not named: it must be grouped, but is not scored. |
| `ignorar` | 3628 | Too blurred, small or turned to be recognized. |
| `no-es-cara` | 60 | A false detection. |

The labels were seeded from the clusters of an ensemble of recognizers that included ArcFace R50,
which therefore has a small advantage below.

## What is measured

The clustering is the Chinese whispers of the app, swept over thresholds. Following the criterion
of the app, several clusters per person are fine (a face changes with age) but they must be pure:

- **wrong** — share of the named faces in a cluster whose majority is another person;
- **mixed** — clusters with more than one person;
- **usable** — share of the named faces in clusters of 5 or more faces with their own majority,
  the clusters the app suggests to name. Missed faces count against it;
- **strict** — the threshold with the most usable faces while wrong stays at 0.1% or less.

Thresholds are written as the app uses them: the cosine distance (1 − cosine similarity) for the
newer recognizers and the Euclidean distance for dlib and face-api. A face joins another when
their distance is below the threshold, so a higher threshold groups more.

With the **app filters**, only the faces the app groups are clustered: at least 40 px and over the
default minimum confidence of each detector. The other faces count as not grouped.

## Recognizers on the same faces

Each recognizer described the same 5592 named faces, aligned with the same 5 points.

| Recognizer | Usable at strict | Strict threshold | ms per face* |
|---|---|---|---|
| AdaFace IR-101 | 98.7% | 0.575 | 2041 |
| ArcFace R50 (buffalo_l) | 98.7% | 0.55 | 262 |
| **EdgeFace-Base** | **97.4%** | 0.525 | **18.8** |
| ArcFace R100 (antelopev2) | 96.4% | 0.45 | 1426 |
| ArcFace MBF (buffalo_sc) | 92.2% | 0.475 | 11.8 |
| FaceNet VGGFace2 | 90.6%† | 0.275 | 36 |
| SFace (OpenCV) | 89.5% | 0.35 | 18 |
| dlib ResNet | 9.0%† | 0.3 (Euclidean) | 77 |

\* Isolated, one thread. † No threshold keeps wrong at 0.1% or less: FaceNet stays at 0.36% and dlib
at 0.18%, where it groups almost nothing.

EdgeFace-Base is within 1.3 points of the best ones at 1/14 of the time of ArcFace R50 and 1/100
of AdaFace. The bigger models were discarded for their cost per face.

## Complete pipelines, with the app filters

Each detector with its own detections and landmarks, as a service runs it. Default threshold: 0.5
cosine (0.4 Euclidean for dlib and face-api).

| Pipeline | Named faces found | Wrong | Mixed | Usable | Usable at strict | ms per photo* |
|---|---|---|---|---|---|---|
| dlib CNN + ResNet (model 4) | 4711 | 3.13% | 20 | 63.1% | 8.2% | ~12 400 |
| dlib HOG + ResNet (model 3) | 3561 | 0% | 0 | 51.0% | 59.2% | ~2 100 |
| face-api.js (Recognize) | 4957 | 6.74% | 18 | 57.5% | 6.9% | ~200 |
| YuNet + SFace | 5408 | 1.20% | 10 | 92.3% | 81.1% | ~245 |
| YuNet + EdgeFace-Base | 5408 | 0.07% | 3 | 91.1% | 91.1% | ~250 |
| **SCRFD-500M + EdgeFace-Base** | 5313 | **0%** | **0** | 92.0% | 93.2% | **~90** |
| SCRFD-500M + ArcFace MBF | 5313 | 0.02% | 1 | 88.9% | 92.7% | ~65 |
| SCRFD-10G + EdgeFace-Base | 5411 | 0.02% | 1 | 94.0% | 95.1% | ~320 |
| SCRFD-10G + ArcFace R50 | 5411 | 0% | 0 | 94.2% | 95.2% | ~1 200 |
| SCRFD-10G + ArcFace R100 | 5411 | 0.07% | 2 | 94.7% | 95.0% | ~5 500 |
| SCRFD-10G + SFace | 5411 | 0.79% | 8 | 93.9% | 89.3% | ~320 |
| SCRFD-10G + FaceNet | 5411 | 3.02% | 11 | 93.3% | 88.6% | ~390 |

\* Detector time plus 3.7 faces per photo (the average of the set), isolated, one thread.

Conclusions:

- The models the app uses today mix people. dlib CNN and face-api.js only stop mixing at
  thresholds where they group almost nothing; dlib HOG does not mix, but finds and groups half the
  faces.
- **The detector changes the quality of the descriptors.** With the same EdgeFace, YuNet mixes 3
  clusters where SCRFD-500M mixes none. The likely cause is that the 5 points of YuNet align the
  faces worse; it was not verified.
- **SCRFD-500M + EdgeFace-Base** is the only pipeline that mixes nobody at the default threshold,
  and the fastest. Its 640 px input loses some small faces: it finds 5313 named faces where
  SCRFD-10G finds 5411.

## Speed and memory

Isolated, one thread:

| Detector | ms per image | | Recognizer | ms per face |
|---|---|---|---|---|
| SCRFD-500M (640) | 23 | | ArcFace MBF | 11.8 |
| YuNet | 179 | | SFace | 18 |
| SCRFD-10G (640) | 253 | | EdgeFace-Base | 18.8 |
| SCRFD-10G (1280) | 1009 | | FaceNet | 36 |
| dlib HOG | 1806 | | dlib ResNet | 77 |
| dlib CNN | 12 123 | | ArcFace R50 | 262 |

Peak memory of a process:

| Model | Memory |
|---|---|
| dlib CNN (model 4) | ~950 MB per megapixel (7.7 GB at 8 MP) |
| dlib HOG | ~45 MB per megapixel |
| YuNet + EdgeFace | ~70 MB per megapixel (227 MB idle, 809 MB at 8 MP) |
| SCRFD (640) + EdgeFace | flat: 250–380 MB for any size up to 12 MP |

## Decisions on the detector

### SCRFD-500M by default, SCRFD-10G and YuNet as options

`DETECTOR` chooses it. SCRFD-500M for its purity and speed; SCRFD-10G for who wants more small
faces at ~4x the time; YuNet only for its MIT weights, which do not make the image free to use
commercially while EdgeFace is CC BY-NC-SA.

### A 640 px input, not the whole image

SCRFD scales every image to 640 px. Running it on the whole image (padded to a multiple of 32) was
tested, with its minimum confidence recalibrated to keep the same 98.4% of the real faces:

| SCRFD + EdgeFace | Named faces found | Mixed | Usable | ms per photo (relative) |
|---|---|---|---|---|
| 500M, 640 | 5313 | 0 | 92.0% | 1x |
| 500M, whole image | 5229 | 1 | 90.8% | 4–5x |
| 10G, 640 | 5411 | 1 | 94.0% | 1x |
| 10G, 1280 | 5373 | 0 | 93.6% | ~4x |
| 10G, whole image | 5252 | 0 | 91.3% | 4–5x |

On the whole image it finds fewer faces of 40 px or more, with lower scores: a big face falls
outside the scales SCRFD was trained for (an inference, not verified). The faces it gains are
smaller than 40 px, which the app does not group, and keeping the real faces costs 17–18 false
positives of 40 px or more (paintings, masks, lamps, glasses), against none at 640.

Its memory grows with the area and depends on the mix of sizes, since onnxruntime keeps a buffer
for each input shape: 500M stays around 380 MB after 20 photos of 2–4 MP, while 10G reaches
1070 MB after 30 and keeps growing (2.35 GB for a single 12 MP photo). At 640 it stays flat.

### The images are not enlarged

The app takes every image to a fixed area, enlarging the small ones, to keep the memory of dlib
under control. 400 photos at several scales, YuNet + EdgeFace:

| Scale | Recall | Recall of faces < 40 px | TAR at FAR 0.1% |
|---|---|---|---|
| 1 MP | 97.4% | 79.3% | 0.938 |
| 2 MP | 97.7% | 93.1% | 0.941 |
| original (~2.7 MP) | 97.6% | 98.3% | 0.941 |
| 4 MP | 97.0% | 96.6% | 0.947 |
| 8 MP | 93.3% | 91.4% | 0.948 |

Reducing loses small faces. Enlarging improves the verification of the faces found a little, but
finds no more faces, and loses some at 8 MP, while it costs time and memory. Hence the new mode of
the app that only reduces (below).

## Calibration of the defaults

### Clustering threshold: 0.5 cosine, range 0.3–0.7

SCRFD-500M + EdgeFace, with the app filters:

| Threshold | 0.35 | 0.4 | 0.45 | 0.5 | 0.55 | 0.575 | 0.6 | 0.65 |
|---|---|---|---|---|---|---|---|---|
| Mixed clusters | 0 | 0 | 0 | **0** | 0 | 0 | 2 | 4 |
| Usable | 80.7% | 86.6% | 90.1% | **92.0%** | 92.8% | 93.1% | 93.2% | 93.5% |

It mixes nobody up to 0.575 and starts mixing at 0.6, while below 0.5 it only splits the persons
in more clusters. 0.5 keeps a margin from the mixing. The link suggestion threshold, that only
proposes to join two clusters, is 0.6.

### Minimum confidence: 0.55 for SCRFD-500M, 0.6 for SCRFD-10G, 0.65 for YuNet

Each detector scores on its own scale, so each default keeps the same share of the real faces of
40 px or more (98.4% for SCRFD) and drops the false positives:

| Minimum | 0.5 | 0.55 | 0.6 | 0.65 | 0.7 |
|---|---|---|---|---|---|
| SCRFD-500M | 100% / 0 | **98.4% / 0** | 96.4% / 0 | 92.2% / 0 | 85.7% / 0 |
| SCRFD-10G | 100% / 3 | 99.3% / 0 | **98.4% / 0** | 97.0% / 0 | 94.6% / 0 |
| YuNet | 100% / 38 | 99.7% / 29 | 99.3% / 20 | **98.9% / 13** | 98.2% / 10 |

Real faces of 40 px or more kept / false positives of 40 px or more kept. The service returns
everything over 0.5, the bottom of the range.

### Minimum face size: 30 px for SCRFD-500M, 40 px for the others

Swept with the app filters at the default threshold:

| Minimum | SCRFD-500M mixed / usable | SCRFD-10G mixed / usable | YuNet mixed / usable |
|---|---|---|---|
| 20 px | 0 / 93.9% | 2 / 96.1% | 2 / 93.2% |
| 30 px | **0 / 93.3%** | 2 / 95.7% | 2 / 92.7% |
| 40 px | 0 / 92.0% | **1 / 94.0%** | **3 / 91.1%** |
| 50 px | 0 / 89.4% | 0 / 91.4% | 1 / 88.5% |
| 80 px | 0 / 72.6% | 0 / 73.8% | 2 / 70.3% |

The same with the faces labeled `ignorar` clustered too, as the app would, gives the same counts
of mixed clusters for SCRFD. But the score only counts named faces, so what decides is the share of
unrecognizable faces that would show up inside the clusters, over the default confidence:

| Face size | SCRFD-500M `ignorar` | SCRFD-10G `ignorar` |
|---|---|---|
| < 20 px | 100% | 100% |
| 20–30 px | 25% | 27% |
| 30–40 px | 2% | 3.6% |
| 40–60 px | 1.3–2.3% | 3–4% |

From 30 px the faces of SCRFD-500M are as good as bigger ones, so it suggests 30 px. SCRFD-10G and
YuNet mix more with small faces and keep the 40 px the app always used.

## Changes in the Nextcloud app

### The model profile

The service reports in `/open`:

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

The dlib service of facerecognition-external-model reports its own (Euclidean, 0.2/0.4/0.6, 0.99
over an unbounded MMOD score, 40 px), and a service that reports nothing is taken as dlib. The app:

- clusters and suggests links with that distance, and its sliders use those ranges;
- forgets the thresholds and the confidence chosen for another profile, since they are distances
  of other descriptors or scores of another detector. A minimum face size chosen by the
  administrator is kept, only limited to the new range: pixels mean the same for every model;
- **refuses to analyze with a service whose descriptors changed** since the images were analyzed,
  in the background job and in `occ face:setup`, and suggests `occ face:reset --model`.

Decided against: rebuilding the clusters automatically when the profile changes without changing
the descriptors (another detector in the same service). Rebuilding them loses the names given by
the users, so it is left to the administrator.

### The image area as a maximum

A new admin setting uses the analysis area only as a maximum: bigger images are reduced and
smaller ones are analyzed at their own size. The default is still the fixed area, which dlib needs.

### The minimum face size

It can be set from the admin settings, in the range suggested by the model.

## Tests of the app against this service

Nextcloud 34 with the app (the `docker/` environment of the app repository), 120 photos of the set:

- `occ face:setup --model 5` adopts the profile; 120 photos analyzed in ~50 s at 1 MP.
- **No mixed cluster, and no named face in the cluster of another person.** 82% of the named faces
  in clusters of 5 or more (fewer than the 92% of the whole set because many people have fewer
  than 5 faces in 120 photos). dlib HOG, through the dlib service, gave 23.5% in the same instance.
- At 4 MP, fixed area: every photo sent at 4.2 MP, 45 s, 82.9% usable. Area as a maximum: photos
  sent at their own size (median 2.7 MP), **21 s**, 83.3% usable.
- The 30 px suggested by the service, against 40 px: 8 faces left alone instead of 16, 85.6%
  usable instead of 83.3%, no mixed cluster.
- Switching to the dlib service without a reset is refused, also for an installation analyzed
  before the profile existed; after `occ face:reset --model` the dlib profile is adopted and the
  thresholds chosen for EdgeFace are forgotten.
- The admin sliders show the ranges of the model, and the settings controller refuses values out
  of them.
- The 70 unit tests of the app pass against Nextcloud 34, and psalm reports no errors. The 37
  integration tests passed too, before the minimum face size was added.

## Licenses

| Model | Weights | License |
|---|---|---|
| SCRFD-500M, SCRFD-10G | InsightFace `buffalo_sc`, `buffalo_l` | Non-commercial research use only |
| EdgeFace-Base | Idiap | CC BY-NC-SA 4.0 |
| YuNet | OpenCV Zoo | MIT |

The weights are downloaded while building the image. An image built with them must not be used
commercially. The only fully free pipeline measured, YuNet + SFace, mixes 10 clusters.

## Limitations and open questions

- One test set, of one kind of photos (actors in press and event photos), and labels reviewed by
  one person, seeded by recognizers that include ArcFace R50.
- Timings are on one machine and one thread; GPU execution was not tested.
- Open: lowering `maximum_area` of the service to ~4 MP (enlarging to 8 MP loses faces), and
  narrowing the range of the minimum face size slider (0–250 px, where the useful values are
  20–80).
