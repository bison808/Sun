"""
Anomaly Detection Autoencoder for Solar Activity
Detects unusual patterns in solar activity data
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional
import numpy as np
from sklearn.metrics import roc_auc_score, precision_recall_curve


class AnomalyAutoencoder(nn.Module):
    """
    Autoencoder for anomaly detection in solar time series

    Architecture:
    - Encoder: Compresses input to low-dimensional latent representation
    - Decoder: Reconstructs input from latent representation
    - Anomaly Score: Based on reconstruction error
    """

    def __init__(self,
                 input_size: int,
                 encoder_layers: list = [64, 32, 16, 8],
                 latent_dim: int = 4,
                 activation: str = 'relu',
                 dropout: float = 0.1):
        """
        Args:
            input_size: Number of input features
            encoder_layers: List of encoder layer sizes
            latent_dim: Dimension of latent space
            activation: Activation function ('relu', 'tanh', 'elu')
            dropout: Dropout probability
        """
        super(AnomalyAutoencoder, self).__init__()

        self.input_size = input_size
        self.latent_dim = latent_dim

        # Activation function
        if activation == 'relu':
            self.activation = nn.ReLU()
        elif activation == 'tanh':
            self.activation = nn.Tanh()
        elif activation == 'elu':
            self.activation = nn.ELU()
        else:
            raise ValueError(f"Unknown activation: {activation}")

        # Encoder
        encoder_modules = []
        prev_size = input_size

        for layer_size in encoder_layers:
            encoder_modules.extend([
                nn.Linear(prev_size, layer_size),
                self.activation,
                nn.Dropout(dropout)
            ])
            prev_size = layer_size

        # Latent layer
        encoder_modules.append(nn.Linear(prev_size, latent_dim))

        self.encoder = nn.Sequential(*encoder_modules)

        # Decoder (mirror of encoder)
        decoder_modules = []
        decoder_layers = list(reversed(encoder_layers))
        prev_size = latent_dim

        for layer_size in decoder_layers:
            decoder_modules.extend([
                nn.Linear(prev_size, layer_size),
                self.activation,
                nn.Dropout(dropout)
            ])
            prev_size = layer_size

        # Output layer (reconstruction)
        decoder_modules.extend([
            nn.Linear(prev_size, input_size),
            nn.Sigmoid()  # Normalize output to [0, 1]
        ])

        self.decoder = nn.Sequential(*decoder_modules)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode input to latent representation

        Args:
            x: Input tensor (batch, input_size)

        Returns:
            z: Latent representation (batch, latent_dim)
        """
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Decode latent representation to reconstruction

        Args:
            z: Latent tensor (batch, latent_dim)

        Returns:
            x_recon: Reconstructed input (batch, input_size)
        """
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass

        Args:
            x: Input tensor (batch, input_size)

        Returns:
            x_recon: Reconstructed input
            z: Latent representation
        """
        z = self.encode(x)
        x_recon = self.decode(z)
        return x_recon, z

    def compute_reconstruction_error(self,
                                     x: torch.Tensor,
                                     reduction: str = 'mean') -> torch.Tensor:
        """
        Compute reconstruction error (MSE)

        Args:
            x: Input tensor
            reduction: 'mean', 'sum', or 'none'

        Returns:
            error: Reconstruction error
        """
        x_recon, _ = self.forward(x)

        if reduction == 'none':
            # Per-sample error
            error = torch.mean((x - x_recon) ** 2, dim=1)
        elif reduction == 'mean':
            error = F.mse_loss(x_recon, x, reduction='mean')
        elif reduction == 'sum':
            error = F.mse_loss(x_recon, x, reduction='sum')
        else:
            raise ValueError(f"Unknown reduction: {reduction}")

        return error

    def compute_anomaly_score(self,
                             x: torch.Tensor,
                             normalize: bool = True) -> np.ndarray:
        """
        Compute anomaly scores for input samples

        Args:
            x: Input tensor (batch, input_size)
            normalize: Normalize scores to [0, 1]

        Returns:
            scores: Anomaly scores (higher = more anomalous)
        """
        self.eval()

        with torch.no_grad():
            # Reconstruction error
            errors = self.compute_reconstruction_error(x, reduction='none')
            scores = errors.cpu().numpy()

            if normalize:
                # Normalize to [0, 1] using min-max scaling
                scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)

        return scores

    def detect_anomalies(self,
                        x: torch.Tensor,
                        threshold: float = 0.75) -> Tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies based on threshold

        Args:
            x: Input tensor
            threshold: Anomaly score threshold (0-1)

        Returns:
            is_anomaly: Boolean array indicating anomalies
            scores: Anomaly scores
        """
        scores = self.compute_anomaly_score(x, normalize=True)
        is_anomaly = scores > threshold

        return is_anomaly, scores


class VariationalAutoencoder(nn.Module):
    """
    Variational Autoencoder (VAE) for anomaly detection
    Uses probabilistic latent representation
    """

    def __init__(self,
                 input_size: int,
                 encoder_layers: list = [64, 32, 16],
                 latent_dim: int = 4,
                 activation: str = 'relu'):
        """
        Args:
            input_size: Number of input features
            encoder_layers: List of encoder layer sizes
            latent_dim: Dimension of latent space
            activation: Activation function
        """
        super(VariationalAutoencoder, self).__init__()

        self.input_size = input_size
        self.latent_dim = latent_dim

        # Activation
        if activation == 'relu':
            self.activation = nn.ReLU()
        elif activation == 'tanh':
            self.activation = nn.Tanh()
        else:
            self.activation = nn.ELU()

        # Encoder
        encoder_modules = []
        prev_size = input_size

        for layer_size in encoder_layers:
            encoder_modules.extend([
                nn.Linear(prev_size, layer_size),
                self.activation
            ])
            prev_size = layer_size

        self.encoder = nn.Sequential(*encoder_modules)

        # Latent parameters
        self.fc_mu = nn.Linear(prev_size, latent_dim)
        self.fc_logvar = nn.Linear(prev_size, latent_dim)

        # Decoder
        decoder_modules = []
        decoder_layers = list(reversed(encoder_layers))
        prev_size = latent_dim

        for layer_size in decoder_layers:
            decoder_modules.extend([
                nn.Linear(prev_size, layer_size),
                self.activation
            ])
            prev_size = layer_size

        decoder_modules.extend([
            nn.Linear(prev_size, input_size),
            nn.Sigmoid()
        ])

        self.decoder = nn.Sequential(*decoder_modules)

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Encode to latent distribution parameters

        Returns:
            mu: Mean of latent distribution
            logvar: Log variance of latent distribution
        """
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """
        Reparameterization trick for sampling

        Args:
            mu: Mean
            logvar: Log variance

        Returns:
            z: Sampled latent vector
        """
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + eps * std
        return z

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent to reconstruction"""
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass

        Returns:
            x_recon: Reconstructed input
            mu: Latent mean
            logvar: Latent log variance
        """
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decode(z)
        return x_recon, mu, logvar

    def compute_vae_loss(self,
                        x: torch.Tensor,
                        x_recon: torch.Tensor,
                        mu: torch.Tensor,
                        logvar: torch.Tensor,
                        beta: float = 1.0) -> torch.Tensor:
        """
        Compute VAE loss (ELBO)

        Args:
            x: Original input
            x_recon: Reconstructed input
            mu: Latent mean
            logvar: Latent log variance
            beta: Weight for KL divergence term

        Returns:
            loss: Total VAE loss
        """
        # Reconstruction loss
        recon_loss = F.mse_loss(x_recon, x, reduction='sum')

        # KL divergence
        kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())

        # Total loss
        total_loss = recon_loss + beta * kl_loss

        return total_loss

    def compute_anomaly_score(self,
                             x: torch.Tensor,
                             n_samples: int = 10) -> np.ndarray:
        """
        Compute anomaly score using reconstruction probability

        Args:
            x: Input tensor
            n_samples: Number of samples for Monte Carlo estimation

        Returns:
            scores: Anomaly scores
        """
        self.eval()

        with torch.no_grad():
            mu, logvar = self.encode(x)

            # Sample multiple reconstructions
            recon_errors = []
            for _ in range(n_samples):
                z = self.reparameterize(mu, logvar)
                x_recon = self.decode(z)
                error = torch.mean((x - x_recon) ** 2, dim=1)
                recon_errors.append(error)

            # Average reconstruction error
            scores = torch.stack(recon_errors).mean(dim=0)
            scores = scores.cpu().numpy()

            # Normalize
            scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)

        return scores


