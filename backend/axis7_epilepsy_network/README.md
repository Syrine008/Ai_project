# axis7_epilepsy_network

Django app for **Epilepsy Vulnerability** (EEG / Signal).

- Endpoint: `POST /api/axis7-epilepsy-network/analyze/`
- Model placeholder: `axis7_epilepsy_network/ml/axis7_epilepsy_network_model.pkl` (drop your trained model here — `ModelLoader` will pick it up).
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability: see `explain/explainer.py::build_explanation()`.
