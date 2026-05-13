# axis2_parkinson_atypical

Django app for **Parkinson's vs Atypical Syndromes** (MRI).

- Endpoint: `POST /api/axis2-parkinson-atypical/analyze/`
- Model placeholder: `axis2_parkinson_atypical/ml/axis2_parkinson_atypical_model.pkl` (drop your trained model here — `ModelLoader` will pick it up).
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability: see `explain/explainer.py::build_explanation()`.
