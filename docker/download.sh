#!/bin/sh
# Downloads the model weights into $1, checking their sha256.
set -eu
M="$1"
mkdir -p "$M"

get() {
  wget -q -O "$M/$2" "$1"
  echo "$3  $M/$2" | sha256sum -c -
}

# YuNet (OpenCV Zoo, MIT)
get https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx \
    yunet_2023mar.onnx 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4

# SCRFD from the InsightFace packs (non-commercial research use only)
insightface() {
  wget -q -O "/tmp/$1.zip" "https://github.com/deepinsight/insightface/releases/download/v0.7/$1.zip"
  unzip -q -o -j "/tmp/$1.zip" "$2" -d "/tmp/$1"
  mv "/tmp/$1/$2" "$M/$3"
  rm -r "/tmp/$1.zip" "/tmp/$1"
  echo "$4  $M/$3" | sha256sum -c -
}
insightface buffalo_sc det_500m.onnx scrfd_500m.onnx 5e4447f50245bbd7966bd6c0fa52938c61474a04ec7def48753668a9d8b4ea3a
insightface buffalo_l det_10g.onnx scrfd_10g.onnx 5838f7fe053675b1c7a08b633df49e7af5495cee0493c7dcf6697200b85b5b91

# EdgeFace-Base (Idiap, CC BY-NC-SA 4.0), exported to ONNX by export_edgeface.py
get https://huggingface.co/Idiap/EdgeFace-Base/resolve/main/edgeface_base.pt \
    edgeface_base.pt 95861c09b22810136f43ec98845e7f09bfc3c43f5a804984a7bd2eac20abc30c
