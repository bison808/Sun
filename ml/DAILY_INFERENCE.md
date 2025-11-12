# Daily Inference Pipeline

Automated daily prediction system for solar activity forecasting.

## Overview

The daily inference pipeline automatically:
1. **Loads** the trained model from registry
2. **Fetches** latest solar data (90-day window)
3. **Preprocesses** inputs with feature engineering
4. **Runs** inference with uncertainty quantification
5. **Post-processes** predictions (denormalization)
6. **Caches** results in Redis (24-hour TTL)
7. **Sends** predictions to backend API

## Quick Start

### Run Manual Inference

```bash
cd ml/
python scripts/daily_inference.py
```

### Schedule Automated Inference

```bash
# Interactive setup
bash scripts/schedule_inference.sh

# Or manually add to crontab (daily at 6:00 AM)
crontab -e
# Add: 0 6 * * * cd /path/to/ml && python scripts/daily_inference.py >> logs/ml/daily_inference.log 2>&1
```

### Monitor Pipeline

```bash
# View status dashboard
python scripts/monitor_inference.py

# View logs
tail -f logs/ml/daily_inference.log
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Daily Inference Pipeline                  │
└─────────────────────────────────────────────────────────────┘

Step 1: Load Model
├─ Load from models/short_term_lstm/best_model.pth
├─ Cache in memory for subsequent runs
└─ Version: Extracted from checkpoint

Step 2: Fetch Latest Data
├─ Download from SIDC/NOAA APIs
├─ Use last 90 days as input window
└─ Handle missing values

Step 3: Preprocess
├─ Run feature engineering pipeline
├─ Apply normalization (MinMax 0-1)
├─ Create 50+ features
└─ Format as tensor (1, 90, features)

Step 4: Run Inference
├─ Monte Carlo dropout (10 samples)
├─ Generate predictions for 30 days
├─ Calculate uncertainty estimates
└─ Compute confidence intervals (68%, 95%)

Step 5: Post-process
├─ Denormalize predictions to actual SSN values
├─ Generate forecast dates
├─ Structure output with metadata
└─ Calculate summary statistics

Step 6: Cache Results
├─ Store in Redis (key: solar:predictions:daily:latest)
├─ TTL: 24 hours (86400 seconds)
├─ Also cache individual days
└─ JSON format for easy retrieval

Step 7: Send to Backend
├─ POST to /api/ml/predictions/update
├─ Include full forecast with confidence intervals
├─ Timeout: 30 seconds
└─ Retry on failure
```

## Output Format

The pipeline produces structured predictions:

```json
{
  "forecast_dates": ["2025-11-13", "2025-11-14", ...],
  "predictions": [100.5, 102.3, 105.1, ...],
  "uncertainty": [8.2, 8.5, 8.9, ...],
  "confidence_intervals": {
    "68%": {
      "lower": [92.3, 93.8, ...],
      "upper": [108.7, 110.8, ...]
    },
    "95%": {
      "lower": [84.1, 85.3, ...],
      "upper": [116.9, 119.3, ...]
    }
  },
  "median": [100.2, 102.1, ...],
  "metadata": {
    "model_version": "v1",
    "generated_at": "2025-11-12T06:00:00Z",
    "forecast_start": "2025-11-13",
    "forecast_end": "2025-12-12",
    "horizon_days": 30
  }
}
```

## Database Schema

Predictions are stored in PostgreSQL for historical tracking:

```sql
CREATE TABLE ml_predictions (
    id SERIAL PRIMARY KEY,
    forecast_date DATE NOT NULL,
    prediction FLOAT NOT NULL,
    uncertainty FLOAT,
    lower_95 FLOAT,
    upper_95 FLOAT,
    median FLOAT,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(forecast_date, model_version)
);
```

### Views

**ml_predictions_latest**: Latest prediction for each date
```sql
SELECT * FROM ml_predictions_latest WHERE forecast_date > CURRENT_DATE;
```

**ml_prediction_accuracy**: Actual vs predicted (when ground truth available)
```sql
SELECT * FROM ml_prediction_accuracy WHERE absolute_error < 10;
```

### Functions

**get_prediction(date)**: Get prediction for specific date
```sql
SELECT * FROM get_prediction('2025-11-15');
```

**calculate_model_metrics(start_date, end_date)**: Performance metrics
```sql
SELECT * FROM calculate_model_metrics(CURRENT_DATE - 30, CURRENT_DATE);
```

## Scheduling Options

### 1. Cron (Traditional)

**Advantages**: Simple, reliable, built-in to most systems

