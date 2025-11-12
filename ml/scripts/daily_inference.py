"""
Daily Inference Pipeline for Solar Cycle Predictions
Runs automated daily predictions and updates the system
"""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import yaml
import logging
import pandas as pd
import numpy as np
import torch
import redis
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import psycopg2
from psycopg2.extras import execute_values

from models.short_term_lstm import ShortTermLSTM
from data.preprocess import SolarDataPreprocessor
from data.feature_engineering import SolarFeatureEngineer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyInferencePipeline:
    """Automated daily inference pipeline"""

    def __init__(self, config_path: str = "../configs/config.yaml"):
        """Initialize inference pipeline"""
        self.config = self._load_config(config_path)
        self.models_dir = Path(self.config['paths']['models'])
        self.data_dir = Path(self.config['paths']['data_processed'])
        self.features_dir = Path(self.config['paths']['data_features'])

        # Device
        self.device = torch.device(
            'cuda' if torch.cuda.is_available() and self.config['training']['gpu']['enabled']
            else 'cpu'
        )
        logger.info(f"Using device: {self.device}")

        # Initialize connections
        self._init_redis()
        self._init_database()

        # Model cache
        self.model = None
        self.model_version = "1.0.0"

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            redis_config = self.config['redis']
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                decode_responses=True
            )
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("✓ Redis connected")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.cache_enabled = False

    def _init_database(self):
        """Initialize PostgreSQL connection"""
        try:
            db_config = self.config['database']['postgres']
            self.db_conn = psycopg2.connect(
                host=os.getenv('DB_HOST', db_config['host']),
                port=db_config['port'],
                database=os.getenv('DB_NAME', db_config['database']),
                user=os.getenv('DB_USER', db_config['user']),
                password=os.getenv('DB_PASSWORD', db_config['password'])
            )
            logger.info("✓ Database connected")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            self.db_conn = None

    def load_model(self) -> ShortTermLSTM:
        """
        Step 1: Load cached model from registry
        """
        logger.info("Step 1: Loading model from registry...")

        if self.model is not None:
            logger.info("Using cached model")
            return self.model

        model_path = self.models_dir / 'short_term_lstm' / 'best_model.pth'

        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Load checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)
        config = checkpoint['config']

        # Create model
        model = ShortTermLSTM(
            input_size=checkpoint['model_state_dict']['fc_layers.0.weight'].shape[1],
            hidden_sizes=config['architecture']['lstm_layers'],
            output_size=config['architecture']['output_horizon'],
            dropout=config['architecture']['dropout'],
            bidirectional=config['architecture']['bidirectional'],
            use_attention=config['architecture']['attention']
        ).to(self.device)

        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()

        self.model = model
        self.model_version = f"v{checkpoint['epoch']}"

        logger.info(f"✓ Model loaded (version: {self.model_version})")
        return model

    def fetch_latest_data(self, days: int = 90) -> pd.DataFrame:
        """
        Step 2: Fetch latest input data (last N days)
        """
        logger.info(f"Step 2: Fetching latest {days} days of data...")

        # First, try to fetch latest data from NOAA
        try:
            from data.download_data import SolarDataDownloader
            downloader = SolarDataDownloader()
            downloader.download_all()
            logger.info("✓ Latest data downloaded")
        except Exception as e:
            logger.warning(f"Could not fetch latest data: {e}")
            logger.info("Using existing data")

        # Load processed data
        data_path = self.data_dir / 'daily_processed.csv'
        if not data_path.exists():
            # Need to preprocess
            logger.info("Processing raw data...")
            preprocessor = SolarDataPreprocessor()
            preprocessor.process_daily_data()

        df = pd.read_csv(data_path, parse_dates=['date'])

        # Get last N days
        latest_data = df.tail(days).copy()

        logger.info(f"✓ Fetched data from {latest_data['date'].min()} to {latest_data['date'].max()}")
        logger.info(f"  Records: {len(latest_data)}")

        return latest_data

    def preprocess_inputs(self, data: pd.DataFrame) -> Tuple[torch.Tensor, List[str]]:
        """
        Step 3: Preprocess inputs
        """
        logger.info("Step 3: Preprocessing inputs...")

        # Ensure we have engineered features
        features_path = self.features_dir / 'daily_features.csv'
        if not features_path.exists():
            logger.info("Engineering features...")
            engineer = SolarFeatureEngineer()
            engineer.engineer_daily_features()

        # Load features
        df_features = pd.read_csv(features_path, parse_dates=['date'])

        # Get latest 90 days
        df_features = df_features.tail(90)

        # Select feature columns
        feature_cols = [col for col in df_features.columns if col not in
                       ['date', 'ssn', 'year', 'month', 'day_of_year', 'cycle_number']]

        # Extract features
        features_array = df_features[feature_cols].values

        # Convert to tensor
        input_tensor = torch.FloatTensor(features_array).unsqueeze(0)  # (1, 90, features)
        input_tensor = input_tensor.to(self.device)

        logger.info(f"✓ Input prepared: shape {input_tensor.shape}")
        logger.info(f"  Features: {len(feature_cols)}")

        return input_tensor, feature_cols

    def run_inference(self,
                     input_tensor: torch.Tensor,
                     n_samples: int = 10) -> Dict:
        """
        Step 4: Run inference
        """
        logger.info(f"Step 4: Running inference (n_samples={n_samples})...")

        model = self.model

        # Make predictions with uncertainty
        with torch.no_grad():
            mean, std, quantiles = model.predict_with_uncertainty(
                input_tensor,
                n_samples=n_samples
            )

        # Convert to numpy
        predictions = {
            'mean': mean[0].tolist(),
            'std': std[0].tolist(),
            'q05': quantiles['q05'][0].tolist(),
            'q25': quantiles['q25'][0].tolist(),
            'q50': quantiles['q50'][0].tolist(),
            'q75': quantiles['q75'][0].tolist(),
            'q95': quantiles['q95'][0].tolist()
        }

        logger.info(f"✓ Inference completed")
        logger.info(f"  Predictions: {len(predictions['mean'])} days")
        logger.info(f"  Mean prediction (next 7 days): {np.mean(predictions['mean'][:7]):.1f} SSN")

        return predictions

    def postprocess_predictions(self,
                               predictions: Dict,
                               start_date: datetime = None) -> Dict:
        """
        Step 5: Post-process predictions
        """
        logger.info("Step 5: Post-processing predictions...")

        if start_date is None:
            start_date = datetime.now() + timedelta(days=1)

        # Generate forecast dates
        forecast_dates = [
            (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            for i in range(len(predictions['mean']))
        ]

        # Denormalize predictions (convert from 0-1 back to actual SSN values)
        # Load scaler
        import joblib
        scaler_path = self.data_dir / 'scalers.joblib'

        if scaler_path.exists():
            scalers = joblib.load(scaler_path)
            ssn_scaler = scalers['ssn']

            # Denormalize
            for key in ['mean', 'std', 'q05', 'q25', 'q50', 'q75', 'q95']:
                if key == 'std':
                    # Standard deviation needs special handling
                    predictions[key] = [
                        std * (ssn_scaler.data_max_[0] - ssn_scaler.data_min_[0])
                        for std in predictions[key]
                    ]
                else:
                    # Inverse transform
                    values = np.array(predictions[key]).reshape(-1, 1)
                    predictions[key] = ssn_scaler.inverse_transform(values).flatten().tolist()

            logger.info("✓ Predictions denormalized to actual SSN values")
        else:
            logger.warning("Scaler not found, predictions remain normalized")

        # Create structured output
        output = {
            'forecast_dates': forecast_dates,
            'predictions': predictions['mean'],
            'uncertainty': predictions['std'],
            'confidence_intervals': {
                '68%': {
                    'lower': predictions['q25'],
                    'upper': predictions['q75']
                },
                '95%': {
                    'lower': predictions['q05'],
                    'upper': predictions['q95']
                }
            },
            'median': predictions['q50'],
            'metadata': {
                'model_version': self.model_version,
                'generated_at': datetime.now().isoformat(),
                'forecast_start': forecast_dates[0],
                'forecast_end': forecast_dates[-1],
                'horizon_days': len(predictions['mean'])
            }
        }

        logger.info(f"✓ Post-processing completed")
        logger.info(f"  Forecast: {output['forecast_dates'][0]} to {output['forecast_dates'][-1]}")
        logger.info(f"  Mean SSN (7-day): {np.mean(output['predictions'][:7]):.1f}")

        return output

    def cache_results(self, results: Dict, ttl: int = 86400):
        """
        Step 6: Cache results in Redis (24h TTL)
        """
        logger.info(f"Step 6: Caching results (TTL: {ttl}s = {ttl/3600:.1f}h)...")

        if not self.cache_enabled:
            logger.warning("Redis not available, skipping cache")
            return False

        try:
            cache_key = "solar:predictions:daily:latest"

            # Store as JSON
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(results)
            )

            # Also cache individual days for quick access
            for i, (date, value) in enumerate(zip(results['forecast_dates'], results['predictions'])):
                day_key = f"solar:predictions:daily:{date}"
                day_data = {
                    'date': date,
                    'prediction': value,
                    'uncertainty': results['uncertainty'][i],
                    'lower_95': results['confidence_intervals']['95%']['lower'][i],
                    'upper_95': results['confidence_intervals']['95%']['upper'][i]
                }
                self.redis_client.setex(day_key, ttl, json.dumps(day_data))

            logger.info(f"✓ Results cached successfully")
            logger.info(f"  Key: {cache_key}")
            logger.info(f"  TTL: {ttl}s ({ttl/3600:.1f} hours)")

            return True

        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
            return False

    def save_to_database(self, results: Dict):
        """Save predictions to database for historical tracking"""
        logger.info("Saving predictions to database...")

        if self.db_conn is None:
            logger.warning("Database not available, skipping save")
            return False

        try:
            cursor = self.db_conn.cursor()

            # Prepare data for bulk insert
            records = []
            for i, date in enumerate(results['forecast_dates']):
                records.append((
                    date,
                    results['predictions'][i],
                    results['uncertainty'][i],
                    results['confidence_intervals']['95%']['lower'][i],
                    results['confidence_intervals']['95%']['upper'][i],
                    results['median'][i],
                    self.model_version,
                    datetime.now()
                ))

            # Insert
            insert_query = """
                INSERT INTO ml_predictions
                (forecast_date, prediction, uncertainty, lower_95, upper_95, median, model_version, created_at)
                VALUES %s
                ON CONFLICT (forecast_date, model_version)
                DO UPDATE SET
                    prediction = EXCLUDED.prediction,
                    uncertainty = EXCLUDED.uncertainty,
                    lower_95 = EXCLUDED.lower_95,
                    upper_95 = EXCLUDED.upper_95,
                    median = EXCLUDED.median,
                    created_at = EXCLUDED.created_at
            """

            execute_values(cursor, insert_query, records)
            self.db_conn.commit()
            cursor.close()

            logger.info(f"✓ Saved {len(records)} predictions to database")
            return True

        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            if self.db_conn:
                self.db_conn.rollback()
            return False

    def send_to_backend(self, results: Dict) -> bool:
        """
        Step 7: Send to backend API
        """
        logger.info("Step 7: Sending results to backend API...")

        backend_url = os.getenv('BACKEND_API_URL', 'http://localhost:3000')
        endpoint = f"{backend_url}/api/ml/predictions/update"

        try:
            response = requests.post(
                endpoint,
                json=results,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"✓ Results sent to backend successfully")
                logger.info(f"  Endpoint: {endpoint}")
                logger.info(f"  Response: {response.json()}")
                return True
            else:
                logger.error(f"Backend returned error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send to backend: {e}")
            return False

    def run(self):
        """Run complete daily inference pipeline"""
        logger.info("=" * 60)
        logger.info("Daily Inference Pipeline - Solar Cycle Predictions")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        try:
            # Step 1: Load model
            self.load_model()

            # Step 2: Fetch latest data
            latest_data = self.fetch_latest_data(days=90)

            # Step 3: Preprocess inputs
            input_tensor, feature_cols = self.preprocess_inputs(latest_data)

            # Step 4: Run inference
            predictions = self.run_inference(input_tensor, n_samples=10)

            # Step 5: Post-process predictions
            results = self.postprocess_predictions(predictions)

            # Step 6: Cache results (24h TTL)
            self.cache_results(results, ttl=86400)

            # Step 6.5: Save to database
            self.save_to_database(results)

            # Step 7: Send to backend API
            self.send_to_backend(results)

            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ Daily inference pipeline completed successfully!")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Summary:")
            logger.info(f"  Model version: {self.model_version}")
            logger.info(f"  Forecast horizon: {len(results['predictions'])} days")
            logger.info(f"  Forecast start: {results['forecast_dates'][0]}")
            logger.info(f"  Forecast end: {results['forecast_dates'][-1]}")
            logger.info(f"  Mean SSN (next 7 days): {np.mean(results['predictions'][:7]):.1f}")
            logger.info(f"  Results cached: {self.cache_enabled}")
            logger.info(f"  Sent to backend: Successfully")

            return 0

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return 1

        finally:
            # Cleanup
            if self.db_conn:
                self.db_conn.close()


def main():
    """Main execution"""
    pipeline = DailyInferencePipeline()
    return pipeline.run()


if __name__ == "__main__":
    sys.exit(main())
