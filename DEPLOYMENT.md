# Solar Cycle API - Quick Start Deployment Guide

## Option 1: Docker (Recommended - Fastest)

```bash
# Clone and start
git clone <repository-url>
cd Sun
cp .env.example .env
docker-compose up -d

# Verify
curl http://localhost:3000/health
```

Access the API:
- API: http://localhost:3000
- Documentation: http://localhost:3000/api-docs
- WebSocket: ws://localhost:3000/ws/live

## Option 2: Local Development

```bash
# Install dependencies
npm install

# Start PostgreSQL and Redis (using Docker)
docker run -d --name solar-postgres -e POSTGRES_PASSWORD=solar_pass -p 5432:5432 postgres:15-alpine
docker run -d --name solar-redis -p 6379:6379 redis:7-alpine

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Start the server
npm run dev
```

## Quick Test

```bash
# Health check
curl http://localhost:3000/health

# Get current solar status
curl http://localhost:3000/api/current-status

# Get historical data
curl "http://localhost:3000/api/sunspot-history?range=1y"

# Get forecast
curl http://localhost:3000/api/forecast
```

## Production Deployment

### AWS

```bash
# Build and push to ECR
docker build -t solar-cycle-api .
docker tag solar-cycle-api:latest <account>.dkr.ecr.us-east-1.amazonaws.com/solar-cycle-api:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/solar-cycle-api:latest

# Deploy to ECS/Fargate
# Set environment variables in task definition
# Use RDS for PostgreSQL and ElastiCache for Redis
```

### Google Cloud

```bash
# Build and push to GCR
docker build -t solar-cycle-api .
docker tag solar-cycle-api gcr.io/<project>/solar-cycle-api
docker push gcr.io/<project>/solar-cycle-api

# Deploy to Cloud Run
gcloud run deploy solar-cycle-api \
  --image gcr.io/<project>/solar-cycle-api \
  --platform managed \
  --allow-unauthenticated
```

## Environment Variables (Production)

Required variables:
```env
NODE_ENV=production
PORT=3000
DB_HOST=<your-db-host>
DB_PASSWORD=<secure-password>
REDIS_HOST=<your-redis-host>
```

## Monitoring

Check service health:
```bash
curl http://localhost:3000/health
```

View logs:
```bash
# Docker
docker-compose logs -f api

# Local
tail -f logs/app.log
```

## Troubleshooting

**Database connection failed:**
```bash
docker-compose logs postgres
docker-compose restart postgres
```

**Redis connection failed:**
```bash
docker-compose logs redis
docker-compose restart redis
```

**Port already in use:**
```bash
# Change PORT in .env
PORT=3001
```

## Documentation

- Full README: [README.md](README.md)
- Setup Guide: [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)
- API Reference: [docs/API.md](docs/API.md)
- Interactive API Docs: http://localhost:3000/api-docs

## Support

Issues: Create an issue in the GitHub repository
