"""Explainability for axis3-cerebellar-dysfunction.

Returns the axis-specific fields appended to the AnalysisResult:
regions, signal, timeline, network, metrics. Replace with real
saliency / attention maps once the model is plugged in.
"""
from __future__ import annotations

from typing import Any, Optional

from common.base import make_signal, make_timeline


REGIONS = [('Cerebellar lobule VI', 'L', 0.27), ('Cerebellar lobule VI', 'R', 0.25), ('Crus I', 'L', 0.22), ('Crus II', 'R', 0.18), ('Vermis', 'B', 0.14)]
METRICS = [('Cerebellar volume %', '-6.4%'), ('SARA-equiv', '9/40'), ('Vermis atrophy', 'Mild')]


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
    payload["signal"] = make_signal(n=80, seed=21)

    return payload
