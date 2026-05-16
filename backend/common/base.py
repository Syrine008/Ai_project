"""Shared base classes for brAIn axis apps.

Each axis app subclasses these to get a fully-working DRF endpoint with the
right model loader, explainer hooks and serialized response shape.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView


def new_case_id() -> str:
    return "BRN-" + secrets.token_hex(3).upper()


# ---------------------------------------------------------------------------
# Model loader — picks up a .pkl file when it is dropped at `model_path`.
# Until then, predictions fall back to the axis-provided mock generator.
# ---------------------------------------------------------------------------


@dataclass
class ModelLoader:
    """Lazy joblib loader for a single .pkl file.

    Usage:
        loader = ModelLoader(Path(__file__).parent / "axis1_model.pkl")
        model = loader.get()  # None if the file does not exist yet
    """

    model_path: Path
    _model: Any = None
    _checked: bool = False

    def get(self) -> Optional[Any]:
        if self._model is not None:
            return self._model
        if self._checked:
            return None
        self._checked = True
        if not self.model_path.exists():
            return None
        try:
            import joblib  # local import — only needed when a real model is plugged in
            self._model = joblib.load(self.model_path)
        except Exception:  # pragma: no cover — keep API alive even on bad pkl
            self._model = None
        return self._model

    @property
    def is_available(self) -> bool:
        return self.get() is not None


# ---------------------------------------------------------------------------
# Base view — wires upload + metadata parsing, model call, explainability and
# response serialization. Each axis only provides an `axis_config`.
# ---------------------------------------------------------------------------


PredictFn = Callable[[Any, Optional[Any], dict], dict]


@dataclass
class AxisConfig:
    axis_id: str
    predict: PredictFn          # ml.inference.predict
    loader: ModelLoader         # ml.inference.MODEL_LOADER
    accepted_extensions: tuple[str, ...] = ()


class BaseAnalyzeView(APIView):
    """Generic /analyze/ endpoint.

    Subclasses set `axis_config: AxisConfig`. The view handles:
      - multipart upload + JSON metadata parsing
      - calling the axis predictor (real model if .pkl present, else mock)
      - persisting Case + Result rows
      - returning the AnalysisResult JSON shape the frontend expects
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    axis_config: AxisConfig

    def get_axis_config(self) -> AxisConfig:
        return self.axis_config

    def post(self, request, *args, **kwargs):
        cfg = self.get_axis_config()

        upload = request.FILES.get("file")
        metadata_raw = request.data.get("metadata", "{}")
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw or "{}")
            except json.JSONDecodeError:
                return Response(
                    {"detail": "metadata must be valid JSON"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            metadata = dict(metadata_raw)

        if upload is None and not metadata.get("demo"):
            return Response(
                {"detail": "file is required (or set metadata.demo=true)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if upload and cfg.accepted_extensions:
            name = (upload.name or "").lower()
            if not any(name.endswith(ext) for ext in cfg.accepted_extensions):
                return Response(
                    {
                        "detail": (
                            f"Unsupported file type for {cfg.axis_id}. "
                            f"Accepted: {', '.join(cfg.accepted_extensions)}"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        case_id = new_case_id()
        model = cfg.loader.get()
        result = cfg.predict(upload, model, metadata)

        # Always stamp the canonical fields
        result.setdefault("axisId", cfg.axis_id)
        result["caseId"] = case_id
        result.setdefault(
            "disclaimer",
            "Decision-support tool. Not a medical diagnosis. "
            "Clinical correlation required.",
        )
        result["modelLoaded"] = cfg.loader.is_available

        # Persist (best-effort — never break the response if DB write fails)
        try:
            from common.models import Case, Result  # late import to avoid circulars
            case = Case.objects.create(
                case_id=case_id,
                axis_id=cfg.axis_id,
                file_name=getattr(upload, "name", "") or "",
                metadata=metadata,
            )
            Result.objects.create(case=case, payload=result)
        except Exception:  # pragma: no cover
            pass

        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Mock generator helpers — used by each axis until a real .pkl is plugged in.
# Kept deterministic-ish per case so the demo feels coherent.
# ---------------------------------------------------------------------------


def _rand(seed: int) -> Callable[[], float]:
    """Tiny LCG so we don't require numpy at import time."""
    state = [seed & 0xFFFFFFFF or 1]

    def _next() -> float:
        state[0] = (1103515245 * state[0] + 12345) & 0x7FFFFFFF
        return state[0] / 0x7FFFFFFF

    return _next


def make_signal(n: int = 120, seed: int = 7) -> list[dict]:
    rnd = _rand(seed)
    out = []
    v = 0.0
    for t in range(n):
        v = 0.85 * v + (rnd() - 0.5) * 0.6
        out.append({"t": t, "v": round(v, 4)})
    return out


def make_timeline(events: list[tuple[int, str, str]]) -> list[dict]:
    return [{"t": t, "label": label, "severity": sev} for t, label, sev in events]
