# axis4_brain_aging

Django app for **Uneven Brain Aging** (MRI).

- Endpoint: `POST /api/axis4-brain-aging/analyze/`
- Model placeholder: `axis4_brain_aging/ml/axis4_brain_aging_model.pkl` (drop your trained model here — `ModelLoader` will pick it up).
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability: see `explain/explainer.py::build_explanation()`.
