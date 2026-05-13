"""Axis 1 Alzheimer MRI pattern inference."""
from __future__ import annotations

import json
import math
import tempfile
import zipfile
from base64 import b64encode
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import numpy as np

from common.base import ModelLoader
from ..explain.explainer import build_explanation

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIRS = (BASE_DIR / "models", BASE_DIR / "model")
CONFIG_DIR = BASE_DIR / "config"

CLASSES = ["Healthy / non-demented pattern", "Alzheimer-like / demented pattern"]
DISCLAIMER = "Decision-support only - not a standalone diagnosis. This result must be interpreted by a qualified clinician."
PREFERRED_3D_T1_KEYWORDS = (
    "mprage",
    "3d t1",
    "t1 3d",
    "t1_mprage",
    "spgr",
    "tfe",
    "bravo",
    "ir-spgr",
    "mpr",
    "iso",
    "sagittal 3d t1",
    "anatomical 3d",
    "structural 3d",
)
REJECT_SERIES_KEYWORDS = (
    "fl2d",
    "t1_fl2d",
    "axial 2d",
    "localizer",
    "scout",
    "dwi",
    "adc",
    "tof",
    "mip",
    "fieldmap",
    "screenshot",
    "derived",
)
ORIENTATION_TERMS = ("tra", "transverse")
MIN_3D_T1_SLICES = 80


@dataclass
class Axis1ModelBundle:
    cnn_model: Any = None
    grad_cam_model: Any = None
    fusion_model: Any = None
    thresholds: dict[str, float] | None = None
    feature_columns: list[str] | None = None
    metadata: dict[str, Any] | None = None
    warnings: list[str] | None = None
    grad_cam_debug: list[str] | None = None


class Axis1ModelLoader(ModelLoader):
    """Load Axis 1 artifacts from either ml/models or the current ml/model."""

    def __init__(self) -> None:
        super().__init__(BASE_DIR / "model" / "final_fusion_logistic_regression.joblib")

    def get(self) -> Optional[Axis1ModelBundle]:
        if self._model is not None:
            return self._model
        if self._checked:
            return None
        self._checked = True

        warnings: list[str] = []
        grad_cam_debug: list[str] = []
        model_dir = next((path for path in MODEL_DIRS if path.exists()), MODEL_DIRS[0])
        thresholds = _read_json(CONFIG_DIR / "thresholds.json", {"cnn_threshold": 0.5, "fusion_threshold": 0.69})
        feature_columns = _read_json(CONFIG_DIR / "fusion_feature_columns.json", [])
        metadata = _read_json(CONFIG_DIR / "deployment_metadata.json", {})
        fusion_model = None
        cnn_model = None
        grad_cam_model = None

        fusion_path = model_dir / "final_fusion_logistic_regression.joblib"
        if fusion_path.exists():
            try:
                import joblib

                fusion_bundle = joblib.load(fusion_path)
                if isinstance(fusion_bundle, dict):
                    fusion_model = fusion_bundle.get("model")
                    feature_columns = fusion_bundle.get("feature_cols") or feature_columns
                else:
                    fusion_model = fusion_bundle
            except Exception as exc:
                warnings.append(f"Fusion model could not be loaded: {exc}")
        else:
            warnings.append("Fusion model file was not found. Mock mode remains available.")

        torchscript_path = model_dir / "convnext_tiny_25d_torchscript.pt"
        full_model_path = model_dir / "convnext_tiny_25d_full_model.pt"
        try:
            import torch

            if torchscript_path.exists():
                cnn_model = torch.jit.load(str(torchscript_path), map_location="cpu")
            elif full_model_path.exists():
                try:
                    cnn_model = torch.load(str(full_model_path), map_location="cpu", weights_only=False)
                except TypeError:
                    cnn_model = torch.load(str(full_model_path), map_location="cpu")
            else:
                warnings.append("CNN model file was not found. CNN probability will use a safe mock value.")
            if hasattr(cnn_model, "eval"):
                cnn_model.eval()
        except Exception as exc:
            warnings.append(f"CNN model could not be loaded: {exc}")

        if full_model_path.exists():
            try:
                import torch

                try:
                    candidate = torch.load(str(full_model_path), map_location="cpu", weights_only=False)
                except TypeError:
                    candidate = torch.load(str(full_model_path), map_location="cpu")
                if hasattr(candidate, "named_modules"):
                    grad_cam_model = candidate
                    if hasattr(grad_cam_model, "eval"):
                        grad_cam_model.eval()
                else:
                    grad_cam_debug.append(f"Grad-CAM hookable model could not be loaded: full model has type {type(candidate).__name__}.")
            except Exception as exc:
                grad_cam_debug.append(f"Grad-CAM hookable model could not be loaded: {exc}")

        if fusion_model is None and cnn_model is None:
            return None

        self._model = Axis1ModelBundle(
            cnn_model=cnn_model,
            grad_cam_model=grad_cam_model,
            fusion_model=fusion_model,
            thresholds=thresholds,
            feature_columns=list(feature_columns or []),
            metadata=metadata,
            warnings=warnings,
            grad_cam_debug=grad_cam_debug,
        )
        return self._model


