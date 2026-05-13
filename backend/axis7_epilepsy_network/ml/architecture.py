from __future__ import annotations

from collections import OrderedDict
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F


SHALLOW_ENCODER_CONFIGS = {
    "eeg": {
        "in_channels": 2,
        "hidden_channels": (32, 64),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": False,
    },
    "ecg": {
        "in_channels": 1,
        "hidden_channels": (16, 32),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": False,
    },
    "emg": {
        "in_channels": 1,
        "hidden_channels": (16, 32),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": False,
    },
    "mov": {
        "in_channels": 3,
        "hidden_channels": (16, 32),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": False,
    },
}

DEEP_ENCODER_CONFIGS = {
    "eeg": {
        "in_channels": 2,
        "hidden_channels": (32, 64, 96),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": True,
    },
    "ecg": {
        "in_channels": 1,
        "hidden_channels": (16, 32, 48),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": True,
    },
    "emg": {
        "in_channels": 1,
        "hidden_channels": (16, 32, 48),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": True,
    },
    "mov": {
        "in_channels": 3,
        "hidden_channels": (16, 32, 48),
        "embedding_dim": 64,
        "dropout": 0.35,
        "use_third_block": True,
    },
}


def clone_encoder_configs(configs: dict[str, dict[str, Any]], dropout: float | None = None) -> dict[str, dict[str, Any]]:
    cloned: dict[str, dict[str, Any]] = {}
    for name, config in configs.items():
        new_config = dict(config)
        if dropout is not None:
            new_config["dropout"] = float(dropout)
        cloned[name] = new_config
    return cloned


