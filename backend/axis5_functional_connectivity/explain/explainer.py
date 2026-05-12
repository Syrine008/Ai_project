"""Explainability for axis5-functional-connectivity.

Returns the axis-specific fields appended to the AnalysisResult:
regions, signal, timeline, network, metrics. Replace with real
saliency / attention maps once the model is plugged in.
"""
from __future__ import annotations

from typing import Any, Optional

from common.base import make_signal, make_timeline


REGIONS = [('Default mode network', 'B', 0.3), ('Frontoparietal network', 'L', 0.24), ('Salience network', 'R', 0.2), ('DLPFC', 'L', 0.16)]
METRICS = [('Network efficiency', '0.71'), ('DMN-FPN coupling', '+0.34'), ('Effort index', 'High')]


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
    payload["network"] = {
        "nodes": [
            {"id": "DMN", "label": "Default Mode"},
            {"id": "FPN", "label": "Frontoparietal"},
            {"id": "SAL", "label": "Salience"},
            {"id": "DAN", "label": "Dorsal Attention"},
        ],
        "edges": [
            {"source": "DMN", "target": "FPN", "weight": 0.71},
            {"source": "FPN", "target": "SAL", "weight": 0.58},
            {"source": "SAL", "target": "DAN", "weight": 0.44},
            {"source": "DMN", "target": "DAN", "weight": 0.22},
        ],
    }
    payload["signal"] = make_signal(n=120, seed=11)

    return payload
