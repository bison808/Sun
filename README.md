# Solar Cycle API

Backend API for Solar Cycle Mobile App - Real-time solar activity monitoring and predictions.

## Overview

The Solar Cycle API provides real-time solar activity data, historical sunspot information, solar event alerts, and AI-powered predictions. It integrates with NOAA SWPC, NASA, and SIDC data sources to deliver comprehensive space weather information.

## Features

- **Real-time Solar Data**: Current solar cycle metrics updated every 15 minutes
- **Historical Data**: Sunspot history with configurable time ranges (1y, 5y, full cycle)
- **Solar Events**: Recent solar activity alerts and notifications
- **Forecasting**: Predicted solar activity based on historical patterns
- **ML Predictions**: AI-powered short-term and long-term predictions
- **Anomaly Detection**: Real-time detection of unusual solar activity
- **WebSocket Support**: Live updates via WebSocket connection
- **Caching**: Redis-based caching for improved performance
- **Rate Limiting**: 100 requests/minute per user
- **API Documentation**: Interactive Swagger/OpenAPI documentation

## Tech Stack

- **Runtime**: Node.js 18+
- **Framework**: Express.js
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Real-time**: WebSocket (ws)
- **Documentation**: Swagger/OpenAPI
- **Testing**: Jest + Supertest
- **Containerization**: Docker + Docker Compose

## Prerequisites

- Node.js 18.x or higher
- npm 9.x or higher
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL 15+ (if running locally without Docker)
- Redis 7+ (if running locally without Docker)

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd Sun
```

2. Copy the environment file:
```bash
cp .env.example .env
```

3. Start all services with Docker Compose:
```bash
docker-compose up -d
```

4. Verify the services are running:
```bash
docker-compose ps
```

5. Access the API:
- API Base URL: http://localhost:3000
- API Documentation: http://localhost:3000/api-docs
- Health Check: http://localhost:3000/health

### Local Development Setup

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your local configuration
```

3. Start PostgreSQL and Redis:
```bash
# Using Docker for databases only
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=your_password postgres:15-alpine
docker run -d -p 6379:6379 redis:7-alpine
```

4. Start the development server:
```bash
npm run dev
```

## API Endpoints

### Solar Data Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/current-status` | Current solar cycle metrics |
| GET | `/api/sunspot-history` | Historical sunspot data |
| GET | `/api/alerts` | Recent solar events and alerts |
| GET | `/api/forecast` | Predicted solar activity |

### Machine Learning Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ml/predict/short-term` | Short-term predictions (7-30 days) |
| POST | `/api/ml/predict/long-term` | Long-term predictions (months-years) |
| GET | `/api/ml/anomaly/current` | Current anomaly detections |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| GET | `/api-docs` | Interactive API documentation |
| WS | `/ws/live` | WebSocket for real-time updates |

## API Examples

### Get Current Solar Status
```bash
curl http://localhost:3000/api/current-status
```

Response:
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T12:00:00Z",
    "solarCycle": {
      "cycleNumber": 25,
      "monthsSinceMinimum": 48,
      "smoothedSunspotNumber": 125.5
    },
    "sunspotNumber": {
      "daily": 130,
      "smoothed": 125.5
    },
    "solarFlux": {
      "observed": 165.2,
      "adjusted": 163.8
    },
    "geomagneticActivity": {
      "kpIndex": 3.5,
      "condition": "Unsettled"
    },
    "activityLevel": "Moderate"
  },
  "cached": false,
  "timestamp": "2024-01-15T12:00:05Z"
}
```

### Get Historical Data
```bash
curl "http://localhost:3000/api/sunspot-history?range=1y&limit=100"
```

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:3000/ws/live');

ws.on('open', () => {
  ws.send(JSON.stringify({ type: 'subscribe' }));
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  console.log('Solar update:', message);
});
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `PORT`: API server port (default: 3000)
- `DB_HOST`: PostgreSQL host
- `DB_NAME`: Database name
- `REDIS_HOST`: Redis host
- `DATA_FETCH_INTERVAL_MINUTES`: Data fetch interval (default: 15)
- `RATE_LIMIT_MAX_REQUESTS`: Max requests per minute (default: 100)

## Testing

### Run all tests:
```bash
npm test
```

### Run unit tests only:
```bash
npm run test:unit
```

### Run integration tests:
```bash
npm run test:integration
```

### Run tests in watch mode:
```bash
npm run test:watch
```

### Generate coverage report:
```bash
npm test -- --coverage
```

Target coverage: 80%+

## Development

### Project Structure
```
Sun/
├── src/
│   ├── config/          # Database, Redis, Swagger configuration
│   ├── controllers/     # Request handlers
│   ├── middleware/      # Express middleware
│   ├── models/          # Database models
│   ├── routes/          # API routes
│   ├── services/        # Business logic and external API integrations
│   ├── utils/           # Utility functions
│   └── server.js        # Application entry point
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── scripts/             # Database migrations and utilities
├── logs/                # Application logs
└── docs/                # Additional documentation
```

### Code Style

The project uses ESLint with Airbnb style guide:
```bash
npm run lint
npm run lint:fix
```

### Adding New Endpoints

1. Create controller method in `src/controllers/`
2. Add route in `src/routes/`
3. Add Swagger documentation
4. Write tests in `tests/`
5. Update this README

## Docker Commands

### Build and start services:
```bash
docker-compose up --build
```

### Stop services:
```bash
docker-compose down
```

### View logs:
```bash
docker-compose logs -f api
```

### Rebuild API service:
```bash
docker-compose up -d --build api
```

### Execute commands in container:
```bash
docker-compose exec api sh
```

## Data Sources

- **NOAA SWPC**: https://services.swpc.noaa.gov
  - Solar cycle observations
  - Geomagnetic activity (Kp index)
  - Solar wind data

- **NASA**: Space weather data and imagery
- **SIDC**: International Sunspot Number

## Monitoring and Logging

- Application logs: `logs/app.log`
- Error logs: `logs/error.log`
- Log level configurable via `LOG_LEVEL` environment variable
- Winston logger with JSON formatting
- Morgan for HTTP request logging

## Performance

- Redis caching with configurable TTL
- Connection pooling for PostgreSQL
- Rate limiting to prevent abuse
- Compression middleware for responses
- WebSocket heartbeat for connection management

## Security

- Helmet.js for security headers
- CORS configuration
- Input validation with Joi
- Rate limiting
- Non-root Docker user
- Environment variable protection

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres
```

### Redis Connection Issues
```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

### API Not Responding
```bash
# Check API logs
docker-compose logs api

# Check health endpoint
curl http://localhost:3000/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Ensure tests pass and coverage is maintained
6. Submit a pull request

## License

MIT

## Support

For issues and questions:
- Create an issue in the repository
- Email: support@solarcycle.app

## Roadmap

- [ ] Machine learning model integration
- [ ] Advanced anomaly detection
- [ ] Additional data sources (SIDC, NASA)
- [ ] GraphQL API
- [ ] Mobile SDK
- [ ] Alert notifications
- [ ] Historical data export
- [ ] Custom dashboard widgets

## Changelog

### Version 1.0.0
- Initial release
- Core API endpoints
- NOAA SWPC integration
- WebSocket support
- Docker deployment
- Comprehensive testing
