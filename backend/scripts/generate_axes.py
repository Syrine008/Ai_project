"""Generate the 7 brAIn Django axis apps with full skeleton.

Run once. Idempotent — overwrites files.
"""
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent.parent  # backend/

AXES = [
    {
        "app": "axis1_alzheimer_dementia",
        "axis_id": "axis1-alzheimer-dementia",
        "title": "Alzheimer's vs Other Dementias",
        "input": "MRI",
        "exts": (".nii", ".nii.gz", ".dcm"),
        "classes": ["Alzheimer's disease", "Vascular dementia", "Frontotemporal dementia", "Other"],
        "regions": [
            ("Hippocampus", "L", 0.34),
            ("Hippocampus", "R", 0.31),
            ("Entorhinal cortex", "L", 0.22),
            ("Entorhinal cortex", "R", 0.20),
            ("Posterior cingulate", "B", 0.18),
            ("Precuneus", "B", 0.15),
        ],
        "metrics": [("Cortical thickness gap", "-0.42 mm"), ("Hippocampal volume %", "-18%"), ("MMSE-equiv", "21/30")],
        "summary": "Atrophy pattern (medial temporal + posterior cingulate) most consistent with Alzheimer's disease.",
        "kind": "mri",
    },
    {
        "app": "axis2_parkinson_atypical",
        "axis_id": "axis2-parkinson-atypical",
        "title": "Parkinson's vs Atypical Syndromes",
        "input": "MRI",
        "exts": (".nii", ".nii.gz", ".dcm"),
        "classes": ["Parkinson's disease", "MSA", "PSP", "Other atypical"],
        "regions": [
            ("Substantia nigra", "B", 0.38),
            ("Putamen", "L", 0.21),
            ("Putamen", "R", 0.19),
            ("Midbrain (SCP)", "B", 0.24),
            ("Pons", "B", 0.12),
        ],
        "metrics": [("MR Parkinsonism Index", "12.4"), ("SCP width", "2.1 mm"), ("Putaminal asymmetry", "8%")],
        "summary": "Imaging signature compatible with idiopathic Parkinson's; atypical features below threshold.",
        "kind": "mri",
    },
    {
        "app": "axis3_cerebellar_dysfunction",
        "axis_id": "axis3-cerebellar-dysfunction",
        "title": "Cerebellar Dysfunction",
        "input": "MRI",
        "exts": (".nii", ".nii.gz", ".dcm"),
        "classes": ["No cerebellar involvement", "Mild cerebellar involvement", "Marked cerebellar involvement"],
        "regions": [
            ("Cerebellar lobule VI", "L", 0.27),
            ("Cerebellar lobule VI", "R", 0.25),
            ("Crus I", "L", 0.22),
            ("Crus II", "R", 0.18),
            ("Vermis", "B", 0.14),
        ],
        "metrics": [("Cerebellar volume %", "-6.4%"), ("SARA-equiv", "9/40"), ("Vermis atrophy", "Mild")],
        "summary": "Mild cerebellar involvement detected in posterior lobules; clinical correlation advised.",
        "kind": "mri",
    },
    {
        "app": "axis4_brain_aging",
        "axis_id": "axis4-brain-aging",
        "title": "Uneven Brain Aging",
        "input": "MRI",
        "exts": (".nii", ".nii.gz", ".dcm"),
        "classes": ["Within expected range", "Mildly accelerated", "Markedly accelerated"],
        "regions": [
            ("Frontal lobe", "L", 0.28),
            ("Frontal lobe", "R", 0.26),
            ("Temporal lobe", "L", 0.21),
            ("Parietal lobe", "B", 0.15),
            ("White matter", "B", 0.10),
        ],
        "metrics": [("Brain age", "67 y"), ("Chronological age", "59 y"), ("Brain-age gap", "+8 y")],
        "summary": "Brain age exceeds chronological age by ~8 years, driven by frontotemporal regions.",
        "kind": "mri",
    },
    {
        "app": "axis5_functional_connectivity",
        "axis_id": "axis5-functional-connectivity",
        "title": "Hidden Cognitive Effort",
        "input": "fMRI",
        "exts": (".nii", ".nii.gz", ".mat"),
        "classes": ["Typical connectivity", "Compensatory pattern", "Disrupted connectivity"],
        "regions": [
            ("Default mode network", "B", 0.30),
            ("Frontoparietal network", "L", 0.24),
            ("Salience network", "R", 0.20),
            ("DLPFC", "L", 0.16),
        ],
        "metrics": [("Network efficiency", "0.71"), ("DMN-FPN coupling", "+0.34"), ("Effort index", "High")],
        "summary": "Compensatory frontoparietal recruitment suggests hidden cognitive effort.",
        "kind": "network",
    },
    {
        "app": "axis6_neuromotor_video",
        "axis_id": "axis6-neuromotor-video",
        "title": "Neuromotor Video Analysis",
        "input": "Video",
        "exts": (".mp4", ".mov", ".webm"),
        "classes": ["No anomaly", "Mild gait anomaly", "Tremor detected", "Postural instability"],
        "regions": [
            ("Right upper limb", "R", 0.32),
            ("Left lower limb", "L", 0.21),
            ("Trunk sway", "B", 0.18),
        ],
        "metrics": [("Stride variability", "12.4%"), ("Tremor freq", "5.2 Hz"), ("Postural sway", "Moderate")],
        "summary": "Resting tremor (~5 Hz) and mild gait asymmetry detected.",
        "kind": "video",
    },
    {
        "app": "axis7_epilepsy_network",
        "axis_id": "axis7-epilepsy-network",
        "title": "Epilepsy Vulnerability",
        "input": "EEG / Signal",
        "exts": (".edf", ".bdf", ".csv"),
        "classes": ["Stable network", "Mild instability", "Vulnerable / pre-ictal pattern"],
        "regions": [
            ("Temporal channel T7", "L", 0.34),
            ("Temporal channel T8", "R", 0.21),
            ("Frontal Fp1", "L", 0.16),
        ],
        "metrics": [("Instability score", "0.72"), ("Spike rate", "4.1/min"), ("Network entropy", "1.81")],
        "summary": "Left-temporal instability windows suggest heightened epilepsy vulnerability.",
        "kind": "signal",
    },
]


