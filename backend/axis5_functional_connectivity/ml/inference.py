"""Inference for axis5 functional connectivity."""
from __future__ import annotations

import base64
import io
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ..explain.explainer import build_explanation
from .preprocess import preprocess_nii

MODEL_PATH = Path(__file__).resolve().parent / "best_model_unet3d_16.pt"


class TorchCheckpointLoader:
    def __init__(self, ckpt_path: Path) -> None:
        self.ckpt_path = ckpt_path
        self._model: Optional[AnomalyDetector] = None
        self._checked = False

    def get(self) -> Optional["AnomalyDetector"]:
        if self._model is not None:
            return self._model
        if self._checked:
            return None
        self._checked = True
        if not self.ckpt_path.exists():
            return None
        try:
            self._model = AnomalyDetector(self.ckpt_path)
        except Exception:
            self._model = None
        return self._model

    @property
    def is_available(self) -> bool:
        return self.get() is not None


MODEL_LOADER = TorchCheckpointLoader(MODEL_PATH)


class Simple2DCNNAE(nn.Module):
    def __init__(self, base_channels: int = 16) -> None:
        super().__init__()
        c = base_channels
        self.encoder = nn.Sequential(
            nn.Conv2d(1, c, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(c, c * 2, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(c * 2, c * 4, 3, padding=1),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(c * 4, c * 2, 2, stride=2),
            nn.ReLU(),
            nn.ConvTranspose2d(c * 2, c, 2, stride=2),
            nn.ReLU(),
            nn.Conv2d(c, 1, 3, padding=1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, t, h, w = x.shape
        x2d = x.permute(0, 2, 1, 3, 4).reshape(b * t, c, h, w)
        out = self.decoder(self.encoder(x2d))
        return out.reshape(b, t, c, h, w).permute(0, 2, 1, 3, 4)


class Simple3DCNNAE(nn.Module):
    def __init__(self, base_channels: int = 16) -> None:
        super().__init__()
        c = base_channels
        self.encoder = nn.Sequential(
            nn.Conv3d(1, c, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool3d(2),
            nn.Conv3d(c, c * 2, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool3d(2),
            nn.Conv3d(c * 2, c * 4, 3, padding=1),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose3d(c * 4, c * 2, 2, stride=2),
            nn.ReLU(),
            nn.ConvTranspose3d(c * 2, c, 2, stride=2),
            nn.ReLU(),
            nn.Conv3d(c, 1, 3, padding=1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))


class UNet3DAE(nn.Module):
    def __init__(self, base_channels: int = 16) -> None:
        super().__init__()
        c = base_channels
        self.enc1 = self._block(1, c)
        self.down1 = nn.MaxPool3d(2)
        self.enc2 = self._block(c, c * 2)
        self.down2 = nn.MaxPool3d(2)
        self.bottle = self._block(c * 2, c * 4)
        self.up2 = nn.ConvTranspose3d(c * 4, c * 2, kernel_size=2, stride=2)
        self.dec2 = self._block(c * 4, c * 2)
        self.up1 = nn.ConvTranspose3d(c * 2, c, kernel_size=2, stride=2)
        self.dec1 = self._block(c * 2, c)
        self.out_conv = nn.Conv3d(c, 1, kernel_size=1)

    @staticmethod
    def _block(in_ch: int, out_ch: int) -> nn.Sequential:
        def _gn(ch: int) -> nn.GroupNorm:
            return nn.GroupNorm(min(8, ch), ch)

        return nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, padding=1),
            _gn(out_ch),
            nn.SiLU(),
            nn.Conv3d(out_ch, out_ch, 3, padding=1),
            _gn(out_ch),
            nn.SiLU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.down1(e1))
        b = self.bottle(self.down2(e2))
        d2 = self.dec2(torch.cat([self.up2(b), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return torch.sigmoid(self.out_conv(d1))


def _group_norm(channels: int, max_groups: int = 8) -> nn.GroupNorm:
    g = min(max_groups, channels)
    while channels % g != 0:
        g -= 1
    return nn.GroupNorm(g, channels)


class ResBlock3D(nn.Module):
    def __init__(self, channels: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.norm1 = _group_norm(channels)
        self.conv1 = nn.Conv3d(channels, channels, 3, padding=1)
        self.norm2 = _group_norm(channels)
        self.conv2 = nn.Conv3d(channels, channels, 3, padding=1)
        self.drop = nn.Dropout3d(dropout) if dropout > 0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        r = x
        x = self.conv1(F.silu(self.norm1(x)))
        x = self.drop(x)
        x = self.conv2(F.silu(self.norm2(x)))
        return x + r


class StrongRes3DAE(nn.Module):
    def __init__(self, base_channels: int = 24, dropout: float = 0.0) -> None:
        super().__init__()
        c1, c2, c3, c4 = [base_channels * (2**i) for i in range(4)]

        self.stem = nn.Conv3d(1, c1, 3, padding=1)
        self.enc1 = ResBlock3D(c1, dropout)
        self.down1 = nn.Conv3d(c1, c2, 3, stride=2, padding=1)
        self.enc2 = ResBlock3D(c2, dropout)
        self.down2 = nn.Conv3d(c2, c3, 3, stride=2, padding=1)
        self.enc3 = ResBlock3D(c3, dropout)
        self.down3 = nn.Conv3d(c3, c4, 3, stride=2, padding=1)

        self.bottleneck = nn.Sequential(ResBlock3D(c4, dropout), ResBlock3D(c4, dropout))

        self.up3 = nn.ConvTranspose3d(c4, c3, 2, stride=2)
        self.dec3 = ResBlock3D(c3, dropout)
        self.up2 = nn.ConvTranspose3d(c3, c2, 2, stride=2)
        self.dec2 = ResBlock3D(c2, dropout)
        self.up1 = nn.ConvTranspose3d(c2, c1, 2, stride=2)
        self.dec1 = ResBlock3D(c1, dropout)
        self.out = nn.Conv3d(c1, 1, 3, padding=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.stem(x)
        x1 = self.enc1(x)
        x2 = self.enc2(self.down1(x1))
        x3 = self.enc3(self.down2(x2))
        xb = self.bottleneck(self.down3(x3))
        x = self.dec3(self.up3(xb) + x3)
        x = self.dec2(self.up2(x) + x2)
        x = self.dec1(self.up1(x) + x1)
        return torch.sigmoid(self.out(x))


def build_model(cfg: dict) -> nn.Module:
    arch = cfg.get("arch")
    bc = cfg.get("base_channels", 16)
    dp = cfg.get("dropout", 0.0)

    if arch == "simple_2d":
        return Simple2DCNNAE(base_channels=bc)
    if arch == "simple_3d":
        return Simple3DCNNAE(base_channels=bc)
    if arch == "unet3d":
        return UNet3DAE(base_channels=bc)
    if arch == "res3d":
        return StrongRes3DAE(base_channels=bc, dropout=dp)
    raise ValueError(f"Unknown architecture: {arch}")


class AnomalyDetector:
    def __init__(self, ckpt_path: Path, device: Optional[str] = None) -> None:
        ckpt = torch.load(ckpt_path, map_location="cpu")
        cfg = ckpt.get("config", {})
        self.threshold = float(ckpt.get("threshold", 0.0))
        self.n_frames = int(ckpt.get("n_frames", 16))
        self.hw = int(ckpt.get("hw", 64))
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = build_model(cfg).to(self.device)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

    def score(self, clip_1thw: np.ndarray) -> tuple[float, np.ndarray]:
        x = torch.from_numpy(clip_1thw[None]).float().to(self.device)
        with torch.no_grad():
            recon = self.model(x)
        err_map = F.mse_loss(recon, x, reduction="none").squeeze(0).cpu().numpy()
        return float(err_map.mean()), err_map

    def is_anomaly(self, score: float) -> bool:
        return bool(self.threshold and score > self.threshold)


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _approx_percentile(score: float, threshold: float) -> Optional[float]:
    if threshold <= 0:
        return None
    ratio = score / threshold
    if ratio <= 1:
        return ratio * 95.0
    return 95.0 + min(5.0, (ratio - 1.0) * 5.0)


def _encode_heatmap(heatmap: np.ndarray) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h_min = float(heatmap.min())
    h_max = float(heatmap.max())
    if h_max > h_min:
        heatmap = (heatmap - h_min) / (h_max - h_min)

    fig, ax = plt.subplots(figsize=(3, 3), dpi=120)
    ax.imshow(heatmap, cmap="hot")
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _upload_suffix(name: str) -> str:
    suffixes = Path(name).suffixes
    return "".join(suffixes) if suffixes else ".nii"


def _write_upload(upload) -> str:
    suffix = _upload_suffix(getattr(upload, "name", "") or "upload.nii")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        for chunk in upload.chunks():
            tmp.write(chunk)
    return tmp.name


def predict(upload, model: Optional[Any], metadata: dict) -> dict:
    """Run inference and return the AnalysisResult dict."""
    if model is None or upload is None:
        return _mock_predict(upload, metadata)

    tmp_path = _write_upload(upload)
    try:
        clip = preprocess_nii(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    score, err_map = model.score(clip)
    threshold = float(model.threshold or 0.0)
    is_anomaly = model.is_anomaly(score) if threshold else False
    ratio = score / threshold if threshold > 0 else 0.0
    prob_anom = _sigmoid(4.0 * (ratio - 1.0)) if threshold > 0 else 0.5

    confidence = [
        {"label": "Atypical pattern", "value": float(prob_anom)},
        {"label": "Typical pattern", "value": float(1.0 - prob_anom)},
    ]
    predicted_class = "Atypical pattern detected" if is_anomaly else "Normal brain pattern"
    summary = (
        "Reconstruction error exceeds the healthy threshold, suggesting atypical connectivity."
        if is_anomaly
        else "Reconstruction error is within the healthy threshold for this model."
    )

    heatmap_b64 = _encode_heatmap(err_map[0].mean(axis=0))
    explanation = build_explanation(upload, metadata, model=model)

    metrics = [
        {"label": "Anomaly score", "value": f"{score:.6f}"},
        {"label": "Threshold", "value": f"{threshold:.6f}" if threshold else "n/a"},
        {"label": "Score/threshold", "value": f"{ratio:.2f}x" if threshold else "n/a"},
    ]
    extra_metrics = explanation.get("metrics") if isinstance(explanation, dict) else None
    if extra_metrics:
        metrics.extend(extra_metrics)
    if isinstance(explanation, dict):
        explanation["metrics"] = metrics

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "predictedClass": predicted_class,
        "topConfidence": float(max(prob_anom, 1.0 - prob_anom)),
        "confidence": confidence,
        "summary": summary,
        "anomalyScore": float(score),
        "threshold": float(threshold),
        "isAnomaly": bool(is_anomaly),
        "heatmapB64": heatmap_b64,
        "nFrames": int(model.n_frames),
        "hw": int(model.hw),
    }
    percentile = _approx_percentile(score, threshold)
    if percentile is not None:
        payload["percentileOfNormal"] = float(percentile)
    if isinstance(explanation, dict):
        payload.update(explanation)
    return payload


def _mock_predict(upload, metadata: dict) -> dict:
    score = 0.0042
    threshold = 0.0061
    is_anomaly = False
    prob_anom = 0.26
    confidence = [
        {"label": "Atypical pattern", "value": float(prob_anom)},
        {"label": "Typical pattern", "value": float(1.0 - prob_anom)},
    ]
    explanation = build_explanation(upload, metadata, model=None)
    metrics = [
        {"label": "Anomaly score", "value": f"{score:.6f}"},
        {"label": "Threshold", "value": f"{threshold:.6f}"},
        {"label": "Score/threshold", "value": f"{score / threshold:.2f}x"},
    ]
    extra_metrics = explanation.get("metrics") if isinstance(explanation, dict) else None
    if extra_metrics:
        metrics.extend(extra_metrics)
    if isinstance(explanation, dict):
        explanation["metrics"] = metrics

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "predictedClass": "Normal brain pattern",
        "topConfidence": float(1.0 - prob_anom),
        "confidence": confidence,
        "summary": "Mock inference result. Upload a scan to run the real model.",
        "anomalyScore": float(score),
        "threshold": float(threshold),
        "isAnomaly": bool(is_anomaly),
        "nFrames": 16,
        "hw": 64,
    }
    percentile = _approx_percentile(score, threshold)
    if percentile is not None:
        payload["percentileOfNormal"] = float(percentile)
    if isinstance(explanation, dict):
        payload.update(explanation)
    return payload