class ConvEncoder(nn.Module):
    def __init__(
        self,
        in_channels: int,
        hidden_channels: tuple[int, ...] = (32, 64),
        embedding_dim: int = 64,
        dropout: float = 0.35,
        use_third_block: bool = False,
    ) -> None:
        super().__init__()
        if len(hidden_channels) < 2:
            raise ValueError("ConvEncoder requires at least two convolution blocks.")

        c1, c2 = hidden_channels[:2]
        c3 = hidden_channels[2] if len(hidden_channels) > 2 else c2
        self.use_third_block = bool(use_third_block and len(hidden_channels) > 2)
        self.hidden_channels = tuple(hidden_channels)
        self.output_channels = c3 if self.use_third_block else c2

        self.conv1 = nn.Conv1d(in_channels, c1, kernel_size=7, padding=3)
        self.bn1 = nn.BatchNorm1d(c1)
        self.drop1 = nn.Dropout(dropout)
        self.pool1 = nn.MaxPool1d(kernel_size=2)

        self.conv2 = nn.Conv1d(c1, c2, kernel_size=5, padding=2)
        self.bn2 = nn.BatchNorm1d(c2)
        self.drop2 = nn.Dropout(dropout)
        self.pool2 = nn.MaxPool1d(kernel_size=2)

        if self.use_third_block:
            self.conv3 = nn.Conv1d(c2, c3, kernel_size=3, padding=1)
            self.bn3 = nn.BatchNorm1d(c3)
            self.drop3 = nn.Dropout(dropout)
            self.pool3 = nn.MaxPool1d(kernel_size=2)
        else:
            self.conv3 = None
            self.bn3 = None
            self.drop3 = None
            self.pool3 = None

        self.last_conv = self.conv3 if self.use_third_block else self.conv2
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.project = nn.Sequential(
            nn.Flatten(),
            nn.Linear(self.output_channels, embedding_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

    def encode_sequence(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.pool1(self.drop1(F.relu(self.bn1(self.conv1(x)))))
        features = F.relu(self.bn2(self.conv2(x)))
        x = self.pool2(self.drop2(features))
        if self.use_third_block and self.conv3 is not None and self.bn3 is not None and self.drop3 is not None and self.pool3 is not None:
            features = F.relu(self.bn3(self.conv3(x)))
            x = self.pool3(self.drop3(features))
        return x, features

    def forward(self, x: torch.Tensor, return_features: bool = False) -> torch.Tensor | tuple[torch.Tensor, torch.Tensor]:
        encoded_sequence, features = self.encode_sequence(x)
        embedding = self.project(self.global_pool(encoded_sequence))
        if return_features:
            return embedding, features
        return embedding


class BaseMultimodalModel(nn.Module):
    def __init__(self, encoder_configs: dict[str, dict[str, Any]], dropout: float = 0.35) -> None:
        super().__init__()
        self.encoder_configs = clone_encoder_configs(encoder_configs, dropout=dropout)
        self.modalities = ["eeg", "ecg", "emg", "mov"]
        self.eeg_encoder = ConvEncoder(**self.encoder_configs["eeg"])
        self.ecg_encoder = ConvEncoder(**self.encoder_configs["ecg"])
        self.emg_encoder = ConvEncoder(**self.encoder_configs["emg"])
        self.mov_encoder = ConvEncoder(**self.encoder_configs["mov"])
        self.embedding_dim = int(self.encoder_configs["eeg"]["embedding_dim"])

    def encode_modalities(
        self,
        batch: dict[str, torch.Tensor],
        return_eeg_features: bool = False,
    ) -> tuple[OrderedDict[str, torch.Tensor], torch.Tensor | None]:
        eeg_output = self.eeg_encoder(batch["eeg"], return_features=return_eeg_features)
        if return_eeg_features:
            eeg_embedding, eeg_features = eeg_output
        else:
            eeg_embedding = eeg_output
            eeg_features = None

        embeddings = OrderedDict(
            eeg=eeg_embedding,
            ecg=self.ecg_encoder(batch["ecg"]),
            emg=self.emg_encoder(batch["emg"]),
            mov=self.mov_encoder(batch["mov"]),
        )
        return embeddings, eeg_features


class BaselineFusionCNN(BaseMultimodalModel):
    def __init__(
        self,
        dropout: float = 0.35,
        classifier_hidden: int = 128,
        encoder_configs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        configs = encoder_configs or clone_encoder_configs(SHALLOW_ENCODER_CONFIGS, dropout=dropout)
        super().__init__(encoder_configs=configs, dropout=dropout)
        fusion_dim = self.embedding_dim * len(self.modalities)
        self.classifier = nn.Sequential(
            nn.Linear(fusion_dim, classifier_hidden),
            nn.BatchNorm1d(classifier_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_hidden, 1),
        )

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        return_embeddings: bool = False,
        return_eeg_features: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, OrderedDict[str, torch.Tensor], torch.Tensor | None]:
        embeddings, eeg_features = self.encode_modalities(batch, return_eeg_features=return_eeg_features)
        fused = torch.cat([embeddings[name] for name in self.modalities], dim=1)
        logits = self.classifier(fused).squeeze(1)
        if return_embeddings or return_eeg_features:
            return logits, embeddings, eeg_features
        return logits


class AttentionFusionCNN(BaseMultimodalModel):
    def __init__(
        self,
        dropout: float = 0.35,
        classifier_hidden: int = 128,
        encoder_configs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        configs = encoder_configs or clone_encoder_configs(SHALLOW_ENCODER_CONFIGS, dropout=dropout)
        super().__init__(encoder_configs=configs, dropout=dropout)
        fusion_dim = self.embedding_dim * len(self.modalities)
        self.attention = nn.Sequential(
            nn.Linear(self.embedding_dim, 32),
            nn.Tanh(),
            nn.Linear(32, 1),
        )
        self.classifier = nn.Sequential(
            nn.Linear(fusion_dim, classifier_hidden),
            nn.BatchNorm1d(classifier_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_hidden, 1),
        )

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        return_attention: bool = False,
        return_embeddings: bool = False,
        return_eeg_features: bool = False,
    ) -> torch.Tensor | tuple[Any, ...]:
        embeddings, eeg_features = self.encode_modalities(batch, return_eeg_features=return_eeg_features)
        stacked = torch.stack([embeddings[name] for name in self.modalities], dim=1)
        scores = self.attention(stacked).squeeze(-1)
        weights = torch.softmax(scores, dim=1)
        weighted_embeddings = (stacked * weights.unsqueeze(-1)).reshape(stacked.size(0), -1)
        logits = self.classifier(weighted_embeddings).squeeze(1)

        outputs: list[Any] = [logits]
        if return_attention:
            outputs.append(weights)
        if return_embeddings:
            outputs.append(embeddings)
        if return_eeg_features:
            outputs.append(eeg_features)
        if len(outputs) == 1:
            return outputs[0]
        return tuple(outputs)


class DeepAttentionFusionCNN(BaseMultimodalModel):
    def __init__(
        self,
        dropout: float = 0.35,
        classifier_hidden: int = 192,
        encoder_configs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        configs = encoder_configs or clone_encoder_configs(DEEP_ENCODER_CONFIGS, dropout=dropout)
        super().__init__(encoder_configs=configs, dropout=dropout)
        fusion_dim = self.embedding_dim * len(self.modalities)
        self.attention = nn.Sequential(
            nn.Linear(self.embedding_dim, 48),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(48, 1),
        )
        self.classifier = nn.Sequential(
            nn.Linear(fusion_dim, classifier_hidden),
            nn.BatchNorm1d(classifier_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_hidden, classifier_hidden // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_hidden // 2, 1),
        )

    def forward(
        self,
        batch: dict[str, torch.Tensor],
        return_attention: bool = False,
        return_embeddings: bool = False,
        return_eeg_features: bool = False,
    ) -> torch.Tensor | tuple[Any, ...]:
        embeddings, eeg_features = self.encode_modalities(batch, return_eeg_features=return_eeg_features)
        stacked = torch.stack([embeddings[name] for name in self.modalities], dim=1)
        scores = self.attention(stacked).squeeze(-1)
        weights = torch.softmax(scores, dim=1)
        weighted_embeddings = (stacked * weights.unsqueeze(-1)).reshape(stacked.size(0), -1)
        logits = self.classifier(weighted_embeddings).squeeze(1)

        outputs: list[Any] = [logits]
        if return_attention:
            outputs.append(weights)
        if return_embeddings:
            outputs.append(embeddings)
        if return_eeg_features:
            outputs.append(eeg_features)
        if len(outputs) == 1:
            return outputs[0]
        return tuple(outputs)


MODEL_REGISTRY = {
    "BaselineFusionCNN": BaselineFusionCNN,
    "AttentionFusionCNN": AttentionFusionCNN,
    "DeepAttentionFusionCNN": DeepAttentionFusionCNN,
}


def build_model_from_artifact(artifact: dict[str, Any]) -> nn.Module:
    model_class = str(artifact.get("model_class") or "AttentionFusionCNN")
    model_type = MODEL_REGISTRY.get(model_class)
    if model_type is None:
        raise ValueError(f"Unsupported Axis 7 model class: {model_class}")

    encoder_configs = artifact.get("encoder_configs")
    dropout = float(artifact.get("dropout", 0.35))
    classifier_hidden = artifact.get("classifier_hidden")

    kwargs: dict[str, Any] = {"dropout": dropout}
    if encoder_configs:
        kwargs["encoder_configs"] = encoder_configs
    if classifier_hidden is not None:
        kwargs["classifier_hidden"] = int(classifier_hidden)

    model = model_type(**kwargs)
    state_dict = artifact.get("model_state_dict")
    if state_dict is None:
        raise ValueError("Axis 7 artifact does not contain model_state_dict.")
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model