APP_INIT = ""

APPS_PY = '''from django.apps import AppConfig


class {cls}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{app}"
'''

URLS_PY = '''from django.urls import path
from .views import AnalyzeView

urlpatterns = [
    path("analyze/", AnalyzeView.as_view(), name="{app}-analyze"),
]
'''

VIEWS_PY = '''from common.base import AxisConfig, BaseAnalyzeView
from .ml.inference import MODEL_LOADER, predict


class AnalyzeView(BaseAnalyzeView):
    axis_config = AxisConfig(
        axis_id="{axis_id}",
        predict=predict,
        loader=MODEL_LOADER,
        accepted_extensions={exts!r},
    )
'''

SERIALIZERS_PY = '''"""Response shape mirrors `AnalysisResult` in src/lib/mockApi.ts.

We don't strictly serialize on the way out (the view returns a plain dict)
but these serializers document and validate the contract.
"""
from rest_framework import serializers


class ConfidenceItem(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.FloatField(min_value=0.0, max_value=1.0)


class RegionItem(serializers.Serializer):
    region = serializers.CharField()
    side = serializers.ChoiceField(choices=["L", "R", "B"])
    contribution = serializers.FloatField()


class SignalPoint(serializers.Serializer):
    t = serializers.IntegerField()
    v = serializers.FloatField()


class TimelineEvent(serializers.Serializer):
    t = serializers.IntegerField()
    label = serializers.CharField()
    severity = serializers.ChoiceField(choices=["low", "moderate", "high"])


class MetricItem(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()


class AnalysisResultSerializer(serializers.Serializer):
    axisId = serializers.CharField()
    caseId = serializers.CharField()
    predictedClass = serializers.CharField()
    topConfidence = serializers.FloatField()
    summary = serializers.CharField()
    disclaimer = serializers.CharField()
    confidence = ConfidenceItem(many=True)
    regions = RegionItem(many=True)
    signal = SignalPoint(many=True, required=False)
    timeline = TimelineEvent(many=True, required=False)
    network = serializers.DictField(required=False)
    metrics = MetricItem(many=True, required=False)


class AnalyzeRequestSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    metadata = serializers.JSONField(required=False)
'''

