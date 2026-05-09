"""Explainability for axis2-parkinson-atypical.

Returns the axis-specific fields appended to the AnalysisResult:
regions, signal, timeline, network, metrics. Replace with real
saliency / attention maps once the model is plugged in.
"""
from __future__ import annotations

from typing import Any, Optional

from common.base import make_signal, make_timeline


REGIONS = [('Substantia nigra', 'B', 0.38), ('Putamen', 'L', 0.21), ('Putamen', 'R', 0.19), ('Midbrain (SCP)', 'B', 0.24), ('Pons', 'B', 0.12)]
METRICS = [('MR Parkinsonism Index', '12.4'), ('SCP width', '2.1 mm'), ('Putaminal asymmetry', '8%')]


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
