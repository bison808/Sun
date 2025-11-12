"""
Monitor Daily Inference Pipeline
Displays status, metrics, and performance of the automated predictions
"""

import sys
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import yaml
import redis
import psycopg2
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd
from tabulate import tabulate

try:
    from colorama import init, Fore, Style
    init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = RED = YELLOW = BLUE = CYAN = MAGENTA = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""


class InferenceMonitor:
    """Monitor the daily inference pipeline"""

    def __init__(self, config_path: str = "../configs/config.yaml"):
        """Initialize monitor"""
        self.config = self._load_config(config_path)
        self._init_connections()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def _init_connections(self):
        """Initialize connections"""
        # Redis
        try:
            redis_config = self.config['redis']
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                decode_responses=True
            )
            self.redis_client.ping()
            self.redis_connected = True
        except:
            self.redis_connected = False

        # PostgreSQL
        try:
            db_config = self.config['database']['postgres']
            self.db_conn = psycopg2.connect(
                host=os.getenv('DB_HOST', db_config['host']),
                port=db_config['port'],
                database=os.getenv('DB_NAME', db_config['database']),
                user=os.getenv('DB_USER', db_config['user']),
                password=os.getenv('DB_PASSWORD', db_config['password'])
            )
            self.db_connected = True
        except:
            self.db_connected = False

    def check_cache_status(self) -> Dict:
        """Check Redis cache status"""
        if not self.redis_connected:
            return {'status': 'disconnected', 'predictions': None}

        try:
            key = "solar:predictions:daily:latest"
            data = self.redis_client.get(key)

            if data:
                predictions = json.loads(data)
                ttl = self.redis_client.ttl(key)

                return {
                    'status': 'active',
                    'predictions': predictions,
                    'ttl_seconds': ttl,
                    'ttl_hours': ttl / 3600,
                    'generated_at': predictions['metadata']['generated_at'],
                    'model_version': predictions['metadata']['model_version']
                }
            else:
                return {'status': 'empty', 'predictions': None}

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def check_database_status(self) -> Dict:
        """Check database predictions"""
        if not self.db_connected:
            return {'status': 'disconnected'}

        try:
            cursor = self.db_conn.cursor()

            # Count total predictions
            cursor.execute("SELECT COUNT(*) FROM ml_predictions")
            total_count = cursor.fetchone()[0]

            # Latest prediction
            cursor.execute("""
                SELECT forecast_date, prediction, model_version, created_at
                FROM ml_predictions
                ORDER BY created_at DESC
                LIMIT 1
            """)
            latest = cursor.fetchone()

            # Future predictions count
            cursor.execute("""
                SELECT COUNT(*)
                FROM ml_predictions
                WHERE forecast_date > CURRENT_DATE
            """)
            future_count = cursor.fetchone()[0]

            cursor.close()

            return {
                'status': 'connected',
                'total_predictions': total_count,
                'future_predictions': future_count,
                'latest_prediction': {
                    'forecast_date': latest[0] if latest else None,
                    'prediction': latest[1] if latest else None,
                    'model_version': latest[2] if latest else None,
                    'created_at': latest[3] if latest else None
                } if latest else None
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def get_model_performance(self, days: int = 30) -> Optional[pd.DataFrame]:
        """Get model performance metrics"""
        if not self.db_connected:
            return None

        try:
            cursor = self.db_conn.cursor()

            # Use the calculate_model_metrics function
            cursor.execute("""
                SELECT * FROM calculate_model_metrics(
                    CURRENT_DATE - INTERVAL '%s days',
                    CURRENT_DATE
                )
            """, (days,))

            rows = cursor.fetchall()
            cursor.close()

            if rows:
                df = pd.DataFrame(rows, columns=[
                    'model_version', 'num_predictions', 'rmse', 'mae', 'mape', 'coverage_95'
                ])
                return df
            else:
                return None

        except Exception as e:
            print(f"Error getting performance: {e}")
            return None

    def get_recent_predictions(self, days: int = 7) -> Optional[pd.DataFrame]:
        """Get recent predictions"""
        if not self.db_connected:
            return None

        try:
            cursor = self.db_conn.cursor()

            cursor.execute("""
                SELECT forecast_date, prediction, uncertainty, lower_95, upper_95
                FROM ml_predictions_latest
                WHERE forecast_date >= CURRENT_DATE
                ORDER BY forecast_date
                LIMIT %s
            """, (days,))

            rows = cursor.fetchall()
            cursor.close()

            if rows:
                df = pd.DataFrame(rows, columns=[
                    'forecast_date', 'prediction', 'uncertainty', 'lower_95', 'upper_95'
                ])
                return df
            else:
                return None

        except Exception as e:
            print(f"Error getting predictions: {e}")
            return None

    def display_status(self):
        """Display comprehensive status"""
        print("\n" + "=" * 70)
        print(f"{Style.BRIGHT}Solar Cycle ML - Daily Inference Pipeline Monitor{Style.RESET_ALL}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # System Status
        print(f"\n{Style.BRIGHT}SYSTEM STATUS{Style.RESET_ALL}")
        print("-" * 70)

        redis_status = f"{Fore.GREEN}✓ Connected{Fore.RESET}" if self.redis_connected else f"{Fore.RED}✗ Disconnected{Fore.RESET}"
        db_status = f"{Fore.GREEN}✓ Connected{Fore.RESET}" if self.db_connected else f"{Fore.RED}✗ Disconnected{Fore.RESET}"

        print(f"Redis Cache:    {redis_status}")
        print(f"Database:       {db_status}")

        # Cache Status
        print(f"\n{Style.BRIGHT}CACHE STATUS{Style.RESET_ALL}")
        print("-" * 70)

        cache_status = self.check_cache_status()

        if cache_status['status'] == 'active':
            print(f"{Fore.GREEN}✓ Cache Active{Fore.RESET}")
            print(f"  Generated:    {cache_status['generated_at']}")
            print(f"  Model:        {cache_status['model_version']}")
            print(f"  TTL:          {cache_status['ttl_hours']:.1f} hours ({cache_status['ttl_seconds']}s)")

            predictions = cache_status['predictions']
            print(f"  Forecast:     {predictions['forecast_dates'][0]} to {predictions['forecast_dates'][-1]}")
            print(f"  Days:         {len(predictions['predictions'])}")

            # Next 7 days summary
            next_7_mean = sum(predictions['predictions'][:7]) / 7
            print(f"  Mean (7-day): {next_7_mean:.1f} SSN")

        elif cache_status['status'] == 'empty':
            print(f"{Fore.YELLOW}⚠ Cache Empty{Fore.RESET}")
            print("  Run daily inference to populate cache")

        else:
            print(f"{Fore.RED}✗ Cache Error{Fore.RESET}")
            if 'error' in cache_status:
                print(f"  Error: {cache_status['error']}")

        # Database Status
        print(f"\n{Style.BRIGHT}DATABASE STATUS{Style.RESET_ALL}")
        print("-" * 70)

        db_status = self.check_database_status()

        if db_status['status'] == 'connected':
            print(f"{Fore.GREEN}✓ Database Active{Fore.RESET}")
            print(f"  Total Predictions:  {db_status['total_predictions']:,}")
            print(f"  Future Predictions: {db_status['future_predictions']}")

            if db_status['latest_prediction']:
                latest = db_status['latest_prediction']
                print(f"  Latest:             {latest['forecast_date']} (SSN: {latest['prediction']:.1f})")
                print(f"  Created:            {latest['created_at']}")
                print(f"  Model:              {latest['model_version']}")

        else:
            print(f"{Fore.RED}✗ Database Error{Fore.RESET}")

        # Recent Predictions
        print(f"\n{Style.BRIGHT}UPCOMING PREDICTIONS (Next 7 Days){Style.RESET_ALL}")
        print("-" * 70)

        recent_df = self.get_recent_predictions(days=7)

        if recent_df is not None and len(recent_df) > 0:
            # Format for display
            recent_df['forecast_date'] = recent_df['forecast_date'].astype(str)
            recent_df['prediction'] = recent_df['prediction'].round(1)
            recent_df['uncertainty'] = recent_df['uncertainty'].round(1)
            recent_df['lower_95'] = recent_df['lower_95'].round(1)
            recent_df['upper_95'] = recent_df['upper_95'].round(1)

            print(tabulate(
                recent_df,
                headers=['Date', 'Prediction', 'Uncertainty', 'Lower 95%', 'Upper 95%'],
                tablefmt='simple',
                showindex=False
            ))
        else:
            print(f"{Fore.YELLOW}No upcoming predictions available{Fore.RESET}")

        # Model Performance
        print(f"\n{Style.BRIGHT}MODEL PERFORMANCE (Last 30 Days){Style.RESET_ALL}")
        print("-" * 70)

        perf_df = self.get_model_performance(days=30)

        if perf_df is not None and len(perf_df) > 0:
            # Format for display
            perf_df['rmse'] = perf_df['rmse'].round(2)
            perf_df['mae'] = perf_df['mae'].round(2)
            perf_df['mape'] = perf_df['mape'].round(2)
            perf_df['coverage_95'] = perf_df['coverage_95'].round(1)

            print(tabulate(
                perf_df,
                headers=['Model', 'Predictions', 'RMSE', 'MAE', 'MAPE (%)', '95% Coverage (%)'],
                tablefmt='simple',
                showindex=False
            ))
        else:
            print(f"{Fore.YELLOW}Performance metrics not available (need actual data for comparison){Fore.RESET}")

        # Log File Status
        print(f"\n{Style.BRIGHT}LOG FILES{Style.RESET_ALL}")
        print("-" * 70)

        log_file = Path(__file__).parent.parent / 'logs' / 'ml' / 'daily_inference.log'

        if log_file.exists():
            size_kb = log_file.stat().st_size / 1024
            modified = datetime.fromtimestamp(log_file.stat().st_mtime)
            print(f"  Log file:     {log_file}")
            print(f"  Size:         {size_kb:.1f} KB")
            print(f"  Last updated: {modified.strftime('%Y-%m-%d %H:%M:%S')}")

            # Show last few lines
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    last_lines = lines[-5:] if len(lines) >= 5 else lines

                print(f"\n  Last 5 log entries:")
                for line in last_lines:
                    print(f"    {line.strip()}")
            except:
                pass
        else:
            print(f"{Fore.YELLOW}  Log file not found: {log_file}{Fore.RESET}")

        # Commands
        print(f"\n{Style.BRIGHT}COMMANDS{Style.RESET_ALL}")
        print("-" * 70)
        print("  Run inference:    python scripts/daily_inference.py")
        print("  Schedule:         bash scripts/schedule_inference.sh")
        print("  View logs:        tail -f logs/ml/daily_inference.log")
        print("  Database:         psql -c 'SELECT * FROM ml_predictions_latest LIMIT 10'")

        print("\n" + "=" * 70 + "\n")


def main():
    """Main execution"""
    try:
        monitor = InferenceMonitor()
        monitor.display_status()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