ML_INIT = ""

INFERENCE_PY = '''"""Inference for {axis_id}.

Plug your trained model in by saving it to:

    {model_filename}

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
MODEL_PATH = Path(__file__).resolve().parent / "{model_filename}"
MODEL_LOADER = ModelLoader(MODEL_PATH)

CLASSES = {classes!r}


def preprocess(upload, metadata: dict) -> Any:
    """Convert the upload into model input.

    TODO: implement real preprocessing for {input_kind} input.
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
        #     {{"label": cls, "value": float(p)}}
        #     for cls, p in zip(CLASSES, probs)
        # ]
        # return {{
        #     "predictedClass": CLASSES[pred_idx],
        #     "topConfidence": float(probs[pred_idx]),
        #     "confidence": confidence,
        #     "summary": "Model-generated summary…",
        #     **build_explanation(upload, metadata, model=model),
        # }}
        pass

    # ---- mock fallback (used until the .pkl is plugged in) ----
    return _mock_predict(upload, metadata)


def _mock_predict(upload, metadata: dict) -> dict:
    probs = {mock_probs!r}
    confidence = [
        {{"label": cls, "value": float(p)}}
        for cls, p in zip(CLASSES, probs)
    ]
    top_idx = max(range(len(probs)), key=lambda i: probs[i])
    return {{
        "predictedClass": CLASSES[top_idx],
        "topConfidence": float(probs[top_idx]),
        "confidence": confidence,
        "summary": {summary!r},
        **build_explanation(upload, metadata, model=None),
    }}
'''

EXPLAIN_INIT = ""

EXPLAINER_PY = '''"""Explainability for {axis_id}.

Returns the axis-specific fields appended to the AnalysisResult:
regions, signal, timeline, network, metrics. Replace with real
saliency / attention maps once the model is plugged in.
"""
from __future__ import annotations

from typing import Any, Optional

from common.base import make_signal, make_timeline


REGIONS = {regions!r}
METRICS = {metrics!r}


def _regions_payload() -> list[dict]:
    return [
        {{"region": r, "side": s, "contribution": c}}
        for r, s, c in REGIONS
    ]


def _metrics_payload() -> list[dict]:
    return [{{"label": k, "value": v}} for k, v in METRICS]


def build_explanation(upload, metadata: dict, model: Optional[Any]) -> dict:
    """Assemble the explainability payload.

    TODO when wiring real model:
      - replace REGIONS with model attention output
      - for signal axes: return the real waveform samples
      - for network axes: return real nodes/edges
      - for video axes: return real timeline markers
    """
    payload: dict = {{
        "regions": _regions_payload(),
        "metrics": _metrics_payload(),
    }}
{kind_block}
    return payload
'''