```bash
# Edit crontab
crontab -e

# Daily at 6:00 AM
0 6 * * * cd /path/to/ml && /path/to/ml/venv/bin/python scripts/daily_inference.py >> logs/ml/daily_inference.log 2>&1

# Every 6 hours
0 */6 * * * cd /path/to/ml && /path/to/ml/venv/bin/python scripts/daily_inference.py >> logs/ml/daily_inference.log 2>&1

# Twice daily (6 AM and 6 PM)
0 6,18 * * * cd /path/to/ml && /path/to/ml/venv/bin/python scripts/daily_inference.py >> logs/ml/daily_inference.log 2>&1
```

### 2. Systemd Timer (Modern Linux)

**Advantages**: Better logging, dependency management, monitoring

```bash
# Create service file: /etc/systemd/system/solar-inference.service
[Unit]
Description=Solar Cycle Daily Inference
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/ml
ExecStart=/path/to/ml/venv/bin/python scripts/daily_inference.py

[Install]
WantedBy=multi-user.target

# Create timer file: /etc/systemd/system/solar-inference.timer
[Unit]
Description=Solar Inference Timer
Requires=solar-inference.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable solar-inference.timer
sudo systemctl start solar-inference.timer

# Check status
sudo systemctl status solar-inference.timer
sudo systemctl list-timers
```

### 3. Docker Compose

**Advantages**: Containerized, portable, integrated with ML service

Add to `docker-compose.ml.yml`:

```yaml
services:
  inference-scheduler:
    image: solar-ml-api:latest
    container_name: solar-inference-scheduler
    command: >
      bash -c "while true; do
        python scripts/daily_inference.py
        sleep 86400  # 24 hours
      done"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
    volumes:
      - ./models:/app/models
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - solar-network
    restart: unless-stopped
```

### 4. Kubernetes CronJob

**Advantages**: Cloud-native, scalable, automatic retries

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: solar-inference
spec:
  schedule: "0 6 * * *"  # Daily at 6:00 AM
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: inference
            image: solar-ml-api:latest
            command: ["python", "scripts/daily_inference.py"]
            env:
            - name: DB_HOST
              value: postgres-service
            - name: REDIS_HOST
              value: redis-service
            volumeMounts:
            - name: models
              mountPath: /app/models
          restartPolicy: OnFailure
          volumes:
          - name: models
            persistentVolumeClaim:
              claimName: ml-models-pvc
```

### 5. AWS Lambda (Serverless)

**Advantages**: No server management, pay-per-use, auto-scaling

```python
# lambda_handler.py
import boto3
import subprocess

def lambda_handler(event, context):
    # Download model from S3
    s3 = boto3.client('s3')
    s3.download_file('my-bucket', 'models/best_model.pth', '/tmp/model.pth')

    # Run inference
    result = subprocess.run(['python', 'daily_inference.py'], capture_output=True)

    return {
        'statusCode': 200,
        'body': result.stdout
    }

# Schedule with EventBridge
# Rule: cron(0 6 * * ? *)  # Daily at 6:00 AM UTC
```

## Monitoring

### Status Dashboard

```bash
python scripts/monitor_inference.py
```

Displays:
- System status (Redis, Database)
- Cache status (active/empty, TTL)
- Recent predictions (next 7 days)
- Model performance metrics (RMSE, MAE, MAPE)
- Log file status

### Metrics to Track

1. **Execution Time**
   - Target: < 5 minutes
   - Alert if > 10 minutes

2. **Cache Hit Rate**
   - Target: > 80%
   - Measure API requests served from cache

3. **Prediction Accuracy** (when ground truth available)
   - RMSE: Target < 15 SSN units
   - MAE: Target < 12 SSN units
   - 95% Coverage: Target > 90%

4. **Data Freshness**
   - Latest data < 2 days old
   - Alert if > 3 days old

5. **Error Rate**
   - Target: < 1% failures
   - Alert on consecutive failures

### Logging

**Log Location**: `logs/ml/daily_inference.log`

**Log Levels**:
- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Failures that need attention

**Example Log Entry**:
```
2025-11-12 06:00:15 - __main__ - INFO - Daily Inference Pipeline - Solar Cycle Predictions
2025-11-12 06:00:16 - __main__ - INFO - Step 1: Loading model from registry...
2025-11-12 06:00:17 - __main__ - INFO - ✓ Model loaded (version: v1)
2025-11-12 06:00:17 - __main__ - INFO - Step 2: Fetching latest 90 days of data...
2025-11-12 06:00:20 - __main__ - INFO - ✓ Fetched data from 2025-08-14 to 2025-11-12
...
2025-11-12 06:00:45 - __main__ - INFO - ✓ Daily inference pipeline completed successfully!
```

### Alerts

Configure alerts for:

1. **Pipeline Failure**
   - Trigger: Exit code != 0
   - Action: Email/Slack notification

2. **Stale Predictions**
   - Trigger: Latest prediction > 48 hours old
   - Action: Run manual inference

3. **Database Issues**
   - Trigger: Cannot save predictions
   - Action: Check database connection

4. **Model Performance Degradation**
   - Trigger: RMSE > 20 for 7 consecutive days
   - Action: Trigger retraining

## Troubleshooting

### Common Issues

**1. Model Not Found**
```
Error: Model not found: models/short_term_lstm/best_model.pth

