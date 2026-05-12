"""MRI / slice preprocessing aligned with notebook 2 (volume z-score, 3ch, 224, [-1,1] normalize)."""
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple

import nibabel as nib
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from .constants import INPUT_SIZE, SLICE_INDEX_DEFAULT


def _zscore_2d(arr: np.ndarray) -> np.ndarray:
    m = float(np.mean(arr))
    s = float(np.std(arr)) + 1e-8
    return (arr - m) / s


def _zscore_volume(vol: np.ndarray) -> np.ndarray:
    return _zscore_2d(vol) if vol.ndim == 2 else (vol - np.mean(vol)) / (np.std(vol) + 1e-8)


def _to_model_tensor(slice_2d: np.ndarray) -> torch.Tensor:
    """HW float slice -> [1, 3, 224, 224] on CPU (move to device in caller)."""
    s = slice_2d.astype(np.float32)
    if s.ndim != 2:
        raise ValueError("Expected 2D slice")
    rgb = np.stack([s, s, s], axis=-1)
    tensor_chw = torch.from_numpy(rgb).permute(2, 0, 1)
    tfm = transforms.Compose(
        [
            transforms.Resize((INPUT_SIZE, INPUT_SIZE)),
            transforms.Normalize([0.5] * 3, [0.5] * 3),
        ]
    )
    return tfm(tensor_chw).unsqueeze(0)


def volume_to_axial_slice(
    data: np.ndarray,
    slice_index: Optional[int] = None,
) -> Tuple[torch.Tensor, np.ndarray]:
    """3D (or 4D single-timepoint) → z-scored axial slice + visualization [0,1]."""
    arr = np.asanyarray(data, dtype=np.float64)
    if arr.ndim == 4:
        arr = arr[..., 0]
    if arr.ndim != 3:
        raise ValueError("Volume must be 3D or 4D (single timepoint)")
    idx = SLICE_INDEX_DEFAULT if slice_index is None else int(slice_index)
    vol = _zscore_volume(arr)
    if not (0 <= idx < vol.shape[2]):
        idx = vol.shape[2] // 2
    slice_2d = np.ascontiguousarray(vol[:, :, idx], dtype=np.float32)
    vis = (slice_2d - slice_2d.min()) / (slice_2d.max() - slice_2d.min() + 1e-8)
    return _to_model_tensor(slice_2d), vis


def load_nifti_slice(
    file_bytes: bytes,
    slice_index: Optional[int] = None,
) -> Tuple[torch.Tensor, np.ndarray]:
    """Single-file NIfTI."""
    bio = io.BytesIO(file_bytes)
    img = nib.load(bio)
    data = np.asanyarray(img.get_fdata(), dtype=np.float64)
    return volume_to_axial_slice(data, slice_index)


def classify_analyze_hdr_img(
    bytes_a: bytes,
    name_a: str,
    bytes_b: bytes,
    name_b: str,
) -> Tuple[bytes, bytes]:
    """Return (hdr_bytes, img_bytes). Uses extensions first, then file-size heuristic."""
    na = (name_a or "").lower()
    nb = (name_b or "").lower()

    def ext_hint(name: str) -> Optional[str]:
        if name.endswith(".hdr"):
            return "hdr"
        if name.endswith(".img"):
            return "img"
        return None

    ha, hb = ext_hint(na), ext_hint(nb)
    if ha == "hdr" and hb == "img":
        return bytes_a, bytes_b
    if hb == "hdr" and ha == "img":
        return bytes_b, bytes_a
    if ha == "hdr":
        return bytes_a, bytes_b
    if hb == "hdr":
        return bytes_b, bytes_a
    if ha == "img":
        return bytes_b, bytes_a
    if hb == "img":
        return bytes_a, bytes_b

    # Typical Analyze pair: header tiny (~KB), raw volume tens of MB
    if len(bytes_a) <= len(bytes_b):
        return bytes_a, bytes_b
    return bytes_b, bytes_a


def load_analyze_hdr_img_pair(
    hdr_bytes: bytes,
    img_bytes: bytes,
    stem: str = "vol",
    slice_index: Optional[int] = None,
) -> Tuple[torch.Tensor, np.ndarray]:
    """Analyze 7.5 pair (.hdr + .img) → same axial slice path as training notebooks."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        hpath = root / f"{stem}.hdr"
        ipath = root / f"{stem}.img"
        hpath.write_bytes(hdr_bytes)
        ipath.write_bytes(img_bytes)
        loaded = nib.load(str(hpath))
        data = np.asanyarray(loaded.get_fdata(), dtype=np.float64)
    return volume_to_axial_slice(data, slice_index)


def load_analyze_zip(
    zip_bytes: bytes,
    slice_index: Optional[int] = None,
) -> Tuple[torch.Tensor, np.ndarray]:
    """ZIP with one Analyze pair: basename.hdr + basename.img (any folder nesting)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(root)
        hdr_candidates = sorted(root.rglob("*.hdr")) + sorted(root.rglob("*.HDR"))
        if not hdr_candidates:
            raise ValueError("ZIP must contain exactly one Analyze .hdr plus matching .img")
        hdr_path = hdr_candidates[0]
        img_path = hdr_path.with_suffix(".img")
        if not img_path.exists():
            alt = hdr_path.with_suffix(".IMG")
            img_path = alt if alt.exists() else img_path
        if not img_path.exists():
            raise ValueError(f"No matching .img for {hdr_path.name}")
        loaded = nib.load(str(hdr_path))
        data = np.asanyarray(loaded.get_fdata(), dtype=np.float64)
    return volume_to_axial_slice(data, slice_index)


def analyze_hdr_img_pair_to_nifti_gz_bytes(hdr_bytes: bytes, img_bytes: bytes, stem: str = "volume") -> bytes:
    """Notebook helper: merge Analyze pair → .nii.gz bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        hpath = root / f"{stem}.hdr"
        ipath = root / f"{stem}.img"
        hpath.write_bytes(hdr_bytes)
        ipath.write_bytes(img_bytes)
        loaded = nib.load(str(hpath))
        nii = nib.Nifti1Image(np.asanyarray(loaded.get_fdata()), loaded.affine, loaded.header)
        out_path = root / "volume.nii.gz"
        nib.save(nii, str(out_path))
        return out_path.read_bytes()


def load_image_slice(file_bytes: bytes) -> Tuple[torch.Tensor, np.ndarray]:
    """PNG/JPEG: grayscale slice; per-image z-score; same 3ch + normalize as training."""
    im = Image.open(io.BytesIO(file_bytes)).convert("L")
    arr = np.asarray(im, dtype=np.float32)
    s = _zscore_2d(arr).astype(np.float32)
    vis = (s - s.min()) / (s.max() - s.min() + 1e-8)
    return _to_model_tensor(s), vis
