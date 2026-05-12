"""Lazy PyTorch checkpoint loader (same role as `common.base.ModelLoader` for `.pkl` axes)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import torch

from .architecture import build_brain_age_efficientnet


def _pick_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class BrainAgeCheckpointLoader:
    """Load `state_dict` once; exposes `.get()` and `.is_available` like `ModelLoader`."""

    def __init__(self, checkpoint_path: Path):
        self.model_path = checkpoint_path
        self._model: Optional[Any] = None
        self._checked = False

    def get(self) -> Optional[Any]:
        if self._model is not None:
            return self._model
        if self._checked:
            return None
        self._checked = True
        if not self.model_path.exists():
            return None
        try:
            model = build_brain_age_efficientnet()
            try:
                state = torch.load(self.model_path, map_location="cpu", weights_only=True)
            except TypeError:
                state = torch.load(self.model_path, map_location="cpu")
            model.load_state_dict(state)
            device = _pick_device()
            model.to(device)
            model.eval()
            self._model = model
        except Exception:
            self._model = None
        return self._model

    @property
    def is_available(self) -> bool:
        return self.get() is not None
