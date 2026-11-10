"""Notebook preprocessing, with explicit input space and separate stage inputs."""
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F

TARGET_SIZE = (128, 128, 64)


def validate_volume(volume):
    if volume.ndim != 3 or not np.isfinite(volume).all():
        raise ValueError("Upload a finite, three-dimensional MRI volume.")
    if float(np.std(volume)) < 1e-8:
        raise ValueError("The MRI volume is empty or has constant intensity.")
    return np.asarray(volume, dtype=np.float32)


def skull_strip(volume):
    from skimage.filters import threshold_otsu
    from skimage.measure import label
    from scipy.ndimage import binary_fill_holes
    result = volume.copy()
    positive = result[result > 0]
    if not positive.size:
        return result
    components = label(result > threshold_otsu(positive) * 0.4)
    counts = np.bincount(components.ravel())
    counts[0] = 0
    if counts.max() > 0:
        result[~binary_fill_holes(components == counts.argmax())] = 0
    return result


def load_crop(path: Path, input_space: str, template_path: Path):
    if input_space == "notebook_crop":
        if path.suffix != ".npy":
            raise ValueError("Notebook crops must be .npy files from the processed folder.")
        volume = validate_volume(np.load(path, allow_pickle=False))
        if volume.shape != TARGET_SIZE:
            raise ValueError("Notebook crops must have shape 128 × 128 × 64.")
        return volume
    if not str(path).lower().endswith((".nii", ".nii.gz")):
        raise ValueError("MRI uploads must be NIfTI (.nii or .nii.gz).")
    import nibabel as nib
    try:
        image = nib.load(path)
    except nib.filebasedimages.ImageFileError as exc:
        raise ValueError("The uploaded file is not a readable NIfTI MRI.") from exc
    if len(image.shape) != 3 or np.prod(image.shape) > 256_000_000:
        raise ValueError("Expected a 3D MRI volume with at most 256 million voxels.")
    validate_volume(image.get_fdata(dtype=np.float32))
    if not template_path.is_file():
        raise RuntimeError("The notebook MNI template is missing from the model bundle.")
    if input_space == "raw":
        import ants
        moving = ants.n4_bias_field_correction(ants.image_read(str(path)))
        registration = ants.registration(
            fixed=ants.image_read(str(template_path)), moving=moving,
            type_of_transform="Affine", outprefix=str(path.parent / "registration_"),
        )
        volume = registration["warpedmovout"].numpy()
    elif input_space == "mni":
        template = nib.load(template_path)
        if image.shape != template.shape or not np.allclose(image.affine, template.affine, atol=1e-3):
            raise ValueError("This scan does not match the notebook MNI template grid. Choose raw MRI.")
        volume = image.get_fdata(dtype=np.float32)
    else:
        raise ValueError("Unknown MRI input space.")
    volume = validate_volume(volume)
    low, high = np.percentile(volume, [1, 99])
    volume = np.clip(volume, low, high)
    volume = (volume - volume.min()) / (volume.max() - volume.min() + 1e-8)
    if any(a < b for a, b in zip(volume.shape, (150, 120, 90))):
        raise ValueError("Registered MRI is smaller than the notebook crop bounds.")
    crop = volume[20:150, 20:120, 0:90].copy()
    return F.interpolate(torch.from_numpy(crop)[None, None], size=TARGET_SIZE,
                         mode="trilinear", align_corners=False)[0, 0].numpy()


def stage_tensor(crop, strip):
    volume = skull_strip(crop) if strip else crop.copy()
    validate_volume(volume)
    volume = (volume - volume.mean()) / (volume.std() + 1e-8)
    return torch.from_numpy(volume.astype(np.float32))[None, None]
