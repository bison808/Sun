"""
Long-Term LSTM-FCN Model for Solar Cycle Prediction
Predicts cycle amplitude, peak timing, and duration
Combines LSTM and Fully Convolutional Network architectures
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict
import numpy as np


class ConvBlock(nn.Module):
    """Convolutional block for FCN"""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int):
        super(ConvBlock, self).__init__()

        self.conv = nn.Conv1d(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            padding=kernel_size // 2,
            bias=False
        )
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, channels, length)
        Returns:
            out: (batch, out_channels, length)
        """
        out = self.conv(x)
        out = self.bn(out)
        out = self.relu(out)
        return out


class FCNEncoder(nn.Module):
    """Fully Convolutional Network encoder"""

    def __init__(self,
                 input_size: int,
                 filters: list = [128, 256, 128],
                 kernel_sizes: list = [8, 5, 3]):
        """
        Args:
            input_size: Number of input features
            filters: List of filter sizes for each conv block
            kernel_sizes: List of kernel sizes for each conv block
        """
        super(FCNEncoder, self).__init__()

        self.blocks = nn.ModuleList()

        in_channels = input_size
        for out_channels, kernel_size in zip(filters, kernel_sizes):
            self.blocks.append(ConvBlock(in_channels, out_channels, kernel_size))
            in_channels = out_channels

        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.output_size = filters[-1]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, length, features)
        Returns:
            out: (batch, filters[-1])
        """
        # Transpose for conv1d: (batch, features, length)
        x = x.transpose(1, 2)

        # Apply conv blocks
        for block in self.blocks:
            x = block(x)

        # Global average pooling
        x = self.global_pool(x).squeeze(-1)  # (batch, filters[-1])

        return x


class LongTermLSTM_FCN(nn.Module):
    """
    Hybrid LSTM-FCN for long-term solar cycle prediction

    Combines:
    - LSTM: Captures sequential dependencies
    - FCN: Captures local patterns and features
    - Multi-task output: Predicts multiple cycle characteristics
    """

    def __init__(self,
                 input_size: int,
                 lstm_hidden: int = 256,
                 fcn_filters: list = [128, 256, 128],
                 fcn_kernels: list = [8, 5, 3],
                 dropout: float = 0.3,
                 num_outputs: int = 4):
        """
        Args:
            input_size: Number of input features
            lstm_hidden: LSTM hidden size
            fcn_filters: FCN filter sizes
            fcn_kernels: FCN kernel sizes
            dropout: Dropout probability
            num_outputs: Number of prediction targets
                (cycle_amplitude, peak_time, duration, ascent_rate)
        """
        super(LongTermLSTM_FCN, self).__init__()

        self.input_size = input_size
        self.lstm_hidden = lstm_hidden
        self.num_outputs = num_outputs

        # LSTM branch
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=lstm_hidden,
            num_layers=2,
            batch_first=True,
            dropout=dropout,
            bidirectional=True
        )

        # FCN branch
        self.fcn = FCNEncoder(
            input_size=input_size,
            filters=fcn_filters,
            kernel_sizes=fcn_kernels
        )

        # Combined feature size
        combined_size = lstm_hidden * 2 + fcn_filters[-1]  # *2 for bidirectional

        # Fusion layer
        self.fusion = nn.Sequential(
            nn.Linear(combined_size, 512),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # Multi-task output heads
        self.amplitude_head = nn.Linear(256, 1)
        self.peak_time_head = nn.Linear(256, 1)
        self.duration_head = nn.Linear(256, 1)
        self.ascent_rate_head = nn.Linear(256, 1)

        # Uncertainty heads (one for each output)
        self.amplitude_uncertainty = nn.Linear(256, 1)
        self.peak_time_uncertainty = nn.Linear(256, 1)
        self.duration_uncertainty = nn.Linear(256, 1)
        self.ascent_rate_uncertainty = nn.Linear(256, 1)

    def forward(self, x: torch.Tensor) -> Tuple[Dict[str, torch.Tensor], Dict[str, torch.Tensor]]:
        """
        Forward pass

        Args:
            x: Input tensor (batch, seq_len, features)

        Returns:
            predictions: Dict with keys:
                - amplitude: Cycle amplitude
                - peak_time: Time to peak (months)
                - duration: Cycle duration (months)
                - ascent_rate: Ascending phase rate
            uncertainties: Dict with log variances for each prediction
        """
        # LSTM branch
        lstm_out, (h_n, c_n) = self.lstm(x)
        # Use last hidden state from both directions
        lstm_features = torch.cat([h_n[-2], h_n[-1]], dim=1)  # (batch, lstm_hidden*2)

        # FCN branch
        fcn_features = self.fcn(x)  # (batch, fcn_filters[-1])

        # Concatenate features
        combined = torch.cat([lstm_features, fcn_features], dim=1)

        # Fusion
        fused = self.fusion(combined)  # (batch, 256)

        # Multi-task predictions
        predictions = {
            'amplitude': self.amplitude_head(fused).squeeze(-1),
            'peak_time': self.peak_time_head(fused).squeeze(-1),
            'duration': self.duration_head(fused).squeeze(-1),
            'ascent_rate': self.ascent_rate_head(fused).squeeze(-1)
        }

        # Uncertainties
        uncertainties = {
            'amplitude': self.amplitude_uncertainty(fused).squeeze(-1),
            'peak_time': self.peak_time_uncertainty(fused).squeeze(-1),
            'duration': self.duration_uncertainty(fused).squeeze(-1),
            'ascent_rate': self.ascent_rate_uncertainty(fused).squeeze(-1)
        }

        return predictions, uncertainties

    def predict_with_bayesian_uncertainty(self,
                                          x: torch.Tensor,
                                          n_samples: int = 50) -> Dict[str, np.ndarray]:
        """
        Bayesian uncertainty estimation using MC Dropout

        Args:
            x: Input tensor
            n_samples: Number of MC samples

        Returns:
            Dictionary with mean, std, and quantiles for each target
        """
        self.train()  # Enable dropout

        samples = {
            'amplitude': [],
            'peak_time': [],
            'duration': [],
            'ascent_rate': []
        }

        with torch.no_grad():
            for _ in range(n_samples):
                preds, _ = self.forward(x)
                for key in samples.keys():
                    samples[key].append(preds[key].cpu().numpy())

        results = {}
        for key in samples.keys():
            samples_array = np.array(samples[key])  # (n_samples, batch)

            results[key] = {
                'mean': np.mean(samples_array, axis=0),
                'std': np.std(samples_array, axis=0),
                'q05': np.percentile(samples_array, 5, axis=0),
                'q25': np.percentile(samples_array, 25, axis=0),
                'q50': np.percentile(samples_array, 50, axis=0),
                'q75': np.percentile(samples_array, 75, axis=0),
                'q95': np.percentile(samples_array, 95, axis=0)
            }

        return results


class MultiTaskLoss(nn.Module):
    """
    Multi-task loss with uncertainty weighting
    Learns task-specific weights automatically
    """

    def __init__(self, num_tasks: int = 4):
        super(MultiTaskLoss, self).__init__()
        # Learnable log variance for each task
        self.log_vars = nn.Parameter(torch.zeros(num_tasks))

    def forward(self,
                predictions: Dict[str, torch.Tensor],
                targets: Dict[str, torch.Tensor]) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Args:
            predictions: Dictionary of predictions
            targets: Dictionary of target values

        Returns:
            total_loss: Combined loss
            individual_losses: Dictionary of individual task losses
        """
        task_names = ['amplitude', 'peak_time', 'duration', 'ascent_rate']

        losses = {}
        total_loss = 0

        for i, task_name in enumerate(task_names):
            if task_name in predictions and task_name in targets:
                # MSE loss for each task
                mse_loss = F.mse_loss(predictions[task_name], targets[task_name])

                # Uncertainty-weighted loss
                precision = torch.exp(-self.log_vars[i])
                weighted_loss = precision * mse_loss + self.log_vars[i]

                losses[task_name] = mse_loss.item()
                total_loss += weighted_loss

        return total_loss, losses


