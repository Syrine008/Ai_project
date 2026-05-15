"""Axis 2 explainability adapter."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any


UNAVAILABLE_MESSAGE = "Explainability output is not available for this case yet."
EXPLANATION_TITLE = "Grad-CAM explainability preview"
EXPLANATION_SUMMARY = (
    "Heatmap highlights image regions that influenced the CNN prediction. "
    "SynthSeg anatomical overlap is included only when available."
)


def _unavailable_payload() -> dict:
    return {
        "regions": [],
        "gradCamDataUrl": None,
        "gradCam": {
            "available": False,
            "message": UNAVAILABLE_MESSAGE,
        },
        "explanation": {
            "title": EXPLANATION_TITLE,
            "summary": UNAVAILABLE_MESSAGE,
        },
    }


def _image_data_url(path_value: Any) -> str | None:
    if not path_value:
        return None

    image_path = Path(path_value)
    if not image_path.exists() or not image_path.is_file():
        return None

    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _regions_from_top_regions(top_regions: Any) -> list[dict]:
    if not isinstance(top_regions, list):
        return []

    regions: list[dict] = []
    for item in top_regions:
        if not isinstance(item, dict):
            continue

        region_name = item.get("region_name") or item.get("region")
        if not region_name:
            continue

        percentage = item.get("percentage_of_total_attention")
        try:
            contribution = float(percentage) / 100.0
        except (TypeError, ValueError):
            contribution = 0.0

        regions.append(
            {
                "region": str(region_name),
                "side": "B",
                "contribution": max(0.0, min(1.0, contribution)),
                "note": "SynthSeg anatomical overlap when available.",
                "region_name": str(region_name),
                "percentage_of_total_attention": percentage,
            }
        )

    return regions


def build_explanation(
    upload=None,
    metadata=None,
    model=None,
    patient_id=None,
    volume_path=None,
    checkpoint_path=None,
    output_dir=None,
    synthseg_dir=None,
    **kwargs,
) -> dict:
    print("[AXIS2 EXPLAINER] build_explanation called")

    if not patient_id or not volume_path:
        return _unavailable_payload()

    try:
        print("[AXIS2 EXPLAINER] importing real explainability.py")
        from .explainability import run_explainability

        print("[AXIS2 EXPLAINER] calling run_explainability")
        summary = run_explainability(
            patient_id=patient_id,
            volume_path=volume_path,
            checkpoint_path=checkpoint_path,
            synthseg_dir=synthseg_dir,
            output_dir=output_dir,
        )
    except Exception as exc:
        warning = f"{type(exc).__name__}: {exc}"
        return {
            "regions": [],
            "gradCamDataUrl": None,
            "gradCam": {
                "available": False,
                "message": "Explainability could not be generated for this case.",
            },
            "explanation": {
                "title": EXPLANATION_TITLE,
                "summary": UNAVAILABLE_MESSAGE,
                "warning": "Explainability could not be generated. Inference result is still available.",
            },
            "explainabilityWarning": warning,
        }

    if not isinstance(summary, dict):
        summary = {}

    grad_cam_data_url = _image_data_url(summary.get("case_report_path"))
    image_exists = grad_cam_data_url is not None
    returned_paths = {
        key: summary.get(key)
        for key in (
            "volume_path",
            "checkpoint_path",
            "synthseg_path",
            "case_report_path",
            "slice_probability_profile_path",
            "top_regions_plot_path",
            "region_attention_table_path",
            "summary_json_path",
        )
        if summary.get(key) is not None
    }

    return {
        "regions": _regions_from_top_regions(summary.get("top_regions")),
        "gradCamDataUrl": grad_cam_data_url,
        "gradCam": {
            "available": image_exists,
            "imageDataUrl": grad_cam_data_url,
            "message": None if image_exists else UNAVAILABLE_MESSAGE,
            "reportPath": summary.get("case_report_path"),
        },
        "explanation": {
            "title": EXPLANATION_TITLE,
            "summary": EXPLANATION_SUMMARY,
        },
        "explainability": {
            "patient_id": summary.get("patient_id"),
            "paths": returned_paths,
            "top_regions": summary.get("top_regions", []),
            "selected_slices": summary.get("selected_slices", []),
        },
    }
