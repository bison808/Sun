"""
Short-Term LSTM Model for Solar Activity Prediction
Predicts 1-90 day sunspot numbers with confidence intervals
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional
import numpy as np


class AttentionLayer(nn.Module):
    """Attention mechanism for LSTM outputs"""

    def __init__(self, hidden_size: int):
        super(AttentionLayer, self).__init__()
        self.attention = nn.Linear(hidden_size, 1)

    def forward(self, lstm_output: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            lstm_output: (batch_size, seq_len, hidden_size)

        Returns:
            context: (batch_size, hidden_size)
            attention_weights: (batch_size, seq_len)
        """
        # Calculate attention scores
        scores = self.attention(lstm_output)  # (batch, seq_len, 1)
        attention_weights = F.softmax(scores.squeeze(-1), dim=1)  # (batch, seq_len)

        # Apply attention weights
        context = torch.bmm(
            attention_weights.unsqueeze(1),  # (batch, 1, seq_len)
            lstm_output  # (batch, seq_len, hidden)
        ).squeeze(1)  # (batch, hidden)

        return context, attention_weights


class ShortTermLSTM(nn.Module):
    """
    Bidirectional LSTM with Attention for short-term solar prediction

    Architecture:
    - Input: (batch, sequence_length, num_features)
    - Bidirectional LSTM layers
    - Attention mechanism
    - Dense layers
    - Output: (batch, forecast_horizon) with uncertainty estimates
    """

    def __init__(self,
                 input_size: int,
                 hidden_sizes: list = [128, 64, 32],
                 output_size: int = 30,
                 dropout: float = 0.2,
                 bidirectional: bool = True,
                 use_attention: bool = True):
        """
        Args:
            input_size: Number of input features
            hidden_sizes: List of hidden layer sizes
            output_size: Forecast horizon (number of days to predict)
            dropout: Dropout probability
            bidirectional: Use bidirectional LSTM
            use_attention: Use attention mechanism
        """
        super(ShortTermLSTM, self).__init__()

        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.output_size = output_size
        self.dropout_prob = dropout
        self.bidirectional = bidirectional
        self.use_attention = use_attention
        self.num_directions = 2 if bidirectional else 1

        # LSTM layers
        self.lstm_layers = nn.ModuleList()
        current_input_size = input_size

        for hidden_size in hidden_sizes:
            self.lstm_layers.append(
                nn.LSTM(
                    input_size=current_input_size,
                    hidden_size=hidden_size,
                    num_layers=1,
                    batch_first=True,
                    dropout=0,  # We'll add dropout separately
                    bidirectional=bidirectional
                )
            )
            current_input_size = hidden_size * self.num_directions

        # Dropout
        self.dropout = nn.Dropout(dropout)

        # Attention
        if use_attention:
            self.attention = AttentionLayer(hidden_sizes[-1] * self.num_directions)

        # Output layers for point prediction
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_sizes[-1] * self.num_directions, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, output_size)
        )

        # Additional output for uncertainty estimation
        # Predicts log variance for each prediction
        self.uncertainty_head = nn.Sequential(
            nn.Linear(hidden_sizes[-1] * self.num_directions, 64),
            nn.ReLU(),
            nn.Linear(64, output_size)
        )

    def forward(self,
                x: torch.Tensor,
                return_attention: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass

        Args:
            x: Input tensor (batch_size, seq_len, input_size)
            return_attention: Whether to return attention weights

        Returns:
            predictions: (batch_size, output_size)
            log_var: (batch_size, output_size) - log variance for uncertainty
            attention_weights: (batch_size, seq_len) if return_attention=True
        """
        # Pass through LSTM layers
        h = x
        for lstm in self.lstm_layers:
            h, _ = lstm(h)
            h = self.dropout(h)

        # Apply attention or use last hidden state
        if self.use_attention:
            context, attention_weights = self.attention(h)
        else:
            context = h[:, -1, :]  # Last time step
            attention_weights = None

        # Predictions
        predictions = self.fc_layers(context)

        # Uncertainty estimation
        log_var = self.uncertainty_head(context)

        if return_attention and attention_weights is not None:
            return predictions, log_var, attention_weights
        else:
            return predictions, log_var

    def predict_with_uncertainty(self,
                                 x: torch.Tensor,
                                 n_samples: int = 10) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Make predictions with uncertainty estimates using Monte Carlo dropout

        Args:
            x: Input tensor (batch_size, seq_len, input_size)
            n_samples: Number of MC dropout samples

        Returns:
            mean: Mean predictions (batch_size, output_size)
            std: Standard deviation (batch_size, output_size)
            quantiles: Dictionary of quantiles (e.g., 5%, 95%)
        """
        self.train()  # Enable dropout for MC sampling

        predictions = []
        log_vars = []

        with torch.no_grad():
            for _ in range(n_samples):
                pred, log_var = self.forward(x)
                predictions.append(pred.cpu().numpy())
                log_vars.append(log_var.cpu().numpy())

        predictions = np.array(predictions)  # (n_samples, batch, output_size)

        # Calculate statistics
        mean = np.mean(predictions, axis=0)
        epistemic_std = np.std(predictions, axis=0)  # Model uncertainty

        # Aleatoric uncertainty from predicted variance
        aleatoric_var = np.exp(np.mean(log_vars, axis=0))
        aleatoric_std = np.sqrt(aleatoric_var)

        # Total uncertainty
        total_std = np.sqrt(epistemic_std**2 + aleatoric_std**2)

        # Calculate quantiles
        quantiles = {
            'q05': np.percentile(predictions, 5, axis=0),
            'q25': np.percentile(predictions, 25, axis=0),
            'q50': np.percentile(predictions, 50, axis=0),
            'q75': np.percentile(predictions, 75, axis=0),
            'q95': np.percentile(predictions, 95, axis=0),
        }

        return mean, total_std, quantiles


class GaussianNLLLoss(nn.Module):
    """
    Gaussian Negative Log-Likelihood Loss
    Learns both mean and variance predictions
    """

    def __init__(self):
        super(GaussianNLLLoss, self).__init__()

    def forward(self,
                predictions: torch.Tensor,
                log_var: torch.Tensor,
                targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            predictions: Predicted means (batch, output_size)
            log_var: Predicted log variances (batch, output_size)
            targets: True values (batch, output_size)

        Returns:
            loss: Scalar loss value
        """
        # Gaussian NLL: 0.5 * (log(var) + (y - mu)^2 / var)
        var = torch.exp(log_var)
        loss = 0.5 * (log_var + ((targets - predictions) ** 2) / var)

        return loss.mean()


def create_short_term_model(config: dict) -> ShortTermLSTM:
    """
    Factory function to create model from config

    Args:
        config: Configuration dictionary

    Returns:
        ShortTermLSTM model instance
    """
    model_config = config['short_term_lstm']

    # Determine input size (will be set during training based on features)
    # This is a placeholder - actual value set in training script
    input_size = 20  # Will be overridden

    model = ShortTermLSTM(
        input_size=input_size,
        hidden_sizes=model_config['architecture']['lstm_layers'],
        output_size=model_config['architecture']['output_horizon'],
        dropout=model_config['architecture']['dropout'],
        bidirectional=model_config['architecture']['bidirectional'],
        use_attention=model_config['architecture']['attention']
    )

    return model


if __name__ == "__main__":
    # Test model
    print("Testing Short-Term LSTM Model")
    print("=" * 60)

    # Create dummy model
    model = ShortTermLSTM(
        input_size=20,
        hidden_sizes=[128, 64, 32],
        output_size=30,
        dropout=0.2,
        bidirectional=True,
        use_attention=True
    )

    # Print model architecture
    print(model)
    print("\nModel Parameters:")
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Test forward pass
    batch_size = 4
    seq_len = 90
    input_size = 20

    dummy_input = torch.randn(batch_size, seq_len, input_size)

    print(f"\nInput shape: {dummy_input.shape}")

    predictions, log_var = model(dummy_input)
    print(f"Predictions shape: {predictions.shape}")
    print(f"Log variance shape: {log_var.shape}")

    # Test uncertainty prediction
    mean, std, quantiles = model.predict_with_uncertainty(dummy_input, n_samples=10)
    print(f"\nUncertainty estimation:")
    print(f"Mean shape: {mean.shape}")
    print(f"Std shape: {std.shape}")
    print(f"Quantiles available: {list(quantiles.keys())}")

    print("\n✓ Model test completed successfully!")
