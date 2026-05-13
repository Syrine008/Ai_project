"""Preprocessing for axis5 functional connectivity fMRI input."""
from __future__ import annotations

import numpy as np
import nibabel as nib
from nilearn import image
from nilearn.signal import clean as signal_clean
from scipy.ndimage import zoom as ndimage_zoom

TARGET_T = 16
TARGET_HW = (64, 64)
N_DROP = 5


def preprocess_nii(path: str, target_t: int = TARGET_T, target_hw: tuple[int, int] = TARGET_HW) -> np.ndarray:
    """Load a NIfTI file and return (1, T, H, W) float32 clip in [0, 1]."""
    raw = nib.load(path)
    zooms = raw.header.get_zooms()
    tr = float(zooms[3]) if len(zooms) >= 4 else 2.5

    trimmed = image.index_img(raw, slice(N_DROP, None))
    smooth_img = image.smooth_img(trimmed, fwhm=6)

    data = smooth_img.get_fdata(dtype=np.float32)
    if data.ndim != 4:
        raise ValueError("Expected 4D fMRI NIfTI input")

    x, y, z, t = data.shape
    flat = data.reshape(-1, t).T
    flat_clean = signal_clean(
        flat,
        detrend=True,
        standardize=None,
        high_pass=0.01,
        low_pass=0.1,
        t_r=tr,
    )
    clean_data = flat_clean.T.reshape(x, y, z, t)

    z_mid = z // 2
    movie = clean_data[:, :, z_mid, :].transpose(2, 0, 1)

    n_frames = movie.shape[0]
    if n_frames >= target_t:
        frame_idx = np.linspace(0, n_frames - 1, target_t).astype(int)
    else:
        frame_idx = np.arange(target_t) % max(1, n_frames)

    clip = np.stack(
        [
            ndimage_zoom(
                movie[i],
                (target_hw[0] / movie.shape[1], target_hw[1] / movie.shape[2]),
                order=1,
            )
            for i in frame_idx
        ],
        axis=0,
    )

    p1, p99 = np.percentile(clip, [1, 99])
    if p99 - p1 > 1e-6:
        clip = (clip - p1) / (p99 - p1 + 1e-6)
    clip = np.clip(clip, 0.0, 1.0).astype(np.float32)

    return clip[None, ...]
