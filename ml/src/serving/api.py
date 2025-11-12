"""
FastAPI Model Serving Service for Solar Cycle ML Models
Provides REST API endpoints for model inference
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import torch
import numpy as np
import pandas as pd
import yaml
import logging
from datetime import datetime, timedelta
import redis
import json
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response

from models.short_term_lstm import ShortTermLSTM
from models.long_term_lstm_fcn import LongTermLSTM_FCN
from models.anomaly_autoencoder import AnomalyAutoencoder
from models.ensemble import WeightedEnsemble

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
prediction_counter = Counter('ml_predictions_total', 'Total predictions', ['model'])
prediction_duration = Histogram('ml_prediction_duration_seconds', 'Prediction duration', ['model'])
error_counter = Counter('ml_errors_total', 'Total errors', ['error_type'])

# Initialize FastAPI app
app = FastAPI(
    title="Solar Cycle ML API",
    description="Machine Learning models for solar activity prediction",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Request/Response models
class ShortTermPredictionRequest(BaseModel):
    """Request model for short-term predictions"""
    historical_data: List[List[float]] = Field(
        ...,
        description="Historical features (window_size x num_features)",
        min_items=90,
        max_items=90
    )
    confidence_intervals: List[float] = Field(
        default=[0.68, 0.95],
        description="Confidence interval levels (e.g., [0.68, 0.95])"
    )
    n_samples: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of MC dropout samples for uncertainty"
    )


class ShortTermPredictionResponse(BaseModel):
    """Response model for short-term predictions"""
    predictions: List[float] = Field(..., description="Point predictions for each day")
    uncertainty: List[float] = Field(..., description="Uncertainty (std dev) for each day")
    confidence_intervals: Dict[str, List[float]] = Field(
        ...,
        description="Confidence intervals (e.g., {'q05': [...], 'q95': [...]})"
    )
    forecast_dates: List[str] = Field(..., description="Dates for predictions")
    model_version: str = Field(..., description="Model version")
    timestamp: str = Field(..., description="Prediction timestamp")


class LongTermPredictionRequest(BaseModel):
    """Request model for long-term cycle predictions"""
    historical_data: List[List[float]] = Field(
        ...,
        description="Historical monthly features (264 months)",
        min_items=264,
        max_items=264
    )
    n_samples: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of samples for Bayesian uncertainty"
    )


class LongTermPredictionResponse(BaseModel):
    """Response model for long-term predictions"""
    cycle_amplitude: Dict[str, float] = Field(
        ...,
        description="Cycle amplitude prediction with uncertainty"
    )
    peak_time: Dict[str, float] = Field(
        ...,
        description="Time to peak (months) with uncertainty"
    )
    cycle_duration: Dict[str, float] = Field(
        ...,
        description="Cycle duration (months) with uncertainty"
    )
    ascent_rate: Dict[str, float] = Field(
        ...,
        description="Ascending phase rate with uncertainty"
    )
    timestamp: str


class AnomalyDetectionRequest(BaseModel):
    """Request model for anomaly detection"""
    recent_data: List[List[float]] = Field(
        ...,
        description="Recent observations for anomaly detection",
        min_items=1,
        max_items=100
    )
    threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Anomaly threshold (0-1)"
    )


class AnomalyDetectionResponse(BaseModel):
    """Response model for anomaly detection"""
    anomaly_scores: List[float] = Field(..., description="Anomaly scores (0-1)")
    is_anomaly: List[bool] = Field(..., description="Anomaly flags")
    mean_score: float = Field(..., description="Mean anomaly score")
    max_score: float = Field(..., description="Maximum anomaly score")
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    models_loaded: Dict[str, bool]
    timestamp: str


# Model manager
class ModelManager:
    """Manages loading and caching of ML models"""

    def __init__(self, config_path: str = "../../configs/config.yaml"):
        """Initialize model manager"""
        self.config = self._load_config(config_path)
        self.models_dir = Path(self.config['paths']['models'])
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Model cache
        self.models = {}

        # Redis cache
        redis_config = self.config['redis']
        try:
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                db=redis_config['db'],
                decode_responses=True
            )
            self.cache_enabled = True
            logger.info("Redis cache enabled")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.cache_enabled = False

        logger.info(f"Using device: {self.device}")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        config_file = Path(__file__).parent / config_path
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def load_short_term_model(self) -> ShortTermLSTM:
        """Load short-term LSTM model"""
        if 'short_term' not in self.models:
            logger.info("Loading short-term LSTM model...")

            model_path = self.models_dir / 'short_term_lstm' / 'best_model.pth'

            if not model_path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")

            checkpoint = torch.load(model_path, map_location=self.device)

            # Create model
            config = checkpoint['config']
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

            self.models['short_term'] = model
            logger.info("✓ Short-term model loaded")

        return self.models['short_term']

    def load_anomaly_model(self) -> AnomalyAutoencoder:
        """Load anomaly detection model"""
        if 'anomaly' not in self.models:
            logger.info("Loading anomaly detection model...")

            model_path = self.models_dir / 'anomaly_autoencoder' / 'best_model.pth'

            if not model_path.exists():
                # Create dummy model for demo
                logger.warning("Anomaly model not found, using default")
                model = AnomalyAutoencoder(
                    input_size=20,
                    encoder_layers=[64, 32, 16, 8],
                    latent_dim=4
                ).to(self.device)
            else:
                checkpoint = torch.load(model_path, map_location=self.device)
                config = checkpoint['config']
                model = AnomalyAutoencoder(
                    input_size=checkpoint['model_state_dict']['encoder.0.weight'].shape[1],
                    encoder_layers=config['architecture']['encoder_layers'],
                    latent_dim=config['architecture']['latent_dim']
                ).to(self.device)
                model.load_state_dict(checkpoint['model_state_dict'])

            model.eval()
            self.models['anomaly'] = model
            logger.info("✓ Anomaly model loaded")

        return self.models['anomaly']

    def get_cache_key(self, prefix: str, data: np.ndarray) -> str:
        """Generate cache key from input data"""
        data_hash = hash(data.tobytes())
        return f"{prefix}:{data_hash}"

    def get_from_cache(self, key: str) -> Optional[Dict]:
        """Get prediction from cache"""
        if not self.cache_enabled:
            return None

        try:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache get error: {e}")

        return None

    def save_to_cache(self, key: str, value: Dict, ttl: int = 900):
        """Save prediction to cache"""
        if not self.cache_enabled:
            return

        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Cache set error: {e}")


# Initialize model manager
model_manager = ModelManager()


# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Load models on startup"""
    logger.info("Starting ML API server...")
    try:
        model_manager.load_short_term_model()
        model_manager.load_anomaly_model()
        logger.info("All models loaded successfully")
    except Exception as e:
        logger.error(f"Error loading models: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    models_loaded = {
        'short_term': 'short_term' in model_manager.models,
        'anomaly': 'anomaly' in model_manager.models
    }

    return HealthResponse(
        status="healthy" if all(models_loaded.values()) else "degraded",
        models_loaded=models_loaded,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/predict/short-term", response_model=ShortTermPredictionResponse)
async def predict_short_term(request: ShortTermPredictionRequest):
    """
    Make short-term predictions (1-30 days)
    """
    try:
        prediction_counter.labels(model='short_term').inc()

        with prediction_duration.labels(model='short_term').time():
            # Load model
            model = model_manager.load_short_term_model()

            # Prepare input
            input_data = torch.FloatTensor(request.historical_data).unsqueeze(0)  # (1, seq, features)
            input_data = input_data.to(model_manager.device)

            # Check cache
            cache_key = model_manager.get_cache_key('short_term', input_data.cpu().numpy())
            cached_result = model_manager.get_from_cache(cache_key)

            if cached_result:
                logger.info("Returning cached prediction")
                return ShortTermPredictionResponse(**cached_result)

            # Make prediction with uncertainty
            mean, std, quantiles = model.predict_with_uncertainty(
                input_data,
                n_samples=request.n_samples
            )

            # Generate forecast dates
            start_date = datetime.now() + timedelta(days=1)
            forecast_dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d')
                            for i in range(len(mean[0]))]

            # Prepare response
            response_data = {
                'predictions': mean[0].tolist(),
                'uncertainty': std[0].tolist(),
                'confidence_intervals': {
                    key: value[0].tolist() for key, value in quantiles.items()
                },
                'forecast_dates': forecast_dates,
                'model_version': '1.0.0',
                'timestamp': datetime.utcnow().isoformat()
            }

            # Cache result
            model_manager.save_to_cache(cache_key, response_data)

            return ShortTermPredictionResponse(**response_data)

    except Exception as e:
        error_counter.labels(error_type='prediction_error').inc()
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/anomaly", response_model=AnomalyDetectionResponse)
async def detect_anomalies(request: AnomalyDetectionRequest):
    """
    Detect anomalies in recent solar activity
    """
    try:
        prediction_counter.labels(model='anomaly').inc()

        with prediction_duration.labels(model='anomaly').time():
            # Load model
            model = model_manager.load_anomaly_model()

            # Prepare input
            input_data = torch.FloatTensor(request.recent_data)
            input_data = input_data.to(model_manager.device)

            # Detect anomalies
            is_anomaly, scores = model.detect_anomalies(input_data, threshold=request.threshold)

            response = AnomalyDetectionResponse(
                anomaly_scores=scores.tolist(),
                is_anomaly=is_anomaly.tolist(),
                mean_score=float(scores.mean()),
                max_score=float(scores.max()),
                timestamp=datetime.utcnow().isoformat()
            )

            return response

    except Exception as e:
        error_counter.labels(error_type='anomaly_error').inc()
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Solar Cycle ML API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "short_term_prediction": "/predict/short-term",
            "anomaly_detection": "/predict/anomaly",
            "metrics": "/metrics"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
