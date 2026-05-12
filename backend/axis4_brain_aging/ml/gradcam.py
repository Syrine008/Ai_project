"""Grad-CAM on EfficientNet-B0 `features[6]` (training notebook default)."""
from __future__ import annotations

from typing import Callable, List, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn

from .constants import INPUT_SIZE


def compute_gradcam(
    model: nn.Module,
    input_tensor: torch.Tensor,
    target_layer_index: int = 6,
) -> np.ndarray:
    """Returns HxW float heatmap in [0, 1] (model should be in eval(); gradients enabled here)."""
    device = next(model.parameters()).device
    x = input_tensor.to(device).detach().requires_grad_(True)

    activations: List[torch.Tensor] = []
    gradients: List[torch.Tensor] = []

    def fwd_hook(_module, _inp, out):
        activations.append(out.detach())

    def full_backward_hook(_module, _grad_in, grad_out):
        gradients.append(grad_out[0].detach())

    layer = model.features[target_layer_index]
    h_fwd = layer.register_forward_hook(fwd_hook)
    h_bwd = layer.register_full_backward_hook(full_backward_hook)

    try:
        model.zero_grad(set_to_none=True)
        out = model(x)
        score = out.squeeze()
        score.backward(retain_graph=False)
    finally:
        h_fwd.remove()
        h_bwd.remove()

    acts = activations[0]
    grads = gradients[0]
    weights = torch.mean(grads, dim=(2, 3), keepdim=True)
    cam = torch.sum(weights * acts, dim=1).squeeze()
    cam = torch.relu(cam)
    cam_np = cam.detach().float().cpu().numpy()
    cam_np = (cam_np - cam_np.min()) / (cam_np.max() - cam_np.min() + 1e-8)
    cam_np = cv2.resize(cam_np, (INPUT_SIZE, INPUT_SIZE))
    return cam_np.astype(np.float32)


def overlay_heatmap(
    base_gray_01: np.ndarray,
    cam_01: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    """base_gray_01, cam_01: HxW in [0,1]. Returns uint8 RGB HxW."""
    base_u8 = (np.clip(base_gray_01, 0, 1) * 255).astype(np.uint8)
    heat = cv2.applyColorMap((np.clip(cam_01, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET)
    base_bgr = cv2.cvtColor(base_u8, cv2.COLOR_GRAY2BGR)
    out = cv2.addWeighted(base_bgr, 1.0 - alpha, heat, alpha, 0)
    return out


def encode_overlay_png_bytes(
    base_gray_01: np.ndarray,
    cam_01: np.ndarray,
) -> bytes:
    """PNG bytes for optional API / frontend."""
    rgb = overlay_heatmap(base_gray_01, cam_01)
    ok, buf = cv2.imencode(".png", rgb)
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return buf.tobytes()
