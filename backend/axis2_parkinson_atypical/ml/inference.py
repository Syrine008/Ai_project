"""Axis 2 Parkinson vs atypical parkinsonism inference."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import numpy as np

from common.base import ModelLoader
from ..explain.explainer import build_explanation
from .model_inference import (
    SLICE_AXIS,
    SLICES_PER_PATIENT,
    aggregate_patient_probabilities,
    choose_informative_slice_indices,
    load_model_checkpoint,
    load_preprocessed_volume,
    predict_slices,
)
from .preprocessing import preprocess_mri


AXIS_DIR = Path(__file__).resolve().parents[1]
ML_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = AXIS_DIR / "runtime"
UPLOAD_DIR = RUNTIME_DIR / "uploads"
OUTPUT_DIR = RUNTIME_DIR / "outputs"
PREPROCESSED_DIR = OUTPUT_DIR / "preprocessed_volumes_128"
MODELSPACE_NIFTI_DIR = OUTPUT_DIR / "modelspace_nifti"
EXPLAINABILITY_DIR = OUTPUT_DIR / "explainability"
CHECKPOINT_PATH = ML_DIR / "final_from_scratch_cnn_best_fold.pth"

THRESHOLD = 0.52
CLASSES = ["PD pattern", "Atypical parkinsonian pattern"]
DISCLAIMER = "Research decision-support output only. This result is not a clinical diagnosis."


@dataclass
class Axis2ModelBundle:
    model: Any
    checkpoint_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class Axis2CheckpointLoader(ModelLoader):
    """Load the local PyTorch checkpoint used by the axis2 CNN."""

    def __init__(self) -> None:
        super().__init__(CHECKPOINT_PATH)
        self._error: Optional[str] = None

    def get(self) -> Optional[Axis2ModelBundle]:
        if self._model is not None:
            return self._model
        if self._checked:
            return None
        self._checked = True

        if not CHECKPOINT_PATH.exists():
            self._error = f"Checkpoint not found: {CHECKPOINT_PATH}"
            return None

        try:
            model, checkpoint_metadata = load_model_checkpoint(CHECKPOINT_PATH)
            self._model = Axis2ModelBundle(
                model=model,
                checkpoint_metadata=checkpoint_metadata if isinstance(checkpoint_metadata, dict) else {},
            )
        except Exception as exc:  # pragma: no cover - keeps API stable when torch/env fails
            self._error = f"Checkpoint could not be loaded: {exc}"
            self._model = None
        return self._model

    @property
    def is_available(self) -> bool:
        return self.get() is not None

    @property
    def error(self) -> Optional[str]:
        return self._error


MODEL_LOADER = Axis2CheckpointLoader()


def _safe_name(value: object, fallback: str = "case") -> str:
    text = str(value or fallback)
    keep = [c if c.isalnum() or c in ("-", "_", ".") else "_" for c in text]
    return "".join(keep).strip("_") or fallback


def _patient_id(metadata: dict, upload: Any = None) -> str:
    explicit = metadata.get("patientId") or metadata.get("patient_id") or metadata.get("caseId")
    if explicit:
        return _safe_name(explicit, fallback="patient")
    stem = Path(getattr(upload, "name", "") or "patient").name
    if stem.endswith(".nii.gz"):
        stem = stem[:-7]
    else:
        stem = Path(stem).stem
    return f"{_safe_name(stem, fallback='patient')}_{uuid4().hex[:8]}"


def _save_upload(upload: Any, patient_id: str) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    original_name = Path(getattr(upload, "name", "") or "upload.nii").name
    target = UPLOAD_DIR / f"{_safe_name(patient_id, fallback='patient')}_{uuid4().hex[:8]}_{_safe_name(original_name, fallback='upload.nii')}"

    try:
        upload.seek(0)
    except Exception:
        pass

    with target.open("wb") as handle:
        for chunk in upload.chunks():
            handle.write(chunk)
    return target


def _run_loaded_model(bundle: Axis2ModelBundle, patient_id: str, volume_path: str | Path) -> dict[str, Any]:
    volume = load_preprocessed_volume(volume_path)
    slice_indices = choose_informative_slice_indices(
        volume,
        axis=SLICE_AXIS,
        n_slices=SLICES_PER_PATIENT,
    )
    device = next(bundle.model.parameters()).device
    slice_probs, used_indices = predict_slices(
        bundle.model,
        volume,
        slice_indices,
        axis=SLICE_AXIS,
        device=device,
    )
    patient_probs = aggregate_patient_probabilities(slice_probs)
    prob_pd = float(np.clip(patient_probs[0], 0.0, 1.0))
    prob_atypical = float(np.clip(patient_probs[1], 0.0, 1.0))
    predicted_label = int(prob_atypical >= THRESHOLD)

    metadata = bundle.checkpoint_metadata or {}
    return {
        "patient_id": str(patient_id),
        "volume_path": str(volume_path),
        "checkpoint_path": str(CHECKPOINT_PATH),
        "model_name": str(metadata.get("model_name", "ImprovedResidualSESmallCNN")),
        "prob_PD": prob_pd,
        "prob_Atypical": prob_atypical,
        "threshold": THRESHOLD,
        "predicted_label": predicted_label,
        "slice_indices": [int(x) for x in used_indices],
        "slice_probabilities": [
            {"slice_index": int(idx), "prob_PD": float(p[0]), "prob_Atypical": float(p[1])}
            for idx, p in zip(used_indices, slice_probs)
        ],
    }


def _confidence(prob_pd: float, prob_atypical: float) -> list[dict[str, float | str]]:
    return [
        {"label": CLASSES[0], "value": float(prob_pd)},
        {"label": CLASSES[1], "value": float(prob_atypical)},
    ]


def _summary(predicted_class: str, prob_pd: float, prob_atypical: float, threshold: float) -> str:
    return (
        f"The CNN detected a {predicted_class} using threshold {threshold:.2f}. "
        f"P(PD pattern)={prob_pd:.3f}; P(atypical parkinsonian pattern)={prob_atypical:.3f}. "
        "Use this only as research decision-support alongside clinical evaluation."
    )


def _format_real_result(
    inference: dict[str, Any],
    explanation: dict[str, Any],
    preprocessing: dict[str, Any],
    uploaded_path: Path,
    warnings: list[str],
) -> dict[str, Any]:
    prob_pd = float(inference["prob_PD"])
    prob_atypical = float(inference["prob_Atypical"])
    predicted_label = int(inference["predicted_label"])
    predicted_class = CLASSES[predicted_label]
    top_confidence = prob_atypical if predicted_label == 1 else prob_pd

    payload = {
        "predictedClass": predicted_class,
        "topConfidence": float(top_confidence),
        "confidence": _confidence(prob_pd, prob_atypical),
        "summary": _summary(predicted_class, prob_pd, prob_atypical, float(inference["threshold"])),
        "probabilities": {
            "probability_PD": prob_pd,
            "probability_atypical": prob_atypical,
            "decisionThreshold": float(inference["threshold"]),
        },
        "metrics": [
            {"label": "PD pattern probability", "value": f"{round(prob_pd * 100)}%"},
            {"label": "Atypical parkinsonian pattern probability", "value": f"{round(prob_atypical * 100)}%"},
            {"label": "Decision threshold", "value": f"{float(inference['threshold']):.2f}"},
            {"label": "Model", "value": str(inference.get("model_name") or "ImprovedResidualSESmallCNN")},
        ],
        "patientId": inference.get("patient_id"),
        "uploadedFilePath": str(uploaded_path),
        "preprocessedVolumePath": preprocessing.get("npy_path"),
        "modelspaceNiftiPath": preprocessing.get("modelspace_nifti_path"),
        "sliceIndices": inference.get("slice_indices", []),
        "sliceProbabilities": inference.get("slice_probabilities", []),
        "modelLoaded": True,
        "disclaimer": DISCLAIMER,
    }

    if warnings:
        payload["warnings"] = warnings

    explanation_metrics = list(explanation.pop("metrics", []) or [])
    if explanation_metrics:
        payload["metrics"].extend(explanation_metrics)
    payload.update(explanation)
    return payload


def predict(upload, model: Optional[Axis2ModelBundle], metadata: dict) -> dict:
    """Run the real axis2 CNN when possible; fall back only on real-pipeline failure."""
    warnings: list[str] = []

    if upload is None:
        return _mock_predict(upload, metadata, ["Demo mode uses representative values."])

    print("[AXIS2] real upload received:", getattr(upload, "name", None))

    if model is None:
        if MODEL_LOADER.error:
            warnings.append(MODEL_LOADER.error)
        warnings.append("Real axis2 inference could not start, so a fallback response was returned.")
        return _mock_predict(upload, metadata, warnings)

    patient_id = _patient_id(metadata, upload)
    try:
        uploaded_path = _save_upload(upload, patient_id)
        preprocessing = preprocess_mri(
            input_path=uploaded_path,
            patient_id=patient_id,
            output_npy_dir=PREPROCESSED_DIR,
            output_nifti_dir=MODELSPACE_NIFTI_DIR,
        )
        print("[AXIS2] preprocessing output:", preprocessing)
        inference = _run_loaded_model(model, patient_id, preprocessing["npy_path"])
        print("[AXIS2] inference output:", inference)
    except Exception as exc:
        warnings.append(f"Real axis2 inference failed: {type(exc).__name__}: {exc}")
        return _mock_predict(upload, metadata, warnings)

    print("[AXIS2] calling build_explanation with volume_path:", preprocessing["npy_path"])
    explanation = build_explanation(
        upload,
        metadata,
        model=model,
        patient_id=patient_id,
        volume_path=preprocessing["npy_path"],
        checkpoint_path=CHECKPOINT_PATH,
        output_dir=EXPLAINABILITY_DIR,
    )
    if explanation.get("explainabilityWarning"):
        warnings.append(str(explanation["explainabilityWarning"]))

    return _format_real_result(
        inference=inference,
        explanation=explanation,
        preprocessing=preprocessing,
        uploaded_path=uploaded_path,
        warnings=warnings,
    )


def _mock_predict(upload, metadata: dict, warnings: Optional[list[str]] = None) -> dict:
    prob_pd = 0.62
    prob_atypical = 0.38
    predicted_class = CLASSES[0]
    payload = {
        "predictedClass": predicted_class,
        "topConfidence": prob_pd,
        "confidence": _confidence(prob_pd, prob_atypical),
        "summary": (
            "Fallback response only. Real PD vs atypical parkinsonism inference was not completed "
            "for this request."
        ),
        "probabilities": {
            "probability_PD": prob_pd,
            "probability_atypical": prob_atypical,
            "decisionThreshold": THRESHOLD,
        },
        "modelLoaded": False,
        "disclaimer": DISCLAIMER,
        **build_explanation(upload, metadata, model=None),
    }
    if warnings:
        payload["warnings"] = warnings
    return payload
