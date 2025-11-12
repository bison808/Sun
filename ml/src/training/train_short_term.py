"""
Training script for Short-Term LSTM model
Includes MLflow tracking, early stopping, and checkpointing
"""

import os
import sys
import yaml
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from pathlib import Path
import mlflow
import mlflow.pytorch
from typing import Dict, Tuple
import logging
from tqdm import tqdm

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models.short_term_lstm import ShortTermLSTM, GaussianNLLLoss
from data.feature_engineering import SolarFeatureEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SolarTimeSeriesDataset(Dataset):
    """PyTorch Dataset for solar time series"""

    def __init__(self,
                 features: np.ndarray,
                 targets: np.ndarray,
                 window_size: int,
                 horizon: int):
        """
        Args:
            features: Feature array (n_samples, n_features)
            targets: Target array (n_samples,)
            window_size: Input sequence length
            horizon: Prediction horizon
        """
        self.features = torch.FloatTensor(features)
        self.targets = torch.FloatTensor(targets)
        self.window_size = window_size
        self.horizon = horizon

        # Create sequences
        self.X, self.y = self._create_sequences()

    def _create_sequences(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """Create sequences for LSTM"""
        X, y = [], []

        for i in range(len(self.features) - self.window_size - self.horizon + 1):
            X.append(self.features[i:i+self.window_size])
            y.append(self.targets[i+self.window_size:i+self.window_size+self.horizon])

        return torch.stack(X), torch.stack(y)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


class EarlyStopping:
    """Early stopping to prevent overfitting"""

    def __init__(self, patience: int = 15, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.early_stop = False

    def __call__(self, val_loss: float) -> bool:
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0

        return self.early_stop


class ShortTermTrainer:
    """Trainer for Short-Term LSTM model"""

    def __init__(self, config_path: str = "../../configs/config.yaml"):
        """Initialize trainer with configuration"""
        self.config = self._load_config(config_path)
        self.model_config = self.config['short_term_lstm']

        # Paths
        self.features_dir = Path(self.config['paths']['data_features'])
        self.models_dir = Path(self.config['paths']['models'])
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Device
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() and self.config['training']['gpu']['enabled']
            else 'cpu'
        )
        logger.info(f"Using device: {self.device}")

        # MLflow
        mlflow.set_tracking_uri(self.config['mlops']['experiment_tracking']['tracking_uri'])
        mlflow.set_experiment(self.model_config['name'])

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def load_data(self) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """Load and prepare data"""
        logger.info("Loading data...")

        # Load features
        features_path = self.features_dir / 'daily_features.csv'
        df = pd.read_csv(features_path, parse_dates=['date'])

        # Select feature columns (excluding date, target, etc.)
        feature_cols = [col for col in df.columns if col not in
                       ['date', 'ssn', 'year', 'month', 'day_of_year', 'cycle_number']]

        # Target column (normalized SSN)
        target_col = 'ssn_normalized'

        # Split data
        train_config = self.config['data_splits']['train']
        val_config = self.config['data_splits']['validation']
        test_config = self.config['data_splits']['test']

        train_mask = (df['year'] >= train_config['start']) & (df['year'] < train_config['end'])
        val_mask = (df['year'] >= val_config['start']) & (df['year'] < val_config['end'])
        test_mask = (df['year'] >= test_config['start']) & (df['year'] <= test_config['end'])

        # Create datasets
        window_size = self.model_config['architecture']['input_window']
        horizon = self.model_config['architecture']['output_horizon']
        batch_size = self.model_config['training']['batch_size']

        train_dataset = SolarTimeSeriesDataset(
            df[train_mask][feature_cols].values,
            df[train_mask][target_col].values,
            window_size,
            horizon
        )

        val_dataset = SolarTimeSeriesDataset(
            df[val_mask][feature_cols].values,
            df[val_mask][target_col].values,
            window_size,
            horizon
        )

        test_dataset = SolarTimeSeriesDataset(
            df[test_mask][feature_cols].values,
            df[test_mask][target_col].values,
            window_size,
            horizon
        )

        # Create dataloaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

        logger.info(f"Train samples: {len(train_dataset)}")
        logger.info(f"Val samples: {len(val_dataset)}")
        logger.info(f"Test samples: {len(test_dataset)}")
        logger.info(f"Features: {len(feature_cols)}")

        return train_loader, val_loader, test_loader, len(feature_cols)

    def create_model(self, input_size: int) -> ShortTermLSTM:
        """Create model instance"""
        model = ShortTermLSTM(
            input_size=input_size,
            hidden_sizes=self.model_config['architecture']['lstm_layers'],
            output_size=self.model_config['architecture']['output_horizon'],
            dropout=self.model_config['architecture']['dropout'],
            bidirectional=self.model_config['architecture']['bidirectional'],
            use_attention=self.model_config['architecture']['attention']
        ).to(self.device)

        return model

    def train_epoch(self,
                   model: nn.Module,
                   dataloader: DataLoader,
                   criterion: nn.Module,
                   optimizer: optim.Optimizer) -> Dict[str, float]:
        """Train for one epoch"""
        model.train()

        total_loss = 0
        total_mse = 0
        num_batches = 0

        pbar = tqdm(dataloader, desc="Training")

        for X_batch, y_batch in pbar:
            X_batch = X_batch.to(self.device)
            y_batch = y_batch.to(self.device)

            # Forward pass
            predictions, log_var = model(X_batch)

            # Loss
            loss = criterion(predictions, log_var, y_batch)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # Metrics
            total_loss += loss.item()
            with torch.no_grad():
                mse = torch.mean((predictions - y_batch) ** 2).item()
                total_mse += mse

            num_batches += 1

            # Update progress bar
            pbar.set_postfix({'loss': loss.item(), 'mse': mse})

        metrics = {
            'loss': total_loss / num_batches,
            'mse': total_mse / num_batches,
            'rmse': np.sqrt(total_mse / num_batches)
        }

        return metrics

    def validate(self,
                model: nn.Module,
                dataloader: DataLoader,
                criterion: nn.Module) -> Dict[str, float]:
        """Validate model"""
        model.eval()

        total_loss = 0
        total_mse = 0
        total_mae = 0
        num_batches = 0

        with torch.no_grad():
            for X_batch, y_batch in tqdm(dataloader, desc="Validation"):
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)

                # Forward pass
                predictions, log_var = model(X_batch)

                # Loss
                loss = criterion(predictions, log_var, y_batch)

                # Metrics
                total_loss += loss.item()
                mse = torch.mean((predictions - y_batch) ** 2).item()
                mae = torch.mean(torch.abs(predictions - y_batch)).item()

                total_mse += mse
                total_mae += mae
                num_batches += 1

        metrics = {
            'loss': total_loss / num_batches,
            'mse': total_mse / num_batches,
            'rmse': np.sqrt(total_mse / num_batches),
            'mae': total_mae / num_batches
        }

        return metrics

    def train(self):
        """Main training loop"""
        logger.info("=" * 60)
        logger.info("Training Short-Term LSTM")
        logger.info("=" * 60)

        # Start MLflow run
        with mlflow.start_run():
            # Log parameters
            mlflow.log_params({
                'model': 'short_term_lstm',
                'window_size': self.model_config['architecture']['input_window'],
                'horizon': self.model_config['architecture']['output_horizon'],
                'lstm_layers': str(self.model_config['architecture']['lstm_layers']),
                'dropout': self.model_config['architecture']['dropout'],
                'learning_rate': self.model_config['training']['learning_rate'],
                'batch_size': self.model_config['training']['batch_size']
            })

            # Load data
            train_loader, val_loader, test_loader, input_size = self.load_data()

            # Create model
            model = self.create_model(input_size)
            logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

            # Loss and optimizer
            criterion = GaussianNLLLoss()
            optimizer = optim.Adam(
                model.parameters(),
                lr=self.model_config['training']['learning_rate']
            )

            # Learning rate scheduler
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=self.model_config['training']['epochs']
            )

            # Early stopping
            early_stopping = EarlyStopping(
                patience=self.model_config['training']['early_stopping_patience']
            )

            # Training loop
            best_val_loss = float('inf')
            epochs = self.model_config['training']['epochs']

            for epoch in range(epochs):
                logger.info(f"\nEpoch {epoch+1}/{epochs}")

                # Train
                train_metrics = self.train_epoch(model, train_loader, criterion, optimizer)

                # Validate
                val_metrics = self.validate(model, val_loader, criterion)

                # Log metrics
                mlflow.log_metrics({
                    'train_loss': train_metrics['loss'],
                    'train_rmse': train_metrics['rmse'],
                    'val_loss': val_metrics['loss'],
                    'val_rmse': val_metrics['rmse'],
                    'val_mae': val_metrics['mae'],
                    'learning_rate': optimizer.param_groups[0]['lr']
                }, step=epoch)

                logger.info(f"Train Loss: {train_metrics['loss']:.4f}, RMSE: {train_metrics['rmse']:.4f}")
                logger.info(f"Val Loss: {val_metrics['loss']:.4f}, RMSE: {val_metrics['rmse']:.4f}")

                # Save best model
                if val_metrics['loss'] < best_val_loss:
                    best_val_loss = val_metrics['loss']
                    checkpoint_path = self.models_dir / 'short_term_lstm' / 'best_model.pth'
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

                    torch.save({
                        'epoch': epoch,
                        'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        'val_loss': val_metrics['loss'],
                        'config': self.model_config
                    }, checkpoint_path)

                    logger.info(f"Saved best model (val_loss: {val_metrics['loss']:.4f})")

                # Learning rate scheduler
                scheduler.step()

                # Early stopping
                if early_stopping(val_metrics['loss']):
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break

            # Test evaluation
            logger.info("\nEvaluating on test set...")
            test_metrics = self.validate(model, test_loader, criterion)

            logger.info(f"Test RMSE: {test_metrics['rmse']:.4f}")
            logger.info(f"Test MAE: {test_metrics['mae']:.4f}")

            mlflow.log_metrics({
                'test_rmse': test_metrics['rmse'],
                'test_mae': test_metrics['mae']
            })

            # Log model
            mlflow.pytorch.log_model(model, "model")

            logger.info("\n✓ Training completed!")


def main():
    """Main execution"""
    trainer = ShortTermTrainer()
    trainer.train()


if __name__ == "__main__":
    main()
