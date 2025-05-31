from typing import Dict

from gymnasium import spaces
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from torch import nn
import torch

from src.utils.config import config


class CustomCombinedExtractor(BaseFeaturesExtractor):
    def __init__(self, observation_space: spaces.Dict):
        super().__init__(observation_space, features_dim=1)  # Temporary dummy value

        # CNN for images
        self.cnn = nn.Sequential(
            nn.Conv2d(config.C, 8, kernel_size=1, stride=1, padding="same"),
            nn.ReLU(),
            nn.Conv2d(8, 32, kernel_size=3, stride=1, padding="same"),
            nn.ReLU(),
            nn.Conv2d(32, 4, kernel_size=5, stride=1, padding="same"),
            nn.ReLU(),
            nn.Flatten(),
        )

        # Compute CNN output dimension
        with torch.no_grad():
            sample_img = torch.as_tensor(observation_space["grid"].sample()[None]).float()
            cnn_output_dim = self.cnn(sample_img).shape[1]

        # FCN for vectors
        out_features = 32
        self.vector_fc = nn.Sequential(
            nn.Linear(observation_space["side"].shape[0], out_features),
            nn.ReLU(),
        )

        # Update features_dim
        self._features_dim = cnn_output_dim + out_features

    def forward(self, observations: Dict[str, torch.Tensor]) -> torch.Tensor:
        image_features = observations["grid"]
        vector_features = observations["side"]

        if vector_features.dim() == 1:
            image_features = image_features.unsqueeze(0)
            vector_features = vector_features.unsqueeze(0)

        image_features = self.cnn(image_features)
        vector_features = self.vector_fc(vector_features)

        return torch.cat([image_features, vector_features], dim=1)