Solution:
- Train model first: python src/training/train_short_term.py
- Or download pre-trained model
- Check path in config.yaml
```

**2. Data Download Fails**
```
Error: Failed to download SIDC data

Solution:
- Check internet connection
- Verify SIDC website is accessible
- Use cached data: Skip download, use existing processed data
- Manual download from https://www.sidc.be/SILSO/datafiles
```

**3. Redis Connection Error**
```
Error: redis.exceptions.ConnectionError

Solution:
- Start Redis: docker-compose up -d redis
- Check REDIS_HOST environment variable
- Disable caching: Set cache_enabled = False in code
```

**4. Database Connection Error**
```
Error: psycopg2.OperationalError

Solution:
- Start PostgreSQL: docker-compose up -d postgres
- Check DB credentials in .env
- Run migration: psql < scripts/add_ml_predictions_table.sql
```

**5. Out of Memory**
```
Error: RuntimeError: CUDA out of memory

Solution:
- Reduce n_samples (default: 10 -> 5)
- Use CPU instead: gpu.enabled: false in config
- Close other applications
```

**6. Stale Predictions**
```
Warning: Latest prediction is 3 days old

Solution:
- Check if cron job is running: crontab -l
- Check logs for errors: tail -f logs/ml/daily_inference.log
- Run manually: python scripts/daily_inference.py
- Verify scheduler is active: systemctl status solar-inference.timer
```

## Performance Optimization

### Speed Improvements

1. **Model Optimization**
   - Convert to TorchScript: `torch.jit.script(model)`
   - Use ONNX runtime
   - Quantization (INT8)
   - Reduce n_samples for uncertainty (10 -> 5)

2. **Data Pipeline**
   - Cache preprocessed features
   - Parallel data loading
   - Incremental updates (only new data)

3. **Caching**
   - Longer TTL for stable predictions
   - Cache intermediate results
   - Use Redis pipeline for bulk operations

### Memory Optimization

1. **Batch Size**
   - Process in smaller batches
   - Clear GPU cache: `torch.cuda.empty_cache()`

2. **Data Loading**
   - Stream data instead of loading all at once
   - Use memory-mapped files for large datasets

3. **Model Size**
   - Use smaller model variants
   - Pruning and distillation

## Best Practices

1. **Scheduling**
   - Run after new data is typically available (6 AM)
   - Avoid peak traffic hours
   - Use retry logic for transient failures

2. **Monitoring**
   - Check logs daily
   - Set up alerts for failures
   - Track prediction accuracy over time

3. **Maintenance**
   - Clean old logs (keep last 30 days)
   - Archive old predictions
   - Retrain model monthly
   - Update data pipeline as needed

4. **Security**
   - Use environment variables for credentials
   - Restrict database permissions
   - Encrypt sensitive data
   - Regular security updates

## Integration with Backend API

### Endpoint Setup

Add to Node.js backend (`src/routes/mlRoutes.js`):

```javascript
router.post('/api/ml/predictions/update', async (req, res) => {
  try {
    const predictions = req.body;

    // Validate predictions
    if (!predictions.forecast_dates || !predictions.predictions) {
      return res.status(400).json({ error: 'Invalid prediction format' });
    }

    // Store in database or cache
    await storePredictions(predictions);

    res.json({
      success: true,
      message: 'Predictions updated',
      count: predictions.forecast_dates.length
    });

  } catch (error) {
    console.error('Error updating predictions:', error);
    res.status(500).json({ error: 'Failed to update predictions' });
  }
});
```

### Environment Variables

```env
# Backend API
BACKEND_API_URL=http://localhost:3000

# ML Service
ML_API_URL=http://localhost:8000
```

## Summary

The daily inference pipeline provides:

✅ **Automated Predictions** - Runs daily without manual intervention
✅ **High Performance** - < 5 minute execution time
✅ **Uncertainty Quantification** - Confidence intervals for all predictions
✅ **Reliable Caching** - 24-hour TTL in Redis
✅ **Historical Tracking** - All predictions saved to database
✅ **Comprehensive Monitoring** - Status dashboard and metrics
✅ **Flexible Scheduling** - Cron, systemd, Docker, Kubernetes
✅ **Error Handling** - Retry logic and graceful degradation
✅ **Scalable** - Can run in containers or serverless

---

**For questions or issues, refer to the main ML documentation or monitoring dashboard.**
