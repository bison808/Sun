const express = require('express');
const SolarController = require('../controllers/solarController');
const { asyncHandler } = require('../middleware/errorHandler');
const { validate, schemas } = require('../middleware/validator');
const { mlLimiter } = require('../middleware/rateLimiter');

const router = express.Router();

/**
 * @swagger
 * /api/current-status:
 *   get:
 *     summary: Get current solar cycle metrics
 *     tags: [Solar Data]
 *     responses:
 *       200:
 *         description: Current solar status
 */
router.get('/current-status', asyncHandler(SolarController.getCurrentStatus));

/**
 * @swagger
 * /api/sunspot-history:
 *   get:
 *     summary: Get historical sunspot data
 *     tags: [Solar Data]
 *     parameters:
 *       - in: query
 *         name: range
 *         schema:
 *           type: string
 *           enum: [1y, 5y, cycle]
 *         description: Time range for historical data
 */
router.get(
  '/sunspot-history',
  validate(schemas.historyRange),
  asyncHandler(SolarController.getSunspotHistory)
);

/**
 * @swagger
 * /api/alerts:
 *   get:
 *     summary: Get recent solar events and alerts
 *     tags: [Solar Data]
 */
router.get(
  '/alerts',
  validate(schemas.eventLimit),
  asyncHandler(SolarController.getAlerts)
);

/**
 * @swagger
 * /api/forecast:
 *   get:
 *     summary: Get predicted solar activity
 *     tags: [Solar Data]
 */
router.get('/forecast', asyncHandler(SolarController.getForecast));

/**
 * @swagger
 * /api/ml/predict/short-term:
 *   post:
 *     summary: AI short-term predictions (7-30 days)
 *     tags: [Machine Learning]
 */
router.post(
  '/ml/predict/short-term',
  mlLimiter,
  asyncHandler(SolarController.predictShortTerm)
);

/**
 * @swagger
 * /api/ml/predict/long-term:
 *   post:
 *     summary: AI long-term predictions (months-years)
 *     tags: [Machine Learning]
 */
router.post(
  '/ml/predict/long-term',
  mlLimiter,
  asyncHandler(SolarController.predictLongTerm)
);

/**
 * @swagger
 * /api/ml/anomaly/current:
 *   get:
 *     summary: Current anomaly detection results
 *     tags: [Machine Learning]
 */
router.get(
  '/ml/anomaly/current',
  asyncHandler(SolarController.getCurrentAnomalies)
);

module.exports = router;
