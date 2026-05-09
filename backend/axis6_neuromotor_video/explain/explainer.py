"""Explainability for axis6-neuromotor-video.

Returns the axis-specific fields appended to the AnalysisResult:
regions, signal, timeline, network, metrics. Replace with real
saliency / attention maps once the model is plugged in.
"""
from __future__ import annotations

from typing import Any, Optional

from common.base import make_signal, make_timeline


REGIONS = [('Right upper limb', 'R', 0.32), ('Left lower limb', 'L', 0.21), ('Trunk sway', 'B', 0.18)]
METRICS = [('Stride variability', '12.4%'), ('Tremor freq', '5.2 Hz'), ('Postural sway', 'Moderate')]


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
    payload["timeline"] = make_timeline([
        (3, "Gait initiation hesitation", "moderate"),
        (11, "Tremor onset (right hand)", "high"),
        (22, "Postural sway", "moderate"),
    ])

    return payload
