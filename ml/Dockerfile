# ML Service Dockerfile for Solar Cycle Prediction

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY configs/ ./configs/
COPY models/ ./models/
COPY data/ ./data/

# Create directories for logs and mlruns
RUN mkdir -p logs/ml mlruns

# Expose port for FastAPI
EXPOSE 8000

# Expose port for Prometheus metrics
EXPOSE 9090

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI server
CMD ["uvicorn", "src.serving.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
