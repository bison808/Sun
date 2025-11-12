"""
Data Preprocessing for Solar Cycle ML Models
Handles missing values, normalization, and data quality
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from scipy import interpolate, signal
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
import logging
import joblib

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SolarDataPreprocessor:
    """Preprocess solar data for ML model training"""

    def __init__(self, config_path: str = "../../configs/config.yaml"):
        """Initialize preprocessor with configuration"""
        self.config = self._load_config(config_path)
        self.raw_data_dir = Path(self.config['paths']['data_raw'])
        self.processed_data_dir = Path(self.config['paths']['data_processed'])
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.scalers = {}

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def load_raw_data(self) -> Dict[str, pd.DataFrame]:
        """Load all raw data files"""
        logger.info("Loading raw data files...")

        data = {}

        # Load daily sunspot numbers (primary dataset)
        daily_path = self.raw_data_dir / 'sidc_sunspot_daily.csv'
        if daily_path.exists():
            data['daily_ssn'] = pd.read_csv(daily_path, parse_dates=['date'])
            logger.info(f"Loaded daily SSN: {len(data['daily_ssn'])} records")
        else:
            raise FileNotFoundError(f"Critical file not found: {daily_path}")

        # Load monthly smoothed
        monthly_path = self.raw_data_dir / 'sidc_sunspot_monthly.csv'
        if monthly_path.exists():
            data['monthly_ssn'] = pd.read_csv(monthly_path, parse_dates=['date'])
            logger.info(f"Loaded monthly SSN: {len(data['monthly_ssn'])} records")

        # Load F10.7 if available
        f107_paths = [
            self.raw_data_dir / 'noaa_f107_historical.csv',
            self.raw_data_dir / 'noaa_f107_recent.csv'
        ]
        f107_data = []
        for path in f107_paths:
            if path.exists():
                df = pd.read_csv(path, parse_dates=['date'])
                f107_data.append(df)

        if f107_data:
            data['f107'] = pd.concat(f107_data, ignore_index=True)
            data['f107'] = data['f107'].drop_duplicates(subset=['date']).sort_values('date')
            logger.info(f"Loaded F10.7: {len(data['f107'])} records")

        return data

    def handle_missing_values(self, df: pd.DataFrame,
                             column: str,
                             method: str = 'interpolate',
                             max_gap: int = 7) -> pd.DataFrame:
        """
        Handle missing values in time series data

        Args:
            df: DataFrame with datetime index
            column: Column name to process
            method: interpolate, forward_fill, or drop
            max_gap: Maximum gap size to interpolate (days)
        """
        logger.info(f"Handling missing values in {column} (method: {method})")

        missing_count = df[column].isna().sum()
        logger.info(f"Missing values: {missing_count} ({missing_count/len(df)*100:.2f}%)")

        if method == 'interpolate':
            # Interpolate small gaps only
            df[column] = df[column].interpolate(
                method='time',
                limit=max_gap,
                limit_direction='both'
            )

            # For remaining NaN, use forward fill
            df[column] = df[column].fillna(method='ffill', limit=max_gap)

        elif method == 'forward_fill':
            df[column] = df[column].fillna(method='ffill', limit=max_gap)

        elif method == 'drop':
            df = df.dropna(subset=[column])

        remaining_missing = df[column].isna().sum()
        logger.info(f"Remaining missing: {remaining_missing}")

        return df

    def add_smoothed_ssn(self, df: pd.DataFrame,
                        window_months: int = 13) -> pd.DataFrame:
        """
        Add 13-month smoothed sunspot number
        Uses centered moving average with Butterworth filter
        """
        logger.info(f"Computing {window_months}-month smoothed SSN...")

        # Resample to monthly if needed
        if 'ssn_monthly' not in df.columns:
            df_monthly = df.set_index('date').resample('MS')['ssn'].mean()
        else:
            df_monthly = df.set_index('date')['ssn']

        # Apply Butterworth low-pass filter
        # Cutoff frequency for 13-month smoothing
        fs = 12  # 12 months per year
        fc = 1 / window_months  # Cutoff frequency
        b, a = signal.butter(N=2, Wn=fc, btype='low', fs=fs)

        # Filter (forward-backward to avoid phase shift)
        smoothed = signal.filtfilt(b, a, df_monthly.values)

        # Add to dataframe
        df_smooth = pd.DataFrame({
            'date': df_monthly.index,
            'ssn_smooth': smoothed
        })

        # Merge back to original dataframe
        df = df.merge(df_smooth, on='date', how='left')

        return df

    def normalize_features(self, df: pd.DataFrame,
                          columns: list,
                          method: str = 'minmax') -> pd.DataFrame:
        """
        Normalize features for ML training

        Args:
            df: DataFrame with features
            columns: List of columns to normalize
            method: minmax, standard, or robust
        """
        logger.info(f"Normalizing features: {columns} (method: {method})")

        for col in columns:
            if col not in df.columns:
                logger.warning(f"Column {col} not found, skipping")
                continue

            # Create scaler
            if method == 'minmax':
                scaler = MinMaxScaler(
                    feature_range=tuple(self.config['preprocessing']['normalize_range'])
                )
            elif method == 'standard':
                scaler = StandardScaler()
            elif method == 'robust':
                scaler = RobustScaler()
            else:
                raise ValueError(f"Unknown normalization method: {method}")

            # Fit and transform
            values = df[col].values.reshape(-1, 1)
            df[f'{col}_normalized'] = scaler.fit_transform(values)

            # Store scaler for inverse transform
            self.scalers[col] = scaler

            logger.info(f"  {col}: [{values.min():.2f}, {values.max():.2f}] -> "
                       f"[{df[f'{col}_normalized'].min():.2f}, {df[f'{col}_normalized'].max():.2f}]")

        return df

    def add_cycle_phase(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add solar cycle phase indicators
        Identifies if cycle is ascending or descending
        """
        logger.info("Adding cycle phase information...")

        # Solar cycle minima (approximate dates)
        cycle_minima = [
            ('1755-03-01', 1), ('1766-06-01', 2), ('1775-06-01', 3),
            ('1784-09-01', 4), ('1798-05-01', 5), ('1810-08-01', 6),
            ('1823-05-01', 7), ('1833-11-01', 8), ('1843-07-01', 9),
            ('1856-12-01', 10), ('1867-03-01', 11), ('1878-12-01', 12),
            ('1890-03-01', 13), ('1902-01-01', 14), ('1913-07-01', 15),
            ('1923-08-01', 16), ('1933-09-01', 17), ('1944-02-01', 18),
            ('1954-04-01', 19), ('1964-10-01', 20), ('1976-03-01', 21),
            ('1986-09-01', 22), ('1996-08-01', 23), ('2008-12-01', 24),
            ('2019-12-01', 25)
        ]

        # Convert to datetime
        minima_dates = [(pd.Timestamp(date), num) for date, num in cycle_minima]

        # Assign cycle number and phase
        cycle_numbers = []
        cycle_phases = []

        for date in df['date']:
            # Find current cycle
            cycle_num = 1
            phase = 'ascending'

            for i, (min_date, num) in enumerate(minima_dates):
                if date >= min_date:
                    cycle_num = num

                    # Check if ascending or descending
                    if i < len(minima_dates) - 1:
                        next_min = minima_dates[i + 1][0]
                        cycle_length = (next_min - min_date).days
                        days_since_min = (date - min_date).days

                        # Assume peak at ~4 years (1460 days) after minimum
                        if days_since_min < 1460:
                            phase = 'ascending'
                        else:
                            phase = 'descending'

            cycle_numbers.append(cycle_num)
            cycle_phases.append(phase)

        df['cycle_number'] = cycle_numbers
        df['cycle_phase'] = cycle_phases
        df['cycle_phase_encoded'] = (df['cycle_phase'] == 'ascending').astype(int)

        logger.info(f"Identified {df['cycle_number'].nunique()} solar cycles")

        return df

    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add temporal features"""
        logger.info("Creating time features...")

        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day_of_year'] = df['date'].dt.dayofyear
        df['days_since_1749'] = (df['date'] - pd.Timestamp('1749-01-01')).dt.days

        # Cyclical encoding for month
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

        return df

    def process_daily_data(self) -> pd.DataFrame:
        """
        Main processing pipeline for daily data
        """
        logger.info("=" * 60)
        logger.info("Processing Daily Solar Data")
        logger.info("=" * 60)

        # Load raw data
        raw_data = self.load_raw_data()
        df = raw_data['daily_ssn'].copy()

        # Set date as index
        df = df.sort_values('date')

        # Handle missing values
        df = self.handle_missing_values(
            df, 'ssn',
            method=self.config['preprocessing']['missing_value_strategy'],
            max_gap=self.config['preprocessing']['interpolation_max_gap']
        )

        # Add smoothed SSN
        df = self.add_smoothed_ssn(df)

        # Add cycle phase
        df = self.add_cycle_phase(df)

        # Add time features
        df = self.create_time_features(df)

        # Normalize features
        features_to_normalize = ['ssn']
        if 'ssn_smooth' in df.columns:
            features_to_normalize.append('ssn_smooth')

        df = self.normalize_features(
            df,
            features_to_normalize,
            method=self.config['preprocessing']['normalization']
        )

        # Save processed data
        output_path = self.processed_data_dir / 'daily_processed.csv'
        df.to_csv(output_path, index=False)
        logger.info(f"Saved processed data to {output_path}")
        logger.info(f"Shape: {df.shape}")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")

        # Save scalers
        scalers_path = self.processed_data_dir / 'scalers.joblib'
        joblib.dump(self.scalers, scalers_path)
        logger.info(f"Saved scalers to {scalers_path}")

        return df

    def process_monthly_data(self) -> pd.DataFrame:
        """
        Process monthly aggregated data for long-term models
        """
        logger.info("=" * 60)
        logger.info("Processing Monthly Solar Data")
        logger.info("=" * 60)

        # Load daily processed data
        daily_path = self.processed_data_dir / 'daily_processed.csv'
        df_daily = pd.read_csv(daily_path, parse_dates=['date'])

        # Resample to monthly
        df = df_daily.set_index('date').resample('MS').agg({
            'ssn': 'mean',
            'ssn_smooth': 'mean',
            'cycle_number': 'first',
            'cycle_phase_encoded': 'first'
        }).reset_index()

        # Add time features
        df = self.create_time_features(df)

        # Normalize
        df = self.normalize_features(df, ['ssn', 'ssn_smooth'], method='minmax')

        # Save
        output_path = self.processed_data_dir / 'monthly_processed.csv'
        df.to_csv(output_path, index=False)
        logger.info(f"Saved monthly data to {output_path}")
        logger.info(f"Shape: {df.shape}")

        return df


def main():
    """Main execution"""
    preprocessor = SolarDataPreprocessor()

    # Process daily data
    df_daily = preprocessor.process_daily_data()

    # Process monthly data
    df_monthly = preprocessor.process_monthly_data()

    logger.info("=" * 60)
    logger.info("✓ Preprocessing completed successfully!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
