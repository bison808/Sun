# Solar Cycle API Documentation

Complete API reference for the Solar Cycle API.

## Base URL

```
Development: http://localhost:3000
Production: https://api.solarcycle.app
```

## Authentication

Currently, the API is open access with rate limiting. Future versions will include API key authentication.

## Rate Limiting

- **General API**: 100 requests per minute per IP
- **ML Endpoints**: 10 requests per minute per IP

Rate limit headers are included in all responses:
```
RateLimit-Limit: 100
RateLimit-Remaining: 95
RateLimit-Reset: 1642262400
```

## Response Format

All responses follow this structure:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2024-01-15T12:00:00Z",
  "cached": false
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "message": "Error description"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

## Endpoints

### 1. Get Current Solar Status

Returns current solar cycle metrics including sunspot numbers, solar flux, and geomagnetic activity.

**Endpoint:** `GET /api/current-status`

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T12:00:00Z",
    "solarCycle": {
      "cycleNumber": 25,
      "monthsSinceMinimum": 48,
      "smoothedSunspotNumber": 125.5,
      "date": "2024-01-01"
    },
    "sunspotNumber": {
      "daily": 130,
      "smoothed": 125.5,
      "timestamp": "2024-01-15T00:00:00Z"
    },
    "solarFlux": {
      "observed": 165.2,
      "adjusted": 163.8,
      "timestamp": "2024-01-15T00:00:00Z"
    },
    "geomagneticActivity": {
      "kpIndex": 3.5,
      "timestamp": "2024-01-15T11:00:00Z",
      "condition": "Unsettled"
    },
    "activityLevel": "Moderate"
  },
  "cached": false,
  "timestamp": "2024-01-15T12:00:05Z"
}
```

**Cache:** 15 minutes

**Example:**
```bash
curl http://localhost:3000/api/current-status
```

---

### 2. Get Sunspot History

Returns historical sunspot data for the specified time range.

**Endpoint:** `GET /api/sunspot-history`

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| range | string | No | 1y | Time range: `1y`, `5y`, or `cycle` |
| limit | integer | No | 1000 | Maximum number of records (1-10000) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "timestamp": "2024-01-01T00:00:00Z",
      "cycle_number": 25,
      "sunspot_number_daily": 120,
      "sunspot_number_smoothed": 115.5,
      "solar_flux_observed": 160.0,
      "solar_flux_adjusted": 158.5,
      "kp_index": 2.5,
      "activity_level": "Moderate"
    }
  ],
  "count": 365,
  "range": "1y",
  "cached": false,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Cache:** 1 hour

**Examples:**
```bash
# Get 1 year of data (default)
curl http://localhost:3000/api/sunspot-history

# Get 5 years of data
curl "http://localhost:3000/api/sunspot-history?range=5y"

# Get full solar cycle data
curl "http://localhost:3000/api/sunspot-history?range=cycle"

# Limit to 100 records
curl "http://localhost:3000/api/sunspot-history?range=1y&limit=100"
```

---

### 3. Get Solar Alerts

Returns recent solar events and alerts.

**Endpoint:** `GET /api/alerts`

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| limit | integer | No | 50 | Maximum number of events (1-100) |

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "event_type": "Solar Flare",
      "event_time": "2024-01-15T10:30:00Z",
      "description": "M-class solar flare detected",
      "severity": "moderate",
      "metadata": {
        "classification": "M2.5",
        "region": "AR3559"
      },
      "created_at": "2024-01-15T10:31:00Z"
    }
  ],
  "count": 10,
  "cached": false,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Cache:** 15 minutes

**Example:**
```bash
curl http://localhost:3000/api/alerts

