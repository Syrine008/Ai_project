# axis1_alzheimer_dementia

Django app for **Alzheimer's vs Other Dementias** (MRI).

- Endpoint: `POST /api/axis1-alzheimer-dementia/analyze/`
- Model placeholder: `axis1_alzheimer_dementia/ml/axis1_alzheimer_dementia_model.pkl` (drop your trained model here — `ModelLoader` will pick it up).
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability: see `explain/explainer.py::build_explanation()`.
