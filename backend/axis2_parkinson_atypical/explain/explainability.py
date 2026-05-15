"""
Anatomy-grounded post-hoc explainability backend for one patient at a time.

This module mirrors the cleaned notebook's final Grad-CAM + SynthSeg workflow:
- Load the final ImprovedResidualSESmallCNN checkpoint.
- Load a preprocessed 128^3 .npy MRI volume.
- Reuse the axial-only 15-slice selection and patient-level probability averaging.
- Generate predicted-class Grad-CAM on selected axial slices.
- Mask attention with SynthSeg labels when available.
- Quantify region-level anatomical overlap.
- Save report figures, region table, and JSON summary.

The outputs are model evidence for research decision support, not diagnostic proof.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import json
import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import cm
import nibabel as nib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

try:
    from scipy import ndimage as explain_ndi
except Exception:
    explain_ndi = None

from ..ml.model_inference import (
    BINARY_LABEL_NAMES,
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_PREPROCESSED_NPY_DIR,
    DEFAULT_THRESHOLD,
    PATTERN_NAMES,
    SLICE_AXIS,
    SLICES_PER_PATIENT,
    TARGET_SHAPE,
    aggregate_patient_probabilities,
    choose_informative_slice_indices,
    extract_slice,
    get_device,
    get_volume_path,
    load_model_checkpoint,
    load_preprocessed_volume,
    logits_to_probabilities,
    slice_to_tensor,
)


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_SYNTHSEG_DIR = PROJECT_DIR / "synthseg_outputs"
DEFAULT_EXPLAINABILITY_OUTPUT_DIR = PROJECT_DIR / "explainability_outputs"
IMAGE_SIZE = 128

SYNTHSEG_LABEL_NAMES = {
    2: "Left cerebral white matter",
    3: "Left cerebral cortex",
    4: "Left lateral ventricle",
    5: "Left inferior lateral ventricle",
    7: "Left cerebellum white matter",
    8: "Left cerebellum cortex",
    10: "Left thalamus",
    11: "Left caudate",
    12: "Left putamen",
    13: "Left pallidum",
    14: "3rd ventricle",
    15: "4th ventricle",
    16: "Brainstem",
    17: "Left hippocampus",
    18: "Left amygdala",
    24: "CSF",
    26: "Left accumbens area",
    28: "Left ventral DC",
    31: "Left choroid plexus",
    41: "Right cerebral white matter",
    42: "Right cerebral cortex",
    43: "Right lateral ventricle",
    44: "Right inferior lateral ventricle",
    46: "Right cerebellum white matter",
    47: "Right cerebellum cortex",
    49: "Right thalamus",
    50: "Right caudate",
    51: "Right putamen",
    52: "Right pallidum",
    53: "Right hippocampus",
    54: "Right amygdala",
    58: "Right accumbens area",
    60: "Right ventral DC",
    63: "Right choroid plexus",
}

REGION_TABLE_COLUMNS = [
    "slice_index",
    "region_label",
    "region_name",
    "mean_attention",
    "max_attention",
    "sum_attention",
    "percentage_of_total_attention",
    "number_of_pixels",
]


def safe_name(value: object) -> str:
    text = str(value)
    keep = [c if c.isalnum() or c in ("-", "_", ".") else "_" for c in text]
    return "".join(keep).strip("_") or "patient"


def normalize01(x: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    if x.size == 0:
        return x
    lo, hi = float(np.min(x)), float(np.max(x))
    if hi <= lo + eps:
        return np.zeros_like(x, dtype=np.float32)
    return np.clip((x - lo) / (hi - lo + eps), 0.0, 1.0).astype(np.float32)


def resize_gray_slice(sl: np.ndarray, image_size: int = IMAGE_SIZE) -> np.ndarray:
    sl = normalize01(sl)
    img = Image.fromarray((sl * 255).astype(np.uint8), mode="L")
    img = img.resize((image_size, image_size), Image.BILINEAR)
    return np.asarray(img, dtype=np.float32) / 255.0


def resize_label_slice(seg: np.ndarray, output_shape: Tuple[int, int]) -> np.ndarray:
    seg = np.asarray(seg, dtype=np.int32)
    img = Image.fromarray(seg, mode="I")
    img = img.resize((int(output_shape[1]), int(output_shape[0])), Image.NEAREST)
    return np.asarray(img, dtype=np.int32)


def replace_inplace_relu(module: nn.Module) -> None:
    """Kept for Grad-CAM compatibility; the final CNN already uses inplace=False."""
    for name, child in module.named_children():
        if isinstance(child, nn.ReLU) and child.inplace:
            setattr(module, name, nn.ReLU(inplace=False))
        else:
            replace_inplace_relu(child)


def find_last_conv2d(model: nn.Module) -> Tuple[nn.Module, str]:
    last_name, last_layer = None, None
    for name, module in model.named_modules():
        if isinstance(module, nn.Conv2d):
            last_name, last_layer = name, module
    if last_layer is None:
        raise ValueError("No Conv2d layer found for Grad-CAM.")
    return last_layer, str(last_name)


class GradCAM:
    """Notebook-matched predicted-class Grad-CAM implementation."""

    def __init__(self, model: nn.Module, target_layer: Optional[nn.Module] = None):
        self.model = model
        self.target_layer, self.target_name = find_last_conv2d(model) if target_layer is None else (target_layer, "custom")
        self.activations = None
        self.gradients = None
        self.handles = [
            self.target_layer.register_forward_hook(self.forward_hook),
            self.target_layer.register_full_backward_hook(self.backward_hook),
        ]

    def forward_hook(self, module: nn.Module, inputs: tuple, output: torch.Tensor) -> None:
        self.activations = output.detach()

    def backward_hook(self, module: nn.Module, grad_input: tuple, grad_output: tuple) -> None:
        self.gradients = grad_output[0].detach()

    def remove(self) -> None:
        for handle in self.handles:
            handle.remove()
        self.handles = []

    def __call__(self, input_tensor: torch.Tensor, class_idx: int, output_size: Tuple[int, int] = (IMAGE_SIZE, IMAGE_SIZE)):
        self.model.eval()
        self.model.zero_grad(set_to_none=True)
        self.activations = None
        self.gradients = None

        logits = self.model(input_tensor)
        probs = logits_to_probabilities(logits)

        if logits.shape[1] == 1:
            score = logits[:, 0].sum() if int(class_idx) == 1 else (-logits[:, 0]).sum()
        else:
            score = logits[:, int(class_idx)].sum()

        score.backward()

        if self.activations is None or self.gradients is None:
            raise RuntimeError("Grad-CAM did not capture activations/gradients.")

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam_tensor = (weights * self.activations).sum(dim=1, keepdim=True)
        cam_tensor = F.relu(cam_tensor)
        cam_tensor = F.interpolate(cam_tensor, size=output_size, mode="bilinear", align_corners=False)

        cam_np = cam_tensor[0, 0].detach().cpu().numpy().astype(np.float32)
        cam_np = normalize01(cam_np)
        self.model.zero_grad(set_to_none=True)
        return cam_np, probs[0].detach().cpu().numpy()


def find_synthseg_path(patient_id: str, synthseg_dir: Optional[str | Path] = None) -> Optional[Path]:
    """Find a SynthSeg output for one patient using the notebook naming patterns."""
    root = Path(synthseg_dir) if synthseg_dir is not None else DEFAULT_SYNTHSEG_DIR
    if not root.exists():
        return None

    patient_id = str(patient_id)
    possible_files: List[Path] = []
    for pattern in ("*.nii.gz", "*.nii", "*.npy"):
        possible_files.extend(list(root.rglob(pattern)))

    matches = [
        p for p in possible_files
        if patient_id in p.name and ("seg" in p.name.lower() or "synth" in p.name.lower())
    ]
    if matches:
        return sorted(matches, key=lambda p: len(str(p)))[0]

    matches = [p for p in possible_files if patient_id in p.name]
    if matches:
        return sorted(matches, key=lambda p: len(str(p)))[0]
    return None


def load_segmentation(seg_path: Optional[str | Path]) -> Optional[np.ndarray]:
    if seg_path is None:
        return None
    seg_path = Path(seg_path)
    if not seg_path.exists():
        return None
    if seg_path.suffix.lower() == ".npy":
        return np.load(seg_path).astype(np.int32)
    if seg_path.name.endswith(".nii") or seg_path.name.endswith(".nii.gz"):
        return np.rint(nib.load(str(seg_path)).get_fdata()).astype(np.int32)
    return None


def match_segmentation_shape(seg: Optional[np.ndarray], volume_shape: Tuple[int, int, int]) -> Optional[np.ndarray]:
    """Use exact shape when possible; otherwise try a transpose that matches model space."""
    if seg is None:
        return None
    if seg.shape == volume_shape:
        return seg

    import itertools

    for perm in itertools.permutations(range(3)):
        candidate = np.transpose(seg, perm)
        if candidate.shape == volume_shape:
            return candidate

    warnings.warn(
        f"SynthSeg shape {seg.shape} does not match model volume shape {volume_shape}. "
        "Region-level table will be skipped."
    )
    return None


def brain_mask_from_segmentation(seg_slice: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if seg_slice is None:
        return None
    return (np.asarray(seg_slice) > 0).astype(np.float32)


def fallback_brain_mask(sl: np.ndarray) -> np.ndarray:
    """Fallback model-space mask, not anatomical segmentation."""
    sl = normalize01(sl)
    positive = sl[sl > 0]
    thr = max(float(np.percentile(positive, 10)), 0.03) if positive.size > 0 else 0.03
    mask = sl > thr
    if explain_ndi is not None:
        mask = explain_ndi.binary_fill_holes(mask)
        mask = explain_ndi.binary_opening(mask, iterations=1)
    return mask.astype(np.float32)


def compute_region_attention(masked_cam: np.ndarray, seg_slice: Optional[np.ndarray], slice_idx: int) -> pd.DataFrame:
    """Compute Grad-CAM attention overlap with each SynthSeg anatomical label."""
    if seg_slice is None:
        return pd.DataFrame(columns=REGION_TABLE_COLUMNS)

    cam = np.asarray(masked_cam, dtype=np.float32)
    seg = np.asarray(seg_slice, dtype=np.int32)
    if cam.shape != seg.shape:
        warnings.warn(f"CAM shape {cam.shape} and segmentation shape {seg.shape} do not match.")
        return pd.DataFrame(columns=REGION_TABLE_COLUMNS)

    valid_labels = sorted([int(x) for x in np.unique(seg) if int(x) != 0])
    if not valid_labels:
        return pd.DataFrame(columns=REGION_TABLE_COLUMNS)

    total = float(cam[seg > 0].sum())
    if total <= 1e-8:
        return pd.DataFrame(columns=REGION_TABLE_COLUMNS)

    rows = []
    for label in valid_labels:
        mask = seg == label
        if int(mask.sum()) == 0:
            continue
        values = cam[mask]
        sum_attention = float(values.sum())
        rows.append(
            {
                "slice_index": int(slice_idx),
                "region_label": int(label),
                "region_name": SYNTHSEG_LABEL_NAMES.get(int(label), f"Label_{int(label)}"),
                "mean_attention": float(values.mean()) if values.size else 0.0,
                "max_attention": float(values.max()) if values.size else 0.0,
                "sum_attention": sum_attention,
                "percentage_of_total_attention": float(100.0 * sum_attention / (total + 1e-8)),
                "number_of_pixels": int(mask.sum()),
            }
        )

    if not rows:
        return pd.DataFrame(columns=REGION_TABLE_COLUMNS)
    return pd.DataFrame(rows, columns=REGION_TABLE_COLUMNS).sort_values(
        "percentage_of_total_attention", ascending=False
    ).reset_index(drop=True)


def aggregate_region_tables(tables: Iterable[pd.DataFrame]) -> pd.DataFrame:
    tables = [t for t in tables if isinstance(t, pd.DataFrame) and not t.empty]
    if not tables:
        return pd.DataFrame(
            columns=[
                "region_label",
                "region_name",
                "sum_attention",
                "max_attention",
                "number_of_pixels",
                "slices_present",
                "mean_attention",
                "percentage_of_total_attention",
            ]
        )

    df = pd.concat(tables, ignore_index=True)
    grouped = df.groupby(["region_label", "region_name"], as_index=False).agg(
        sum_attention=("sum_attention", "sum"),
        max_attention=("max_attention", "max"),
        number_of_pixels=("number_of_pixels", "sum"),
        slices_present=("slice_index", "nunique"),
    )
    grouped["mean_attention"] = grouped["sum_attention"] / grouped["number_of_pixels"].replace(0, np.nan)
    total = float(grouped["sum_attention"].sum())
    grouped["percentage_of_total_attention"] = 100.0 * grouped["sum_attention"] / (total + 1e-8)
    return grouped.sort_values("percentage_of_total_attention", ascending=False).reset_index(drop=True)


def overlay_heatmap(gray: np.ndarray, heatmap: np.ndarray, alpha: float = 0.45, cmap_name: str = "magma") -> np.ndarray:
    gray = normalize01(gray)
    if gray.shape != heatmap.shape:
        gray = resize_gray_slice(gray, image_size=heatmap.shape[0])
    base = np.repeat(gray[:, :, None], 3, axis=2)
    colored = cm.get_cmap(cmap_name)(normalize01(heatmap))[:, :, :3]
    opacity = alpha * (normalize01(heatmap) > 0.05)[..., None]
    return np.clip((1 - opacity) * base + opacity * colored, 0, 1)


def overlay_segmentation(gray: np.ndarray, seg_slice: Optional[np.ndarray], alpha: float = 0.35) -> np.ndarray:
    gray = normalize01(gray)
    base = np.repeat(gray[:, :, None], 3, axis=2)
    if seg_slice is None:
        return base

    seg = np.asarray(seg_slice)
    labels = [int(x) for x in np.unique(seg) if int(x) != 0]
    if not labels:
        return base

    palette = cm.get_cmap("tab20", max(len(labels), 1))
    out = base.copy()
    for i, label in enumerate(labels):
        mask = seg == label
        color = np.array(palette(i % 20)[:3])
        out[mask] = (1 - alpha) * out[mask] + alpha * color
    return np.clip(out, 0, 1)


@torch.no_grad()
def predict_patient_probability(model: nn.Module, volume: np.ndarray, candidate_indices: List[int], axis: int = SLICE_AXIS):
    probs = []
    device = next(model.parameters()).device
    model.eval()
    for idx in candidate_indices:
        sl = extract_slice(volume, axis, idx)
        x = slice_to_tensor(sl, device=device)
        logits = model(x)
        p = logits_to_probabilities(logits)[0].detach().cpu().numpy()
        probs.append(p)
    probs = np.asarray(probs, dtype=np.float32)
    return aggregate_patient_probabilities(probs), probs


def _build_slice_probability_table(patient_id: str, candidate_indices: List[int], slice_probs: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "patient_id": patient_id,
                "slice_index": int(idx),
                "prob_PD": float(slice_probs[i, 0]),
                "prob_Atypical": float(slice_probs[i, 1]),
            }
            for i, idx in enumerate(candidate_indices)
        ]
    )


def _plot_case_report(
    patient_id: str,
    output_path: Path,
    selected_records: List[Dict[str, object]],
    predicted_name: str,
    prob_pd: float,
    prob_atypical: float,
    threshold: float,
) -> str:
    fig = plt.figure(figsize=(16, 3.2 * len(selected_records) + 2.8), constrained_layout=False)
    gs = fig.add_gridspec(
        nrows=len(selected_records) + 1,
        ncols=4,
        height_ratios=[0.65] + [1] * len(selected_records),
        width_ratios=[1, 1, 1, 1.15],
        hspace=0.36,
        wspace=0.18,
    )

    ax_header = fig.add_subplot(gs[0, :])
    ax_header.axis("off")
    header = (
        "Final CNN Explainability Report\n"
        "Research decision support - model evidence, not diagnosis\n"
        f"Patient: {patient_id}\n"
        f"Predicted AI-detected pattern: {predicted_name}\n"
        f"P(PD)={prob_pd:.3f} | P(Atypical)={prob_atypical:.3f} | threshold={threshold:.3f}"
    )
    ax_header.text(0.01, 0.95, header, ha="left", va="top", fontsize=12, linespacing=1.25)

    for row_i, rec in enumerate(selected_records, start=1):
        sl = rec["display_slice"]
        seg = rec["seg_slice"]
        cam_img = rec["brain_masked_cam"]

        ax0 = fig.add_subplot(gs[row_i, 0])
        ax0.imshow(sl, cmap="gray")
        ax0.set_title(f"Original MRI\nslice {rec['slice_index']}", fontsize=10)
        ax0.axis("off")

        ax1 = fig.add_subplot(gs[row_i, 1])
        ax1.imshow(overlay_segmentation(sl, seg))
        ax1.set_title("SynthSeg overlay" if seg is not None else "SynthSeg unavailable", fontsize=10)
        ax1.axis("off")

        ax2 = fig.add_subplot(gs[row_i, 2])
        ax2.imshow(overlay_heatmap(sl, cam_img, alpha=0.45, cmap_name="magma"))
        ax2.set_title("Brain-masked Grad-CAM", fontsize=10)
        ax2.axis("off")

        ax3 = fig.add_subplot(gs[row_i, 3])
        ax3.axis("off")
        if seg is not None:
            rt = compute_region_attention(cam_img, seg, int(rec["slice_index"])).head(5)
            if not rt.empty:
                region_lines = "\n".join(
                    [f"{r.region_name}: {r.percentage_of_total_attention:.1f}%" for r in rt.itertuples()]
                )
            else:
                region_lines = "No region attention."
        else:
            region_lines = "No SynthSeg region table."

        stats = (
            f"P(PD): {rec['probs'][0]:.3f}\n"
            f"P(Atypical): {rec['probs'][1]:.3f}\n"
            f"Evidence score: {rec['evidence_score']:.3f}\n"
            f"Inside-brain attention: {100 * rec['inside_brain_attention_fraction']:.1f}%\n\n"
            f"Top anatomical overlaps:\n{region_lines}"
        )
        ax3.text(0.02, 0.98, stats, ha="left", va="top", fontsize=9, family="monospace")

    fig.text(
        0.02,
        0.015,
        "Grad-CAM indicates image regions contributing to the CNN prediction. "
        "SynthSeg overlap provides anatomy-grounded model evidence, not confirmed pathology.",
        fontsize=9,
        ha="left",
    )
    fig.savefig(output_path, dpi=230, bbox_inches="tight")
    plt.close(fig)
    return str(output_path)


def _plot_slice_probability_profile(
    patient_id: str,
    output_path: Path,
    slice_probability_table: pd.DataFrame,
    selected_slice_indices: List[int],
    prob_pd: float,
    prob_atypical: float,
    threshold: float,
) -> str:
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    dfp = slice_probability_table.sort_values("slice_index")
    ax.plot(dfp["slice_index"], dfp["prob_PD"], marker="o", linewidth=2, label="Slice P(PD pattern)")
    ax.plot(dfp["slice_index"], dfp["prob_Atypical"], marker="o", linewidth=2, label="Slice P(Atypical pattern)")
    ax.axhline(threshold, linestyle="--", linewidth=1.5, label=f"Threshold {threshold:.3f}")
    ax.axhline(prob_pd, linestyle=":", linewidth=1.8, label=f"Patient P(PD) {prob_pd:.3f}")
    ax.axhline(prob_atypical, linestyle=":", linewidth=1.8, label=f"Patient P(Atypical) {prob_atypical:.3f}")
    for idx in selected_slice_indices:
        ax.axvline(idx, alpha=0.20, linewidth=2)
    ax.set_title(f"Slice-Level Probability Profile - {patient_id}")
    ax.set_xlabel("Axial slice index")
    ax.set_ylabel("Probability")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=230, bbox_inches="tight")
    plt.close(fig)
    return str(output_path)


def _plot_top_regions(patient_id: str, output_path: Path, region_attention_table: pd.DataFrame) -> Optional[str]:
    """Save top regions only when region table exists, as requested."""
    if region_attention_table.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 5.5))
    top = region_attention_table.head(10).iloc[::-1]
    ax.barh(top["region_name"], top["percentage_of_total_attention"])
    ax.set_xlabel("Percent of total brain-masked Grad-CAM attention")
    ax.set_title(f"Top SynthSeg Region Overlaps - {patient_id}")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=230, bbox_inches="tight")
    plt.close(fig)
    return str(output_path)


def run_explainability(
    patient_id: str,
    volume_path: Optional[str | Path] = None,
    checkpoint_path: Optional[str | Path] = None,
    synthseg_dir: Optional[str | Path] = None,
    output_dir: Optional[str | Path] = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> Dict[str, object]:
    """Generate Grad-CAM + SynthSeg explainability outputs for one patient."""
    patient_id = str(patient_id)
    output_root = Path(output_dir) if output_dir is not None else DEFAULT_EXPLAINABILITY_OUTPUT_DIR
    patient_dir = output_root / safe_name(patient_id)
    patient_dir.mkdir(parents=True, exist_ok=True)

    model, _metadata = load_model_checkpoint(checkpoint_path)
    replace_inplace_relu(model)
    device = next(model.parameters()).device

    resolved_volume_path = get_volume_path(patient_id, volume_path)
    volume = load_preprocessed_volume(resolved_volume_path)

    candidate_indices = choose_informative_slice_indices(
        volume,
        axis=SLICE_AXIS,
        n_slices=SLICES_PER_PATIENT,
    )
    patient_probs, slice_probs = predict_patient_probability(model, volume, candidate_indices, axis=SLICE_AXIS)
    prob_pd = float(patient_probs[0])
    prob_atypical = float(patient_probs[1])
    predicted_label = int(prob_atypical >= float(threshold))
    predicted_name = BINARY_LABEL_NAMES[predicted_label]

    seg_path = find_synthseg_path(patient_id, synthseg_dir=synthseg_dir)
    seg_volume = match_segmentation_shape(load_segmentation(seg_path), tuple(volume.shape))

    gradcam = GradCAM(model)
    records: List[Dict[str, object]] = []
    region_tables: List[pd.DataFrame] = []

    try:
        for slice_idx in candidate_indices:
            sl = extract_slice(volume, SLICE_AXIS, slice_idx)
            display_sl = resize_gray_slice(sl, image_size=IMAGE_SIZE)
            x = slice_to_tensor(sl, device=device)

            cam, probs = gradcam(x, class_idx=predicted_label, output_size=(IMAGE_SIZE, IMAGE_SIZE))

            seg_slice = None
            if seg_volume is not None and seg_volume.ndim == 3 and seg_volume.shape[SLICE_AXIS] == volume.shape[SLICE_AXIS]:
                raw_seg_slice = extract_slice(seg_volume, SLICE_AXIS, slice_idx)
                seg_slice = resize_label_slice(raw_seg_slice, output_shape=(IMAGE_SIZE, IMAGE_SIZE))

            brain_mask = brain_mask_from_segmentation(seg_slice)
            if brain_mask is None:
                brain_mask = fallback_brain_mask(display_sl)

            masked_cam = normalize01(cam * brain_mask)
            raw_total = float(cam.sum())
            inside_total = float((cam * brain_mask).sum())
            inside_fraction = float(inside_total / (raw_total + 1e-8)) if raw_total > 0 else 0.0

            region_table = compute_region_attention(masked_cam, seg_slice, slice_idx)
            if not region_table.empty:
                region_tables.append(region_table)

            evidence_score = (
                0.50 * float(probs[predicted_label])
                + 0.25 * min(1.0, float(brain_mask.mean()) / 0.20)
                + 0.25 * float(masked_cam.mean())
            )

            records.append(
                {
                    "slice_index": int(slice_idx),
                    "display_slice": display_sl,
                    "probs": probs,
                    "target_class": int(predicted_label),
                    "seg_slice": seg_slice,
                    "brain_masked_cam": masked_cam,
                    "inside_brain_attention_fraction": inside_fraction,
                    "brain_fraction": float(brain_mask.mean()),
                    "cam_mean": float(masked_cam.mean()),
                    "cam_max": float(masked_cam.max()),
                    "evidence_score": float(evidence_score),
                }
            )
    finally:
        gradcam.remove()

    evidence_df = pd.DataFrame(
        [
            {
                "patient_id": patient_id,
                "slice_index": r["slice_index"],
                "prob_PD": float(r["probs"][0]),
                "prob_Atypical": float(r["probs"][1]),
                "brain_fraction": r["brain_fraction"],
                "inside_brain_attention_fraction": r["inside_brain_attention_fraction"],
                "cam_mean": r["cam_mean"],
                "cam_max": r["cam_max"],
                "evidence_score": r["evidence_score"],
            }
            for r in records
        ]
    ).sort_values("evidence_score", ascending=False).reset_index(drop=True)

    selected_slice_indices = evidence_df.head(4)["slice_index"].tolist()
    selected_records = [r for r in records if r["slice_index"] in selected_slice_indices]
    selected_records = sorted(selected_records, key=lambda r: r["slice_index"])

    region_attention_table = aggregate_region_tables(region_tables)
    slice_probability_table = _build_slice_probability_table(patient_id, candidate_indices, slice_probs)

    case_report_path = _plot_case_report(
        patient_id=patient_id,
        output_path=patient_dir / "final_case_report.png",
        selected_records=selected_records,
        predicted_name=predicted_name,
        prob_pd=prob_pd,
        prob_atypical=prob_atypical,
        threshold=float(threshold),
    )
    probability_profile_path = _plot_slice_probability_profile(
        patient_id=patient_id,
        output_path=patient_dir / "slice_probability_profile.png",
        slice_probability_table=slice_probability_table,
        selected_slice_indices=selected_slice_indices,
        prob_pd=prob_pd,
        prob_atypical=prob_atypical,
        threshold=float(threshold),
    )
    top_regions_plot_path = _plot_top_regions(
        patient_id=patient_id,
        output_path=patient_dir / "top_synthseg_regions.png",
        region_attention_table=region_attention_table,
    )

    region_table_path = patient_dir / "region_attention_table.csv"
    region_attention_table.to_csv(region_table_path, index=False)
    slice_probability_table.to_csv(patient_dir / "slice_probability_table.csv", index=False)
    evidence_df.to_csv(patient_dir / "evidence_scores.csv", index=False)

    top_regions = []
    if not region_attention_table.empty:
        top_regions = [
            {
                "region_name": str(row.region_name),
                "percentage_of_total_attention": float(row.percentage_of_total_attention),
            }
            for row in region_attention_table.head(10).itertuples()
        ]

    summary = {
        "patient_id": patient_id,
        "volume_path": str(resolved_volume_path),
        "checkpoint_path": str(Path(checkpoint_path) if checkpoint_path is not None else DEFAULT_CHECKPOINT_PATH),
        "synthseg_path": str(seg_path) if seg_path is not None else None,
        "prob_PD": prob_pd,
        "prob_Atypical": prob_atypical,
        "threshold": float(threshold),
        "predicted_label": predicted_label,
        "predicted_pattern_name": predicted_name,
        "predicted_ai_pattern_name": PATTERN_NAMES[predicted_label],
        "selected_slices": [int(x) for x in selected_slice_indices],
        "case_report_path": case_report_path,
        "slice_probability_profile_path": probability_profile_path,
        "top_regions_plot_path": top_regions_plot_path,
        "region_attention_table_path": str(region_table_path),
        "top_regions": top_regions,
        "note": "Grad-CAM highlights model evidence. SynthSeg provides anatomical context. This is not diagnostic proof.",
    }

    summary_json_path = patient_dir / "explainability_summary.json"
    summary["summary_json_path"] = str(summary_json_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Grad-CAM + SynthSeg explainability for one patient.")
    parser.add_argument("--patient_id", required=True)
    parser.add_argument("--volume_path", default=None, help="Optional path to preprocessed 128^3 .npy volume.")
    parser.add_argument("--checkpoint_path", default=None, help="Optional path to final checkpoint.")
    parser.add_argument("--synthseg_dir", default=None, help="Directory containing SynthSeg outputs.")
    parser.add_argument("--output_dir", default=None, help="Directory for explainability outputs.")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    result = run_explainability(
        patient_id=args.patient_id,
        volume_path=args.volume_path,
        checkpoint_path=args.checkpoint_path,
        synthseg_dir=args.synthseg_dir,
        output_dir=args.output_dir,
        threshold=args.threshold,
    )
    print(json.dumps(result, indent=2))
