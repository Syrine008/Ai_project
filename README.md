# B-R-A-I-N — AI-Powered Neurology Decision Support Platform

## Overview

**B-R-A-I-N** is an AI-powered neurology decision support platform designed to help clinicians and researchers analyze neurological data using artificial intelligence.

The platform allows users to upload different types of neurological data, including **MRI**, **fMRI**, **EEG signals**, and **neuromotor video**, run a dedicated AI model for each clinical axis, and generate an **explainable clinical report**.

This project was developed as part of an academic artificial intelligence engineering project at **Esprit School of Engineering**. It explores the use of **medical AI**, **deep learning**, **medical imaging**, **signal processing**, **computer vision**, and **explainable AI** to support neurological research and clinical decision-making.

The repository contains two main parts: a frontend built with **React**, **TanStack Start**, and **Vite**, and a backend built with **Django** and **Django REST Framework**. The backend is organized into one application per neurological axis and is fully wired end-to-end with realistic mock outputs for demo purposes.

The project is deployed online:

- **Frontend deployment:** https://b-r-a-i-n-mu.vercel.app
- **Backend deployment:** https://b-r-a-i-n-46js.onrender.com

## Features

- Upload neurological data such as **MRI**, **fMRI**, **EEG**, **video**, and signal files.
- Run an AI model dedicated to each neurological axis.
- Generate explainable reports for clinicians and researchers.
- Support multiple neurological analysis axes in one unified clinical platform.
- Use realistic mock outputs for demo and testing.
- Integrate trained `.pkl` models or PyTorch checkpoints.
- Support explainability methods such as **Grad-CAM**, brain region activation, signal interpretation, and network-level analysis.
- Connect the frontend to the Django REST API using environment variables.
- Provide a demo-ready platform for academic, medical, and AI project presentations.
- Deploy the frontend using **Vercel** and the backend using **Render**.

The platform currently includes **7 neurological axes**:

| # | Axis | Data Type | Backend Folder |
|---|------|-----------|----------------|
| 1 | Alzheimer’s vs Healthy Subjects | MRI | `backend/axis1_alzheimer_dementia/` |
| 2 | Parkinson’s vs Atypical Parkinsonism | MRI | `backend/axis2_parkinson_atypical/` |
| 3 | Cerebellar Dysfunction | MRI | `backend/axis3_cerebellar_dysfunction/` |
| 4 | Uneven Brain Aging | MRI | `backend/axis4_brain_aging/` |
| 5 | Functional Connectivity | fMRI | `backend/axis5_functional_connectivity/` |
| 6 | Neuromotor Video Analysis | Video | `backend/axis6_neuromotor_video/` |
| 7 | Epilepsy Vulnerability | EEG / Signal | `backend/axis7_epilepsy_network/` |

## Tech Stack

### Frontend

- **React**
- **TanStack Start**
- **Vite**
- **TypeScript**
- **Tailwind CSS**
- Responsive user interface
- Environment-based API configuration
- Mock API support for demo mode
- Deployed with **Vercel**

### Backend

- **Python**
- **Django**
- **Django REST Framework**
- **Gunicorn**
- Modular Django architecture
- One backend application per neurological axis
- REST API endpoints
- File upload handling
- Model inference structure
- Mock and real-model prediction support
- Clinical report generation
- Explainability module per axis
- Deployed with **Render**

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
- **PyTorch**
- **scikit-learn**
- **GitHub**
- **GitHub Education for Students**
- **Vercel**
- **Render**

## Directory Structure

```bash
.
├── src/                         # Frontend — React + TanStack Start + Vite
│   ├── lib/
│   │   └── mockApi.ts           # Mock API used when backend URL is not configured
│   ├── routes/
│   ├── components/
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
    ├── brain_backend/
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

## Getting Started

Clone the repository:

```bash
git clone https://github.com/Syrine008/Ai_project.git
cd Ai_project
```

Run the frontend from the repository root:

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

For the deployed backend, use:

```env
VITE_API_BASE_URL=https://b-r-a-i-n-46js.onrender.com
```

Run the backend:

```bash
cd backend
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

Install dependencies and start the Django server:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

On Windows, the full development environment can also be started from the repository root using:

```bash
.\dev-all.ps1
```

Smoke test example:

```bash
curl -X POST http://localhost:8000/api/axis1-alzheimer-dementia/analyze/ \
  -F 'metadata={"demo":true}'
```

To integrate a trained model, each team member should place their model in the correct axis folder:

```bash
backend/axisN_axis_name/ml/axisN_axis_name_model.pkl
```

Then edit:

```bash
backend/axisN_axis_name/ml/inference.py
```

and:

```bash
backend/axisN_axis_name/explain/explainer.py
```

The deployed version of the project is available here:

```txt
Frontend: https://b-r-a-i-n-mu.vercel.app
Backend: https://b-r-a-i-n-46js.onrender.com
```

## Acknowledgments

This project was developed by the **AICONICS team** at **Esprit School of Engineering**.

We acknowledge the academic supervision, technical guidance, and clinical collaboration that supported the development of this AI-powered neurology decision support platform.

B-R-A-I-N aims to demonstrate how **artificial intelligence**, **deep learning**, **medical imaging**, **signal processing**, **computer vision**, and **explainable AI** can support neurological research and clinical decision-making.

This project also benefits from the visibility and collaboration opportunities offered by **GitHub** and the **GitHub Education for Students** program.
