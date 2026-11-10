"""Recover data-only weights/template from the user's saved Kaggle session.

No dill.load/pickle.load or saved Python callbacks are executed. Tensor storage
payloads are read with torch.load(weights_only=True). No patient inputs are exported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import zipfile
import nibabel as nib
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from axis3_cerebellar_dysfunction.ml.models import SessionFast3DCNN, Strong3DCNN
from safe_session import parse, model_state, tensor, ndarray
from export_cerebellum import export_cerebellum


def recover(session, checkpoint, output):
    namespace = parse(session).state
    first = SessionFast3DCNN().eval()
    first.load_state_dict(model_state(namespace["model_fast"]), strict=True)
    second = Strong3DCNN().eval()
    second.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True)
    # Independently compare the recovered model with logits actually saved in Kaggle.
    saved_input, saved_output = tensor(namespace["x"]), tensor(namespace["out"])
    with torch.no_grad():
        actual = first(saved_input)
    torch.testing.assert_close(actual, saved_output, atol=1e-4, rtol=1e-4)
    difference = float((actual - saved_output).abs().max())
    state = namespace["MNI_TEMPLATE"].state
    voxels, origin, spacing, direction = ndarray(state[0]), state[1], state[2], ndarray(state[3])
    # ANTs stores LPS physical coordinates; NIfTI affines use RAS coordinates.
    lps_to_ras = np.diag([-1., -1., 1.])
    affine = np.eye(4)
    affine[:3, :3] = lps_to_ras @ direction @ np.diag(spacing)
    affine[:3, 3] = lps_to_ras @ np.asarray(origin)
    with TemporaryDirectory() as directory:
        template = Path(directory) / "mni_template.nii.gz"
        nib.save(nib.Nifti1Image(voxels, affine), template)
        archive = export_cerebellum({"model_fast": first, "model_ft": second, "MNI_PATH": template}, output)
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update({
        "source": "hassening/cerebellum-finall: saved session model_fast (history cell 43) + strong3dcnn_finetuned_best.pth",
        "provenance": {
            "stage1": "Earlier trained three-block Fast3DCNN recovered from state.db; not the later two-block grid-search model.",
            "session_sha256": hashlib.sha256(session.read_bytes()).hexdigest(),
            "stage2_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            "stage1_saved_logits_max_abs_difference": difference,
            "stage1_saved_logits_tolerance": 1e-4,
            "template": "Voxel data and LPS geometry recovered from saved MNI_TEMPLATE; affine converted to NIfTI RAS.",
            "stage2_validation": "Strict state-dict match to the submitted notebook Strong3DCNN architecture.",
        },
    })
    manifest_path.write_text(json.dumps(manifest, indent=2))
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in ["manifest.json", "stage1.pth", "stage2.pth", "mni_template.nii.gz", "parity.json"]:
            bundle.write(output / name, name)
    print(f"Saved Stage 1 logits reproduced; maximum difference: {difference:.3g}")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(4)
    recover(args.session, args.checkpoint, args.output)
