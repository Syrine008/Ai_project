"""Two-stage cerebellum inference. Missing weights never produce mock findings."""
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
import base64
import io
import json
import os
import numpy as np
import torch
from torch.nn import functional as F
from .models import Fast3DCNN, SessionFast3DCNN, Strong3DCNN
from .preprocessing import load_crop, stage_tensor

INFERENCE_LOCK = RLock()
STAGE1_LABELS = ["Healthy", "Anomaly"]
STAGE2_LABELS = ["Motor anomaly", "Cognitive anomaly"]


class ModelUnavailable(RuntimeError):
    pass


class CerebellumLoader:
    def __init__(self, directory=None):
        self.directory = Path(directory or os.environ.get(
            "CEREBELLUM_MODEL_DIR", Path(__file__).parent / "artifacts"))
        self._model = None

    def get(self):
        with INFERENCE_LOCK:
            if self._model is not None:
                return self._model
            required = ["manifest.json", "stage1.pth", "stage2.pth", "mni_template.nii.gz"]
            if any(not (self.directory / name).is_file() for name in required):
                raise ModelUnavailable("Cerebellum model bundle is not installed. Export it with notebooks/export_cerebellum.py.")
            try:
                manifest = json.loads((self.directory / "manifest.json").read_text())
                if (manifest["version"] != 1 or manifest["stage1_labels"] != STAGE1_LABELS
                        or manifest["stage2_labels"] != STAGE2_LABELS
                        or manifest["target_size"] != [128, 128, 64]
                        or manifest["crop"] != [[20, 150], [20, 120], [0, 90]]
                        or manifest["normalization"] != "percentile_1_99_minmax_then_per_stage_zscore"
                        or manifest["stage1_skull_strip"] is not True
                        or manifest["stage2_skull_strip"] is not False):
                    raise ValueError("Unsupported preprocessing or label contract")
                first = torch.load(self.directory / "stage1.pth", map_location="cpu", weights_only=True)
                second = torch.load(self.directory / "stage2.pth", map_location="cpu", weights_only=True)
                architecture = manifest.get("stage1_architecture", "Fast3DCNN")
                if architecture == "Fast3DCNN":
                    stage1 = Fast3DCNN(hidden=first["classifier.0.weight"].shape[0])
                elif architecture == "SessionFast3DCNN":
                    stage1 = SessionFast3DCNN()
                else:
                    raise ValueError("Unsupported Stage 1 architecture")
                stage2 = Strong3DCNN()
                stage1.load_state_dict(first, strict=True)
                stage2.load_state_dict(second, strict=True)
                stage1.eval()
                stage2.eval()
                parity_path = self.directory / "parity.json"
                if not parity_path.is_file():
                    raise ValueError("Missing notebook parity fixture")
                parity = json.loads(parity_path.read_text())
                sample = torch.tensor(parity["input"], dtype=torch.float32)
                if sample.shape != (1, 1, 16, 16, 16):
                    raise ValueError("Invalid parity input shape")
                with torch.no_grad():
                    for key, model in [("stage1", stage1), ("stage2", stage2)]:
                        expected = torch.tensor(parity[key], dtype=torch.float32)
                        if expected.shape != (1, 2) or not torch.allclose(model(sample), expected, atol=1e-4, rtol=1e-4):
                            raise ValueError("Notebook prediction parity failed")
                self._model = (stage1.eval(), stage2.eval(), self.directory / "mni_template.nii.gz")
            except Exception as exc:
                raise ModelUnavailable("Cerebellum model bundle is incompatible; re-export the notebook models.") from exc
            return self._model


MODEL_LOADER = CerebellumLoader()


def stage_result(probs, labels):
    index = int(np.argmax(probs))
    return {"predictedClass": labels[index], "topConfidence": float(probs[index]),
            "confidence": [{"label": label, "value": float(p)} for label, p in zip(labels, probs)]}


def gradcam(model, tensor, target):
    """3D Grad-CAM on the last convolution; display the middle crop slice."""
    from PIL import Image
    activation = []
    layer = next(layer for layer in reversed(list(model.features)) if isinstance(layer, torch.nn.Conv3d))
    hook = layer.register_forward_hook(lambda _m, _i, output: activation.append(output))
    try:
        with torch.enable_grad():
            scores = model(tensor.requires_grad_(True))
            gradient = torch.autograd.grad(scores[0, target], activation[0])[0]
            weights = gradient.mean(dim=(2, 3, 4), keepdim=True)
            cam = (weights * activation[0]).sum(1, keepdim=True).relu()
            cam = F.interpolate(cam, size=tensor.shape[2:], mode="trilinear", align_corners=False)
            heat = cam[0, 0].detach().numpy()
    finally:
        hook.remove()
    heat /= heat.max() + 1e-8
    mid = tensor.shape[-1] // 2
    scan = tensor.detach().numpy()[0, 0, :, :, mid]
    scan = (scan - scan.min()) / (np.ptp(scan) + 1e-8)
    gray = np.repeat(scan[..., None], 3, axis=-1)
    h = heat[:, :, mid]
    color = np.stack([h, 0.25 * h, 1 - h], axis=-1)
    overlay = gray * (1 - 0.5 * h[..., None]) + color * (0.5 * h[..., None])
    images = []
    for title, pixels in [("MRI crop", gray), ("Grad-CAM overlay", overlay)]:
        output = io.BytesIO()
        Image.fromarray(np.uint8(np.clip(pixels, 0, 1) * 255)).save(output, format="PNG")
        images.append({"title": title, "dataUrl": "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()})
    return {"images": images, "sliceIndex": mid,
            "explanation": "Model attention on the middle slice of the processed cerebellum crop; not a segmentation or lesion map."}


def predict_path(path, input_space, bundle):
    stage1, stage2, template = bundle
    crop = load_crop(path, input_space, template)
    with INFERENCE_LOCK:
        first_tensor = stage_tensor(crop, strip=True)
        with torch.no_grad():
            p1 = stage1(first_tensor).softmax(1)[0].numpy()
        if not np.isfinite(p1).all():
            raise RuntimeError("Model produced invalid scores.")
        first = stage_result(p1, STAGE1_LABELS)
        second = None
        selected, selected_tensor, index = stage1, first_tensor, int(np.argmax(p1))
        if index == 1:
            second_tensor = stage_tensor(crop, strip=False)
            with torch.no_grad():
                p2 = stage2(second_tensor).softmax(1)[0].numpy()
            if not np.isfinite(p2).all():
                raise RuntimeError("Model produced invalid scores.")
            second = stage_result(p2, STAGE2_LABELS)
            selected, selected_tensor, index = stage2, second_tensor, int(np.argmax(p2))
        final = second or first
        explanation = gradcam(selected, selected_tensor, index)
    return {
        "axisId": "axis3-cerebellar-dysfunction", "generatedAt": datetime.now(timezone.utc).isoformat(),
        "predictedClass": final["predictedClass"],
        "topConfidence": final["topConfidence"],
        "confidence": final["confidence"], "modelLoaded": True,
        "summary": ("Stage 1 classified the MRI as healthy; Stage 2 was not run." if second is None else
                    f"Stage 1 detected an anomaly. Stage 2 classified it as {second['predictedClass'].lower()}."),
        "disclaimer": "Research decision support, not a diagnosis. Model scores are not calibrated clinical probabilities.",
        "cerebellum": {"stage1": first, "stage2": second, "inputSpace": input_space,
                       "explainabilityStage": 2 if second else 1, **explanation},
    }
