"""Inference for axis3-cerebellar-dysfunction.

Plug your trained model in by saving it to:

    axis3_cerebellar_dysfunction_model.pkl

Once the file exists, `MODEL_LOADER` will joblib-load it on first call and
`predict()` will hand it to your real inference code (see TODO below).
Until then, `predict()` returns a realistic mock so the API stays usable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from common.base import ModelLoader, make_signal, make_timeline
from ..explain.explainer import build_explanation

# === PLACEHOLDER PATH — drop the real .pkl here ===
MODEL_PATH = Path(__file__).resolve().parent / "axis3_cerebellar_dysfunction_model.pkl"
MODEL_LOADER = ModelLoader(MODEL_PATH)

CLASSES = ['No cerebellar involvement', 'Mild cerebellar involvement', 'Marked cerebellar involvement']


def preprocess(upload, metadata: dict) -> Any:
    """Convert the upload into model input.

    TODO: implement real preprocessing for MRI input.
    For MRI: load NIfTI/DICOM, skull-strip, normalize, resample.
    For fMRI: parcellate, build connectivity matrix.
    For Video: extract frames, run pose estimation.
    For EEG: load EDF, bandpass filter, segment.
    """
    return upload  # placeholder


def predict(upload, model: Optional[Any], metadata: dict) -> dict:
    """Run inference and return the AnalysisResult dict.

    If a real model is loaded, we delegate to it. Otherwise we fall back to
    a deterministic mock so the demo stays alive.
    """
    if model is not None:
        # === PLUG YOUR MODEL HERE ===
        # x = preprocess(upload, metadata)
        # probs = model.predict_proba([x])[0]
        # pred_idx = int(probs.argmax())
        # confidence = [
        #     {"label": cls, "value": float(p)}
        #     for cls, p in zip(CLASSES, probs)
        # ]
        # return {
        #     "predictedClass": CLASSES[pred_idx],
        #     "topConfidence": float(probs[pred_idx]),
        #     "confidence": confidence,
        #     "summary": "Model-generated summary…",
        #     **build_explanation(upload, metadata, model=model),
        # }
        pass

    # ---- mock fallback (used until the .pkl is plugged in) ----
    return _mock_predict(upload, metadata)


def _mock_predict(upload, metadata: dict) -> dict:
    probs = [0.62, 0.19, 0.19]
    confidence = [
        {"label": cls, "value": float(p)}
        for cls, p in zip(CLASSES, probs)
    ]
    top_idx = max(range(len(probs)), key=lambda i: probs[i])
    return {
        "predictedClass": CLASSES[top_idx],
        "topConfidence": float(probs[top_idx]),
        "confidence": confidence,
        "summary": 'Mild cerebellar involvement detected in posterior lobules; clinical correlation advised.',
        **build_explanation(upload, metadata, model=None),
    }
