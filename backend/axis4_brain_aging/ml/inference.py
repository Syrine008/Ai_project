"""Axis 4 — brain age regression (EfficientNet-B0, refinement B checkpoint)."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
import torch
from django.core.files.uploadedfile import UploadedFile

from common.base import make_signal
from ..explain.explainer import build_explanation, regions_from_cam

from .checkpoint import BrainAgeCheckpointLoader
from .constants import TYPICAL_MAE_YEARS
from .gradcam import compute_gradcam, encode_overlay_png_bytes
from .preprocess import (
    classify_analyze_hdr_img,
    load_analyze_hdr_img_pair,
    load_analyze_zip,
    load_image_slice,
    load_nifti_slice,
)

CHECKPOINT_PATH = Path(__file__).resolve().parent / "checkpoints" / "best_ref_b_dropout03_lr5e5.pth"
MODEL_LOADER = BrainAgeCheckpointLoader(CHECKPOINT_PATH)

CLASSES = ["Within expected range", "Mildly accelerated", "Markedly accelerated"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_chronological_age(metadata: dict) -> Optional[float]:
    raw = metadata.get("age")
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _confidence_from_gap(gap: Optional[float]) -> list[dict]:
    """Soft three-way display (not calibrated probabilities)."""
    if gap is None:
        return [
            {"label": "Regression estimate (± typical MAE)", "value": 0.55},
            {"label": "Chronological age not provided for gap", "value": 0.30},
            {"label": "Research prototype — interpret cautiously", "value": 0.15},
        ]
    a = abs(gap)
    if a <= 3.0:
        return [
            {"label": CLASSES[0], "value": 0.72},
            {"label": CLASSES[1], "value": 0.20},
            {"label": CLASSES[2], "value": 0.08},
        ]
    if a <= 8.0:
        return [
            {"label": CLASSES[0], "value": 0.22},
            {"label": CLASSES[1], "value": 0.58},
            {"label": CLASSES[2], "value": 0.20},
        ]
    return [
        {"label": CLASSES[0], "value": 0.12},
        {"label": CLASSES[1], "value": 0.28},
        {"label": CLASSES[2], "value": 0.60},
    ]


def _top_confidence(confidence: list[dict]) -> float:
    return max(float(c["value"]) for c in confidence)


def _load_input_tensor(
    upload: UploadedFile,
    *,
    pair_bytes: Optional[bytes] = None,
    pair_name: str = "",
) -> tuple[torch.Tensor, np.ndarray, str]:
    """Primary upload + optional Analyze companion (.hdr+.img), or single .zip / NIfTI / image."""
    name = (upload.name or "").lower()
    raw = upload.read()

    if pair_bytes is not None:
        hdr_b, img_b = classify_analyze_hdr_img(
            raw,
            upload.name or "",
            pair_bytes,
            pair_name or "",
        )
        return (*load_analyze_hdr_img_pair(hdr_b, img_b), "analyze")

    if name.endswith(".zip"):
        return (*load_analyze_zip(raw), "analyze_zip")

    if name.endswith((".nii", ".nii.gz")):
        return (*load_nifti_slice(raw), "nifti")

    if name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return (*load_image_slice(raw), "image")

    if name.endswith((".hdr", ".img")):
        raise ValueError(
            "Analyze .hdr/.img requires both parts: upload a .zip containing them, "
            "or use primary upload + second slot ('Analyze pair') for the other file."
        )

    raise ValueError(f"Unsupported upload type: {name}")


def predict(upload: Optional[UploadedFile], model: Optional[Any], metadata: dict) -> dict:
    """Return `AnalysisResult`-shaped dict for the brAIn frontend."""
    base = {"generatedAt": _utc_now_iso()}
    meta = dict(metadata)
    pair_bytes = meta.pop("_internal_analyze_pair_bytes", None)
    pair_name = meta.pop("_internal_analyze_pair_name", "") or ""

    if upload is None and meta.get("demo"):
        return {**base, **_mock_predict(meta)}

    if model is None:
        return {**base, **_mock_predict(meta)}

    if upload is None:
        return {**base, **_mock_predict(meta)}

    try:
        x, vis_01, _kind = _load_input_tensor(
            upload,
            pair_bytes=pair_bytes,
            pair_name=pair_name,
        )
    except Exception as exc:  # noqa: BLE001 — user uploads; stay JSON-stable
        return {
            **base,
            "predictedClass": "Preprocessing failed",
            "topConfidence": 0.0,
            "confidence": [{"label": "Error", "value": 1.0}],
            "summary": (
                f"Could not read input: {exc}. "
                "Use .nii/.nii.gz, PNG/JPEG slice, .zip with .hdr+.img, or two uploads (.hdr + .img)."
            ),
            "disclaimer": (
                "Research prototype on OASIS-like preprocessing only. "
                "Not a clinical diagnostic tool."
            ),
            "regions": [{"region": "N/A", "side": "B", "contribution": 0.0}],
            "metrics": [{"label": "Status", "value": "Read error"}],
            "signal": make_signal(n=40, seed=3),
        }

    device = next(model.parameters()).device
    x = x.to(device)
    with torch.no_grad():
        pred_t = model(x)
    pred_age = float(pred_t.squeeze().cpu().item())

    chron = _parse_chronological_age(metadata)
    gap = (pred_age - chron) if chron is not None else None

    confidence = _confidence_from_gap(gap)
    predicted_class = f"Predicted brain age: {pred_age:.1f} years"

    mae = TYPICAL_MAE_YEARS
    low, high = pred_age - mae, pred_age + mae
    summary_parts = [
        f"Point estimate {pred_age:.1f} y (validation subject MAE ≈ ±{mae:.1f} y on OASIS).",
        f"Approximate band [{low:.1f}, {high:.1f}] y — illustrative, not calibrated for new scanners or cohorts.",
    ]
    if chron is not None:
        summary_parts.append(f"Chronological age entered: {chron:.1f} y (Δ ≈ {gap:+.1f} y).")
    else:
        summary_parts.append("Enter patient age in metadata to compare brain vs chronological age.")
    summary = " ".join(summary_parts)

    cam = compute_gradcam(model, x.cpu())
    vis224 = np.asarray(
        np.clip(cv2.resize(vis_01, (224, 224), interpolation=cv2.INTER_LINEAR), 0, 1),
        dtype=np.float32,
    )
    png_bytes = encode_overlay_png_bytes(vis224, cam)
    grad_cam_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")

    regions = regions_from_cam(cam)
    metrics = [
        {"label": "Predicted brain age", "value": f"{pred_age:.1f} y"},
        {"label": "Typical error (MAE)", "value": f"±{mae:.1f} y", "hint": "OASIS validation subject MAE"},
        {"label": "Approx. range", "value": f"[{low:.1f}, {high:.1f}] y"},
    ]
    if chron is not None:
        metrics.append({"label": "Chronological age", "value": f"{chron:.1f} y"})
        metrics.append({"label": "Brain–chronology Δ", "value": f"{gap:+.1f} y"})

    disclaimer = (
        "Research prototype (student project). Not FDA/CE-marked and not a substitute for "
        "clinical diagnosis or radiology review."
    )

    return {
        **base,
        "predictedClass": predicted_class,
        "topConfidence": _top_confidence(confidence),
        "confidence": confidence,
        "summary": summary,
        "disclaimer": disclaimer,
        "gradCamDataUrl": grad_cam_url,
        "regions": regions,
        "metrics": metrics,
        "signal": make_signal(n=80, seed=min(9999, max(1, int(abs(pred_age) * 10) % 10000))),
    }


def _mock_predict(metadata: dict) -> dict:
    probs = [0.62, 0.19, 0.19]
    confidence = [{"label": cls, "value": float(p)} for cls, p in zip(CLASSES, probs)]
    top_idx = max(range(len(probs)), key=lambda i: probs[i])
    return {
        "predictedClass": CLASSES[top_idx],
        "topConfidence": float(probs[top_idx]),
        "confidence": confidence,
        "summary": (
            "Mock brain-aging summary (no checkpoint or demo mode). "
            "Add `best_ref_b_dropout03_lr5e5.pth` under `ml/checkpoints/` for real inference."
        ),
        **build_explanation(None, metadata, model=None, regions=None, metrics=None),
    }
