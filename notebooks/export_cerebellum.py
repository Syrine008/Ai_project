"""Run this whole file in the trained Kaggle notebook's namespace after cell 85.

Exports existing trained model_fast and model_ft; never initializes replacement weights.
The export includes only model state, a public template and synthetic parity data.
"""
from pathlib import Path
import json
import zipfile
import numpy as np
import nibabel as nib
import torch


def export_cerebellum(namespace, output_dir="/kaggle/working/cerebellum_bundle"):
    first = namespace.get("model_fast")
    second = namespace.get("model_ft")
    if first is None or second is None:
        raise RuntimeError("Run Stage 1 cell 68 and fine-tuned Stage 2 cell 85 first. Their trained objects are required.")
    first_state = {k: v.detach().cpu().clone() for k, v in first.state_dict().items()}
    second_state = {k: v.detach().cpu().clone() for k, v in second.state_dict().items()}
    if (first_state["features.0.weight"].shape != (8, 1, 3, 3, 3)
            or second_state["features.0.weight"].shape != (16, 1, 3, 3, 3)
            or first_state["classifier.3.weight"].shape[0] != 2
            or second_state["classifier.3.weight"].shape != (2, 32)):
        raise RuntimeError("Unexpected model architectures; export the cell 68 Fast3DCNN and cell 85 Strong3DCNN.")
    template = namespace.get("MNI_PATH")
    if not template or not Path(template).is_file():
        raise RuntimeError("MNI_PATH must reference the exact template used for preprocessing.")
    # Stage 2 in the submitted notebook uses the original processed manifest.
    stage2_train = namespace.get("stage2_train")
    if stage2_train is not None and any("final_stripping" in str(p) for p in stage2_train["path"]):
        raise RuntimeError("Stage 2 now uses stripped data. Update the integration preprocessing contract before exporting.")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    torch.save(first_state, output / "stage1.pth")
    torch.save(second_state, output / "stage2.pth")
    nib.save(nib.load(template), output / "mni_template.nii.gz")
    manifest = {
        "version": 1,
        "stage1_architecture": "SessionFast3DCNN" if "features.8.weight" in first_state else "Fast3DCNN",
        "stage2_architecture": "Strong3DCNN",
        "stage1_labels": ["Healthy", "Anomaly"],
        "stage2_labels": ["Motor anomaly", "Cognitive anomaly"],
        "stage1_skull_strip": True, "stage2_skull_strip": False,
        "target_size": [128, 128, 64], "crop": [[20, 150], [20, 120], [0, 90]],
        "normalization": "percentile_1_99_minmax_then_per_stage_zscore",
        "source": "cerebellum-final (6).ipynb cells 19, 59, 68, 71, 76, 85",
        "torch_version": str(torch.__version__),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    # Small synthetic tensor checks architecture/weight parity without patient data.
    sample = np.random.default_rng(42).normal(size=(1, 1, 16, 16, 16)).astype(np.float32)
    parity = {"input": sample.tolist()}
    for key, model in [("stage1", first), ("stage2", second)]:
        was_training = model.training
        model.eval()
        try:
            with torch.no_grad():
                tensor = torch.from_numpy(sample).to(next(model.parameters()).device)
                parity[key] = model(tensor).cpu().tolist()
        finally:
            model.train(was_training)
    (output / "parity.json").write_text(json.dumps(parity))
    archive = output.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in ["manifest.json", "stage1.pth", "stage2.pth", "mni_template.nii.gz", "parity.json"]:
            bundle.write(output / name, name)
    print(f"Exported trained cerebellum models: {archive}")
    return archive


if __name__ == "__main__":
    export_cerebellum(globals())