def kind_block(kind: str) -> str:
    if kind == "signal":
        return textwrap.indent(
            'payload["signal"] = make_signal(n=160, seed=42)\n'
            'payload["timeline"] = make_timeline([\n'
            '    (12, "Spike train", "moderate"),\n'
            '    (47, "Instability window", "high"),\n'
            '    (98, "Quiet period", "low"),\n'
            '])\n',
            "    ",
        )
    if kind == "video":
        return textwrap.indent(
            'payload["timeline"] = make_timeline([\n'
            '    (3, "Gait initiation hesitation", "moderate"),\n'
            '    (11, "Tremor onset (right hand)", "high"),\n'
            '    (22, "Postural sway", "moderate"),\n'
            '])\n',
            "    ",
        )
    if kind == "network":
        return textwrap.indent(
            'payload["network"] = {\n'
            '    "nodes": [\n'
            '        {"id": "DMN", "label": "Default Mode"},\n'
            '        {"id": "FPN", "label": "Frontoparietal"},\n'
            '        {"id": "SAL", "label": "Salience"},\n'
            '        {"id": "DAN", "label": "Dorsal Attention"},\n'
            '    ],\n'
            '    "edges": [\n'
            '        {"source": "DMN", "target": "FPN", "weight": 0.71},\n'
            '        {"source": "FPN", "target": "SAL", "weight": 0.58},\n'
            '        {"source": "SAL", "target": "DAN", "weight": 0.44},\n'
            '        {"source": "DMN", "target": "DAN", "weight": 0.22},\n'
            '    ],\n'
            '}\n'
            'payload["signal"] = make_signal(n=120, seed=11)\n',
            "    ",
        )
    # MRI default
    return textwrap.indent(
        'payload["signal"] = make_signal(n=80, seed=21)\n',
        "    ",
    )


MIGRATIONS_INIT = ""


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main() -> None:
    for axis in AXES:
        app = axis["app"]
        cls = "".join(p.capitalize() for p in app.split("_"))
        base = ROOT / app
        model_filename = f"{app}_model.pkl"

        # Mock probabilities — peaked on first class
        n = len(axis["classes"])
        primary = 0.62
        rest = (1 - primary) / (n - 1)
        probs = [primary] + [round(rest, 4)] * (n - 1)

        write(base / "__init__.py", APP_INIT)
        write(base / "apps.py", APPS_PY.format(cls=cls, app=app))
        write(base / "models.py", "# Persistence is shared via the `common` app (Case, Result).\n")
        write(base / "urls.py", URLS_PY.format(app=app))
        write(base / "views.py", VIEWS_PY.format(axis_id=axis["axis_id"], exts=axis["exts"]))
        write(base / "serializers.py", SERIALIZERS_PY)
        write(base / "migrations" / "__init__.py", MIGRATIONS_INIT)

        write(base / "ml" / "__init__.py", ML_INIT)
        write(
            base / "ml" / "inference.py",
            INFERENCE_PY.format(
                axis_id=axis["axis_id"],
                model_filename=model_filename,
                classes=axis["classes"],
                input_kind=axis["input"],
                mock_probs=probs,
                summary=axis["summary"],
            ),
        )
        # Placeholder marker so colleagues see exactly where to drop the .pkl
        write(
            base / "ml" / f"{model_filename}.PLACEHOLDER",
            f"Drop the trained model for {axis['axis_id']} here as `{model_filename}`.\n",
        )

        write(base / "explain" / "__init__.py", EXPLAIN_INIT)
        write(
            base / "explain" / "explainer.py",
            EXPLAINER_PY.format(
                axis_id=axis["axis_id"],
                regions=axis["regions"],
                metrics=axis["metrics"],
                kind_block=kind_block(axis["kind"]),
            ),
        )

        # Per-axis README
        write(
            base / "README.md",
            f"# {app}\n\n"
            f"Django app for **{axis['title']}** ({axis['input']}).\n\n"
            f"- Endpoint: `POST /api/{axis['axis_id']}/analyze/`\n"
            f"- Model placeholder: `{app}/ml/{model_filename}` "
            f"(drop your trained model here — `ModelLoader` will pick it up).\n"
            f"- Real-model wiring: see `ml/inference.py::predict()`.\n"
            f"- Explainability: see `explain/explainer.py::build_explanation()`.\n",
        )

    print("Generated", len(AXES), "axis apps.")


if __name__ == "__main__":
    main()
