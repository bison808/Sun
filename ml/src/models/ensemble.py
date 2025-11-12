"""
Ensemble Meta-Learner for Solar Prediction
Combines predictions from multiple models
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque


class WeightedEnsemble(nn.Module):
    """
    Weighted ensemble that combines predictions from multiple models
    Weights can be learned or performance-based
    """

    def __init__(self,
                 num_models: int,
                 output_size: int,
                 method: str = 'learned'):
        """
        Args:
            num_models: Number of base models
            output_size: Size of prediction output
            method: 'learned', 'equal', or 'performance'
        """
        super(WeightedEnsemble, self).__init__()

        self.num_models = num_models
        self.output_size = output_size
        self.method = method

        if method == 'learned':
            # Learnable weights
            self.weights = nn.Parameter(torch.ones(num_models) / num_models)
        elif method == 'equal':
            # Equal weights (fixed)
            self.register_buffer('weights', torch.ones(num_models) / num_models)
        else:  # performance-based
            # Will be set dynamically during inference
            self.register_buffer('weights', torch.ones(num_models) / num_models)

    def forward(self, predictions: List[torch.Tensor]) -> torch.Tensor:
        """
        Combine predictions from multiple models

        Args:
            predictions: List of tensors (batch, output_size) from each model

        Returns:
            combined: Weighted combination (batch, output_size)
        """
        # Stack predictions
        stacked = torch.stack(predictions, dim=0)  # (num_models, batch, output_size)

        # Normalize weights with softmax
        normalized_weights = torch.softmax(self.weights, dim=0)

        # Weighted sum
        combined = torch.einsum('m,mbo->bo', normalized_weights, stacked)

        return combined

    def set_performance_weights(self, performance_scores: np.ndarray):
        """
        Set weights based on model performance

        Args:
            performance_scores: Array of performance scores (lower is better)
                Shape: (num_models,)
        """
        # Inverse weighting (better performance = higher weight)
        inverse_scores = 1.0 / (performance_scores + 1e-8)
        weights = inverse_scores / inverse_scores.sum()

        self.weights.data = torch.tensor(weights, dtype=torch.float32)


class StackingEnsemble(nn.Module):
    """
    Stacking ensemble with a meta-learner neural network
    Learns non-linear combinations of base model predictions
    """

    def __init__(self,
                 num_models: int,
                 output_size: int,
                 hidden_sizes: List[int] = [32, 16],
                 dropout: float = 0.2):
        """
        Args:
            num_models: Number of base models
            output_size: Size of prediction output
            hidden_sizes: Hidden layer sizes for meta-learner
            dropout: Dropout probability
        """
        super(StackingEnsemble, self).__init__()

        self.num_models = num_models
        self.output_size = output_size

        # Meta-learner network
        layers = []
        input_size = num_models * output_size

        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            input_size = hidden_size

        layers.append(nn.Linear(input_size, output_size))

        self.meta_learner = nn.Sequential(*layers)

    def forward(self, predictions: List[torch.Tensor]) -> torch.Tensor:
        """
        Combine predictions using meta-learner

        Args:
            predictions: List of tensors from each model

        Returns:
            combined: Meta-learned combination
        """
        # Concatenate all predictions
        concatenated = torch.cat(predictions, dim=-1)  # (batch, num_models * output_size)

        # Meta-learner
        combined = self.meta_learner(concatenated)

        return combined


class AdaptiveEnsemble:
    """
    Adaptive ensemble that adjusts weights based on recent performance
    Uses sliding window of performance metrics
    """

    def __init__(self,
                 num_models: int,
                 window_size: int = 90,
                 metric: str = 'rmse'):
        """
        Args:
            num_models: Number of base models
            window_size: Window size for performance calculation (days)
            metric: Performance metric ('rmse', 'mae', 'mape')
        """
        self.num_models = num_models
        self.window_size = window_size
        self.metric = metric

        # Track recent predictions and targets
        self.recent_predictions = [deque(maxlen=window_size) for _ in range(num_models)]
        self.recent_targets = deque(maxlen=window_size)

        # Current weights
        self.weights = np.ones(num_models) / num_models

    def add_observation(self,
                       predictions: List[np.ndarray],
                       target: np.ndarray):
        """
        Add new observation to history

        Args:
            predictions: List of predictions from each model
            target: True target value
        """
        for i, pred in enumerate(predictions):
            self.recent_predictions[i].append(pred)

        self.recent_targets.append(target)

        # Update weights if we have enough observations
        if len(self.recent_targets) >= min(30, self.window_size):
            self._update_weights()

    def _compute_metric(self, predictions: np.ndarray, targets: np.ndarray) -> float:
        """Compute performance metric"""
        if self.metric == 'rmse':
            return np.sqrt(np.mean((predictions - targets) ** 2))
        elif self.metric == 'mae':
            return np.mean(np.abs(predictions - targets))
        elif self.metric == 'mape':
            return np.mean(np.abs((predictions - targets) / (targets + 1e-8))) * 100
        else:
            return np.mean((predictions - targets) ** 2)

    def _update_weights(self):
        """Update weights based on recent performance"""
        if len(self.recent_targets) < 10:
            return

        # Calculate performance for each model
        performance_scores = []

        targets = np.array(list(self.recent_targets))

        for model_preds in self.recent_predictions:
            preds = np.array(list(model_preds))
            score = self._compute_metric(preds, targets)
            performance_scores.append(score)

        performance_scores = np.array(performance_scores)

        # Inverse weighting (lower error = higher weight)
        inverse_scores = 1.0 / (performance_scores + 1e-8)
        self.weights = inverse_scores / inverse_scores.sum()

    def predict(self, predictions: List[np.ndarray]) -> np.ndarray:
        """
        Make weighted prediction

        Args:
            predictions: List of predictions from each model

        Returns:
            combined: Weighted combination
        """
        predictions_array = np.array(predictions)  # (num_models, ...)
        combined = np.average(predictions_array, axis=0, weights=self.weights)

        return combined

    def get_weights(self) -> Dict[int, float]:
        """Get current model weights"""
        return {i: weight for i, weight in enumerate(self.weights)}


class UncertaintyEnsemble:
    """
    Ensemble that combines predictions with uncertainty weighting
    Higher confidence predictions get more weight
    """

    def __init__(self,
                 num_models: int,
                 aggregation: str = 'conservative'):
        """
        Args:
            num_models: Number of base models
            aggregation: 'conservative', 'average', or 'optimistic'
        """
        self.num_models = num_models
        self.aggregation = aggregation

    def predict(self,
               predictions: List[np.ndarray],
               uncertainties: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Combine predictions with uncertainty weighting

        Args:
            predictions: List of predictions from each model
            uncertainties: List of uncertainty estimates (std dev)

        Returns:
            combined_prediction: Weighted combination
            combined_uncertainty: Combined uncertainty estimate
        """
        predictions = np.array(predictions)  # (num_models, batch, output)
        uncertainties = np.array(uncertainties)

        # Precision weighting (inverse variance)
        variances = uncertainties ** 2
        precisions = 1.0 / (variances + 1e-8)

        # Normalize weights
        weights = precisions / precisions.sum(axis=0, keepdims=True)

        # Weighted mean
        combined_pred = np.sum(weights * predictions, axis=0)

        # Combined uncertainty
        if self.aggregation == 'conservative':
            # Maximum uncertainty
            combined_unc = np.max(uncertainties, axis=0)
        elif self.aggregation == 'average':
            # Average uncertainty
            combined_unc = np.mean(uncertainties, axis=0)
        elif self.aggregation == 'optimistic':
            # Precision-weighted uncertainty
            combined_variance = 1.0 / precisions.sum(axis=0)
            combined_unc = np.sqrt(combined_variance)
        else:
            combined_unc = np.mean(uncertainties, axis=0)

        return combined_pred, combined_unc


