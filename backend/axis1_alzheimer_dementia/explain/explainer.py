"""Explainability for axis1-alzheimer-dementia.

Returns the axis-specific fields appended to the AnalysisResult:
regions, signal, timeline, network, metrics. Replace with real
saliency / attention maps once the model is plugged in.
"""
from __future__ import annotations

from typing import Any, Optional

from common.base import make_signal, make_timeline


REGIONS = [('Hippocampus', 'L', 0.34), ('Hippocampus', 'R', 0.31), ('Entorhinal cortex', 'L', 0.22), ('Entorhinal cortex', 'R', 0.2), ('Posterior cingulate', 'B', 0.18), ('Precuneus', 'B', 0.15)]
METRICS = [('Cortical thickness gap', '-0.42 mm'), ('Hippocampal volume %', '-18%'), ('MMSE-equiv', '21/30')]


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
