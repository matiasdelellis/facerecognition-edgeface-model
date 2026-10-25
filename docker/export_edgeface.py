"""Exports EdgeFace-Base to ONNX and checks that onnxruntime gives the same embeddings as torch.

Usage: export_edgeface.py <edgeface repo> <edgeface_base.pt> <out.onnx>
"""
import sys

import numpy as np
import onnxruntime as ort
import torch

repo, weights, out = sys.argv[1:4]
sys.path.insert(0, repo)
from backbones import get_model  # noqa: E402

model = get_model("edgeface_base")
model.load_state_dict(torch.load(weights, map_location="cpu"))
model.eval()

dummy = torch.zeros(1, 3, 112, 112)
torch.onnx.export(model, dummy, out, input_names=["input"], output_names=["embedding"],
                  dynamic_axes={"input": {0: "batch"}, "embedding": {0: "batch"}}, opset_version=17)

x = np.random.default_rng(0).uniform(-1, 1, (4, 3, 112, 112)).astype(np.float32)
with torch.inference_mode():
    expected = model(torch.from_numpy(x)).numpy()
got = ort.InferenceSession(out, providers=["CPUExecutionProvider"]).run(None, {"input": x})[0]
cos = (expected * got).sum(1) / np.linalg.norm(expected, axis=1) / np.linalg.norm(got, axis=1)
print(f"torch vs onnxruntime cosine: min {cos.min():.6f}")
if cos.min() < 0.9999:
    sys.exit("The exported model does not match the torch one")