def create_long_term_model(config: dict) -> LongTermLSTM_FCN:
    """
    Factory function to create model from config

    Args:
        config: Configuration dictionary

    Returns:
        LongTermLSTM_FCN model instance
    """
    model_config = config['long_term_lstm_fcn']

    model = LongTermLSTM_FCN(
        input_size=20,  # Will be set during training
        lstm_hidden=model_config['architecture']['lstm_units'],
        fcn_filters=model_config['architecture']['fcn_filters'],
        fcn_kernels=model_config['architecture']['kernel_sizes'],
        dropout=model_config['architecture']['dropout'],
        num_outputs=len(model_config['targets'])
    )

    return model


if __name__ == "__main__":
    # Test model
    print("Testing Long-Term LSTM-FCN Model")
    print("=" * 60)

    # Create model
    model = LongTermLSTM_FCN(
        input_size=20,
        lstm_hidden=256,
        fcn_filters=[128, 256, 128],
        fcn_kernels=[8, 5, 3],
        dropout=0.3,
        num_outputs=4
    )

    # Print model
    print(model)
    print("\nModel Parameters:")
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Test forward pass
    batch_size = 4
    seq_len = 264  # 22 years of monthly data
    input_size = 20

    dummy_input = torch.randn(batch_size, seq_len, input_size)
    print(f"\nInput shape: {dummy_input.shape}")

    predictions, uncertainties = model(dummy_input)

    print("\nPredictions:")
    for key, value in predictions.items():
        print(f"  {key}: {value.shape}")

    print("\nUncertainties:")
    for key, value in uncertainties.items():
        print(f"  {key}: {value.shape}")

    # Test Bayesian uncertainty
    results = model.predict_with_bayesian_uncertainty(dummy_input, n_samples=10)
    print("\nBayesian Uncertainty Results:")
    for key, stats in results.items():
        print(f"  {key}:")
        print(f"    Mean shape: {stats['mean'].shape}")
        print(f"    Std shape: {stats['std'].shape}")

    print("\n✓ Model test completed successfully!")
