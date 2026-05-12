"""EfficientNet-B0 regression head matching `best_ref_b_dropout03_lr5e5.pth` (dropout 0.3 + linear)."""
from __future__ import annotations

import torch.nn as nn
from torchvision import models
from torchvision.models import EfficientNet_B0_Weights


def build_brain_age_efficientnet() -> nn.Module:
    """ImageNet-init backbone; classifier block matches refinement-B checkpoint."""
    model = models.efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Sequential(
        nn.Dropout(p=0.3, inplace=False),
        nn.Linear(in_features, 1),
    )
    return model
