const noaaService = require('../services/noaaService');
const SolarDataModel = require('../models/solarData');
const { cacheService } = require('../config/redis');
const logger = require('../utils/logger');

class SolarController {
  /**
   * Get current solar status
   * @route GET /api/current-status
   */
  static async getCurrentStatus(req, res, next) {
    const cacheKey = 'solar:current-status';

    try {
      // Check cache first
      const cachedData = await cacheService.get(cacheKey);
      if (cachedData) {
        logger.info('Returning cached current status');
        return res.json({
          success: true,
          data: cachedData,
          cached: true,
          timestamp: new Date().toISOString(),
        });
      }

      // Fetch from NOAA
      const currentStatus = await noaaService.fetchCurrentStatus();

      // Save to database
      await SolarDataModel.saveObservation({
        timestamp: currentStatus.timestamp,
        cycleNumber: currentStatus.solarCycle?.cycleNumber,
        sunspotNumber: currentStatus.sunspotNumber,
        solarFlux: currentStatus.solarFlux,
        geomagneticActivity: currentStatus.geomagneticActivity,
        activityLevel: currentStatus.activityLevel,
      });

      // Cache the result
      await cacheService.set(cacheKey, currentStatus, 900); // 15 minutes TTL

      res.json({
        success: true,
        data: currentStatus,
        cached: false,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Error in getCurrentStatus', { error: error.message });
      next(error);
    }
  }

  /**
   * Get historical sunspot data
   * @route GET /api/sunspot-history
   */
  static async getSunspotHistory(req, res, next) {
    const { range = '1y', limit = 1000 } = req.query;
    const cacheKey = `solar:history:${range}:${limit}`;

    try {
      // Check cache
      const cachedData = await cacheService.get(cacheKey);
      if (cachedData) {
        logger.info('Returning cached sunspot history', { range });
        return res.json({
          success: true,
          data: cachedData,
          cached: true,
          timestamp: new Date().toISOString(),
        });
      }

      // Try database first
      let historicalData = await SolarDataModel.getHistoricalObservations(range, limit);

      // If no data in database, fetch from NOAA
      if (!historicalData || historicalData.length === 0) {
        logger.info('No historical data in database, fetching from NOAA');
        const noaaData = await noaaService.fetchHistoricalData(range);
        historicalData = noaaData;
      }

      // Cache the result
      await cacheService.set(cacheKey, historicalData, 3600); // 1 hour TTL

      res.json({
        success: true,
        data: historicalData,
        count: historicalData.length,
        range,
        cached: false,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Error in getSunspotHistory', { error: error.message, range });
      next(error);
    }
  }

  /**
   * Get recent solar alerts/events
   * @route GET /api/alerts
   */
  static async getAlerts(req, res, next) {
    const { limit = 50 } = req.query;
    const cacheKey = `solar:alerts:${limit}`;

    try {
      // Check cache
      const cachedData = await cacheService.get(cacheKey);
      if (cachedData) {
        logger.info('Returning cached alerts');
        return res.json({
          success: true,
          data: cachedData,
          cached: true,
          timestamp: new Date().toISOString(),
        });
      }

      // Get from database
      const events = await SolarDataModel.getRecentEvents(limit);

      // If no events, fetch from NOAA
      if (!events || events.length === 0) {
        logger.info('No events in database, fetching from NOAA');
        const noaaEvents = await noaaService.fetchSolarEvents();

        // Save to database
        for (const event of noaaEvents) {
          await SolarDataModel.saveEvent(event);
        }

        // Cache and return
        await cacheService.set(cacheKey, noaaEvents, 900); // 15 minutes
        return res.json({
          success: true,
          data: noaaEvents,
          count: noaaEvents.length,
          cached: false,
          timestamp: new Date().toISOString(),
        });
      }

      // Cache the result
      await cacheService.set(cacheKey, events, 900);

      res.json({
        success: true,
        data: events,
        count: events.length,
        cached: false,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Error in getAlerts', { error: error.message });
      next(error);
    }
  }

  /**
   * Get solar activity forecast
   * @route GET /api/forecast
   */
  static async getForecast(req, res, next) {
    const cacheKey = 'solar:forecast';

    try {
      // Check cache
      const cachedData = await cacheService.get(cacheKey);
      if (cachedData) {
        return res.json({
          success: true,
          data: cachedData,
          cached: true,
          timestamp: new Date().toISOString(),
        });
      }

      // Generate basic forecast (placeholder for ML integration)
      const latestObs = await SolarDataModel.getLatestObservation();

      const forecast = {
        shortTerm: {
          period: 'Next 7 days',
          predictedSunspotNumber: latestObs?.sunspot_number_daily || 0,
          trend: 'stable',
          confidence: 0.75,
        },
        mediumTerm: {
          period: 'Next 30 days',
          predictedSunspotNumber: latestObs?.sunspot_number_daily || 0,
          trend: 'increasing',
          confidence: 0.65,
        },
        longTerm: {
          period: 'Next 6 months',
          predictedPeak: 'Q2 2025',
          confidence: 0.55,
        },
      };

      // Cache forecast
      await cacheService.set(cacheKey, forecast, 3600);

      res.json({
        success: true,
        data: forecast,
        cached: false,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Error in getForecast', { error: error.message });
      next(error);
    }
  }

  /**
   * ML short-term prediction
   * @route POST /api/ml/predict/short-term
   */
  static async predictShortTerm(req, res, next) {
    try {
      const { horizon = 7 } = req.body;

      // Placeholder for ML model integration
      const prediction = {
        type: 'short-term',
        horizon: `${horizon} days`,
        predictions: Array.from({ length: horizon }, (_, i) => ({
          day: i + 1,
          predictedSunspotNumber: Math.floor(Math.random() * 150) + 50,
          confidence: 0.8 - (i * 0.05),
        })),
        modelVersion: '1.0',
        generatedAt: new Date().toISOString(),
      };

      // Save prediction to database
      for (const pred of prediction.predictions) {
        await SolarDataModel.savePrediction({
          type: 'short-term',
          time: new Date(Date.now() + pred.day * 24 * 60 * 60 * 1000).toISOString(),
          value: pred.predictedSunspotNumber,
          confidence: pred.confidence,
          modelVersion: prediction.modelVersion,
        });
      }

      res.json({
        success: true,
        data: prediction,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Error in predictShortTerm', { error: error.message });
      next(error);
    }
  }

  /**
   * ML long-term prediction
   * @route POST /api/ml/predict/long-term
   */
  static async predictLongTerm(req, res, next) {
    try {
      const { horizon = 180 } = req.body;

      // Placeholder for ML model integration
      const prediction = {
        type: 'long-term',
        horizon: `${horizon} days`,
        predictedPeak: {
          date: '2025-07-01',
          sunspotNumber: 180,
          confidence: 0.65,
        },
        predictedMinimum: {
          date: '2030-12-01',
          sunspotNumber: 5,
          confidence: 0.50,
        },
        modelVersion: '1.0',
        generatedAt: new Date().toISOString(),
      };

      res.json({
        success: true,
        data: prediction,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Error in predictLongTerm', { error: error.message });
      next(error);
    }
  }

  /**
   * Get current anomalies
   * @route GET /api/ml/anomaly/current
   */
  static async getCurrentAnomalies(req, res, next) {
    const cacheKey = 'solar:anomalies:current';

    try {
      // Check cache
      const cachedData = await cacheService.get(cacheKey);
      if (cachedData) {
        return res.json({
          success: true,
          data: cachedData,
          cached: true,
          timestamp: new Date().toISOString(),
        });
      }

      // Get from database
      const anomalies = await SolarDataModel.getCurrentAnomalies();

      // Cache results
      await cacheService.set(cacheKey, anomalies, 600); // 10 minutes

      res.json({
        success: true,
        data: anomalies,
        count: anomalies.length,
        cached: false,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Error in getCurrentAnomalies', { error: error.message });
      next(error);
    }
  }

  /**
   * Health check endpoint
   * @route GET /health
   */
  static async healthCheck(req, res) {
    const { testConnection } = require('../config/database');
    const { redisClient } = require('../config/redis');

    const health = {
      status: 'ok',
      timestamp: new Date().toISOString(),
      services: {
        database: 'unknown',
        redis: 'unknown',
        noaa: 'unknown',
      },
    };

    // Check database
    try {
      await testConnection();
      health.services.database = 'healthy';
    } catch (error) {
      health.services.database = 'unhealthy';
      health.status = 'degraded';
    }

    // Check Redis
    try {
      await redisClient.ping();
      health.services.redis = 'healthy';
    } catch (error) {
      health.services.redis = 'unhealthy';
      health.status = 'degraded';
    }

    // Check NOAA API
    try {
      await noaaService.fetchCurrentStatus();
      health.services.noaa = 'healthy';
    } catch (error) {
      health.services.noaa = 'unhealthy';
      health.status = 'degraded';
    }

    const statusCode = health.status === 'ok' ? 200 : 503;
    res.status(statusCode).json(health);
  }
}

module.exports = SolarController;
