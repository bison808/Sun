"""
Automated Model Retraining Script
Checks for data drift, performance degradation, and retrains if needed
"""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import yaml
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import torch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelMonitor:
    """Monitor model performance and data drift"""

    def __init__(self, config_path: str = "../configs/config.yaml"):
        """Initialize monitor"""
        self.config = self._load_config(config_path)
        self.data_dir = Path(self.config['paths']['data_processed'])
        self.models_dir = Path(self.config['paths']['models'])

    def _load_config(self, config_path: str) -> dict:
        """Load configuration"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def check_data_drift(self) -> tuple[bool, float]:
        """
        Check for data drift using KS test

        Returns:
            (has_drift, p_value)
        """
        logger.info("Checking for data drift...")

        # Load historical data (training period)
        historical_path = self.data_dir / 'daily_processed.csv'
        df = pd.read_csv(historical_path, parse_dates=['date'])

        # Training period
        train_start = self.config['data_splits']['train']['start']
        train_end = self.config['data_splits']['train']['end']

        # Recent period (last 90 days)
        recent_days = 90
        recent_start = df['date'].max() - timedelta(days=recent_days)

        train_data = df[(df['date'].dt.year >= train_start) &
                       (df['date'].dt.year < train_end)]['ssn'].dropna()

        recent_data = df[df['date'] >= recent_start]['ssn'].dropna()

        # KS test
        statistic, p_value = stats.ks_2samp(train_data, recent_data)

        threshold = self.config['mlops']['monitoring']['data_drift']['alert_threshold']
        has_drift = p_value < threshold

        logger.info(f"KS test: statistic={statistic:.4f}, p_value={p_value:.4f}")
        logger.info(f"Data drift detected: {has_drift}")

        return has_drift, p_value

    def check_performance(self) -> tuple[bool, dict]:
        """
        Check if model performance has degraded

        Returns:
            (needs_retraining, metrics)
        """
        logger.info("Checking model performance...")

        # In production, this would compare predictions to actual values
        # For now, we'll check if enough new data is available

        data_path = self.data_dir / 'daily_processed.csv'
        df = pd.read_csv(data_path, parse_dates=['date'])

        # Check how many new data points since last training
        train_end = self.config['data_splits']['train']['end']
        new_data = df[df['date'].dt.year >= train_end]

        min_new_points = self.config['mlops']['retraining']['min_new_data_points']
        has_enough_data = len(new_data) >= min_new_points

        metrics = {
            'new_data_points': len(new_data),
            'min_required': min_new_points,
            'has_enough_data': has_enough_data
        }

        logger.info(f"New data points: {len(new_data)} (minimum: {min_new_points})")

        return has_enough_data, metrics

    def should_retrain(self) -> tuple[bool, dict]:
        """
        Determine if models should be retrained

        Returns:
            (should_retrain, reasons)
        """
        logger.info("=" * 60)
        logger.info("Model Retraining Check")
        logger.info("=" * 60)

        reasons = {}

        # Check data drift
        if self.config['mlops']['retraining']['trigger_on_drift']:
            has_drift, p_value = self.check_data_drift()
            reasons['data_drift'] = {
                'detected': has_drift,
                'p_value': p_value
            }
        else:
            has_drift = False

        # Check performance/data availability
        has_enough_data, metrics = self.check_performance()
        reasons['performance'] = metrics

        # Decision
        should_retrain = has_drift or has_enough_data

        logger.info(f"\nDecision: {'RETRAIN' if should_retrain else 'SKIP'}")

        if should_retrain:
            logger.info("Reasons for retraining:")
            if has_drift:
                logger.info("  - Data drift detected")
            if has_enough_data:
                logger.info("  - Sufficient new data available")

        return should_retrain, reasons


class ModelRetrainer:
    """Handle model retraining"""

    def __init__(self):
        """Initialize retrainer"""
        self.config = None

    def retrain_short_term_model(self):
        """Retrain short-term LSTM model"""
        logger.info("=" * 60)
        logger.info("Retraining Short-Term LSTM")
        logger.info("=" * 60)

        try:
            # Import and run training script
            from training.train_short_term import ShortTermTrainer

            trainer = ShortTermTrainer()
            trainer.train()

            logger.info("✓ Short-term model retrained successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to retrain short-term model: {e}")
            return False

    def update_data(self):
        """Update data pipeline with latest data"""
        logger.info("Updating data pipeline...")

        try:
            # Run data pipeline
            from data.download_data import SolarDataDownloader
            from data.preprocess import SolarDataPreprocessor
            from data.feature_engineering import SolarFeatureEngineer

            # Download
            logger.info("Downloading latest data...")
            downloader = SolarDataDownloader()
            downloader.download_all()

            # Preprocess
            logger.info("Preprocessing data...")
            preprocessor = SolarDataPreprocessor()
            preprocessor.process_daily_data()
            preprocessor.process_monthly_data()

            # Feature engineering
            logger.info("Engineering features...")
            engineer = SolarFeatureEngineer()
            engineer.engineer_daily_features()
            engineer.engineer_monthly_features()

            logger.info("✓ Data pipeline updated successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to update data: {e}")
            return False


def main():
    """Main retraining workflow"""
    logger.info("=" * 60)
    logger.info("Solar Cycle ML - Automated Retraining")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Initialize monitor
    monitor = ModelMonitor()

    # Check if retraining is needed
    should_retrain, reasons = monitor.should_retrain()

    if not should_retrain:
        logger.info("\n✓ No retraining needed at this time")
        return 0

    # Proceed with retraining
    logger.info("\n" + "=" * 60)
    logger.info("Starting Retraining Process")
    logger.info("=" * 60)

    retrainer = ModelRetrainer()

    # Update data
    if not retrainer.update_data():
        logger.error("✗ Failed to update data. Aborting retraining.")
        return 1

    # Retrain models
    if not retrainer.retrain_short_term_model():
        logger.error("✗ Failed to retrain models")
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("✓ Retraining completed successfully!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
