# axis5_functional_connectivity

Django app for **Hidden Cognitive Effort** (fMRI).

- Endpoint: `POST /api/axis5-functional-connectivity/analyze/`
- Model checkpoint: `axis5_functional_connectivity/ml/best_model_unet3d_16.pt` (drop your trained model here).
- Real-model wiring: see `ml/inference.py::predict()` (PyTorch checkpoint loader).
- Explainability: see `explain/explainer.py::build_explanation()`.
