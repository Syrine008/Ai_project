# brAIn — Django backend

One Django app per neurology axis. Every app exposes a `POST /analyze/`
endpoint that accepts a file + JSON metadata and returns the
`AnalysisResult` shape the frontend expects.

The backend is **fully working today** with realistic mock predictions.
To ship a real model, each axis owner only has to touch **2 files**.

---

## Repo layout (per axis)

```
axisN_<name>/
├── ml/
│   ├── inference.py          ← (1) plug your model here
│   └── axisN_<name>_model.pkl ← (2) drop your trained model here
├── explain/
│   └── explainer.py          ← (3) plug your explainability here
├── views.py                  ← do not edit (generic AnalyzeView)
├── serializers.py            ← do not edit (matches frontend contract)
├── urls.py                   ← do not edit
└── models.py                 ← do not edit (Case + Result persistence)
```

Shared infra lives in `common/` (model loader, base view, mock helpers).

---

## Endpoints

| Axis | URL |
|------|-----|
| 1 — Alzheimer's vs Other Dementias | `POST /api/axis1-alzheimer-dementia/analyze/` |
| 2 — Parkinson's vs Atypical        | `POST /api/axis2-parkinson-atypical/analyze/` |
| 3 — Cerebellar Dysfunction         | `POST /api/axis3-cerebellar-dysfunction/analyze/` |
| 4 — Uneven Brain Aging             | `POST /api/axis4-brain-aging/analyze/` |
| 5 — Functional Connectivity        | `POST /api/axis5-functional-connectivity/analyze/` |
| 6 — Neuromotor Video               | `POST /api/axis6-neuromotor-video/analyze/` |
| 7 — Epilepsy Network               | `POST /api/axis7-epilepsy-network/analyze/` |
| Patient summary email              | `POST /api/send-report-email/` (JSON — see below) |

Request (multipart/form-data):
- `file` — the upload (`.nii`, `.nii.gz`, `.dcm`, `.mp4`, `.edf`, `.csv` …)
- `metadata` — JSON string, e.g. `{"age":68,"sex":"F","notes":"…"}`
  (or `{"demo":true}` to skip the file in dev)

Response: the `AnalysisResult` object — see `src/lib/mockApi.ts` on the
frontend for the canonical shape (`predictedClass`, `topConfidence`,
`confidence[]`, `summary`, `regions[]`/`signal[]`/`graph`/`timeline`,
`caseId`, `axisId`, `disclaimer`, `modelLoaded`).

---

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Smoke test:
```bash
curl -X POST http://localhost:8000/api/axis1-alzheimer-dementia/analyze/ \
  -F 'metadata={"demo":true}'
```

`modelLoaded: false` in the response = the API is alive but still using mocks.
After you drop the `.pkl` it becomes `true`.

---

## Patient email (optional UI feature)

The React axis pages can email an **HTML summary** of the last analysis to the address entered under **Patient metadata → Patient email**, via:

`POST /api/send-report-email/`  
`Content-Type: application/json`

Body fields:

| Field | Meaning |
|-------|---------|
| `to` | Recipient email (patient). |
| `axis_id` | Same slug as the frontend `AxisId` (e.g. `axis4-brain-aging`). |
| `axis_title` | Human-readable axis name for the subject line. |
| `patient` | Optional `{ "id", "age", "sex" }` — shown as “Prepared for …”. |
| `result` | The same `AnalysisResult` JSON returned by `/analyze/` (large `gradCamDataUrl` is stripped server-side for size). |

**Behavior:** By default Django uses the **console email backend** — nothing is delivered; the full MIME message is printed in the terminal where `runserver` is running (good for local demos).

### Step 1 — Try it without SMTP

1. Start backend: `python manage.py runserver 127.0.0.1:8000`
2. Frontend `.env`: `VITE_API_BASE_URL=http://127.0.0.1:8000`
3. Run any axis analysis; enter a patient email; click **Send analysis to patient**
4. Watch the **Django console** for the email HTML.

### Step 2 — Real delivery (SMTP)

**Easiest on your machine:** copy `backend/.env.example` to `backend/.env` and fill values (that file is gitignored). Django loads it automatically via `python-dotenv`.

Alternatively, set environment variables before starting Django (examples — adjust for your provider):

