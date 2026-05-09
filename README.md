# brAIn — AI-powered Neurology Decision Support

A demo-ready clinical platform that lets clinicians/researchers upload
neurological data (MRI, fMRI, EEG, video…), run an AI model per axis, and
get an explainable report.

The repo has two parts:

```
.
├── src/         # Frontend — React + TanStack Start (Vite)
└── backend/     # Backend — Django + Django REST Framework (one app per axis)
```

The backend is fully wired end-to-end with realistic **mock outputs**.
Each team member is responsible for **one axis** and only needs to drop a
trained `.pkl` model in the right folder + adapt 2 functions. See
[`backend/README.md`](backend/README.md) for the per-axis integration guide.

---

## The 7 axes

| # | Axis | Data | Owner folder |
|---|------|------|--------------|
| 1 | Alzheimer's vs Other Dementias | MRI            | `backend/axis1_alzheimer_dementia/` |
| 2 | Parkinson's vs Atypical        | MRI            | `backend/axis2_parkinson_atypical/` |
| 3 | Cerebellar Dysfunction         | MRI            | `backend/axis3_cerebellar_dysfunction/` |
| 4 | Uneven Brain Aging             | MRI            | `backend/axis4_brain_aging/` |
| 5 | Functional Connectivity        | fMRI           | `backend/axis5_functional_connectivity/` |
| 6 | Neuromotor Video               | Video          | `backend/axis6_neuromotor_video/` |
| 7 | Epilepsy Vulnerability         | EEG / Signal   | `backend/axis7_epilepsy_network/` |

---

## Run the frontend

```bash
npm install
npm run dev
```

Opens at <http://localhost:8080>. Frontend currently calls the **mock API**
in `src/lib/mockApi.ts`. To hit the real Django backend, point
`mockApi.ts` (or your axis page) at `http://localhost:8000/api/<axis-id>/analyze/`.

## Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Smoke test (works even without any `.pkl`, returns a mock):

```bash
curl -X POST http://localhost:8000/api/axis1-alzheimer-dementia/analyze/ \
  -F 'metadata={"demo":true}'
```

---

## What each member must do (TL;DR)

For your axis (e.g. axis 1):

1. **Drop your trained model** at:
   `backend/axisN_<name>/ml/axisN_<name>_model.pkl`
2. **Edit `ml/inference.py`** — implement `preprocess()` and uncomment the
   real-model block inside `predict()` (search for `# === PLUG YOUR MODEL HERE ===`).
3. **Edit `explain/explainer.py`** — replace the mock regions / signal /
   network with your real explainability output (Grad-CAM, SHAP, etc.).
4. Test:
   `curl -X POST http://localhost:8000/api/<your-axis-id>/analyze/ -F file=@sample.nii`
5. Done — the view, serializer, persistence and frontend already work.

Full step-by-step in [`backend/README.md`](backend/README.md).

---

## Deployment

- **Frontend**: published from the Lovable editor (Publish button).
- **Backend**: any Django host (Render, Railway, Fly.io, a VM…). Set
  `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, and `CORS_ALLOWED_ORIGINS` to
  your published frontend URL. Models (`.pkl`) ship with the container.