def create_anomaly_model(config: dict, variational: bool = False):
    """
    Factory function to create anomaly detection model

    Args:
        config: Configuration dictionary
        variational: Use VAE instead of standard autoencoder

    Returns:
        Model instance
    """
    model_config = config['anomaly_autoencoder']

    if variational:
        model = VariationalAutoencoder(
            input_size=20,  # Will be set during training
            encoder_layers=model_config['architecture']['encoder_layers'],
            latent_dim=model_config['architecture']['latent_dim'],
            activation=model_config['architecture']['activation']
        )
    else:
        model = AnomalyAutoencoder(
            input_size=20,
            encoder_layers=model_config['architecture']['encoder_layers'],
            latent_dim=model_config['architecture']['latent_dim'],
            activation=model_config['architecture']['activation'],
            dropout=0.1
        )

    return model


if __name__ == "__main__":
    # Test models
    print("Testing Anomaly Detection Models")
    print("=" * 60)

    # Standard Autoencoder
    print("\n1. Standard Autoencoder")
    model_ae = AnomalyAutoencoder(
        input_size=20,
        encoder_layers=[64, 32, 16, 8],
        latent_dim=4,
        activation='relu',
        dropout=0.1
    )

    print(f"Total parameters: {sum(p.numel() for p in model_ae.parameters()):,}")

    # Test forward pass
    batch_size = 32
    input_size = 20
    dummy_input = torch.randn(batch_size, input_size)

    x_recon, z = model_ae(dummy_input)
    print(f"Input shape: {dummy_input.shape}")
    print(f"Reconstruction shape: {x_recon.shape}")
    print(f"Latent shape: {z.shape}")

    # Test anomaly detection
    scores = model_ae.compute_anomaly_score(dummy_input)
    print(f"Anomaly scores shape: {scores.shape}")
    print(f"Score range: [{scores.min():.4f}, {scores.max():.4f}]")

    is_anomaly, _ = model_ae.detect_anomalies(dummy_input, threshold=0.75)
    print(f"Detected anomalies: {is_anomaly.sum()} / {len(is_anomaly)}")

    # VAE
    print("\n2. Variational Autoencoder")
    model_vae = VariationalAutoencoder(
        input_size=20,
        encoder_layers=[64, 32, 16],
        latent_dim=4,
        activation='relu'
    )

    print(f"Total parameters: {sum(p.numel() for p in model_vae.parameters()):,}")

    x_recon, mu, logvar = model_vae(dummy_input)
    print(f"Reconstruction shape: {x_recon.shape}")
    print(f"Mu shape: {mu.shape}")
    print(f"Logvar shape: {logvar.shape}")

    # Test VAE loss
    loss = model_vae.compute_vae_loss(dummy_input, x_recon, mu, logvar)
    print(f"VAE Loss: {loss.item():.4f}")

    # VAE anomaly scores
    vae_scores = model_vae.compute_anomaly_score(dummy_input, n_samples=10)
    print(f"VAE anomaly scores: [{vae_scores.min():.4f}, {vae_scores.max():.4f}]")

    print("\n✓ Model tests completed successfully!")