def create_ensemble_model(config: dict,
                         num_models: int,
                         output_size: int) -> nn.Module:
    """
    Factory function to create ensemble model

    Args:
        config: Configuration dictionary
        num_models: Number of base models
        output_size: Output size

    Returns:
        Ensemble model instance
    """
    ensemble_config = config['ensemble']
    meta_learner_type = ensemble_config['meta_learner']['type']

    if meta_learner_type == 'weighted_average':
        weights_method = ensemble_config['weights']['method']

        if weights_method == 'learned':
            method = 'learned'
        elif weights_method == 'performance_based':
            method = 'performance'
        else:
            method = 'equal'

        model = WeightedEnsemble(
            num_models=num_models,
            output_size=output_size,
            method=method
        )

    elif meta_learner_type == 'stacking':
        model = StackingEnsemble(
            num_models=num_models,
            output_size=output_size,
            hidden_sizes=ensemble_config['meta_learner']['architecture'],
            dropout=0.2
        )

    else:
        # Default to weighted average
        model = WeightedEnsemble(
            num_models=num_models,
            output_size=output_size,
            method='equal'
        )

    return model


if __name__ == "__main__":
    # Test ensemble models
    print("Testing Ensemble Models")
    print("=" * 60)

    num_models = 3
    batch_size = 8
    output_size = 30

    # Create dummy predictions
    predictions = [
        torch.randn(batch_size, output_size) for _ in range(num_models)
    ]

    print(f"\nInput: {num_models} models, batch_size={batch_size}, output_size={output_size}")

    # Test Weighted Ensemble
    print("\n1. Weighted Ensemble (Learned)")
    model_weighted = WeightedEnsemble(num_models, output_size, method='learned')
    combined = model_weighted(predictions)
    print(f"Output shape: {combined.shape}")
    print(f"Weights: {torch.softmax(model_weighted.weights, dim=0).detach().numpy()}")

    # Test Stacking Ensemble
    print("\n2. Stacking Ensemble")
    model_stacking = StackingEnsemble(num_models, output_size, hidden_sizes=[32, 16])
    combined = model_stacking(predictions)
    print(f"Output shape: {combined.shape}")
    print(f"Parameters: {sum(p.numel() for p in model_stacking.parameters()):,}")

    # Test Adaptive Ensemble
    print("\n3. Adaptive Ensemble")
    adaptive = AdaptiveEnsemble(num_models, window_size=90, metric='rmse')

    # Simulate some observations
    for _ in range(50):
        preds_np = [torch.randn(output_size).numpy() for _ in range(num_models)]
        target_np = torch.randn(output_size).numpy()
        adaptive.add_observation(preds_np, target_np)

    print(f"Current weights: {adaptive.get_weights()}")

    # Make prediction
    test_preds = [torch.randn(output_size).numpy() for _ in range(num_models)]
    combined = adaptive.predict(test_preds)
    print(f"Prediction shape: {combined.shape}")

    # Test Uncertainty Ensemble
    print("\n4. Uncertainty Ensemble")
    unc_ensemble = UncertaintyEnsemble(num_models, aggregation='conservative')

    test_preds = [torch.randn(batch_size, output_size).numpy() for _ in range(num_models)]
    test_uncs = [torch.rand(batch_size, output_size).numpy() * 0.5 for _ in range(num_models)]

    combined_pred, combined_unc = unc_ensemble.predict(test_preds, test_uncs)
    print(f"Prediction shape: {combined_pred.shape}")
    print(f"Uncertainty shape: {combined_unc.shape}")

    print("\n✓ Ensemble tests completed successfully!")
