# brAIn — Django backend

Full Django + Django REST Framework backend for the 7 brAIn neurology
decision-support axes. Each axis is a self-contained Django app with:

- `views.py`         — DRF `AnalyzeView` accepting upload + metadata
- `serializers.py`   — request / response serializers (mirror frontend `AnalysisResult`)
- `models.py`        — `Case` + `Result` persistence
- `urls.py`          — route wiring
- `ml/inference.py`  — model loader + `predict()` (plug your `.pkl` here)
- `ml/<axis>_model.pkl`  — **placeholder** path — drop your trained model here
- `explain/explainer.py` — axis-specific explainability (heatmaps, regions, signals, network…)

The `predict()` function currently returns realistic mock outputs so the API is
fully functional end-to-end. To wire the real model, just replace the `.pkl`
file at the placeholder path — `ModelLoader` will pick it up automatically.

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Endpoints

| Axis | Endpoint |
|------|----------|
| 1 — Alzheimer's vs Other Dementias | `POST /api/axis1-alzheimer-dementia/analyze/` |
| 2 — Parkinson's vs Atypical        | `POST /api/axis2-parkinson-atypical/analyze/` |
| 3 — Cerebellar Dysfunction         | `POST /api/axis3-cerebellar-dysfunction/analyze/` |
| 4 — Uneven Brain Aging             | `POST /api/axis4-brain-aging/analyze/` |
| 5 — Functional Connectivity        | `POST /api/axis5-functional-connectivity/analyze/` |
| 6 — Neuromotor Video               | `POST /api/axis6-neuromotor-video/analyze/` |
| 7 — Epilepsy Network               | `POST /api/axis7-epilepsy-network/analyze/` |

Each endpoint accepts `multipart/form-data`:

- `file`     — the upload (.nii / .dcm / .mp4 / .edf / .csv …)
- `metadata` — JSON string with patient context (age, sex, notes…)

Response matches the frontend `AnalysisResult` contract in
`src/lib/mockApi.ts`.

## Plugging in a real model

1. Train your model and save it as the placeholder path printed in
   `backend/<axis>/ml/inference.py` (e.g.
   `backend/axis1_alzheimer_dementia/ml/axis1_alzheimer_dementia_model.pkl`).
2. Implement preprocessing in `ml/inference.py::preprocess()`.
3. Replace the mock branch in `predict()` with the real model call.
4. Update `explain/explainer.py` with your real explainability output.

The view, serializer and persistence layers do not need to change.
