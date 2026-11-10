"""Inference architectures from notebook cells 68 and 76."""
from torch import nn


class Fast3DCNN(nn.Module):
    def __init__(self, hidden=8, dropout=0.4):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv3d(1, 8, 3, padding=1), nn.BatchNorm3d(8), nn.ReLU(), nn.MaxPool3d(2),
            nn.Conv3d(8, 16, 3, padding=1), nn.BatchNorm3d(16), nn.ReLU(), nn.MaxPool3d(2),
            nn.Dropout3d(dropout), nn.AdaptiveAvgPool3d(1),
        )
        self.classifier = nn.Sequential(
            nn.Linear(16, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, 2),
        )

    def forward(self, x):
        return self.classifier(self.features(x).flatten(1))


class Strong3DCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv3d(1, 16, 3, padding=1), nn.BatchNorm3d(16), nn.ReLU(), nn.MaxPool3d(2),
            nn.Conv3d(16, 32, 3, padding=1), nn.BatchNorm3d(32), nn.ReLU(), nn.MaxPool3d(2),
            nn.Conv3d(32, 64, 3, padding=1), nn.BatchNorm3d(64), nn.ReLU(), nn.MaxPool3d(2),
            nn.Dropout3d(0.35), nn.AdaptiveAvgPool3d(1),
        )
        self.classifier = nn.Sequential(
            nn.Linear(64, 32), nn.ReLU(), nn.Dropout(0.5), nn.Linear(32, 2),
        )

    def forward(self, x):
        return self.classifier(self.features(x).flatten(1))


class SessionFast3DCNN(nn.Module):
    """Three-block Stage 1 variant preserved in the Kaggle session snapshot."""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv3d(1, 8, 3, padding=1), nn.BatchNorm3d(8), nn.ReLU(), nn.MaxPool3d(2),
            nn.Conv3d(8, 16, 3, padding=1), nn.BatchNorm3d(16), nn.ReLU(), nn.MaxPool3d(2),
            nn.Conv3d(16, 32, 3, padding=1), nn.BatchNorm3d(32), nn.ReLU(),
            nn.Dropout3d(0.35), nn.AdaptiveAvgPool3d(1),
        )
        self.classifier = nn.Sequential(
            nn.Linear(32, 16), nn.ReLU(), nn.Dropout(0.4), nn.Linear(16, 2),
        )

    def forward(self, x):
        return self.classifier(self.features(x).flatten(1))
