"""Axis 1 Alzheimer-specific explainability payloads."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Optional

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts"
FEATURE_IMPORTANCE_PATH = ARTIFACT_DIR / "final_selected_fusion_feature_importance.csv"

FEATURE_LABELS = {
    "cnn_ad_probability": "CNN Alzheimer probability",
    "intensity_std": "MRI intensity variability",
    "intensity_p10": "MRI intensity percentiles",
    "intensity_p50": "MRI intensity percentiles",
    "intensity_p90": "MRI intensity percentiles",
    "brain_volume_ratio_proxy": "Brain volume proxy / nWBV if available",
    "brain_voxel_count_proxy": "Brain volume proxy / nWBV if available",
    "sex_encoded": "Sex",
}


def _read_feature_importance() -> list[dict[str, Any]]:
    if not FEATURE_IMPORTANCE_PATH.exists():
        return []

    rows: list[dict[str, Any]] = []
    with FEATURE_IMPORTANCE_PATH.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            feature = row.get("feature") or ""
            if feature in {"education", "ses"}:
                continue
            try:
                importance = float(row.get("importance_mean") or row.get("importance") or 0.0)
                std = float(row.get("importance_std") or 0.0)
            except ValueError:
                continue
            rows.append(
                {
                    "feature": feature,
                    "label": FEATURE_LABELS.get(feature, feature.replace("_", " ").title()),
                    "importance": importance,
                    "std": std,
                }
            )
    return rows[:10]


def build_explanation(upload, metadata: dict, model: Optional[Any], features: Optional[dict[str, float]] = None) -> dict:
    """Return explainability fields compatible with the frontend AnalysisResult."""
    payload = {
        "regions": [],
        "featureImportance": [],
        "gradCam": {
            "available": False,
            "message": "Grad-CAM could not be generated.",
            "debugReason": "Grad-CAM was not attempted for this response.",
        },
        "technicalDetails": {
            "pipeline": "MRI -> ConvNeXt-Tiny 2.5D -> CNN probability",
            "agePolicy": "Age is not included in the final prediction model.",
            "metadataPolicy": "Education and SES are not provided by the doctor and are handled internally as default values for model compatibility.",
            "computedFeatureCount": len(features or {}),
            "globalFeatureImportance": _read_feature_importance(),
        },
    }
    return payload
