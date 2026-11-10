# brAIn — neurological research workspace

React and Django workspace for reviewing neurological model outputs. The cerebellum workflow runs trained notebook models locally, displays both classification stages and Grad-CAM images, and supports saving, downloading and printing reports.

**Research use only.** Model scores are not calibrated clinical probabilities. The application has not been clinically validated and is not a medical record system. Use de-identified research inputs.

## Quick start

Requirements: Node.js 22.12+ (tested with 24), npm, Python 3.10+, Git LFS. Use Linux for hosted Gunicorn deployments.

```sh
git lfs install
git clone https://github.com/Syrine008/Ai_project.git
cd Ai_project
git lfs pull
npm ci --legacy-peer-deps
cp .env.example .env
python -m venv backend/.venv
# Activate backend/.venv (Windows: backend\.venv\Scripts\Activate.ps1)
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
python backend/manage.py migrate
python backend/manage.py runserver 127.0.0.1:8000
```

In a second terminal: `npm run dev`. Open `http://localhost:8080`. The frontend `.env` must set `VITE_API_BASE_URL=http://127.0.0.1:8000`. On Windows, after dependency setup, `powershell -ExecutionPolicy Bypass -File ./dev-all.ps1` runs both services.

## Model availability

The repository contains seven analysis workflows. Their availability depends on installed weights and runtime dependencies; a visible workflow is not a claim of validated performance. The shared API and frontend do not substitute mock findings when a model or service is absent.

The cerebellum bundle includes:

- Stage 1: trained three-block `SessionFast3DCNN`, recovered from notebook history cell 43. This is not the later two-block grid-search model.
- Stage 2: `Strong3DCNN`, loaded from `strong3dcnn_finetuned_best.pth`.
- MNI template, label/preprocessing manifest and synthetic parity fixture.

See [cerebellum provenance and input contract](backend/axis3_cerebellar_dysfunction/README.md). Weights are tracked with Git LFS. Do not commit patient scans, credentials, local databases or notebook session dumps.

## Review workflow

1. Open Cerebellum MRI and select the scan preparation.
2. Upload a 3D NIfTI scan; advanced users may supply a template-aligned scan or the specified preprocessed NumPy crop.
3. Review the classification stages and model attention images with the clinical examination.
4. Save a report in this browser, download JSON, or print to PDF.

Browser reports are local to the device and are not an authenticated patient archive. Deleting one does not delete the backend record. Email delivery requires configured SMTP and authenticated access in production.

## Validation

```sh
npm run typecheck
npm run build
# Use development settings for local tests, never for a public deployment.
DJANGO_DEBUG=1 python backend/manage.py test common.test_security
cd backend
DJANGO_DEBUG=1 python -m unittest axis3_cerebellar_dysfunction.tests -v
```

PowerShell: use `$env:DJANGO_DEBUG='1'` before the Python commands.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md). Production mode fails closed without a strong secret and explicit allowed hosts, enforces HTTPS, and requires staff session authentication for analysis and email. A GitHub push does not provision hosting or configure deployment secrets.
