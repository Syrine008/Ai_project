"""Inference for axis6-neuromotor-video."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np

from common.base import make_signal, make_timeline
from ..explain.explainer import build_explanation

MODEL_PATH = Path(__file__).resolve().parent / "lstm_autoencoder_ataxia.keras"
SCALER_PATH = Path(__file__).resolve().parent / "scaler_ataxia.pkl"

CLASSES = ["No anomaly", "Mild gait anomaly", "Ataxia gait anomaly"]


class Axis6ModelLoader:
    def __init__(self) -> None:
        self._model = None
        self._scaler = None

    def is_available(self) -> bool:
        return MODEL_PATH.exists() and SCALER_PATH.exists()

    def get(self) -> dict | None:
        if not self.is_available():
            return None

        if self._model is None:
            from tensorflow.keras.models import load_model

            self._model = load_model(MODEL_PATH, compile=False)

        if self._scaler is None:
            self._scaler = joblib.load(SCALER_PATH)

        return {"model": self._model, "scaler": self._scaler}


MODEL_LOADER = Axis6ModelLoader()


def preprocess(upload, metadata: dict) -> Any:
    """
    Placeholder preprocessing.
    Ton modèle LSTM Autoencoder a besoin normalement d'une séquence numérique
    de forme proche de: (1, timesteps, features).

    Pour l'instant, on garde un fallback demo pour ne pas casser l'API.
    """
    return None


def predict(upload, model: Optional[Any], metadata: dict) -> dict:
    """
    Return the AnalysisResult dict expected by the frontend.
    """
    if model is not None:
        try:
            keras_model = model.get("model")
            scaler = model.get("scaler")

            x = preprocess(upload, metadata)

            if x is not None:
                x = np.asarray(x, dtype=np.float32)

                if x.ndim == 2:
                    x = np.expand_dims(x, axis=0)

                original_shape = x.shape
                x_2d = x.reshape(-1, x.shape[-1])
                x_scaled = scaler.transform(x_2d).reshape(original_shape)

                reconstructed = keras_model.predict(x_scaled, verbose=0)
                error = float(np.mean(np.square(x_scaled - reconstructed)))

                threshold = float(metadata.get("threshold", 0.15)) if metadata else 0.15

                if error <= threshold:
                    predicted_class = "No anomaly"
                    top_confidence = 0.90
                else:
                    predicted_class = "Ataxia gait anomaly"
                    top_confidence = min(0.99, 0.60 + error)

                confidence = [
                    {
                        "label": "No anomaly",
                        "value": float(1 - top_confidence if predicted_class != "No anomaly" else top_confidence),
                    },
                    {
                        "label": "Ataxia gait anomaly",
                        "value": float(top_confidence if predicted_class != "No anomaly" else 1 - top_confidence),
                    },
                ]

                return {
                    "predictedClass": predicted_class,
                    "topConfidence": float(top_confidence),
                    "confidence": confidence,
                    "summary": f"LSTM autoencoder reconstruction error: {error:.4f}.",
                    "metrics": {
                        "reconstructionError": error,
                        "threshold": threshold,
                    },
                    **build_explanation(upload, metadata, model=keras_model),
                }

        except Exception as exc:
            return {
                "predictedClass": "Model integration error",
                "topConfidence": 0.0,
                "confidence": [],
                "summary": f"Model files found, but inference failed: {exc}",
                **build_explanation(upload, metadata, model=None),
            }

    return _mock_predict(upload, metadata)


def _mock_predict(upload, metadata: dict) -> dict:
    probs = [0.62, 0.38]

    confidence = [
        {"label": "No anomaly", "value": float(probs[0])},
        {"label": "Ataxia gait anomaly", "value": float(probs[1])},
    ]

    top_idx = int(np.argmax(probs))

    return {
        "predictedClass": confidence[top_idx]["label"],
        "topConfidence": float(confidence[top_idx]["value"]),
        "confidence": confidence,
        "summary": "Demo mode: mild gait asymmetry detected. Real preprocessing still needs to be connected.",
        "signal": make_signal(),
        "timeline": make_timeline(),
        **build_explanation(upload, metadata, model=None),
    }