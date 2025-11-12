# Solar Cycle ML Models - Complete Setup Guide

This guide provides step-by-step instructions for setting up, training, and deploying the machine learning models for solar activity prediction.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Model Training](#model-training)
5. [API Deployment](#api-deployment)
6. [Integration with Node.js Backend](#integration-with-nodejs-backend)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What's Included

The ML service provides four specialized models:

1. **Short-Term LSTM (Priority 1)**
   - Predicts daily sunspot numbers for 1-90 days ahead
   - Bidirectional LSTM with attention mechanism
   - Uncertainty quantification via Monte Carlo dropout
   - Daily updates, 15-minute cache TTL

2. **Long-Term LSTM-FCN (Priority 2)**
   - Predicts solar cycle characteristics (amplitude, peak timing, duration)
   - Hybrid LSTM + Fully Convolutional Network architecture
   - Multi-task learning for cycle parameters
   - Monthly updates, Bayesian uncertainty estimation

3. **Anomaly Detection Autoencoder (Priority 3)**
   - Detects unusual patterns in solar activity
   - Autoencoder with reconstruction error analysis
   - Real-time inference, 0-1 anomaly scores
   - Optional: Variational Autoencoder (VAE) for probabilistic detection

4. **Ensemble Meta-Learner (Priority 4)**
   - Combines predictions from multiple models
   - Weighted averaging with learned or performance-based weights
   - Stacking ensemble with neural network meta-learner
   - Adaptive weighting based on recent performance

### Tech Stack

- **ML Framework**: PyTorch 2.1.2
- **Model Serving**: FastAPI + Uvicorn
- **Data Processing**: Pandas, NumPy, SciPy
- **MLOps**: MLflow, DVC, Weights & Biases (optional)
- **Experiment Tracking**: MLflow
- **Model Monitoring**: Custom metrics + Prometheus
- **Containerization**: Docker, Docker Compose
- **Cache**: Redis
- **Database**: PostgreSQL

---

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Navigate to ML directory
cd ml/

# Run automated setup script
chmod +x scripts/setup_pipeline.sh
./scripts/setup_pipeline.sh

# This will:
# 1. Create virtual environment
# 2. Install dependencies
# 3. Download solar data from SIDC/NOAA
# 4. Preprocess and engineer features
# 5. Prepare data for training
```

### Option 2: Docker (Fastest for Deployment)

```bash
cd ml/

# Build and start all services (ML API, MLflow, Redis, PostgreSQL)
docker-compose -f docker-compose.ml.yml up -d

# Check status
docker-compose -f docker-compose.ml.yml ps

# View logs
docker-compose -f docker-compose.ml.yml logs -f ml-api
```

### Option 3: Manual Setup

```bash
cd ml/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run data pipeline
python src/data/download_data.py
python src/data/preprocess.py
python src/data/feature_engineering.py

# Train models (optional - pre-trained models may be provided)
python src/training/train_short_term.py

# Start API server
uvicorn src.serving.api:app --host 0.0.0.0 --port 8000
```

---

## Detailed Setup

### 1. System Requirements

**Minimum:**
- Python 3.10+
- 8GB RAM
- 10GB disk space
- CPU: 4 cores

**Recommended:**
- Python 3.10+
- 16GB RAM
- 50GB disk space
- GPU: NVIDIA with CUDA 11.8+ (for training)
- CPU: 8+ cores

### 2. Data Pipeline

#### Download Data

```bash
python src/data/download_data.py
```

**Data Sources:**
- **SIDC Sunspot Numbers**: Daily data from 1749-present
- **NOAA F10.7 Radio Flux**: Solar radio flux measurements
- **Geomagnetic Indices**: Kp index for geomagnetic activity

**Output:**
- `data/raw/sidc_sunspot_daily.csv` (~100,000 records)
- `data/raw/sidc_sunspot_monthly.csv` (~3,000 records)
- `data/raw/noaa_f107_historical.csv` (if available)
- `data/raw/noaa_f107_recent.csv`
- `data/raw/noaa_kp_recent.csv`

#### Preprocess Data

```bash
python src/data/preprocess.py
```

**Processing Steps:**
1. Handle missing values (interpolation, forward fill)
2. Normalize features (MinMax scaling 0-1)
3. Add 13-month smoothed SSN (Butterworth filter)
4. Identify solar cycle phases
5. Create temporal features

**Output:**
- `data/processed/daily_processed.csv`
- `data/processed/monthly_processed.csv`
- `data/processed/scalers.joblib` (for inverse transforms)

#### Engineer Features

```bash
python src/data/feature_engineering.py
```

**Features Created:**
- **Moving Averages**: 6, 12, 24 month windows
- **Rate of Change**: 1, 3, 6, 12 month periods
- **Fourier Components**: 11, 22, 132 year cycles
- **Lag Features**: 1, 3, 6, 12, 24 period lags
- **Statistical Features**: mean, std, min, max, skewness, kurtosis
- **Cycle Features**: days in cycle, cycle progress, position relative to max
- **Momentum Indicators**: RSI, MACD, Bollinger Bands

**Output:**
- `data/features/daily_features.csv` (~50+ features)
- `data/features/monthly_features.csv`

### 3. Configuration

Edit `configs/config.yaml` to customize:

```yaml
# Example customizations

# Data splits
data_splits:
  train:
    start: 1749
    end: 2010  # Extend training period

# Model architecture
short_term_lstm:
  architecture:
    lstm_layers: [256, 128, 64]  # Larger model
    dropout: 0.3

# Training
short_term_lstm:
  training:
    batch_size: 64
    epochs: 150
    learning_rate: 0.0005

# Serving
serving:
  api:
    workers: 8  # More workers
  caching:
    ttl: 1800  # 30 minute cache
```

---

## Model Training

### Short-Term LSTM

```bash
# Basic training
python src/training/train_short_term.py

# With custom config
python src/training/train_short_term.py --config configs/custom_config.yaml

# Monitor training
# Open another terminal:
mlflow ui --backend-store-uri file:///mlruns
# Visit http://localhost:5000
```

**Training Process:**
1. Load and split data (train/val/test)
2. Create PyTorch datasets and dataloaders
3. Initialize model, optimizer, scheduler
4. Training loop with early stopping
5. Save best model based on validation loss
6. Evaluate on test set
7. Log metrics to MLflow

**Expected Results:**
- Training time: 30-60 minutes (CPU), 10-20 minutes (GPU)
- Test RMSE: 10-15 SSN units
- Test MAE: 8-12 SSN units
- Model size: ~5-10 MB

**Output:**
- `models/short_term_lstm/best_model.pth`
- MLflow experiment logs
- Training plots in MLflow UI

### Long-Term LSTM-FCN

```bash
# Create training script if needed
python src/training/train_long_term.py

# This model predicts:
# - Cycle amplitude (max SSN)
# - Peak timing (months to peak)
# - Cycle duration (total months)
# - Ascent rate (SSN/month)
```

### Anomaly Detection

```bash
python src/training/train_anomaly.py

# Trains autoencoder on normal patterns
# Reconstruction error indicates anomalies
```

### Hyperparameter Tuning

```bash
# Use Optuna for automated tuning
python src/training/tune_hyperparameters.py --model short_term_lstm --n-trials 50

# Results logged to MLflow
# Best hyperparameters saved to config
```

---

## API Deployment

### Local Development

```bash
# Start API server
uvicorn src.serving.api:app --host 0.0.0.0 --port 8000 --reload

# API documentation: http://localhost:8000/docs
# Health check: http://localhost:8000/health
# Metrics: http://localhost:8000/metrics
```

### Docker Deployment

```bash
# Build Docker image
cd ml/
docker build -t solar-ml-api:latest .

# Run container
docker run -d \
  --name solar-ml-api \
  -p 8000:8000 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/data:/app/data \
  -e REDIS_HOST=host.docker.internal \
  solar-ml-api:latest

# Check logs
docker logs -f solar-ml-api
```

### Docker Compose (Full Stack)

```bash
# Start all services
docker-compose -f docker-compose.ml.yml up -d

# Services started:
# - ml-api (port 8000)
# - mlflow (port 5000)
# - postgres (port 5432)
# - redis (port 6379)

# Check status
docker-compose -f docker-compose.ml.yml ps

# Stop services
docker-compose -f docker-compose.ml.yml down
```

### Production Deployment

**AWS ECS:**
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t solar-ml-api .
docker tag solar-ml-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/solar-ml-api:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/solar-ml-api:latest

# Deploy ECS task definition
# Use AWS Console or Terraform
```

**Kubernetes:**
```bash
# Apply manifests
kubectl apply -f k8s/ml-deployment.yaml
kubectl apply -f k8s/ml-service.yaml

# Scale
kubectl scale deployment solar-ml-api --replicas=3
```

---

## Integration with Node.js Backend

### Update Node.js API

The Node.js backend needs to call the ML API for predictions. Update `src/controllers/solarController.js`:

```javascript
// src/controllers/solarController.js

const axios = require('axios');

// ML API configuration
const ML_API_URL = process.env.ML_API_URL || 'http://localhost:8000';

// Short-term prediction endpoint
exports.predictShortTerm = async (req, res, next) => {
  try {
    const { historical_data, confidence_intervals, n_samples } = req.body;

    // Call ML API
    const response = await axios.post(`${ML_API_URL}/predict/short-term`, {
      historical_data,
      confidence_intervals: confidence_intervals || [0.68, 0.95],
      n_samples: n_samples || 10
    }, {
      timeout: 30000  // 30 second timeout
    });

    res.json({
      success: true,
      data: response.data
    });

  } catch (error) {
    logger.error('ML prediction error:', error);
    res.status(500).json({
      success: false,
      error: 'Prediction failed',
      message: error.message
    });
  }
};

// Anomaly detection endpoint
exports.detectAnomaly = async (req, res, next) => {
  try {
    const { recent_data, threshold } = req.body;

    const response = await axios.post(`${ML_API_URL}/predict/anomaly`, {
      recent_data,
      threshold: threshold || 0.75
    });

    res.json({
      success: true,
      data: response.data
    });

  } catch (error) {
    logger.error('Anomaly detection error:', error);
    res.status(500).json({
      success: false,
      error: 'Anomaly detection failed'
    });
  }
};
```

### Environment Variables

Add to `.env`:

```env
# ML Service
ML_API_URL=http://ml-api:8000
ML_API_TIMEOUT=30000
```

### Docker Compose Integration

Update root `docker-compose.yml` to include ML service:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - ML_API_URL=http://ml-api:8000
    depends_on:
      - postgres
      - redis
      - ml-api
    networks:
      - solar-network

  ml-api:
    build: ./ml
    ports:
      - "8000:8000"
    volumes:
      - ./ml/models:/app/models
      - ./ml/data:/app/data
    depends_on:
      - redis
      - postgres
    networks:
      - solar-network

  postgres:
    image: postgres:15
    # ... existing config

  redis:
    image: redis:7-alpine
    # ... existing config

networks:
  solar-network:
    driver: bridge
```

---

## Monitoring & Maintenance

### Model Monitoring

**Metrics Tracked:**
- Prediction latency
- Throughput (requests/sec)
- Error rates
- Cache hit ratio
- Model accuracy (when ground truth available)
- Data drift detection
- Feature distribution changes

**Access Prometheus Metrics:**
```bash
curl http://localhost:8000/metrics

# Metrics available:
# - ml_predictions_total
# - ml_prediction_duration_seconds
# - ml_errors_total
```

### Automated Retraining

**Schedule:**
```bash
# Add to crontab
0 0 * * 0 cd /path/to/ml && python scripts/retrain_models.py

# Or use systemd timer
# Or use Kubernetes CronJob
```

**Manual Retraining:**
```bash
python scripts/retrain_models.py

# Checks for:
# 1. Data drift (KS test)
# 2. Performance degradation
# 3. Sufficient new data

# If needed, retrains models automatically
```

### Model Versioning

**MLflow Model Registry:**
```python
import mlflow

# Register model
mlflow.register_model(
    "runs:/<run-id>/model",
    "short_term_lstm"
)

# Promote to production
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="short_term_lstm",
    version=3,
    stage="Production"
)
```

### Logging

**Application Logs:**
```bash
# Location: logs/ml/ml_service.log

# View logs
tail -f logs/ml/ml_service.log

# Docker logs
docker-compose -f docker-compose.ml.yml logs -f ml-api
```

---

## Troubleshooting

### Common Issues

**1. CUDA/GPU Not Available**
```
Error: RuntimeError: CUDA out of memory

Solution:
- Reduce batch_size in config.yaml
- Set gpu.enabled: false to use CPU
- Close other GPU applications
```

**2. Data Download Fails**
```
Error: Failed to download SIDC data

Solution:
- Check internet connection
- Verify URLs in config.yaml
- Try manual download from https://www.sidc.be/SILSO/datafiles
- Place files in data/raw/
```

**3. Model Not Found**
```
Error: FileNotFoundError: Model not found

Solution:
- Train models first: python src/training/train_short_term.py
- Or download pre-trained models
- Check models/ directory exists
```

**4. Redis Connection Error**
```
Error: redis.exceptions.ConnectionError

Solution:
- Start Redis: docker-compose up -d redis
- Or disable caching in config.yaml: caching.enabled: false
- Check REDIS_HOST environment variable
```

**5. Out of Memory During Training**
```
Error: MemoryError or killed process

Solution:
- Reduce batch_size
- Reduce model size (fewer/smaller layers)
- Use smaller input_window
- Close other applications
- Add swap space
```

**6. Slow API Response**
```
Issue: Predictions taking > 5 seconds

Solution:
- Enable Redis caching
- Reduce n_samples for uncertainty (default: 10)
- Use GPU for inference
- Increase API workers
- Check model is loaded (not loading on each request)
```

### Performance Optimization

**Training:**
- Use GPU (10x faster)
- Enable mixed precision training
- Increase batch size (if memory allows)
- Use DataLoader with multiple workers
- Profile with PyTorch Profiler

**Inference:**
- Enable model caching
- Use TorchScript or ONNX export
- Batch inference when possible
- Use appropriate number of workers
- Enable Redis caching
- Profile API endpoints

### Getting Help

- Check logs: `logs/ml/ml_service.log`
- MLflow UI: http://localhost:5000
- API docs: http://localhost:8000/docs
- GitHub Issues: [repository]/issues

---

## Summary Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Data downloaded and preprocessed
- [ ] Features engineered
- [ ] Models trained (or pre-trained models available)
- [ ] API server running
- [ ] Redis and PostgreSQL accessible
- [ ] MLflow tracking setup
- [ ] Node.js backend integrated
- [ ] Monitoring configured
- [ ] Automated retraining scheduled
- [ ] Documentation reviewed

---

**🚀 You're ready to predict solar activity with machine learning!**

For questions or support, refer to the main README or open an issue on GitHub.
