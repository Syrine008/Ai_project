"""Explainability for axis7-epilepsy-network.

Returns the axis-specific fields appended to the AnalysisResult:
regions, signal, timeline, network, metrics. Replace with real
saliency / attention maps once the model is plugged in.
"""
from __future__ import annotations

from typing import Any, Optional

from common.base import make_signal, make_timeline


REGIONS = [('Temporal channel T7', 'L', 0.34), ('Temporal channel T8', 'R', 0.21), ('Frontal Fp1', 'L', 0.16)]
METRICS = [('Instability score', '0.72'), ('Spike rate', '4.1/min'), ('Network entropy', '1.81')]


def _regions_payload() -> list[dict]:
    return [
        {"region": r, "side": s, "contribution": c}
        for r, s, c in REGIONS
    ]


def _metrics_payload() -> list[dict]:
    return [{"label": k, "value": v} for k, v in METRICS]


def build_explanation(upload, metadata: dict, model: Optional[Any]) -> dict:
    """Assemble the explainability payload.

    TODO when wiring real model:
      - replace REGIONS with model attention output
      - for signal axes: return the real waveform samples
      - for network axes: return real nodes/edges
      - for video axes: return real timeline markers
    """
    payload: dict = {
        "regions": _regions_payload(),
        "metrics": _metrics_payload(),
    }
    payload["signal"] = make_signal(n=160, seed=42)
    payload["timeline"] = make_timeline([
        (12, "Spike train", "moderate"),
        (47, "Instability window", "high"),
        (98, "Quiet period", "low"),
    ])

    return payload
