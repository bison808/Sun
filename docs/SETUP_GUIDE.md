# Solar Cycle API - Setup Guide

Complete guide for setting up the Solar Cycle API in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Setup (Recommended)](#docker-setup-recommended)
3. [Local Development Setup](#local-development-setup)
4. [Production Deployment](#production-deployment)
5. [Configuration](#configuration)
6. [Database Setup](#database-setup)
7. [Verification](#verification)
8. [Common Issues](#common-issues)

## Prerequisites

### Required Software

- **Node.js**: Version 18.x or higher
  ```bash
  node --version  # Should be >= 18.0.0
  ```

- **npm**: Version 9.x or higher
  ```bash
  npm --version   # Should be >= 9.0.0
  ```

- **Docker**: Latest stable version
  ```bash
  docker --version
  ```

- **Docker Compose**: Version 2.x or higher
  ```bash
  docker-compose --version
  ```

### Optional (for local development without Docker)

- **PostgreSQL**: Version 15 or higher
- **Redis**: Version 7 or higher

## Docker Setup (Recommended)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Sun
```

### Step 2: Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` if needed. Default values work for Docker Compose setup.

### Step 3: Start Services

```bash
# Start all services (PostgreSQL, Redis, API)
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Step 4: Verify Installation

```bash
# Health check
curl http://localhost:3000/health

# Get current solar status
curl http://localhost:3000/api/current-status

# Access API documentation
open http://localhost:3000/api-docs
```

### Step 5: Stop Services

```bash
# Stop services
docker-compose down

# Stop and remove volumes (deletes data)
docker-compose down -v
```

## Local Development Setup

### Step 1: Install Dependencies

```bash
npm install
```

### Step 2: Setup PostgreSQL

#### Using Docker for PostgreSQL only:
```bash
docker run -d \
  --name solar-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=solar_cycle_db \
  -p 5432:5432 \
  postgres:15-alpine
```

#### Using local PostgreSQL:
```bash
# Create database
createdb solar_cycle_db

# Or using psql
psql -U postgres
CREATE DATABASE solar_cycle_db;
\q
```

### Step 3: Setup Redis

#### Using Docker for Redis only:
```bash
docker run -d \
  --name solar-redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### Using local Redis:
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

### Step 4: Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
NODE_ENV=development
PORT=3000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=solar_cycle_db
DB_USER=postgres
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Logging
LOG_LEVEL=debug
```

### Step 5: Start Development Server

```bash
# With auto-reload
npm run dev

# Or standard start
npm start
```

### Step 6: Run Tests

```bash
# All tests
npm test

# Unit tests only
npm run test:unit

# With coverage
npm test -- --coverage
```

## Production Deployment

### AWS/GCP Deployment

#### Step 1: Build Docker Image

```bash
docker build -t solar-cycle-api:latest .
```

#### Step 2: Push to Container Registry

```bash
# AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag solar-cycle-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/solar-cycle-api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/solar-cycle-api:latest

# Google Container Registry
docker tag solar-cycle-api:latest gcr.io/<project-id>/solar-cycle-api:latest
docker push gcr.io/<project-id>/solar-cycle-api:latest
```

#### Step 3: Set Environment Variables

Create a production `.env` file or use your cloud provider's secret management:

```env
NODE_ENV=production
PORT=3000

# Use managed database endpoints
DB_HOST=your-rds-endpoint.amazonaws.com
DB_PORT=5432
DB_NAME=solar_cycle_db
DB_USER=admin
DB_PASSWORD=<secure-password>

# Use managed Redis
REDIS_HOST=your-elasticache-endpoint.amazonaws.com
REDIS_PORT=6379

# Production settings
RATE_LIMIT_MAX_REQUESTS=100
LOG_LEVEL=info
```

#### Step 4: Deploy

**AWS ECS/Fargate:**
```bash
# Create task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-def.json

# Create service
aws ecs create-service \
  --cluster solar-cycle-cluster \
  --service-name solar-cycle-api \
  --task-definition solar-cycle-api:1 \
  --desired-count 2
```

**Google Cloud Run:**
```bash
gcloud run deploy solar-cycle-api \
  --image gcr.io/<project-id>/solar-cycle-api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/

# Check deployment
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/solar-cycle-api
```

## Configuration

### Environment Variables Reference

#### Server Configuration
```env
NODE_ENV=development|production
PORT=3000
API_VERSION=v1
```

#### Database Configuration
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=solar_cycle_db
DB_USER=postgres
DB_PASSWORD=secure_password
DB_POOL_MIN=2
DB_POOL_MAX=10
```

#### Redis Configuration
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
CACHE_TTL=3600
```

#### External APIs
```env
NOAA_SWPC_BASE_URL=https://services.swpc.noaa.gov
NASA_API_KEY=your_key_here
```

#### Rate Limiting
```env
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=100
```

#### Data Fetching
```env
DATA_FETCH_INTERVAL_MINUTES=15
RETRY_MAX_ATTEMPTS=3
RETRY_DELAY_MS=2000
```

#### Logging
```env
LOG_LEVEL=info|debug|warn|error
LOG_FILE_PATH=./logs/app.log
```

## Database Setup

### Initial Setup

The application automatically creates tables on first run. To manually initialize:

```bash
# Using Docker Compose
docker-compose exec postgres psql -U postgres -d solar_cycle_db -f /docker-entrypoint-initdb.d/init.sql

# Using local PostgreSQL
psql -U postgres -d solar_cycle_db -f scripts/init-db.sql
```

### Database Migrations

```bash
npm run db:migrate
```

### Seed Data (Optional)

```bash
npm run db:seed
```

### Database Backup

```bash
# Docker Compose
docker-compose exec postgres pg_dump -U postgres solar_cycle_db > backup.sql

# Local
pg_dump solar_cycle_db > backup.sql
```

### Database Restore

```bash
# Docker Compose
docker-compose exec -T postgres psql -U postgres solar_cycle_db < backup.sql

# Local
psql solar_cycle_db < backup.sql
```

## Verification

### Health Check

```bash
curl http://localhost:3000/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T12:00:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "noaa": "healthy"
  }
}
```

### Test API Endpoints

```bash
# Current status
curl http://localhost:3000/api/current-status

# Historical data
curl "http://localhost:3000/api/sunspot-history?range=1y"

# Forecast
curl http://localhost:3000/api/forecast

# Alerts
curl http://localhost:3000/api/alerts
```

### Check Logs

```bash
# Docker
docker-compose logs -f api

# Local
tail -f logs/app.log
```

### Monitor Data Fetching

The application fetches data every 15 minutes. Check logs for:
```
[info]: Starting data fetch cycle
[info]: Data fetch cycle completed successfully
```

## Common Issues

### Issue: Cannot connect to database

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U postgres -c "SELECT 1"
```

### Issue: Redis connection failed

**Solution:**
```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis
docker-compose exec redis redis-cli ping
```

### Issue: Port already in use

**Solution:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or change PORT in .env
PORT=3001
```

### Issue: NOAA API fetch failed

**Solution:**
- Check internet connection
- Verify NOAA service is up: https://services.swpc.noaa.gov
- Check retry settings in .env
- Review logs for specific error

### Issue: High memory usage

**Solution:**
```bash
# Adjust database connection pool
DB_POOL_MAX=5

# Reduce cache TTL
CACHE_TTL=1800

# Restart services
docker-compose restart
```

### Issue: Tests failing

**Solution:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Run tests with verbose output
npm test -- --verbose

# Check test database
NODE_ENV=test npm test
```

## Next Steps

1. **Configure monitoring**: Set up monitoring tools (Prometheus, Grafana)
2. **Set up alerts**: Configure alerting for critical errors
3. **Enable HTTPS**: Use reverse proxy (nginx) with SSL certificates
4. **Implement CI/CD**: Set up automated testing and deployment
5. **Scale horizontally**: Deploy multiple instances behind load balancer
6. **Optimize caching**: Fine-tune Redis TTL values
7. **Add ML models**: Integrate machine learning predictions

## Support

For additional help:
- Check API documentation: http://localhost:3000/api-docs
- Review main README: [README.md](../README.md)
- Create an issue in the repository
