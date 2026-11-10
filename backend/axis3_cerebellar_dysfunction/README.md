# Cerebellum MRI integration

Axis 3 now runs the submitted notebook's two-stage pipeline through
`POST /api/axis3-cerebellar-dysfunction/analyze/` and the existing
`/axes/cerebellar-dysfunction` frontend route.

## Installed trained models

The local integration now includes a validated model bundle recovered from the
Kaggle outputs of `hassening/cerebellum-finall`:

- **Stage 1:** trained three-block Fast3DCNN recovered from `state.db`, history cell 43.
  This is an earlier saved model, not the later two-block grid-search variant.
  Recovery parses pickle opcodes as inert data and uses weights-only tensor loading;
  it does not execute the saved session. Predictions reproduce saved Kaggle logits
  with maximum absolute difference `1.49e-08`.
- **Stage 2:** the downloaded `strong3dcnn_finetuned_best.pth` checkpoint, loaded strictly
  into the submitted notebook's Strong3DCNN architecture.
- **MNI template:** voxel data and physical geometry recovered from the session;
  ANTs confirms exact voxel, origin, spacing and direction agreement after conversion.

`ml/artifacts/manifest.json` records source hashes and recovery evidence. Both model
architectures are supported: a future standard notebook export can still use the
later two-block Fast3DCNN. The backend must be restarted after replacing a bundle.

To reproduce recovery from the downloaded outputs, run from the repository root:

```powershell
python notebooks/recover_cerebellum_bundle.py ../kaggle-output/cerebellum-finall/state.db ../kaggle-output/cerebellum-finall/strong3dcnn_finetuned_best.pth ../kaggle-output/cerebellum_bundle
```

Only trained weights, the public template, a synthetic parity fixture and provenance
are included in the distributable bundle. Patient scans and Kaggle credentials are excluded.

## Behavior

- Stage 1: saved-session Fast3DCNN (or the later cell 68 variant), healthy (0) vs anomaly (1).
- Stage 2: fine-tuned Strong3DCNN from cells 76/85, motor (0) vs cognitive (1).
  Runs only when Stage 1 predicts anomaly. Its scores are conditional on that decision.
- Real MRI crop and 3D Grad-CAM overlay, generated from the model selected by the cascade.
  Uses the last convolution (rather than the notebook's intermediate ReLU/BatchNorm targets).
- Missing or incompatible artifacts return HTTP 503. No mock findings or invented region scores.
- Frontend shows per-stage scores, upload/progress/error states and downloadable JSON.

## Export and install the learned weights

The original submission ZIP contains notebooks and a report, not weights or training datasets. The separately downloaded Kaggle outputs supplied the trained bundle now installed locally.
The notebook's saved outputs are plots/text; they cannot restore learned parameters.
The source also contains indentation errors in several experimental cells, so this
integration does not claim that the submitted notebook runs unchanged in a fresh kernel.

1. In the **existing trained Kaggle notebook session**, run the entire contents of
   `notebooks/export_cerebellum.py` as a final cell. It reads `model_fast`, `model_ft`, and `MNI_PATH`.
   It exports both checkpoints, the exact MNI template, a preprocessing/label manifest,
   and a synthetic prediction parity fixture. It never substitutes random weights.
   If that session no longer has trained objects, its training data and training run
   are required to recover them; the exporter reports that clearly.
2. Download `/kaggle/working/cerebellum_bundle.zip`.
3. From `backend`, run:

   ```powershell
   python -m pip install -r requirements.txt -r requirements-cerebellum.txt
   python -m axis3_cerebellar_dysfunction.install_bundle C:/path/to/cerebellum_bundle.zip
   python manage.py runserver
   ```

   The installer validates the architecture, labels, preprocessing contract and prediction
   parity before copying the files. Restart the API after replacing an installed bundle.
   Alternatively set `CEREBELLUM_MODEL_DIR` to the extracted bundle directory.
4. Set `VITE_API_BASE_URL=http://127.0.0.1:8000` in the frontend `.env`, start the frontend,
   and open Axis 3. No request is sent to a Kaggle service at inference time.

## Input contract

Multipart fields: `file` and JSON `metadata`, including `inputSpace`:

| inputSpace | File | Processing |
| --- | --- | --- |
| `raw` (default) | 3D `.nii` / `.nii.gz` | N4 correction, affine registration to exported MNI template, normalization, crop, resize |
| `mni` | `.nii` / `.nii.gz` on exactly the exported template grid | normalization, crop, resize; shape and affine checked |
| `notebook_crop` | `.npy`, shape 128 x 128 x 64 | use the notebook's `processed` crop before `final_stripping` |

Common preprocessing matches cell 19: clip percentiles 1/99, min-max normalization,
crop `[20:150, 20:120, 0:90]`, trilinear resize to `(128,128,64)`.
Stage 1 applies cell 59's Otsu threshold x 0.4, largest connected component and
hole filling, then z-score normalization. Stage 2 uses the unstripped processed crop
and its own z-score normalization, matching cells 70-72 and their `processed` manifest.
The exporter rejects a Stage 2 manifest changed to `final_stripping`.

Single DICOM files, JPEGs, and fMRI time series are not accepted by this notebook model.
Uploads are limited to 128 MB and temporary files are removed after every request.
Raw registration requires ANTsPy and can take minutes. Set the deployment request
and worker timeouts accordingly; this implementation uses synchronous inference.

## Verification

From `backend`:

```powershell
python -m unittest axis3_cerebellar_dysfunction.tests -v
```

Tests cover export/reload parity with synthetic weights, label validation, input
validation, MNI grid checks, notebook crop math, both cascade branches, Grad-CAM,
missing-model errors, upload cleanup and API persistence wiring. These checks do
not measure the trained model's clinical accuracy. Actual trained-weight parity
is checked by the installer using the exported fixture. Three downloaded test crops were run through the installed trained pipeline (one healthy, one motor, one cognitive). All three returned the matching class and Grad-CAM images. This is a smoke test, not a clinical performance evaluation.

## Validation

From the project root, run `npm run typecheck` and `npm run build`.
From `backend`, with `DJANGO_DEBUG=1`, run `python -m unittest axis3_cerebellar_dysfunction.tests -v`.
See the root DEPLOYMENT.md for authenticated hosted deployment.
