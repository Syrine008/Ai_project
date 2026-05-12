# axis6_neuromotor_video

Django app for **Neuromotor Video Analysis** (Video).

- Endpoint: `POST /api/axis6-neuromotor-video/analyze/`
- Model placeholder: `axis6_neuromotor_video/ml/axis6_neuromotor_video_model.pkl` (drop your trained model here — `ModelLoader` will pick it up).
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability: see `explain/explainer.py::build_explanation()`.
