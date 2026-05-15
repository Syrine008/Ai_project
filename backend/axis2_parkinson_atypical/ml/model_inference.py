"""
Model inference backend for the final PD vs atypical parkinsonism CNN.

Notebook-matched behavior:
- Final architecture: ImprovedResidualSESmallCNN.
- Input volume: preprocessed 128 x 128 x 128 .npy.
- Slice strategy: axial_only, 15 informative axial slices.
- Slice transform: grayscale -> RGB -> tensor -> Normalize(mean=0.5, std=0.5).
- Patient prediction: average slice probabilities, then threshold P(Atypical).

Outputs are non-diagnostic decision-support model evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CHECKPOINT_PATH = PROJECT_DIR / "final_from_scratch_cnn_best_fold.pth"
DEFAULT_PREPROCESSED_NPY_DIR = PROJECT_DIR / "preprocessed_volumes_128"

TARGET_SHAPE = (128, 128, 128)
SLICE_AXIS = 2
SLICES_PER_PATIENT = 15
DEFAULT_THRESHOLD = 0.52
BINARY_LABEL_NAMES = {0: "PD", 1: "Atypical"}
PATTERN_NAMES = {
    0: "PD AI-detected pattern",
    1: "Atypical parkinsonism AI-detected pattern",
}


class SEBlock(nn.Module):
    """Squeeze-and-excitation block from the final notebook CNN."""

    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        hidden = max(channels // reduction, 8)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, hidden),
            nn.ReLU(inplace=False),
            nn.Linear(hidden, channels),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, _, _ = x.shape
        weights = self.pool(x).view(b, c)
        weights = self.fc(weights).view(b, c, 1, 1)
        return x * weights


class ResidualSEBlock(nn.Module):
    """Residual convolutional block with squeeze-and-excitation."""

    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.10):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=False),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
        )
        self.se = SEBlock(out_channels)

        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.shortcut = nn.Identity()

        self.relu = nn.ReLU(inplace=False)
        self.dropout = nn.Dropout2d(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = self.shortcut(x)
        out = self.conv(x)
        out = self.se(out)
        out = out + identity
        out = self.relu(out)
        out = self.dropout(out)
        return out


class ImprovedResidualSESmallCNN(nn.Module):
    """Final from-scratch CNN architecture used by the cleaned notebook."""

    def __init__(self, num_classes: int = 2, dropout: float = 0.40):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=False),
        )
        self.features = nn.Sequential(
            ResidualSEBlock(32, 32, dropout=0.05),
            nn.MaxPool2d(2),
            ResidualSEBlock(32, 64, dropout=0.08),
            nn.MaxPool2d(2),
            ResidualSEBlock(64, 128, dropout=0.10),
            nn.MaxPool2d(2),
            ResidualSEBlock(128, 256, dropout=0.12),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(inplace=False),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x = self.features(x)
        x = self.classifier(x)
        return x


def get_device(device: Optional[str | torch.device] = None) -> torch.device:
    if device is not None:
        return torch.device(device)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _extract_state_dict(checkpoint: object) -> Dict[str, torch.Tensor]:
    if isinstance(checkpoint, dict):
        for key in ("model_state_dict", "state_dict", "model"):
            value = checkpoint.get(key)
            if isinstance(value, dict):
                return value
        if all(isinstance(k, str) for k in checkpoint.keys()):
            return checkpoint  # raw state_dict
    raise ValueError("Checkpoint does not contain a compatible model state dictionary.")


def load_model_checkpoint(
    checkpoint_path: Optional[str | Path] = None,
    device: Optional[str | torch.device] = None,
) -> Tuple[ImprovedResidualSESmallCNN, Dict[str, object]]:
    """Load the final CNN checkpoint without modifying model weights."""
    checkpoint_path = Path(checkpoint_path) if checkpoint_path is not None else DEFAULT_CHECKPOINT_PATH
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    device = get_device(device)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model = ImprovedResidualSESmallCNN(num_classes=2, dropout=0.40).to(device)
    model.load_state_dict(_extract_state_dict(checkpoint))
    model.eval()

    metadata = checkpoint if isinstance(checkpoint, dict) else {}
    return model, metadata


def load_preprocessed_volume(volume_path: str | Path) -> np.ndarray:
    """Load a preprocessed 128^3 .npy volume."""
    volume_path = Path(volume_path)
    if not volume_path.exists():
        raise FileNotFoundError(f"Preprocessed volume not found: {volume_path}")
    volume = np.load(volume_path).astype(np.float32)
    if volume.shape != TARGET_SHAPE:
        raise ValueError(f"Expected volume shape {TARGET_SHAPE}, got {volume.shape} at {volume_path}")
    return np.clip(volume, 0.0, 1.0).astype(np.float32)


def get_volume_path(patient_id: str, volume_path: Optional[str | Path] = None) -> Path:
    """Resolve the patient .npy path using the configured default directory when needed."""
    if volume_path is not None:
        return Path(volume_path)
    return DEFAULT_PREPROCESSED_NPY_DIR / f"{patient_id}.npy"


def extract_slice(volume: np.ndarray, axis: int, idx: int) -> np.ndarray:
    if axis == 0:
        return volume[int(idx), :, :]
    if axis == 1:
        return volume[:, int(idx), :]
    if axis == 2:
        return volume[:, :, int(idx)]
    raise ValueError(f"Invalid axis: {axis}")


def choose_informative_slice_indices(
    volume: np.ndarray,
    axis: int = SLICE_AXIS,
    n_slices: int = SLICES_PER_PATIENT,
) -> List[int]:
    """
    Notebook-matched informative slice selection:
    score = mean + 0.5 * std, keep slices above the 30th percentile,
    then sample evenly across valid slices.
    """
    scores = []
    n_axis = volume.shape[axis]
    for idx in range(n_axis):
        sl = np.take(volume, idx, axis=axis)
        scores.append(float(sl.mean() + 0.5 * sl.std()))
    scores = np.asarray(scores)

    valid = np.where(scores > np.percentile(scores, 30))[0]
    if len(valid) < n_slices:
        valid = np.arange(n_axis)

    chosen_positions = np.linspace(0, len(valid) - 1, n_slices).round().astype(int)
    return sorted(np.unique(valid[chosen_positions]).tolist())


def slice_to_tensor(slice_2d: np.ndarray, device: Optional[str | torch.device] = None) -> torch.Tensor:
    """
    Match the notebook evaluation transform:
    np slice in [0, 1] -> RGB -> ToTensor -> Normalize(mean=0.5, std=0.5).
    """
    sl = np.clip(np.asarray(slice_2d, dtype=np.float32), 0.0, 1.0)
    rgb = np.repeat(sl[..., None], 3, axis=2).astype(np.float32)
    tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).float()
    tensor = (tensor - 0.5) / 0.5
    tensor = tensor.unsqueeze(0)
    if device is not None:
        tensor = tensor.to(get_device(device))
    return tensor


def logits_to_probabilities(logits: torch.Tensor) -> torch.Tensor:
    if logits.ndim == 1:
        logits = logits.unsqueeze(0)
    if logits.shape[1] == 1:
        p1 = torch.sigmoid(logits[:, 0])
        return torch.stack([1.0 - p1, p1], dim=1)
    return torch.softmax(logits[:, :2], dim=1)


@torch.no_grad()
def predict_slices(
    model: nn.Module,
    volume: np.ndarray,
    slice_indices: Iterable[int],
    axis: int = SLICE_AXIS,
    device: Optional[str | torch.device] = None,
) -> Tuple[np.ndarray, List[int]]:
    """Return per-slice probabilities for the selected axial slices."""
    device = get_device(device)
    model.eval()
    probs = []
    used_indices = []
    for idx in slice_indices:
        sl = extract_slice(volume, axis=axis, idx=int(idx))
        x = slice_to_tensor(sl, device=device)
        logits = model(x)
        p = logits_to_probabilities(logits)[0].detach().cpu().numpy()
        probs.append(p)
        used_indices.append(int(idx))
    if not probs:
        raise ValueError("No slice probabilities were computed.")
    return np.asarray(probs, dtype=np.float32), used_indices


def aggregate_patient_probabilities(slice_probabilities: np.ndarray) -> np.ndarray:
    """Average slice probabilities to match the notebook patient-level aggregation."""
    slice_probabilities = np.asarray(slice_probabilities, dtype=np.float32)
    if slice_probabilities.ndim != 2 or slice_probabilities.shape[1] < 2:
        raise ValueError(f"Expected Nx2 slice probabilities, got shape {slice_probabilities.shape}")
    return slice_probabilities[:, :2].mean(axis=0)


def run_model_inference(
    patient_id: str,
    volume_path: Optional[str | Path] = None,
    checkpoint_path: Optional[str | Path] = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> Dict[str, object]:
    """
    Run patient-level CNN inference for one preprocessed .npy volume.

    The return value is API-friendly and intentionally non-diagnostic.
    """
    model, checkpoint_metadata = load_model_checkpoint(checkpoint_path)
    device = next(model.parameters()).device
    resolved_volume_path = get_volume_path(patient_id, volume_path)
    volume = load_preprocessed_volume(resolved_volume_path)

    slice_indices = choose_informative_slice_indices(volume, axis=SLICE_AXIS, n_slices=SLICES_PER_PATIENT)
    slice_probs, used_indices = predict_slices(model, volume, slice_indices, axis=SLICE_AXIS, device=device)
    patient_probs = aggregate_patient_probabilities(slice_probs)

    prob_pd = float(patient_probs[0])
    prob_atypical = float(patient_probs[1])
    predicted_label = int(prob_atypical >= float(threshold))

    return {
        "patient_id": str(patient_id),
        "volume_path": str(resolved_volume_path),
        "checkpoint_path": str(Path(checkpoint_path) if checkpoint_path is not None else DEFAULT_CHECKPOINT_PATH),
        "model_name": str(checkpoint_metadata.get("model_name", "ImprovedResidualSESmallCNN"))
        if isinstance(checkpoint_metadata, dict)
        else "ImprovedResidualSESmallCNN",
        "prob_PD": prob_pd,
        "prob_Atypical": prob_atypical,
        "threshold": float(threshold),
        "predicted_label": predicted_label,
        "predicted_pattern_name": BINARY_LABEL_NAMES[predicted_label],
        "predicted_ai_pattern_name": PATTERN_NAMES[predicted_label],
        "slice_indices": used_indices,
        "slice_probabilities": [
            {"slice_index": int(idx), "prob_PD": float(p[0]), "prob_Atypical": float(p[1])}
            for idx, p in zip(used_indices, slice_probs)
        ],
        "note": "Research decision-support output, not a diagnosis.",
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run final CNN patient-level inference.")
    parser.add_argument("--patient_id", required=True)
    parser.add_argument("--volume_path", default=None, help="Optional path to preprocessed 128^3 .npy volume.")
    parser.add_argument("--checkpoint_path", default=None, help="Optional checkpoint path.")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args()

    result = run_model_inference(
        patient_id=args.patient_id,
        volume_path=args.volume_path,
        checkpoint_path=args.checkpoint_path,
        threshold=args.threshold,
    )
    print(json.dumps(result, indent=2))
