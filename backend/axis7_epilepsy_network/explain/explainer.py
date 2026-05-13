from __future__ import annotations

from typing import Any

import numpy as np


def infer_side(channel_name: str) -> str:
    name = channel_name.strip().upper()
    if any(token in name for token in ["LEFT", " LT", " T7", " F7", " P7", " O1", " FP1", "-L", "_L"]):
        return "L"
    if any(token in name for token in ["RIGHT", " RT", " T8", " F8", " P8", " O2", " FP2", "-R", "_R"]):
        return "R"

    digits = [char for char in name if char.isdigit()]
    if digits:
        try:
            return "L" if int(digits[-1]) % 2 else "R"
        except ValueError:
            pass
    return "B"


def build_regions(channel_names: list[str], channel_importance: np.ndarray) -> list[dict[str, Any]]:
    if channel_importance.size == 0:
        return []

    scores = np.asarray(channel_importance, dtype=np.float32)
    if np.allclose(scores.sum(), 0):
        scores = np.ones_like(scores, dtype=np.float32)
    scores = scores / max(float(scores.sum()), 1e-6)
    order = np.argsort(scores)[::-1]

    items: list[dict[str, Any]] = []
    for idx in order[: min(6, len(order))]:
        channel_name = channel_names[idx] if idx < len(channel_names) else f"Channel {idx + 1}"
        items.append(
            {
                "region": channel_name,
                "side": infer_side(channel_name),
                "contribution": round(float(scores[idx]), 4),
                "note": "Top model-attributed signal channel" if not items else None,
            }
        )
    return items


def build_signal(primary_signal: np.ndarray, sample_rate: float, max_points: int = 240) -> list[dict[str, Any]]:
    if primary_signal.size == 0:
        return []

    signal = np.asarray(primary_signal, dtype=np.float32)
    stride = max(1, int(np.ceil(signal.size / max_points)))
    points = []
    for start in range(0, signal.size, stride):
        chunk = signal[start : start + stride]
        t = int(round(start / max(sample_rate, 1e-6)))
        points.append({"t": t, "v": round(float(chunk.mean()), 4)})
    return points


def build_timeline(events: list[dict[str, Any]], dominant_channel: str) -> list[dict[str, Any]]:
    timeline = []
    for event in events[:6]:
        label = event.get("label")
        if not label:
            label = f"{dominant_channel} instability"
        timeline.append(
            {
                "t": int(round(float(event["t"]))),
                "label": label,
                "severity": str(event["severity"]),
            }
        )
    return timeline


def build_network(channel_names: list[str], display_matrix: np.ndarray) -> dict[str, Any] | None:
    if display_matrix.ndim != 2:
        return None
    if display_matrix.shape[0] < 2 or display_matrix.shape[1] < 8:
        return None

    nodes = list(channel_names[: min(6, display_matrix.shape[0])])
    matrix = np.asarray(display_matrix[: len(nodes)], dtype=np.float32)
    if not np.isfinite(matrix).any():
        return None

    corr = np.corrcoef(matrix)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)

    edges = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            weight = abs(float(corr[i, j]))
            if weight < 0.2:
                continue
            edges.append(
                {
                    "from": nodes[i],
                    "to": nodes[j],
                    "weight": round(min(weight, 0.99), 4),
                }
            )

    edges.sort(key=lambda edge: edge["weight"], reverse=True)
    if not edges:
        return None
    return {"nodes": nodes, "edges": edges[:8]}

