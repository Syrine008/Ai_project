# B-R-A-I-N — AI-Powered Neurology Decision Support Platform

## Overview

**B-R-A-I-N** is an AI-powered neurology decision support platform designed to help clinicians and researchers analyze neurological data using artificial intelligence.

The platform allows users to upload different types of neurological data, including **MRI**, **fMRI**, **EEG signals**, and **neuromotor video**, run a dedicated AI model for each clinical axis, and generate an **explainable clinical report**.

This project was developed as part of an academic artificial intelligence engineering project at **Esprit School of Engineering**. It explores the use of **medical AI**, **deep learning**, **medical imaging**, **signal processing**, **computer vision**, and **explainable AI** to support neurological research and clinical decision-making.

The repository is public and designed to benefit from the **GitHub Education for Students** program, especially for hosting, deployment, collaboration, and project visibility.

B-R-A-I-N is demo-ready: the backend is already wired end-to-end with realistic mock outputs, and each team member can integrate a trained model by adding it to the correct backend folder and adapting the inference and explainability functions.

---

## Features

- Upload neurological data such as **MRI**, **fMRI**, **EEG**, **video**, and signal files.
- Run an AI model dedicated to each neurological axis.
- Generate explainable reports for clinicians, researchers, and project evaluators.
- Support multiple neurological analysis axes in one unified clinical platform.
- Modular backend architecture with one Django application per axis.
- Realistic mock outputs for demo, testing, and presentation purposes.
- Easy integration of trained `.pkl` models or PyTorch checkpoints.
- Support for explainability methods such as **Grad-CAM**, **SHAP**, brain region activation, signal interpretation, and network-level analysis.
- Frontend connected to the Django REST API using environment variables.
- Mock API fallback for frontend-only demos.
- Demo-ready platform for academic, medical, and AI project presentations.
- Designed for clinical decision support, medical imaging analysis, deep learning experimentation, and explainable AI research.

The platform currently includes **7 neurological axes**:

| # | Axis | Data Type | Backend Folder |
|---|------|-----------|----------------|
| 1 | Alzheimer’s vs Healthy subjects | MRI | `backend/axis1_alzheimer_dementia/` |
| 2 | Parkinson’s vs Atypical Parkinsonism | MRI | `backend/axis2_parkinson_atypical/` |
| 3 | Cerebellar Dysfunction | MRI | `backend/axis3_cerebellar_dysfunction/` |
| 4 | Uneven Brain Aging | MRI | `backend/axis4_brain_aging/` |
| 5 | Functional Connectivity | fMRI | `backend/axis5_functional_connectivity/` |
| 6 | Neuromotor Video Analysis | Video | `backend/axis6_neuromotor_video/` |
| 7 | Epilepsy Vulnerability | EEG / Signal | `backend/axis7_epilepsy_network/` |

---

## Tech Stack

### Frontend

- **React**
- **TanStack Start**
- **Vite**
- **TypeScript**
- Modern responsive user interface
- Environment-based API configuration
- Mock API support for demo mode

Main frontend folder:

```bash
src/
```

The frontend communicates with the Django backend through the API base URL configured in the `.env` file.

Example:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Without this variable, the frontend uses the in-browser mock API located in:

```bash
src/lib/mockApi.ts
```

---

### Backend

- **Python**
- **Django**
- **Django REST Framework**
- Modular Django architecture
- One backend application per neurological axis
- REST API endpoints
- File upload handling
- Model inference structure
- Mock and real-model prediction support
- Clinical report generation
- Explainability module per axis

Main backend folder:

```bash
backend/
```

Each axis contains its own inference logic, explainability module, views, serializers, and API route.

---

### Other Tools

- **Artificial Intelligence**
- **Machine Learning**
- **Deep Learning**
- **Medical Image Analysis**
- **MRI Classification**
- **fMRI Functional Connectivity**
- **EEG Signal Processing**
- **Computer Vision**
- **Explainable AI**
- **Grad-CAM**
- **SHAP**
- **PyTorch**
- **scikit-learn**
- **GitHub**
- **GitHub Education for Students**
- **Docker**
- **Docker Compose**
- **Gunicorn**
- **Nginx**

Possible hosting and deployment platforms:

- Heroku
- DigitalOcean
- Render
- Railway
- Fly.io
- Namecheap
- Lovable Publish
- GitHub Pages for static frontend hosting

GitHub topics:

```txt
artificial-intelligence
medical-ai
neurology
clinical-decision-support
deep-learning
machine-learning
brain-mri
fmri
eeg
computer-vision
explainable-ai
grad-cam
django
django-rest-framework
react
vite
tanstack-start
pytorch
healthcare
esprit-school-of-engineering
```

---

## Directory Structure

```bash
.
├── src/                         # Frontend — React + TanStack Start + Vite
│   ├── lib/
│   │   └── mockApi.ts           # Mock API used when backend URL is not configured
│   ├── routes/                  # Frontend pages and routes
│   ├── components/              # Reusable UI components
│   └── ...
│
└── backend/                     # Backend — Django + Django REST Framework
    ├── axis1_alzheimer_dementia/
    ├── axis2_parkinson_atypical/
    ├── axis3_cerebellar_dysfunction/
    ├── axis4_brain_aging/
    ├── axis5_functional_connectivity/
    ├── axis6_neuromotor_video/
    ├── axis7_epilepsy_network/
    ├── manage.py
    └── requirements.txt
```

