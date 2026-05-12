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

### One command on Windows (no need to “remember” two terminals)

From `Ai_project-Ahmed`, run:

```powershell
.\dev-all.ps1
```

That **opens Django in a second PowerShell window** and starts the Vite dev server in this one. Same machine, two windows — you only typed **one** command.

On **deployment / demo day**, you do **not** SSH in and run two dev servers. You **build** the frontend once (`npm run build`), host the static files (or let your platform serve them), and run Django with **gunicorn + nginx** (or a managed service). CI/CD or Docker Compose can start everything with a single `docker compose up` or one click on your host.

`npm run dev` prints the local URL (often `:5173` or `:8080`). With `.env` containing `VITE_API_BASE_URL=http://127.0.0.1:8000`, the UI calls the real Django API instead of the in-browser mock in `src/lib/mockApi.ts`.

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

### Axis 4 — brain age (EfficientNet-B0)

This repo ships a **real** PyTorch path under `backend/axis4_brain_aging/ml/`:

- Checkpoint: `backend/axis4_brain_aging/ml/checkpoints/best_ref_b_dropout03_lr5e5.pth` (not committed if you add it to `.gitignore`; copy yours here).
- Code is split into `architecture.py`, `checkpoint.py`, `preprocess.py`, `gradcam.py`, and `inference.py` (keeps `predict()` readable for reviewers).
- **Analyze 7.5 (OASIS RAW `.hdr` + `.img`):** either zip both as matching names (`basename.hdr` / `basename.img`) and upload the `.zip`, or fill **both** upload slots on Axis 4 (order irrelevant). For notebooks, `preprocess.analyze_hdr_img_pair_to_nifti_gz_bytes(hdr, img)` produces `.nii.gz` bytes.

**Frontend → Django:** copy [`.env.example`](.env.example) to `.env` and set `VITE_API_BASE_URL=http://127.0.0.1:8000`, then `npm run dev`. Without it, the UI stays on mock data.

---

## Deployment

- **Frontend**: published from the Lovable editor (Publish button).
- **Backend**: any Django host (Render, Railway, Fly.io, a VM…). Set
  `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, and `CORS_ALLOWED_ORIGINS` to
  your published frontend URL. Models (`.pkl`) ship with the container.
