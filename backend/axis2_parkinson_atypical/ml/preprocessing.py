"""
Reusable MRI preprocessing for the PD vs atypical parkinsonism website backend.

This file mirrors the cleaned notebook preprocessing logic:
1. Load a 3D NIfTI volume.
2. Convert to closest canonical orientation.
3. Robust percentile normalization.
4. Crop low-signal background.
5. Resize to 128 x 128 x 128.
6. Save the model-space volume as .npy and, optionally, as NIfTI for SynthSeg.

The output is research infrastructure for a decision-support model. It does not
produce a clinical diagnosis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence

import nibabel as nib
import numpy as np
from scipy import ndimage


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_NPY_DIR = PROJECT_DIR / "preprocessed_volumes_128"
DEFAULT_OUTPUT_NIFTI_DIR = PROJECT_DIR / "modelspace_nifti"
TARGET_SHAPE = (128, 128, 128)


def robust_percentile_normalize(volume: np.ndarray, lower: float = 1, upper: float = 99) -> np.ndarray:
    """Notebook-matched robust intensity normalization to [0, 1]."""
    volume = np.asarray(volume, dtype=np.float32)
    finite_mask = np.isfinite(volume)
    if not finite_mask.any():
        return np.zeros_like(volume, dtype=np.float32)

    valid = volume[finite_mask]
    p_low, p_high = np.percentile(valid, [lower, upper])
    if p_high <= p_low:
        return np.zeros_like(volume, dtype=np.float32)

    volume = np.clip(volume, p_low, p_high)
    volume = (volume - p_low) / (p_high - p_low)
    volume[~finite_mask] = 0
    return volume.astype(np.float32)


def crop_background(volume: np.ndarray, margin: int = 4) -> np.ndarray:
    """Crop low-signal borders using the same threshold rule as the notebook."""
    threshold = max(
        0.01,
        float(np.percentile(volume[volume > 0], 5)) if np.any(volume > 0) else 0.01,
    )
    mask = volume > threshold
    if not mask.any():
        return volume

    coords = np.array(np.where(mask))
    start = np.maximum(coords.min(axis=1) - margin, 0)
    end = np.minimum(coords.max(axis=1) + margin + 1, volume.shape)
    slices = tuple(slice(int(s), int(e)) for s, e in zip(start, end))
    return volume[slices]


def resize_volume(volume: np.ndarray, target_shape: Sequence[int] = TARGET_SHAPE) -> np.ndarray:
    """Resample a 3D volume to model space with linear interpolation."""
    if len(volume.shape) != 3:
        raise ValueError(f"Expected a 3D volume, got shape {volume.shape}.")
    zoom = [float(t) / float(s) for t, s in zip(target_shape, volume.shape)]
    resized = ndimage.zoom(volume, zoom=zoom, order=1)
    return resized.astype(np.float32)


def load_mri_volume(input_path: str | Path) -> np.ndarray:
    """Load a NIfTI MRI volume and convert it to closest canonical orientation."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"MRI input not found: {input_path}")
    if not (input_path.name.endswith(".nii") or input_path.name.endswith(".nii.gz")):
        raise ValueError(f"Expected a .nii or .nii.gz file, got: {input_path}")

    img = nib.load(str(input_path))
    img = nib.as_closest_canonical(img)
    volume = img.get_fdata(dtype=np.float32)
    volume = np.squeeze(volume)
    if volume.ndim != 3:
        raise ValueError(f"Expected 3D NIfTI volume, got shape {volume.shape} for {input_path}")
    return volume.astype(np.float32)


def preprocess_volume(volume: np.ndarray, target_shape: Sequence[int] = TARGET_SHAPE) -> np.ndarray:
    """Apply the notebook preprocessing sequence to a loaded 3D volume."""
    volume = robust_percentile_normalize(volume)
    volume = crop_background(volume)
    volume = resize_volume(volume, target_shape=target_shape)
    volume = np.clip(volume, 0.0, 1.0).astype(np.float32)
    return volume


def save_preprocessed_npy(volume: np.ndarray, output_path: str | Path) -> Path:
    """Save a preprocessed model-space volume as .npy."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, volume.astype(np.float32))
    return output_path


def export_modelspace_nifti(volume: np.ndarray, output_path: str | Path) -> Path:
    """
    Save the preprocessed model-space volume as NIfTI for SynthSeg.

    The notebook model operates in normalized 128^3 array space. We therefore use
    an identity affine for this exported model-space image.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = nib.Nifti1Image(volume.astype(np.float32), affine=np.eye(4, dtype=np.float32))
    nib.save(img, str(output_path))
    return output_path


def preprocess_mri(
    input_path: str | Path,
    patient_id: str,
    output_npy_dir: Optional[str | Path] = None,
    output_nifti_dir: Optional[str | Path] = None,
) -> Dict[str, object]:
    """
    Preprocess one MRI volume for model inference and SynthSeg.

    Returns paths and status. This function is safe to import and call from an API.
    """
    patient_id = str(patient_id)
    output_npy_dir = Path(output_npy_dir) if output_npy_dir is not None else DEFAULT_OUTPUT_NPY_DIR
    output_nifti_dir = Path(output_nifti_dir) if output_nifti_dir is not None else DEFAULT_OUTPUT_NIFTI_DIR

    raw_volume = load_mri_volume(input_path)
    volume = preprocess_volume(raw_volume, target_shape=TARGET_SHAPE)

    npy_path = output_npy_dir / f"{patient_id}.npy"
    nifti_path = output_nifti_dir / f"{patient_id}_modelspace.nii.gz"

    save_preprocessed_npy(volume, npy_path)
    export_modelspace_nifti(volume, nifti_path)

    return {
        "patient_id": patient_id,
        "npy_path": str(npy_path),
        "modelspace_nifti_path": str(nifti_path),
        "volume_shape": [int(x) for x in volume.shape],
        "status": "preprocessed",
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Preprocess one MRI NIfTI for the website backend.")
    parser.add_argument("--input_path", required=True, help="Path to .nii or .nii.gz MRI volume.")
    parser.add_argument("--patient_id", required=True, help="Patient/case identifier.")
    parser.add_argument("--output_npy_dir", default=None, help="Optional output directory for .npy volume.")
    parser.add_argument("--output_nifti_dir", default=None, help="Optional output directory for model-space NIfTI.")
    args = parser.parse_args()

    result = preprocess_mri(
        input_path=args.input_path,
        patient_id=args.patient_id,
        output_npy_dir=args.output_npy_dir,
        output_nifti_dir=args.output_nifti_dir,
    )
    print(json.dumps(result, indent=2))
