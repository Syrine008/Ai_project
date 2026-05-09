# axis3_cerebellar_dysfunction

Django app for **Cerebellar Dysfunction** (MRI).

- Endpoint: `POST /api/axis3-cerebellar-dysfunction/analyze/`
- Model placeholder: `axis3_cerebellar_dysfunction/ml/axis3_cerebellar_dysfunction_model.pkl` (drop your trained model here — `ModelLoader` will pick it up).
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability: see `explain/explainer.py::build_explanation()`.
