require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const morgan = require('morgan');
const http = require('http');

const logger = require('./utils/logger');
const { connectRedis } = require('./config/redis');
const { testConnection } = require('./config/database');
const SolarDataModel = require('./models/solarData');
const dataFetcher = require('./services/dataFetcher');
const websocketService = require('./services/websocketService');
const solarRoutes = require('./routes/solarRoutes');
const SolarController = require('./controllers/solarController');
const { errorHandler, notFoundHandler } = require('./middleware/errorHandler');
const { apiLimiter } = require('./middleware/rateLimiter');
const { swaggerUi, swaggerSpec } = require('./config/swagger');

// Create Express app
const app = express();
const server = http.createServer(app);

// Middleware
app.use(helmet());
app.use(cors({ origin: process.env.CORS_ORIGIN || '*' }));
app.use(compression());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Logging
if (process.env.NODE_ENV !== 'test') {
  app.use(morgan('combined', { stream: { write: (message) => logger.info(message.trim()) } }));
}

// API Documentation
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// Health check (no rate limiting)
app.get('/health', SolarController.healthCheck);

// Rate limiting for API routes
app.use('/api', apiLimiter);

// API routes
app.use('/api', solarRoutes);

// Root route
app.get('/', (req, res) => {
  res.json({
    name: 'Solar Cycle API',
    version: '1.0.0',
    description: 'Backend API for Solar Cycle Mobile App',
    documentation: '/api-docs',
    endpoints: {
      currentStatus: '/api/current-status',
      sunspotHistory: '/api/sunspot-history?range={1y|5y|cycle}',
      alerts: '/api/alerts',
      forecast: '/api/forecast',
      mlShortTerm: '/api/ml/predict/short-term',
      mlLongTerm: '/api/ml/predict/long-term',
      mlAnomaly: '/api/ml/anomaly/current',
      websocket: '/ws/live',
      health: '/health',
    },
  });
});

// Error handling
app.use(notFoundHandler);
app.use(errorHandler);

// Initialize services
async function initializeServices() {
  try {
    logger.info('Initializing services...');

    // Test database connection
    const dbConnected = await testConnection();
    if (!dbConnected) {
      throw new Error('Database connection failed');
    }

    // Create database tables
    await SolarDataModel.createTables();

    // Connect to Redis
    const redisConnected = await connectRedis();
    if (!redisConnected) {
      logger.warn('Redis connection failed - caching will be disabled');
    }

    // Initialize WebSocket service
    websocketService.initialize(server);

    // Start data fetcher
    dataFetcher.start();

    logger.info('All services initialized successfully');
  } catch (error) {
    logger.error('Failed to initialize services', { error: error.message });
    throw error;
  }
}

// Graceful shutdown
async function gracefulShutdown(signal) {
  logger.info(`${signal} received, starting graceful shutdown`);

  // Stop accepting new connections
  server.close(() => {
    logger.info('HTTP server closed');
  });

  // Stop services
  dataFetcher.stop();
  websocketService.stop();

  // Close database connections
  const { pool } = require('./config/database');
  await pool.end();

  // Close Redis connection
  const { redisClient } = require('./config/redis');
  if (redisClient.isOpen) {
    await redisClient.quit();
  }

  logger.info('Graceful shutdown complete');
  process.exit(0);
}

// Handle shutdown signals
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle uncaught errors
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception', { error: error.message, stack: error.stack });
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled rejection', { reason, promise });
  process.exit(1);
});

// Start server
const PORT = process.env.PORT || 3000;

async function startServer() {
  try {
    await initializeServices();

    server.listen(PORT, () => {
      logger.info(`Solar Cycle API server started on port ${PORT}`);
      logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
      logger.info(`API Documentation: http://localhost:${PORT}/api-docs`);
      logger.info(`WebSocket endpoint: ws://localhost:${PORT}/ws/live`);
    });
  } catch (error) {
    logger.error('Failed to start server', { error: error.message });
    process.exit(1);
  }
}

// Start the server if this file is run directly
if (require.main === module) {
  startServer();
}

module.exports = { app, server };