MODEL_LOADER = Axis1ModelLoader()


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def detect_upload_type(upload) -> str:
    name = (getattr(upload, "name", "") or "").lower()
    if name.endswith(".nii.gz") or name.endswith(".nii"):
        return "nifti"
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".dcm") or name == "dicomdir":
        return "dicom"
    return "unknown"


def extract_zip_to_temp(upload, temp_dir: Path) -> Path:
    target = temp_dir / "exam"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(upload) as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError("ZIP contains an unsafe file path.")
            archive.extract(member, target)
    return target


def find_dicom_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and (path.suffix.lower() in ("", ".dcm", ".ima") or path.name.upper() == "DICOMDIR")
    ]


def find_nifti_files(root: Path) -> list[Path]:
    return [path for path in root.rglob("*") if path.is_file() and (path.name.lower().endswith(".nii") or path.name.lower().endswith(".nii.gz"))]


def _nifti_slice_count(path: Path) -> Optional[int]:
    try:
        import nibabel as nib

        shape = nib.load(str(path)).shape
        return int(shape[2]) if len(shape) >= 3 else None
    except Exception:
        return None


def select_structural_nifti(files: list[Path]) -> tuple[Optional[Path], list[dict[str, Any]]]:
    available: list[dict[str, Any]] = []
    candidates: list[tuple[int, Path]] = []
    reject_terms = ("segmask", "mask", "segmentation", "label", "aparc", "atlas", "thickness", "dseg", "lesion")
    structural_terms = ("t1w", "t1", "mni_registered_t1w", "mprage", "mpr", "spgr", "tfe", "bravo", "structural", "anat")

    for path in files:
        text = str(path).lower()
        slice_count = _nifti_slice_count(path)
        if any(term in text for term in reject_terms):
            available.append(
                {
                    "seriesDescription": path.name,
                    "modality": "NIfTI",
                    "numberOfSlices": slice_count,
                    "status": "rejected",
                    "reason": "Rejected: segmentation, mask, label, or derived NIfTI file.",
                }
            )
            continue
        matched_terms = [term for term in structural_terms if term in text]
        if not matched_terms:
            available.append(
                {
                    "seriesDescription": path.name,
                    "modality": "NIfTI",
                    "numberOfSlices": slice_count,
                    "status": "rejected",
                    "reason": "Rejected: NIfTI file does not look like a structural T1w MRI.",
                }
            )
            continue
        score = (slice_count or 0) + (100 * len(matched_terms))
        available.append(
            {
                "seriesDescription": path.name,
                "modality": "NIfTI",
                "numberOfSlices": slice_count,
                "status": "candidate",
                "reason": f"Candidate: structural T1w indicator detected ({', '.join(matched_terms)}).",
            }
        )
        candidates.append((score, path))

    if not candidates:
        return None, available
    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = candidates[0][1]
    for item in available:
        if item["seriesDescription"] == selected.name:
            item["status"] = "selected"
            item["reason"] = "Structural T1w NIfTI volume accepted directly."
        elif item["status"] == "candidate":
            item["status"] = "rejected"
            item["reason"] = "Rejected: another compatible structural T1w NIfTI volume was selected."
    return selected, available


def group_dicom_series(files: list[Path]) -> list[dict[str, Any]]:
    try:
        import pydicom
    except Exception:
        return []

    grouped: dict[str, dict[str, Any]] = {}
    for path in files:
        try:
            ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        except Exception:
            continue
        modality = str(getattr(ds, "Modality", "MR") or "MR")
        if modality.upper() != "MR":
            continue
        uid = str(getattr(ds, "SeriesInstanceUID", path.parent.as_posix()))
        item = grouped.setdefault(
            uid,
            {
                "uid": uid,
                "description": str(getattr(ds, "SeriesDescription", "MRI series")),
                "modality": modality,
                "files": [],
            },
        )
        item["files"].append(path)
    return list(grouped.values())


def _series_description(item: dict[str, Any]) -> str:
    return str(item.get("description") or "MRI series")


def _series_slice_count(item: dict[str, Any]) -> int:
    return len(item.get("files") or [])


