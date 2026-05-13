# axis7_epilepsy_network

Django app for **Epilepsy Vulnerability** (EEG / Signal).

- Endpoint: `POST /api/axis7-epilepsy-network/analyze/`
- Upload mode: multipart folder upload using repeated `files` fields, not a zip. The folder should contain matching `eeg`, `ecg`, `emg`, and `mov` EDF/BDF files for one patient run.
- Model artifact: `axis7_epilepsy_network/ml/axis7_epilepsy_network_model.pt`. The notebook export cell saves this file after training.
- Real-model wiring: see `ml/inference.py::predict()`.
- Explainability output: channel contribution, network coupling, modality occlusion, attention weights when available, and EEG Grad-CAM time focus.