```bash
set DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
set EMAIL_HOST=smtp.gmail.com
set EMAIL_PORT=587
set EMAIL_HOST_USER=youraccount@gmail.com
set EMAIL_HOST_PASSWORD=your_app_password
set EMAIL_USE_TLS=1
set DEFAULT_FROM_EMAIL=brAIn Demo <youraccount@gmail.com>
```

For Gmail, create an **App password** (Google Account → Security → 2-Step Verification → App passwords). Other providers (SendGrid SMTP, Mailgun, Outlook) use their host/port and credentials.

Production: use a dedicated transactional provider, SPF/DKIM, and tighten CORS/auth — this endpoint is intentionally open for the student demo.

---

## Plugging in YOUR model — 3 steps

> Replace `axisN_<name>` with your folder, e.g. `axis1_alzheimer_dementia`.

### Step 1 — Drop the trained model

Save your trained model exactly here:

```
backend/axisN_<name>/ml/axisN_<name>_model.pkl
```

The filename must match — `ModelLoader` looks for it on first request and
joblib-loads it. No code change needed for it to be picked up.

> Anything pickle-able works (sklearn, xgboost, a thin wrapper around a
> torch/tf model with a `.predict()` method, etc.). For very large models,
> use `joblib.dump(model, path, compress=3)`.

**Exception — `axis4_brain_aging`:** uses a PyTorch `state_dict` at
`axis4_brain_aging/ml/checkpoints/best_ref_b_dropout03_lr5e5.pth` loaded by
`BrainAgeCheckpointLoader` (see `ml/checkpoint.py`). Same HTTP contract; no
`.pkl` required for that axis.

### Step 2 — Implement preprocessing + real inference

Open `backend/axisN_<name>/ml/inference.py`:

1. Fill in `preprocess(upload, metadata)` to turn the Django `UploadedFile`
   into your model's input (load NIfTI, decode video, read EDF, build
   connectivity matrix, etc.).
2. **Uncomment the block under `# === PLUG YOUR MODEL HERE ===`** inside
   `predict()`. The block already shows the canonical pattern:

   ```python
   x = preprocess(upload, metadata)
   probs = model.predict_proba([x])[0]
   pred_idx = int(probs.argmax())
   confidence = [{"label": cls, "value": float(p)} for cls, p in zip(CLASSES, probs)]
   return {
       "predictedClass": CLASSES[pred_idx],
       "topConfidence": float(probs[pred_idx]),
       "confidence": confidence,
       "summary": "…short clinical sentence…",
       **build_explanation(upload, metadata, model=model),
   }
   ```

3. If your class labels differ, edit the `CLASSES = [...]` list at the top.

The mock branch below stays as a fallback if the `.pkl` is missing.

### Step 3 — Plug real explainability

Open `backend/axisN_<name>/explain/explainer.py` and replace the mock
regions / signal / graph / timeline with the real output of your
explainer (Grad-CAM, SHAP, attention map, occlusion, …). Keep the same
JSON keys — the frontend visualizers depend on them.

That's it. **Do not edit** `views.py`, `serializers.py`, `urls.py`,
`models.py`, or anything in `common/` — they handle parsing,
persistence, response shaping and CORS for every axis.

---

## Verifying your axis

```bash
# 1. Confirm the model is detected
curl -s -X POST http://localhost:8000/api/<your-axis-id>/analyze/ \
  -F 'metadata={"demo":true}' | python -m json.tool | grep modelLoaded
# → "modelLoaded": true

# 2. Real upload
curl -X POST http://localhost:8000/api/<your-axis-id>/analyze/ \
  -F file=@/path/to/sample.nii \
  -F 'metadata={"age":68,"sex":"F"}'
```

Then open the corresponding axis page in the frontend and click "Run analysis".

---

## Deployment checklist

1. `pip install -r requirements.txt` on the host (add your model's deps).
2. Set env vars: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
   `DJANGO_ALLOWED_HOSTS=<your-domain>`,
   `CORS_ALLOWED_ORIGINS=https://<your-frontend>`.
3. `python manage.py migrate`.
4. Make sure every `axisN_<name>/ml/axisN_<name>_model.pkl` ships with
   your container/image (or is mounted from object storage on boot).
5. Run with the Render start command:
   `gunicorn brain_backend.wsgi:application --timeout 120 --workers 1 --threads 2`.
6. Point the frontend at the deployed URL (replace the mock calls in
   `src/lib/mockApi.ts` or wire a real fetch in each axis page).
