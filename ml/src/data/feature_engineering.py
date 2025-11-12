"""
Feature Engineering for Solar Cycle Prediction
Creates advanced features: moving averages, rate of change, Fourier components
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SolarFeatureEngineer:
    """Create advanced features for solar prediction models"""

    def __init__(self, config_path: str = "../../configs/config.yaml"):
        """Initialize feature engineer with configuration"""
        self.config = self._load_config(config_path)
        self.processed_data_dir = Path(self.config['paths']['data_processed'])
        self.features_data_dir = Path(self.config['paths']['data_features'])
        self.features_data_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def add_moving_averages(self, df: pd.DataFrame,
                           column: str,
                           windows: List[int]) -> pd.DataFrame:
        """
        Add moving average features

        Args:
            df: DataFrame with time series
            column: Column to compute MA on
            windows: List of window sizes (in time steps)
        """
        logger.info(f"Adding moving averages for {column}: {windows}")

        for window in windows:
            df[f'{column}_ma{window}'] = df[column].rolling(
                window=window,
                min_periods=1,
                center=False
            ).mean()

            # Also add standard deviation
            df[f'{column}_std{window}'] = df[column].rolling(
                window=window,
                min_periods=1
            ).std()

        return df

    def add_rate_of_change(self, df: pd.DataFrame,
                          column: str,
                          windows: List[int]) -> pd.DataFrame:
        """
        Add rate of change features

        Args:
            df: DataFrame with time series
            column: Column to compute ROC on
            windows: List of periods to look back
        """
        logger.info(f"Adding rate of change for {column}: {windows}")

        for window in windows:
            # Absolute change
            df[f'{column}_change{window}'] = df[column].diff(window)

            # Percentage change
            df[f'{column}_pct_change{window}'] = df[column].pct_change(window)

            # Acceleration (second derivative)
            if window <= 6:
                df[f'{column}_accel{window}'] = df[f'{column}_change{window}'].diff(1)

        return df

    def add_lag_features(self, df: pd.DataFrame,
                        column: str,
                        lags: List[int]) -> pd.DataFrame:
        """
        Add lagged features

        Args:
            df: DataFrame with time series
            column: Column to create lags for
            lags: List of lag periods
        """
        logger.info(f"Adding lag features for {column}: {lags}")

        for lag in lags:
            df[f'{column}_lag{lag}'] = df[column].shift(lag)

        return df

    def add_fourier_features(self, df: pd.DataFrame,
                            column: str,
                            periods: List[int]) -> pd.DataFrame:
        """
        Add Fourier transform features to capture cyclical patterns

        Args:
            df: DataFrame with time series
            column: Column to extract Fourier features from
            periods: List of periods (in years)
        """
        logger.info(f"Adding Fourier features for {column}: {periods} years")

        # Get time index in years since start
        if 'days_since_1749' in df.columns:
            t = df['days_since_1749'] / 365.25
        else:
            t = np.arange(len(df)) / 365.25

        for period_years in periods:
            # Sine and cosine components
            freq = 2 * np.pi / period_years

            df[f'{column}_fourier_sin_{period_years}y'] = np.sin(freq * t)
            df[f'{column}_fourier_cos_{period_years}y'] = np.cos(freq * t)

        return df

    def add_statistical_features(self, df: pd.DataFrame,
                                 column: str,
                                 window: int = 90) -> pd.DataFrame:
        """
        Add statistical features over rolling window

        Args:
            df: DataFrame with time series
            column: Column to compute statistics on
            window: Rolling window size
        """
        logger.info(f"Adding statistical features for {column} (window: {window})")

        rolling = df[column].rolling(window=window, min_periods=1)

        # Basic statistics
        df[f'{column}_mean_{window}'] = rolling.mean()
        df[f'{column}_std_{window}'] = rolling.std()
        df[f'{column}_min_{window}'] = rolling.min()
        df[f'{column}_max_{window}'] = rolling.max()

        # Percentiles
        df[f'{column}_q25_{window}'] = rolling.quantile(0.25)
        df[f'{column}_q75_{window}'] = rolling.quantile(0.75)

        # Skewness and kurtosis
        df[f'{column}_skew_{window}'] = rolling.skew()
        df[f'{column}_kurt_{window}'] = rolling.kurt()

        return df

    def add_cycle_features(self, df: pd.DataFrame,
                          column: str = 'ssn') -> pd.DataFrame:
        """
        Add solar cycle specific features

        Args:
            df: DataFrame with solar data
            column: SSN column name
        """
        logger.info("Adding solar cycle features...")

        # Time since cycle minimum
        df['days_in_cycle'] = 0
        for cycle_num in df['cycle_number'].unique():
            mask = df['cycle_number'] == cycle_num
            cycle_data = df[mask]
            if len(cycle_data) > 0:
                cycle_start = cycle_data['date'].min()
                df.loc[mask, 'days_in_cycle'] = (
                    cycle_data['date'] - cycle_start
                ).dt.days

        # Normalize days in cycle
        df['cycle_progress'] = df['days_in_cycle'] / 4015  # ~11 years in days

        # Cycle amplitude (max SSN in rolling cycle window)
        df[f'{column}_cycle_max'] = df[column].rolling(
            window=4015,  # ~11 years
            min_periods=365,
            center=True
        ).max()

        # Position relative to cycle max
        df[f'{column}_rel_to_cycle_max'] = df[column] / (df[f'{column}_cycle_max'] + 1e-6)

        return df

    def add_momentum_features(self, df: pd.DataFrame,
                             column: str = 'ssn') -> pd.DataFrame:
        """
        Add momentum and trend features

        Args:
            df: DataFrame with time series
            column: Column to compute momentum on
        """
        logger.info("Adding momentum features...")

        # RSI (Relative Strength Index)
        delta = df[column].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()

        rs = avg_gain / (avg_loss + 1e-6)
        df[f'{column}_rsi'] = 100 - (100 / (1 + rs))

        # MACD (Moving Average Convergence Divergence)
        ema_12 = df[column].ewm(span=12, adjust=False).mean()
        ema_26 = df[column].ewm(span=26, adjust=False).mean()
        df[f'{column}_macd'] = ema_12 - ema_26
        df[f'{column}_macd_signal'] = df[f'{column}_macd'].ewm(span=9, adjust=False).mean()

        # Bollinger Bands
        ma_20 = df[column].rolling(window=20).mean()
        std_20 = df[column].rolling(window=20).std()
        df[f'{column}_bb_upper'] = ma_20 + (std_20 * 2)
        df[f'{column}_bb_lower'] = ma_20 - (std_20 * 2)
        df[f'{column}_bb_width'] = df[f'{column}_bb_upper'] - df[f'{column}_bb_lower']

        return df

    def create_sequences_for_lstm(self, df: pd.DataFrame,
                                  target_col: str,
                                  feature_cols: List[str],
                                  window_size: int,
                                  horizon: int) -> tuple:
        """
        Create sequences for LSTM training

        Args:
            df: DataFrame with features
            target_col: Target column name
            feature_cols: List of feature column names
            window_size: Input sequence length
            horizon: Prediction horizon

        Returns:
            X, y arrays for training
        """
        logger.info(f"Creating sequences: window={window_size}, horizon={horizon}")

        # Ensure no NaN values
        df_clean = df[feature_cols + [target_col]].dropna()

        X, y = [], []

        for i in range(len(df_clean) - window_size - horizon + 1):
            # Input features
            X.append(df_clean[feature_cols].iloc[i:i+window_size].values)

            # Target values
            y.append(df_clean[target_col].iloc[i+window_size:i+window_size+horizon].values)

        X = np.array(X)
        y = np.array(y)

        logger.info(f"Created sequences - X shape: {X.shape}, y shape: {y.shape}")

        return X, y

    def engineer_daily_features(self) -> pd.DataFrame:
        """
        Main feature engineering pipeline for daily data
        """
        logger.info("=" * 60)
        logger.info("Engineering Daily Features")
        logger.info("=" * 60)

        # Load processed data
        input_path = self.processed_data_dir / 'daily_processed.csv'
        df = pd.read_csv(input_path, parse_dates=['date'])
        logger.info(f"Loaded data: {df.shape}")

        # Get config parameters
        ma_windows = self.config['preprocessing']['feature_engineering']['moving_averages']
        roc_windows = self.config['preprocessing']['feature_engineering']['rate_of_change_windows']
        fourier_periods = self.config['preprocessing']['feature_engineering']['fourier_periods']
        lag_features = self.config['preprocessing']['feature_engineering']['lag_features']

        # Apply feature engineering
        df = self.add_moving_averages(df, 'ssn', ma_windows)
        df = self.add_rate_of_change(df, 'ssn', roc_windows)
        df = self.add_fourier_features(df, 'ssn', fourier_periods)
        df = self.add_lag_features(df, 'ssn', lag_features)
        df = self.add_statistical_features(df, 'ssn', window=90)
        df = self.add_cycle_features(df, 'ssn')
        df = self.add_momentum_features(df, 'ssn')

        # Drop rows with NaN (from rolling operations)
        initial_len = len(df)
        df = df.dropna()
        logger.info(f"Dropped {initial_len - len(df)} rows with NaN")

        # Save
        output_path = self.features_data_dir / 'daily_features.csv'
        df.to_csv(output_path, index=False)
        logger.info(f"Saved features to {output_path}")
        logger.info(f"Final shape: {df.shape}")
        logger.info(f"Features created: {len(df.columns)}")

        return df

    def engineer_monthly_features(self) -> pd.DataFrame:
        """
        Feature engineering for monthly data (long-term models)
        """
        logger.info("=" * 60)
        logger.info("Engineering Monthly Features")
        logger.info("=" * 60)

        # Load processed data
        input_path = self.processed_data_dir / 'monthly_processed.csv'
        df = pd.read_csv(input_path, parse_dates=['date'])
        logger.info(f"Loaded data: {df.shape}")

        # Monthly-specific windows (in months)
        ma_windows = [6, 12, 24, 36]
        roc_windows = [1, 3, 6, 12]
        lag_features = [1, 3, 6, 12, 24]

        # Apply feature engineering
        df = self.add_moving_averages(df, 'ssn', ma_windows)
        df = self.add_rate_of_change(df, 'ssn', roc_windows)
        df = self.add_fourier_features(df, 'ssn', [11, 22, 132])
        df = self.add_lag_features(df, 'ssn', lag_features)
        df = self.add_statistical_features(df, 'ssn', window=132)  # 11 years
        df = self.add_cycle_features(df, 'ssn')

        # Drop NaN
        initial_len = len(df)
        df = df.dropna()
        logger.info(f"Dropped {initial_len - len(df)} rows with NaN")

        # Save
        output_path = self.features_data_dir / 'monthly_features.csv'
        df.to_csv(output_path, index=False)
        logger.info(f"Saved features to {output_path}")
        logger.info(f"Final shape: {df.shape}")

        return df


def main():
    """Main execution"""
    engineer = SolarFeatureEngineer()

    # Engineer daily features
    df_daily = engineer.engineer_daily_features()

    # Engineer monthly features
    df_monthly = engineer.engineer_monthly_features()

    logger.info("=" * 60)
    logger.info("✓ Feature engineering completed successfully!")
    logger.info("=" * 60)

    # Print feature summary
    logger.info("\nDaily features:")
    logger.info(f"  Total features: {df_daily.shape[1]}")
    logger.info(f"  Data points: {df_daily.shape[0]}")
    logger.info(f"  Date range: {df_daily['date'].min()} to {df_daily['date'].max()}")

    logger.info("\nMonthly features:")
    logger.info(f"  Total features: {df_monthly.shape[1]}")
    logger.info(f"  Data points: {df_monthly.shape[0]}")
    logger.info(f"  Date range: {df_monthly['date'].min()} to {df_monthly['date'].max()}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