Each backend axis follows a similar structure:

```bash
backend/axisN_axis_name/
├── ml/
│   ├── inference.py
│   └── axisN_axis_name_model.pkl
├── explain/
│   └── explainer.py
├── views.py
├── serializers.py
└── urls.py
```

Each team member is responsible for one neurological axis and should place the trained model in the corresponding `ml/` folder.

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/B-R-A-I-N.git
cd B-R-A-I-N
```

---

### 2. Run the Frontend

From the repository root:

```bash
npm install
npm run dev
```

The frontend development server will print a local URL, usually:

```bash
http://localhost:5173
```

or:

```bash
http://localhost:8080
```

To connect the frontend to the real Django backend, copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Then set:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

### 3. Run the Backend

Go to the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment.

On Linux or macOS:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Run the Django server:

```bash
python manage.py runserver 0.0.0.0:8000
```

---

### 4. One-Command Development on Windows

From the repository root, run:

```bash
.\dev-all.ps1
```

This command opens Django in a second PowerShell window and starts the Vite frontend development server in the current window.

---

### 5. Smoke Test

The backend works even without a trained `.pkl` model because it returns realistic mock outputs.

Example for Axis 1:

```bash
curl -X POST http://localhost:8000/api/axis1-alzheimer-dementia/analyze/ \
  -F 'metadata={"demo":true}'
```

Example with a file:

```bash
curl -X POST http://localhost:8000/api/axis1-alzheimer-dementia/analyze/ \
  -F file=@sample.nii
```

---

### 6. Model Integration Guide

For each axis, the team member should follow these steps.

#### Step 1: Add the trained model

Place the trained model in the correct folder:

```bash
backend/axisN_axis_name/ml/axisN_axis_name_model.pkl
```

Example for Axis 1:

```bash
backend/axis1_alzheimer_dementia/ml/axis1_alzheimer_dementia_model.pkl
```

#### Step 2: Edit the inference file

Open:

```bash
backend/axisN_axis_name/ml/inference.py
```

Implement:

```python
preprocess()
```

Then adapt the real-model block inside:

```python
predict()
```

Search for:

```python
# === PLUG YOUR MODEL HERE ===
```

#### Step 3: Edit the explainability file

Open:

```bash
backend/axisN_axis_name/explain/explainer.py
```

Replace the mock explanation with the real explainability output.

Examples of explainability outputs:

- Grad-CAM heatmaps
- SHAP feature importance
- Brain region activation
- MRI region-based explanation
- EEG signal-level interpretation
- fMRI connectivity explanation
- Neuromotor video movement explanation

#### Step 4: Test the endpoint

```bash
curl -X POST http://localhost:8000/api/<your-axis-id>/analyze/ \
  -F file=@sample.nii
```

---

### 7. Axis 4 — Brain Age Prediction with EfficientNet-B0

Axis 4 includes a real PyTorch inference path under:

```bash
backend/axis4_brain_aging/ml/
```

The code is split into:

```bash
architecture.py
checkpoint.py
preprocess.py
gradcam.py
inference.py
```

The checkpoint should be placed here:

```bash
backend/axis4_brain_aging/ml/checkpoints/best_ref_b_dropout03_lr5e5.pth
```

For OASIS RAW `.hdr` and `.img` files, Axis 4 supports two options.

Option 1: Zip both files with matching names:

```bash
basename.hdr
basename.img
```

Then upload the `.zip`.

Option 2: Upload both files separately using the two upload slots in the frontend.

For notebooks, the following function produces `.nii.gz` bytes:

```python
preprocess.analyze_hdr_img_pair_to_nifti_gz_bytes(hdr, img)
```

---

### 8. Deployment

For demo day or production deployment, the frontend and backend should not be run using development servers.

Build the frontend:

```bash
npm run build
```

The frontend can be hosted using:

- Lovable Publish
- Vercel
- Netlify
- GitHub Pages
- Any static hosting platform

The Django backend can be deployed using:

- Render
- Railway
- Fly.io
- Heroku
- DigitalOcean
- A virtual machine

Recommended production stack:

```txt
Django + Gunicorn + Nginx
```

Required backend environment variables:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=0
CORS_ALLOWED_ORIGINS=https://your-frontend-url.com
```

Models can be shipped inside the backend container or mounted separately depending on the hosting platform.

Docker Compose can also be used to start the platform with a single command:

```bash
docker compose up
```

---

## Acknowledgments

This project was developed by the **AICONICS team** at **Esprit School of Engineering**.

We acknowledge the academic supervision, technical guidance, and clinical collaboration that supported the development of this AI-powered neurology decision support platform.

B-R-A-I-N aims to demonstrate how **artificial intelligence**, **deep learning**, **medical imaging**, **signal processing**, **computer vision**, and **explainable AI** can support neurological research and clinical decision-making.

This project also benefits from the visibility and collaboration opportunities offered by **GitHub** and the **GitHub Education for Students** program.
