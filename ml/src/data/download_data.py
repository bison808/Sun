"""
Data Download Script for Solar Cycle ML Models
Downloads historical solar data from multiple sources
"""

import os
import sys
import requests
import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SolarDataDownloader:
    """Download and store solar activity data from multiple sources"""

    def __init__(self, config_path: str = "../../configs/config.yaml"):
        """Initialize downloader with configuration"""
        self.config = self._load_config(config_path)
        self.data_dir = Path(self.config['paths']['data_raw'])
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def download_sidc_sunspot_daily(self) -> Optional[pd.DataFrame]:
        """
        Download daily sunspot numbers from SIDC
        Returns DataFrame with columns: date, ssn, ssn_std, n_obs
        """
        logger.info("Downloading SIDC daily sunspot data...")

        try:
            url = self.config['data_sources']['sidc_sunspot']['url']
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse CSV with semicolon delimiter
            from io import StringIO
            df = pd.read_csv(
                StringIO(response.text),
                sep=';',
                names=['year', 'month', 'day', 'decimal_year', 'ssn',
                       'ssn_std', 'n_obs', 'definitive'],
                comment='#'
            )

            # Create date column
            df['date'] = pd.to_datetime(df[['year', 'month', 'day']])

            # Replace missing values (-1) with NaN
            df['ssn'] = df['ssn'].replace(-1, pd.NA)
            df['ssn_std'] = df['ssn_std'].replace(-1, pd.NA)

            # Save to CSV
            output_path = self.data_dir / 'sidc_sunspot_daily.csv'
            df.to_csv(output_path, index=False)
            logger.info(f"Saved daily sunspot data to {output_path}")
            logger.info(f"Data range: {df['date'].min()} to {df['date'].max()}")
            logger.info(f"Total records: {len(df)}")

            return df

        except Exception as e:
            logger.error(f"Error downloading SIDC daily data: {e}")
            return None

    def download_sidc_sunspot_monthly(self) -> Optional[pd.DataFrame]:
        """
        Download monthly smoothed sunspot numbers from SIDC
        Returns DataFrame with 13-month smoothed values
        """
        logger.info("Downloading SIDC monthly smoothed sunspot data...")

        try:
            url = self.config['data_sources']['sidc_smoothed']['url']
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse CSV
            from io import StringIO
            df = pd.read_csv(
                StringIO(response.text),
                sep=';',
                names=['year', 'month', 'decimal_year', 'ssn_smooth',
                       'ssn_std', 'n_obs', 'definitive'],
                comment='#'
            )

            # Create date column (first day of month)
            df['date'] = pd.to_datetime(df[['year', 'month']].assign(day=1))

            # Replace missing values
            df['ssn_smooth'] = df['ssn_smooth'].replace(-1, pd.NA)

            # Save to CSV
            output_path = self.data_dir / 'sidc_sunspot_monthly.csv'
            df.to_csv(output_path, index=False)
            logger.info(f"Saved monthly sunspot data to {output_path}")
            logger.info(f"Data range: {df['date'].min()} to {df['date'].max()}")

            return df

        except Exception as e:
            logger.error(f"Error downloading SIDC monthly data: {e}")
            return None

    def download_noaa_f107(self) -> Optional[pd.DataFrame]:
        """
        Download F10.7 cm radio flux from NOAA
        Recent data only (last 30 days)
        """
        logger.info("Downloading NOAA F10.7 radio flux data...")

        try:
            url = self.config['data_sources']['noaa_f107']['url']
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse JSON
            data = response.json()
            df = pd.DataFrame(data)

            # Parse time_tag to datetime
            df['date'] = pd.to_datetime(df['time_tag'])
            df = df.rename(columns={'flux': 'f107'})
            df = df[['date', 'f107']]

            # Save to CSV
            output_path = self.data_dir / 'noaa_f107_recent.csv'
            df.to_csv(output_path, index=False)
            logger.info(f"Saved F10.7 data to {output_path}")
            logger.info(f"Records: {len(df)}")

            return df

        except Exception as e:
            logger.error(f"Error downloading NOAA F10.7 data: {e}")
            return None

    def download_noaa_f107_historical(self) -> Optional[pd.DataFrame]:
        """
        Download historical F10.7 data from NOAA archives
        Data from 1947 onwards
        """
        logger.info("Downloading historical F10.7 data...")

        try:
            # NOAA historical F10.7 archive
            url = "https://www.ngdc.noaa.gov/stp/space-weather/solar-data/solar-features/solar-radio/noontime-flux/penticton/penticton_observed/tables/observed_flux_values.txt"

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse fixed-width format
            from io import StringIO
            lines = [line for line in response.text.split('\n')
                     if line and not line.startswith('#')]

            data_rows = []
            for line in lines[2:]:  # Skip header rows
                if len(line) < 50:
                    continue
                try:
                    year = int(line[0:4])
                    month = int(line[5:7])
                    day = int(line[8:10])
                    flux = float(line[34:40])

                    data_rows.append({
                        'date': pd.Timestamp(year, month, day),
                        'f107': flux
                    })
                except (ValueError, IndexError):
                    continue

            df = pd.DataFrame(data_rows)

            # Save to CSV
            output_path = self.data_dir / 'noaa_f107_historical.csv'
            df.to_csv(output_path, index=False)
            logger.info(f"Saved historical F10.7 data to {output_path}")
            logger.info(f"Data range: {df['date'].min()} to {df['date'].max()}")

            return df

        except Exception as e:
            logger.error(f"Error downloading historical F10.7 data: {e}")
            logger.info("Skipping historical F10.7 - using daily sunspot data as primary feature")
            return None

    def download_geomagnetic_indices(self) -> Optional[pd.DataFrame]:
        """
        Download planetary K-index (geomagnetic activity)
        """
        logger.info("Downloading geomagnetic indices...")

        try:
            url = self.config['data_sources']['geomagnetic']['url']
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse JSON
            data = response.json()
            df = pd.DataFrame(data)

            # Parse time_tag
            df['date'] = pd.to_datetime(df['time_tag'])
            df = df.rename(columns={'kp_index': 'kp'})
            df = df[['date', 'kp']]

            # Save to CSV
            output_path = self.data_dir / 'noaa_kp_recent.csv'
            df.to_csv(output_path, index=False)
            logger.info(f"Saved K-index data to {output_path}")

            return df

        except Exception as e:
            logger.error(f"Error downloading geomagnetic data: {e}")
            return None

    def download_all(self) -> Dict[str, pd.DataFrame]:
        """Download all available data sources"""
        logger.info("=" * 60)
        logger.info("Starting Solar Data Download")
        logger.info("=" * 60)

        results = {}

        # Primary data source: SIDC sunspot numbers
        results['daily_ssn'] = self.download_sidc_sunspot_daily()
        results['monthly_ssn'] = self.download_sidc_sunspot_monthly()

        # Additional features
        results['f107_recent'] = self.download_noaa_f107()
        results['f107_historical'] = self.download_noaa_f107_historical()
        results['kp_index'] = self.download_geomagnetic_indices()

        # Summary
        logger.info("=" * 60)
        logger.info("Download Summary:")
        for name, df in results.items():
            if df is not None:
                logger.info(f"  ✓ {name}: {len(df)} records")
            else:
                logger.info(f"  ✗ {name}: Failed")
        logger.info("=" * 60)

        return results


def main():
    """Main execution"""
    downloader = SolarDataDownloader()
    results = downloader.download_all()

    # Check if critical data was downloaded
    if results.get('daily_ssn') is not None:
        logger.info("✓ Data download completed successfully!")
        return 0
    else:
        logger.error("✗ Failed to download critical data (daily SSN)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
