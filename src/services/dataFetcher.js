const cron = require('node-cron');
const noaaService = require('./noaaService');
const SolarDataModel = require('../models/solarData');
const logger = require('../utils/logger');

class DataFetcherService {
  constructor() {
    this.isRunning = false;
    this.cronJob = null;
  }

  /**
   * Start the data fetching service
   */
  start() {
    if (this.isRunning) {
      logger.warn('Data fetcher is already running');
      return;
    }

    const interval = parseInt(process.env.DATA_FETCH_INTERVAL_MINUTES) || 15;

    // Run immediately on start
    this.fetchAndStore();

    // Schedule periodic fetching (every 15 minutes by default)
    this.cronJob = cron.schedule(`*/${interval} * * * *`, () => {
      this.fetchAndStore();
    });

    this.isRunning = true;
    logger.info(`Data fetcher started, running every ${interval} minutes`);
  }

  /**
   * Stop the data fetching service
   */
  stop() {
    if (this.cronJob) {
      this.cronJob.stop();
      this.cronJob = null;
    }
    this.isRunning = false;
    logger.info('Data fetcher stopped');
  }

  /**
   * Fetch data from NOAA and store in database
   */
  async fetchAndStore() {
    try {
      logger.info('Starting data fetch cycle');

      // Fetch current solar status
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

      // Fetch and store solar events
      try {
        const events = await noaaService.fetchSolarEvents();
        for (const event of events) {
          await SolarDataModel.saveEvent(event);
        }
      } catch (error) {
        logger.error('Failed to fetch solar events', { error: error.message });
      }

      logger.info('Data fetch cycle completed successfully');
    } catch (error) {
      logger.error('Data fetch cycle failed', { error: error.message });
    }
  }

  /**
   * Get service status
   */
  getStatus() {
    return {
      isRunning: this.isRunning,
      interval: `${process.env.DATA_FETCH_INTERVAL_MINUTES || 15} minutes`,
    };
  }
}

module.exports = new DataFetcherService();
