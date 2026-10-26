# Notice on the model weights and non-commercial use

This repository does not contain the model weights. The Docker image downloads
them at build time. Each weight set has its own license. This notice covers the
weights; it does not grant a license to the source code of this repository.

## Weights used by the service

| Model | Used for | Source | License | Commercial use |
|---|---|---|---|---|
| EdgeFace-Base | face recognition (512-d descriptors) | Idiap Research Institute, [`Idiap/EdgeFace-Base`](https://huggingface.co/Idiap/EdgeFace-Base) | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) | No |
| SCRFD-500M | face detection (`DETECTOR=scrfd_500m`) | InsightFace [`buffalo_sc`](https://github.com/deepinsight/insightface/tree/master/model_zoo) | Non-commercial research use only | No |
| SCRFD-10G | face detection (`DETECTOR=scrfd_10g`) | InsightFace [`buffalo_l`](https://github.com/deepinsight/insightface/tree/master/model_zoo) | Non-commercial research use only | No |
| YuNet | face detection (`DETECTOR=yunet`) | OpenCV Zoo [`face_detection_yunet_2023mar`](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | [MIT](https://github.com/opencv/opencv_zoo/blob/main/LICENSE) | Yes, on its own |

## What “non-commercial” means here

- The service **as built and distributed is for non-commercial use only**,
  because EdgeFace-Base and the SCRFD weights are non-commercial. Choosing YuNet
  does not change that: EdgeFace-Base is still in the pipeline.
- CC BY-NC-SA 4.0 does not allow use “primarily intended for or directed
  towards commercial advantage or monetary compensation” (see the
  [license](https://creativecommons.org/licenses/by-nc-sa/4.0/) and the
  [CC FAQ](https://creativecommons.org/faq/#what-does-noncommercial-mean)).
  It also requires attribution and, for adaptations, distribution under the
  same license.
- To the extent the ONNX file produced by `docker/export_edgeface.py` is an
  adaptation of EdgeFace-Base, it must be distributed with attribution, an
  indication that it was converted to ONNX, and under CC BY-NC-SA 4.0 as well.
- The InsightFace source code is MIT, but the `buffalo_*` model packs are
  licensed for non-commercial research use only. The MIT code license does not
  apply to the weights.
- YuNet's MIT license applies only to YuNet.

## Commercial use

Commercial use requires a license from the rights holders, or replacing the
weights with commercially licensed ones:

- EdgeFace-Base: Idiap Research Institute (see the
  [model card](https://huggingface.co/Idiap/EdgeFace-Base)).
- SCRFD: InsightFace (see their
  [face recognition model licensing](https://insightface.ai/solutions/face-recognition-licensing)).

This repository does not grant such a license.

## Attribution

When redistributing the weights or a built image, keep this notice and the
upstream license links, and cite:

- A. George, C. Ecabert, H. Otroshi Shahreza, K. Kotwal, S. Marcel,
  “EdgeFace: Efficient Face Recognition Model for Edge Devices”,
  IEEE Transactions on Biometrics, Behavior, and Identity Science 6(2):158–168,
  2024. [arXiv:2307.01838](https://arxiv.org/abs/2307.01838).
- J. Guo et al., “Sample and Computation Redistribution for Efficient Face
  Detection”, [arXiv:2105.04714](https://arxiv.org/abs/2105.04714) (SCRFD).
- OpenCV Zoo, `face_detection_yunet_2023mar` (YuNet).

## Acknowledgement

The service refuses to start until `LICENSE_ACCEPTED=non-commercial` is set.
That variable is an acknowledgement by the operator; it does not verify the
actual use and is not a license. The upstream licenses remain in force.

This notice is informational and does not modify the upstream licenses. Read
them before using or redistributing the weights.