# Get last 10 alerts
curl "http://localhost:3000/api/alerts?limit=10"
```

---

### 4. Get Solar Forecast

Returns predicted solar activity for short, medium, and long-term periods.

**Endpoint:** `GET /api/forecast`

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": {
    "shortTerm": {
      "period": "Next 7 days",
      "predictedSunspotNumber": 130,
      "trend": "stable",
      "confidence": 0.75
    },
    "mediumTerm": {
      "period": "Next 30 days",
      "predictedSunspotNumber": 145,
      "trend": "increasing",
      "confidence": 0.65
    },
    "longTerm": {
      "period": "Next 6 months",
      "predictedPeak": "Q2 2025",
      "confidence": 0.55
    }
  },
  "cached": false,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Cache:** 1 hour

**Example:**
```bash
curl http://localhost:3000/api/forecast
```

---

### 5. ML Short-term Prediction

AI-powered short-term prediction (7-30 days).

**Endpoint:** `POST /api/ml/predict/short-term`

**Rate Limit:** 10 requests/minute

**Request Body:**
```json
{
  "horizon": 7
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| horizon | integer | No | 7 | Prediction horizon in days (1-30) |

**Response:**
```json
{
  "success": true,
  "data": {
    "type": "short-term",
    "horizon": "7 days",
    "predictions": [
      {
        "day": 1,
        "predictedSunspotNumber": 135,
        "confidence": 0.8
      },
      {
        "day": 2,
        "predictedSunspotNumber": 138,
        "confidence": 0.75
      }
    ],
    "modelVersion": "1.0",
    "generatedAt": "2024-01-15T12:00:00Z"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:3000/api/ml/predict/short-term \
  -H "Content-Type: application/json" \
  -d '{"horizon": 14}'
```

---

### 6. ML Long-term Prediction

AI-powered long-term prediction (months to years).

**Endpoint:** `POST /api/ml/predict/long-term`

**Rate Limit:** 10 requests/minute

**Request Body:**
```json
{
  "horizon": 180
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| horizon | integer | No | 180 | Prediction horizon in days (30-1825) |

**Response:**
```json
{
  "success": true,
  "data": {
    "type": "long-term",
    "horizon": "180 days",
    "predictedPeak": {
      "date": "2025-07-01",
      "sunspotNumber": 180,
      "confidence": 0.65
    },
    "predictedMinimum": {
      "date": "2030-12-01",
      "sunspotNumber": 5,
      "confidence": 0.50
    },
    "modelVersion": "1.0",
    "generatedAt": "2024-01-15T12:00:00Z"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Example:**
```bash
curl -X POST http://localhost:3000/api/ml/predict/long-term \
  -H "Content-Type: application/json" \
  -d '{"horizon": 365}'
```

---

### 7. Get Current Anomalies

Returns detected anomalies in solar activity from the last 24 hours.

**Endpoint:** `GET /api/ml/anomaly/current`

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 45,
      "detection_time": "2024-01-15T08:30:00Z",
      "anomaly_type": "Unusual Sunspot Spike",
      "anomaly_score": 0.85,
      "description": "Sunspot number increased by 50% in 24 hours",
      "metadata": {
        "previousValue": 100,
        "currentValue": 150,
        "threshold": 0.8
      },
      "created_at": "2024-01-15T08:31:00Z"
    }
  ],
  "count": 1,
  "cached": false,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Cache:** 10 minutes

**Example:**
```bash
curl http://localhost:3000/api/ml/anomaly/current
```

---

### 8. Health Check

Returns the health status of the API and its dependencies.

**Endpoint:** `GET /health`

**Parameters:** None

**Response:**
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

**Status Codes:**
- `200 OK`: All services healthy
- `503 Service Unavailable`: One or more services unhealthy

**Example:**
```bash
curl http://localhost:3000/health
```

---

## WebSocket API

Real-time solar data updates via WebSocket.

**Endpoint:** `ws://localhost:3000/ws/live`

### Connection

```javascript
const ws = new WebSocket('ws://localhost:3000/ws/live');

ws.onopen = () => {
  console.log('Connected to Solar Cycle WebSocket');

  // Subscribe to updates
  ws.send(JSON.stringify({
    type: 'subscribe'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Solar update:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from WebSocket');
};
```

### Message Types

#### Client to Server

**Subscribe:**
```json
{
  "type": "subscribe"
}
```

**Ping:**
```json
{
  "type": "ping"
}
```

#### Server to Client

**Solar Update:**
```json
{
  "type": "solar_update",
  "data": {
    "timestamp": "2024-01-15T12:00:00Z",
    "solarCycle": { ... },
    "sunspotNumber": { ... },
    "solarFlux": { ... },
    "geomagneticActivity": { ... },
    "activityLevel": "Moderate"
  },
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Pong:**
```json
{
  "type": "pong",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### Update Frequency

- Automatic updates every 5 minutes
- Initial data sent on connection
- Heartbeat ping every 30 seconds

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Route doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Dependency failure |

## Data Refresh Schedule

- **Current Status**: Every 15 minutes
- **Historical Data**: Daily aggregation
- **Alerts**: Real-time from NOAA
- **Forecasts**: Updated hourly
- **ML Predictions**: On-demand

## Best Practices

1. **Use caching**: Leverage the `cached` field to understand data freshness
2. **Handle rate limits**: Implement exponential backoff for retries
3. **WebSocket for real-time**: Use WebSocket instead of polling for live updates
4. **Error handling**: Always check the `success` field
5. **Respect TTL**: Don't poll faster than cache TTL values

## Examples

### Complete Workflow

```javascript
// 1. Check API health
const healthCheck = await fetch('http://localhost:3000/health');
const health = await healthCheck.json();

if (health.status === 'ok') {
  // 2. Get current solar status
  const statusRes = await fetch('http://localhost:3000/api/current-status');
  const status = await statusRes.json();

  console.log('Activity Level:', status.data.activityLevel);

  // 3. Get historical data for context
  const historyRes = await fetch('http://localhost:3000/api/sunspot-history?range=1y');
  const history = await historyRes.json();

  console.log('Data points:', history.count);

  // 4. Check for recent alerts
  const alertsRes = await fetch('http://localhost:3000/api/alerts?limit=10');
  const alerts = await alertsRes.json();

  console.log('Recent alerts:', alerts.count);

  // 5. Get forecast
  const forecastRes = await fetch('http://localhost:3000/api/forecast');
  const forecast = await forecastRes.json();

  console.log('Next 7 days:', forecast.data.shortTerm.trend);
}
```

## Support

For API issues or questions:
- Interactive docs: http://localhost:3000/api-docs
- GitHub Issues: <repository-url>/issues
