"""Explainability payloads for axis 4 (Grad-CAM–derived regions + metrics fallbacks)."""
from __future__ import annotations

from typing import Any, Optional

import numpy as np

from common.base import make_signal


def regions_from_cam(cam: np.ndarray) -> list[dict]:
    """Pool Grad-CAM into coarse axial bands for the `RegionTable` UI."""
    h, _w = cam.shape[:2]
    h3 = max(1, h // 3)
    bands = [
        ("Anterior third", cam[:h3, :]),
        ("Central third", cam[h3 : 2 * h3, :]),
        ("Posterior third", cam[2 * h3 :, :]),
    ]
    scores = [max(0.0, float(b.mean())) for _n, b in bands]
    t = sum(scores) + 1e-8
    return [
        {"region": name, "side": "B", "contribution": round(s / t, 3), "note": "Grad-CAM mass (normalized)"}
        for (name, _), s in zip(bands, scores)
    ]


def build_explanation(
    upload: Any,
    metadata: dict,
    model: Optional[Any],
    *,
    regions: Optional[list[dict]] = None,
    metrics: Optional[list[dict]] = None,
) -> dict:
    """Assemble explainability fields; used by mock and real paths."""
    payload: dict = {
        "regions": regions
        if regions is not None
        else [
            {"region": "Prefrontal cortex", "side": "B", "contribution": 0.81},
            {"region": "Temporal pole", "side": "L", "contribution": 0.62},
            {"region": "Insula", "side": "R", "contribution": 0.47},
        ],
        "metrics": metrics
        if metrics is not None
        else [
            {"label": "Brain age (mock)", "value": "67 y"},
            {"label": "Chronological age (mock)", "value": "59 y"},
            {"label": "Brain-age gap (mock)", "value": "+8 y"},
        ],
    }
    payload["signal"] = make_signal(n=80, seed=21)
    return payload
