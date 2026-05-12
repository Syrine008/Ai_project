# axis5_functional_connectivity

Django app for **Hidden Cognitive Effort** (fMRI).

- Endpoint: `POST /api/axis5-functional-connectivity/analyze/`
- Model placeholder: `axis5_functional_connectivity/ml/axis5_functional_connectivity_model.pkl` (drop your trained model here — `ModelLoader` will pick it up).
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability: see `explain/explainer.py::build_explanation()`.