def _available_series_item(item: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    return {
        "seriesDescription": _series_description(item),
        "modality": item.get("modality") or "MR",
        "numberOfSlices": _series_slice_count(item),
        "status": status,
        "reason": reason,
    }


def select_structural_t1_series(
    series: list[dict[str, Any]],
) -> tuple[Optional[dict[str, Any]], list[str], list[str], list[dict[str, Any]], bool]:
    warnings: list[str] = []
    available: list[dict[str, Any]] = []
    candidates: list[tuple[int, dict[str, Any]]] = []

    for item in series:
        desc = _series_description(item)
        desc_lower = desc.lower()
        slice_count = _series_slice_count(item)
        reject_terms = [word for word in REJECT_SERIES_KEYWORDS if word in desc_lower]
        has_orientation_only_term = any(word in desc_lower for word in ORIENTATION_TERMS)
        preferred_terms = [word for word in PREFERRED_3D_T1_KEYWORDS if word in desc_lower]
        has_t1_mpr_iso = all(word in desc_lower for word in ("t1", "mpr", "iso"))
        if has_t1_mpr_iso:
            preferred_terms.extend([word for word in ("t1", "mpr", "iso") if word not in preferred_terms])

        if reject_terms:
            reason = f"Rejected: likely non-structural or 2D sequence ({', '.join(reject_terms)})."
            available.append(_available_series_item(item, "rejected", reason))
            continue
        if has_orientation_only_term and not preferred_terms:
            reason = "Rejected: transverse/axial orientation without strong 3D structural T1 indicators."
            available.append(_available_series_item(item, "rejected", reason))
            continue
        if slice_count < MIN_3D_T1_SLICES:
            reason = f"Rejected: fewer than {MIN_3D_T1_SLICES} slices; not reliable as a 3D structural T1 volume."
            available.append(_available_series_item(item, "rejected", reason))
            continue
        if not preferred_terms:
            reason = "Candidate: sufficient slices, but the description does not clearly indicate a 3D T1 structural sequence."
            available.append(_available_series_item(item, "candidate", reason))
            candidates.append((slice_count, item))
            continue

        score = 1000 + slice_count + (100 * len(preferred_terms))
        reason = f"Candidate: true 3D structural T1 keyword detected ({', '.join(preferred_terms)})."
        available.append(_available_series_item(item, "candidate", reason))
        candidates.append((score, item))

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    if not candidates:
        warnings.append("No compatible 3D structural T1 MRI series was detected. Please upload a 3D T1/MPRAGE/SPGR/TFE/BRAVO structural MRI or a compatible NIfTI volume.")
        for item in available:
            warnings.append(f"{item['seriesDescription']}: {item['reason']}")
        return None, [], warnings, available, False

    top_score, selected = candidates[0]
    compatible = [item for score, item in candidates if score >= 1000]
    uncertain = len(compatible) == 0 or (len(candidates) > 1 and top_score - candidates[1][0] < 100)
    if uncertain:
        warnings.append("Several compatible MRI series were found. Please select the structural 3D T1 series to continue.")
        return None, [], warnings, available, True

    ignored = []
    selected_desc = _series_description(selected)
    for item in available:
        if item["seriesDescription"] == selected_desc:
            item["status"] = "selected"
            item["reason"] = "Selected: best clear 3D structural T1 sequence."
        elif item["status"] == "candidate":
            item["status"] = "rejected"
            item["reason"] = "Rejected: a clearer 3D structural T1 sequence was selected."
            ignored.append(item["seriesDescription"])
        else:
            ignored.append(item["seriesDescription"])

    return selected, ignored, warnings, available, False


def load_nifti_volume(upload) -> np.ndarray:
    try:
        import nibabel as nib
    except Exception as exc:
        raise RuntimeError("NIfTI support requires nibabel.") from exc

    name = (getattr(upload, "name", "") or "").lower()
    suffix = ".nii.gz" if name.endswith(".nii.gz") else Path(name).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        for chunk in upload.chunks():
            handle.write(chunk)
        temp_path = Path(handle.name)
    try:
        return np.asarray(nib.load(str(temp_path)).get_fdata(), dtype=np.float32)
    finally:
        temp_path.unlink(missing_ok=True)


def load_nifti_volume_from_path(path: Path) -> np.ndarray:
    try:
        import nibabel as nib
    except Exception as exc:
        raise RuntimeError("NIfTI support requires nibabel.") from exc
    return np.asarray(nib.load(str(path)).get_fdata(), dtype=np.float32)


def convert_dicom_series_to_volume(series: dict[str, Any]) -> np.ndarray:
    try:
        import pydicom
    except Exception as exc:
        raise RuntimeError("DICOM support requires pydicom.") from exc

    slices = []
    for path in series.get("files") or []:
        try:
            ds = pydicom.dcmread(str(path), force=True)
            slices.append((float(getattr(ds, "InstanceNumber", len(slices))), ds.pixel_array.astype(np.float32)))
        except Exception:
            continue
    if not slices:
        raise RuntimeError("Selected DICOM series could not be converted to a volume.")
    slices.sort(key=lambda item: item[0])
    return np.stack([arr for _, arr in slices], axis=-1)


def normalize_volume(volume: np.ndarray) -> np.ndarray:
    volume = np.nan_to_num(volume.astype(np.float32), copy=False)
    p1, p99 = np.percentile(volume, [1, 99])
    clipped = np.clip(volume, p1, p99)
    return (clipped - float(clipped.mean())) / (float(clipped.std()) or 1.0)


def extract_25d_slices(volume: np.ndarray) -> np.ndarray:
    if volume.ndim != 3:
        raise ValueError("Expected a 3D MRI volume.")
    z = volume.shape[2]
    indexes = np.linspace(max(1, z // 4), min(z - 2, 3 * z // 4), num=min(9, max(1, z - 2))).astype(int)
    samples = []
    for idx in indexes:
        samples.append(_resize_25d(np.stack([volume[:, :, idx - 1], volume[:, :, idx], volume[:, :, idx + 1]], axis=0)))
    return np.stack(samples, axis=0)


def _resize_25d(sample: np.ndarray, size: int = 224) -> np.ndarray:
    try:
        import cv2

        return np.stack([cv2.resize(channel, (size, size), interpolation=cv2.INTER_AREA) for channel in sample], axis=0)
    except Exception:
        rows = np.linspace(0, sample.shape[1] - 1, size).astype(int)
        cols = np.linspace(0, sample.shape[2] - 1, size).astype(int)
        return sample[:, rows][:, :, cols]


def compute_mri_proxy_features(volume: np.ndarray, cnn_probability: float, metadata: dict) -> dict[str, float]:
    mask = volume > np.percentile(volume, 35)
    coords = np.argwhere(mask)
    bbox = np.ptp(coords, axis=0) if coords.size else np.array([0, 0, 0])
    mid = mask.shape[2] // 2
    central = mask[:, :, max(0, mid - 3) : min(mask.shape[2], mid + 4)]
    values = volume[mask] if mask.any() else volume.reshape(-1)
    sex = str(metadata.get("sex") or "").upper()
    return {
        "cnn_ad_probability": float(cnn_probability),
        "brain_voxel_count_proxy": float(mask.sum()),
        "brain_volume_ratio_proxy": float(mask.mean()),
        "intensity_mean": float(values.mean()),
        "intensity_std": float(values.std()),
        "intensity_p10": float(np.percentile(values, 10)),
        "intensity_p50": float(np.percentile(values, 50)),
        "intensity_p90": float(np.percentile(values, 90)),
        "left_right_asymmetry_proxy": float(abs(mask[: mask.shape[0] // 2].mean() - mask[mask.shape[0] // 2 :].mean())),
        "bbox_x": float(bbox[0]),
        "bbox_y": float(bbox[1]),
        "bbox_z": float(bbox[2]),
        "central_slice_area_mean": float(central.mean()),
        "central_slice_area_std": float(central.std()),
        "sex_encoded": 1.0 if sex == "M" else 0.0,
        "education": 0.0,
        "ses": 0.0,
    }


def _to_float(value: Any, fallback: float) -> float:
    try:
        return fallback if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return fallback


def _predict_cnn(bundle: Axis1ModelBundle, inputs: np.ndarray, warnings: list[str]) -> float:
    if bundle.cnn_model is None:
        warnings.append("CNN model is not loaded. A deterministic demo probability was used.")
        return 0.71
    try:
        import torch

        with torch.no_grad():
            output = bundle.cnn_model(torch.from_numpy(inputs).float())
            if isinstance(output, (tuple, list)):
                output = output[0]
            if output.ndim == 1:
                values = torch.sigmoid(output)
            elif output.ndim == 2 and output.shape[1] == 1:
                values = torch.sigmoid(output[:, 0])
            elif output.ndim == 2 and output.shape[1] >= 2:
                values = torch.softmax(output, dim=1)[:, 1]
            else:
                values = torch.sigmoid(output.reshape(output.shape[0], -1)[:, 0])
            return float(max(0.0, min(1.0, values.mean().item())))
    except Exception as exc:
        warnings.append(f"CNN inference could not be completed: {exc}")
        return 0.71


def _grad_cam_unavailable(debug_reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "message": "Grad-CAM could not be generated.",
        "debugReason": debug_reason,
    }


def _unwrap_grad_cam_model(model: Any) -> Any:
    current = model
    for attr in ("module", "model", "net", "network", "backbone"):
        wrapped = getattr(current, attr, None)
        if wrapped is not None and wrapped is not current and hasattr(wrapped, "named_modules"):
            current = wrapped
    return current


def _find_grad_cam_layer(model: Any) -> tuple[Any, str]:
    try:
        import torch.nn as nn
    except Exception as exc:
        return None, f"torch.nn unavailable: {exc}"

    model = _unwrap_grad_cam_model(model)
    modules = list(model.named_modules()) if hasattr(model, "named_modules") else []
    if not modules:
        return None, f"No named_modules available on model type {type(model).__name__}."

    conv_modules = [(name, module) for name, module in modules if isinstance(module, nn.Conv2d)]
    for name, module in reversed(conv_modules):
        if isinstance(module, nn.Conv2d):
            return module, f"Selected Conv2d layer: {name or '<root>'}."
    return None, f"No Conv2d layer found in model type {type(model).__name__}; module count={len(modules)}."


def _to_uint8_image(channel: np.ndarray) -> np.ndarray:
    channel = np.nan_to_num(channel.astype(np.float32), copy=False)
    low, high = np.percentile(channel, [1, 99])
    scaled = np.clip((channel - low) / ((high - low) or 1.0), 0.0, 1.0)
    return (scaled * 255).astype(np.uint8)


def _generate_grad_cam(bundle: Axis1ModelBundle, inputs: np.ndarray, volume: np.ndarray) -> dict[str, Any]:
    model = bundle.grad_cam_model
    if model is None and hasattr(bundle.cnn_model, "named_modules"):
        model = bundle.cnn_model
    if model is None:
        load_reason = "; ".join(bundle.grad_cam_debug or [])
        reason = "No hookable model loaded. TorchScript prediction may work, but a full PyTorch model with named_modules is required for Grad-CAM."
        if load_reason:
            reason = f"{reason} {load_reason}"
        return _grad_cam_unavailable(reason)

    layer, layer_debug = _find_grad_cam_layer(model)
    if layer is None:
        return _grad_cam_unavailable(layer_debug)

    try:
        import cv2
        import torch
        import torch.nn.functional as F
        from PIL import Image

        model = _unwrap_grad_cam_model(model)
        model.eval()
        try:
            device = next(model.parameters()).device
        except Exception:
            device = torch.device("cpu")

        sample_index = int(len(inputs) // 2)
        sample = torch.from_numpy(inputs[sample_index : sample_index + 1]).float().to(device)
        if sample.ndim != 4:
            return _grad_cam_unavailable(f"Sample tensor shape unsupported for CNN Grad-CAM: {tuple(sample.shape)}.")
        sample.requires_grad_(True)
        for parameter in model.parameters():
            parameter.requires_grad_(True)
        activations: dict[str, Any] = {}
        gradients: dict[str, Any] = {}

        def forward_hook(_module, _args, output):
            if isinstance(output, (tuple, list)):
                output = output[0]
            if not hasattr(output, "register_hook"):
                return
            activations["value"] = output
            output.register_hook(lambda grad: gradients.__setitem__("value", grad))

        forward_handle = layer.register_forward_hook(forward_hook)
        try:
            if hasattr(model, "zero_grad"):
                model.zero_grad(set_to_none=True)
            with torch.enable_grad():
                output = model(sample)
                if isinstance(output, (tuple, list)):
                    output = output[0]
                if not hasattr(output, "ndim"):
                    return _grad_cam_unavailable(f"Model output type unsupported for Grad-CAM: {type(output).__name__}.")
                if output.ndim == 1:
                    target = output[0]
                elif output.ndim == 2 and output.shape[1] == 1:
                    target = output[0, 0]
                elif output.ndim == 2 and output.shape[1] >= 2:
                    target = output[0, 1]
                else:
                    target = output.reshape(output.shape[0], -1)[0, 0]
                target.backward()
        finally:
            forward_handle.remove()

        if "value" not in activations or "value" not in gradients:
            return _grad_cam_unavailable(f"No gradients captured from target layer. {layer_debug}")
        acts = activations["value"].detach()
        grads = gradients["value"].detach()
        if acts.ndim != 4 or grads.ndim != 4:
            return _grad_cam_unavailable(f"Target layer did not produce 4D activation/gradient maps. activation_shape={tuple(acts.shape)}, gradient_shape={tuple(grads.shape)}. {layer_debug}")

        weights = grads.mean(dim=(2, 3), keepdim=True)
        heatmap = torch.relu((weights * acts).sum(dim=1, keepdim=True))
        heatmap = F.interpolate(heatmap, size=sample.shape[-2:], mode="bilinear", align_corners=False)[0, 0]
        heatmap_np = heatmap.detach().cpu().numpy()
        heatmap_np = heatmap_np / (float(heatmap_np.max()) or 1.0)

        base_slice = _to_uint8_image(sample[0, 1].detach().cpu().numpy())
        color = cv2.applyColorMap((heatmap_np * 255).astype(np.uint8), cv2.COLORMAP_JET)
        color = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
        base_rgb = np.stack([base_slice, base_slice, base_slice], axis=-1)
        overlay = np.clip((0.6 * base_rgb) + (0.4 * color), 0, 255).astype(np.uint8)
        buffer = BytesIO()
        Image.fromarray(overlay).save(buffer, format="PNG")
        if not buffer.getvalue():
            return _grad_cam_unavailable("PNG encoder produced an empty Grad-CAM image.")
        return {
            "available": True,
            "imageDataUrl": f"data:image/png;base64,{b64encode(buffer.getvalue()).decode('ascii')}",
            "sliceIndex": int(volume.shape[2] // 2) if getattr(volume, "ndim", 0) == 3 else sample_index,
            "explanation": "Grad-CAM highlights image regions that influenced the CNN probability for the Alzheimer-like class. It is a model attention map, not a clinical localization of disease.",
        }
    except Exception as exc:
        return _grad_cam_unavailable(f"Grad-CAM hook failed: {type(exc).__name__}: {exc}")


def _predict_fusion(bundle: Axis1ModelBundle, features: dict[str, float], warnings: list[str]) -> float:
    columns = bundle.feature_columns or []
    missing = [col for col in columns if col not in features or not math.isfinite(float(features[col]))]
    if bundle.fusion_model is None or missing:
        if missing:
            warnings.append("Fusion model could not run because required non-age features are incomplete.")
        return float(features.get("cnn_ad_probability", 0.71))
    try:
        import pandas as pd

        x = pd.DataFrame([{col: features[col] for col in columns}], columns=columns)
        if hasattr(bundle.fusion_model, "predict_proba"):
            return float(bundle.fusion_model.predict_proba(x)[0][-1])
        return float(bundle.fusion_model.predict(x)[0])
    except Exception as exc:
        warnings.append(f"Fusion model inference could not be completed: {exc}")
        return float(features.get("cnn_ad_probability", 0.71))


def _confidence_level(probability: float, threshold: float) -> str:
    margin = abs(probability - threshold)
    if margin >= 0.25:
        return "High"
    if margin >= 0.10:
        return "Moderate"
    return "Low"


def _cnn_threshold(bundle: Axis1ModelBundle) -> float:
    thresholds = bundle.thresholds or {}
    return float(thresholds.get("cnn_threshold", thresholds.get("threshold", 0.5)))


def _mri_features_payload(features: dict[str, float]) -> list[dict[str, Any]]:
    definitions = [
        ("brain_voxel_count_proxy", "Brain volume proxy", "voxels", "Estimated count of MRI voxels above the internal brain-intensity threshold."),
        ("brain_volume_ratio_proxy", "Brain volume ratio proxy", "ratio", "Ratio of voxels included by the internal brain-intensity mask."),
        ("central_slice_area_mean", "Central slice area mean", "ratio", "Mean masked area across central MRI slices."),
        ("intensity_mean", "Intensity mean", "", "Mean normalized MRI intensity within the internal mask."),
        ("intensity_std", "Intensity standard deviation", "", "Standard deviation of normalized MRI intensity within the internal mask."),
        ("left_right_asymmetry_proxy", "Left-right asymmetry proxy", "ratio", "Approximate difference between left and right masked MRI volume proportions."),
        ("bbox_x", "Bounding box X", "voxels", "X-axis extent of the internal MRI mask."),
        ("bbox_y", "Bounding box Y", "voxels", "Y-axis extent of the internal MRI mask."),
        ("bbox_z", "Bounding box Z", "voxels", "Z-axis extent of the internal MRI mask."),
    ]
    payload = []
    for key, label, unit, description in definitions:
        value = features.get(key)
        if value is None or not math.isfinite(float(value)):
            continue
        payload.append({"label": label, "value": round(float(value), 4), "unit": unit, "description": description})
    return payload


def _series_info(upload_type: str, selected: Optional[dict[str, Any]], ignored: list[str], upload, volume=None) -> dict[str, Any]:
    if upload_type == "nifti":
        selected_name = selected.name if isinstance(selected, Path) else getattr(upload, "name", "NIfTI volume")
        return {
            "selectedSeries": selected_name,
            "seriesDescription": "NIfTI structural MRI volume",
            "modality": "NIfTI",
            "numberOfSlices": int(volume.shape[2]) if getattr(volume, "ndim", 0) == 3 else None,
            "reasonSelected": "Structural T1w NIfTI volume accepted directly",
            "ignoredSeries": ignored,
        }
    if selected:
        return {
            "selectedSeries": selected.get("description") or "Selected MRI series",
            "seriesDescription": selected.get("description") or "Selected MRI series",
            "modality": selected.get("modality") or "MR",
            "numberOfSlices": len(selected.get("files") or []),
            "reasonSelected": "structural T1-like sequence with sufficient slice count",
            "ignoredSeries": ignored,
        }
    return {"selectedSeries": None, "seriesDescription": None, "modality": "MRI", "numberOfSlices": None, "reasonSelected": None, "ignoredSeries": ignored}


def _clinical_metadata(metadata: dict) -> dict[str, Any]:
    payload = {
        "sex": metadata.get("sex"),
        "age": metadata.get("age"),
        "notes": metadata.get("notes"),
    }
    if metadata.get("mmse") not in (None, ""):
        payload["mmse"] = metadata.get("mmse")
    if metadata.get("cdr") not in (None, ""):
        payload["cdr"] = metadata.get("cdr")
    return payload


def _has_clinical_scores(metadata: dict) -> bool:
    return metadata.get("mmse") not in (None, "") or metadata.get("cdr") not in (None, "")


def _failure_response(upload, metadata: dict, warnings: list[str], available_series: Optional[list[dict[str, Any]]] = None) -> dict:
    return {
        "predictedClass": "MRI could not be processed",
        "topConfidence": 0.0,
        "confidence": [],
        "summary": "No compatible 3D structural T1 MRI series was detected. Please upload a 3D T1/MPRAGE/SPGR/TFE/BRAVO structural MRI or a compatible NIfTI volume.",
        "probabilities": {},
        "metrics": [],
        "seriesInfo": {
            "selectedSeries": None,
            "seriesDescription": None,
            "modality": "MRI",
            "numberOfSlices": None,
            "reasonSelected": None,
            "ignoredSeries": [],
        },
        "availableSeries": available_series or [],
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
        "metadataUsed": ["sex"],
        "metadataExcluded": ["age", "MMSE", "CDR", "education"],
        "uploadedExamName": getattr(upload, "name", ""),
        "patientId": metadata.get("patientId"),
        "clinicalMetadata": _clinical_metadata(metadata),
        **build_explanation(upload, metadata, model=None),
    }


def _mock_predict(upload, metadata: dict, warnings: Optional[list[str]] = None) -> dict:
    probability = 0.74
    threshold = 0.5
    healthy_probability = 1.0 - probability
    predicted = CLASSES[1] if probability >= threshold else CLASSES[0]
    warnings = warnings or []
    if metadata.get("demo"):
        warnings.append("Demo mode uses representative values. Upload a patient MRI exam for case-specific analysis.")
    return {
        "predictedClass": predicted,
        "topConfidence": max(probability, healthy_probability),
        "confidence": [{"label": CLASSES[1], "value": probability}, {"label": CLASSES[0], "value": healthy_probability}],
        "summary": "The MRI-based model detected an Alzheimer-like pattern with moderate confidence. This output is intended for decision support and should be interpreted with clinical examination and cognitive testing.",
        "probabilities": {
            "alzheimerProbability": probability,
            "healthyProbability": healthy_probability,
            "cnnAlzheimerProbability": probability,
            "decisionThreshold": threshold,
            "confidenceLevel": _confidence_level(probability, threshold),
        },
        "metrics": [
            {"label": "Alzheimer-like / demented probability", "value": "74%"},
            {"label": "Healthy / non-demented probability", "value": "26%"},
            {"label": "Decision threshold", "value": "50%"},
        ],
        "seriesInfo": {
            "selectedSeries": "Demo structural MRI" if metadata.get("demo") else getattr(upload, "name", None),
            "seriesDescription": "T1-like anatomical volume",
            "modality": "MRI",
            "numberOfSlices": 160 if metadata.get("demo") else None,
            "reasonSelected": "structural T1-like sequence with sufficient slice count",
            "ignoredSeries": ["Localizer", "DWI", "ADC"] if metadata.get("demo") else [],
        },
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
        "metadataUsed": ["sex"],
        "metadataExcluded": ["age", "MMSE", "CDR", "education"],
        "uploadedExamName": getattr(upload, "name", "demo-mri-exam"),
        "patientId": metadata.get("patientId"),
        "clinicalMetadata": _clinical_metadata(metadata),
        **build_explanation(upload, metadata, model=None),
    }


def predict(upload, model: Optional[Axis1ModelBundle], metadata: dict) -> dict:
    warnings: list[str] = []
    if model is None:
        warnings.append("Axis 1 model files were not fully loaded. Real MRI analysis cannot run.")
        if metadata.get("demo"):
            return _mock_predict(upload, metadata, warnings)
        return _failure_response(upload, metadata, warnings)

    warnings.extend([warning for warning in (model.warnings or []) if "fusion" not in warning.lower()])
    if metadata.get("demo") or upload is None:
        return _mock_predict(upload, metadata, warnings)

    upload_type = detect_upload_type(upload)
    selected_series = None
    selected_nifti: Optional[Path] = None
    ignored_series: list[str] = []
    available_series: list[dict[str, Any]] = []
    volume = None
    cnn_inputs = None
    try:
        if upload_type == "nifti":
            volume = load_nifti_volume(upload)
            available_series = [
                {
                    "seriesDescription": getattr(upload, "name", "NIfTI volume"),
                    "modality": "NIfTI",
                    "numberOfSlices": int(volume.shape[2]) if getattr(volume, "ndim", 0) == 3 else None,
                    "status": "selected",
                    "reason": "Structural T1w NIfTI volume accepted directly.",
                }
            ]
        elif upload_type in ("zip", "dicom"):
            with tempfile.TemporaryDirectory() as temp:
                temp_dir = Path(temp)
                if upload_type == "zip":
                    root = extract_zip_to_temp(upload, temp_dir)
                    nifti_files = find_nifti_files(root)
                    if nifti_files:
                        selected_nifti, nifti_available = select_structural_nifti(nifti_files)
                        available_series.extend(nifti_available)
                        structural_nifti_count = sum(
                            1
                            for item in nifti_available
                            if item.get("status") == "selected"
                            or str(item.get("reason", "")).startswith("Rejected: another compatible structural T1w")
                        )
                        if structural_nifti_count > 1:
                            warnings.append(
                                "Multiple structural NIfTI files were found. The selected structural T1w file was used. For cleaner analysis, upload one subject at a time."
                            )
                        if selected_nifti is not None:
                            upload_type = "nifti"
                            volume = load_nifti_volume_from_path(selected_nifti)
                else:
                    root = temp_dir
                    dicom_file = root / (getattr(upload, "name", "upload.dcm") or "upload.dcm")
                    with dicom_file.open("wb") as handle:
                        for chunk in upload.chunks():
                            handle.write(chunk)
                if volume is None:
                    series = group_dicom_series(find_dicom_files(root))
                    selected_series, ignored_series, series_warnings, dicom_available, selection_uncertain = select_structural_t1_series(series)
                    available_series.extend(dicom_available)
                    warnings.extend(series_warnings)
                    if selected_series is None or selection_uncertain:
                        return _failure_response(upload, metadata, warnings, available_series)
                    volume = convert_dicom_series_to_volume(selected_series)
        else:
            warnings.append("Unsupported upload type. Please upload a T1-weighted NIfTI volume or ZIP containing DICOM files.")
            return _failure_response(upload, metadata, warnings, available_series)

        normalized = normalize_volume(volume)
        cnn_inputs = extract_25d_slices(normalized)
        cnn_probability = _predict_cnn(model, cnn_inputs, warnings)
        features = compute_mri_proxy_features(normalized, cnn_probability, metadata)
        fusion_warnings: list[str] = []
        fusion_probability = _predict_fusion(model, features, fusion_warnings)
    except Exception as exc:
        warnings.append(f"MRI preprocessing is incomplete for this upload: {exc}")
        return _failure_response(upload, metadata, warnings, available_series)

    threshold = _cnn_threshold(model)
    alzheimer_probability = float(cnn_probability)
    healthy_probability = float(1.0 - alzheimer_probability)
    predicted = CLASSES[1] if alzheimer_probability >= threshold else CLASSES[0]
    confidence_level = _confidence_level(alzheimer_probability, threshold)
    top_confidence = max(alzheimer_probability, healthy_probability)
    confidence = [{"label": CLASSES[1], "value": alzheimer_probability}, {"label": CLASSES[0], "value": healthy_probability}]
    article = "an" if predicted == CLASSES[1] else "a"
    pattern_text = "Alzheimer-like" if predicted == CLASSES[1] else "healthy / non-demented"
    summary = (
        f"The MRI-based model detected {article} {pattern_text} pattern with {confidence_level.lower()} confidence. "
        "This output is intended for decision support and should be interpreted with clinical examination and cognitive testing."
    )
    explanation = build_explanation(upload, metadata, model=model, features=features)
    if cnn_inputs is not None:
        explanation["gradCam"] = _generate_grad_cam(model, cnn_inputs, normalized)
    technical_details = explanation.setdefault("technicalDetails", {})
    grad_cam = explanation.get("gradCam") or {}
    technical_details["gradCamStatus"] = grad_cam.get("debugReason") or grad_cam.get("message")
    technical_details["experimentalFusionProbability"] = float(fusion_probability)
    technical_details["fusionNote"] = "Fusion output is experimental and is not used for the final doctor-facing prediction."
    if fusion_warnings:
        technical_details["fusionWarnings"] = fusion_warnings

    return {
        "predictedClass": predicted,
        "topConfidence": top_confidence,
        "confidence": confidence,
        "summary": summary,
        "probabilities": {
            "alzheimerProbability": alzheimer_probability,
            "healthyProbability": healthy_probability,
            "cnnAlzheimerProbability": float(cnn_probability),
            "decisionThreshold": threshold,
            "confidenceLevel": confidence_level,
        },
        "metrics": [
            {"label": "Alzheimer-like / demented probability", "value": f"{round(alzheimer_probability * 100)}%"},
            {"label": "Healthy / non-demented probability", "value": f"{round(healthy_probability * 100)}%"},
            {"label": "Decision threshold", "value": f"{round(threshold * 100)}%"},
        ],
        "mriFeatures": _mri_features_payload(features),
        "seriesInfo": _series_info(upload_type, selected_nifti if selected_nifti is not None else selected_series, ignored_series, upload, volume),
        "availableSeries": available_series,
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
        "metadataUsed": ["sex"],
        "metadataExcluded": ["age", "MMSE", "CDR", "education"],
        "uploadedExamName": getattr(upload, "name", ""),
        "patientId": metadata.get("patientId"),
        "clinicalMetadata": _clinical_metadata(metadata),
        **explanation,
    }

