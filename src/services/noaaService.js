const axios = require('axios');
const logger = require('../utils/logger');
const { retryWithBackoff } = require('../utils/retry');

class NoaaService {
  constructor() {
    this.baseUrl = process.env.NOAA_SWPC_BASE_URL || 'https://services.swpc.noaa.gov';
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: 10000,
      headers: {
        'User-Agent': 'Solar-Cycle-API/1.0',
      },
    });
  }

  /**
   * Fetch current solar cycle data from NOAA SWPC
   * @returns {Promise<Object>} Solar cycle data
   */
  async fetchCurrentStatus() {
    try {
      const data = await retryWithBackoff(async () => {
        logger.info('Fetching current solar status from NOAA SWPC');

        // Fetch multiple data points in parallel
        const [solarCycle, sunspotNumber, solarFlux, geomagneticActivity] = await Promise.allSettled([
          this.fetchSolarCycleProgression(),
          this.fetchSunspotNumber(),
          this.fetchSolarFlux(),
          this.fetchGeomagneticActivity(),
        ]);

        return {
          timestamp: new Date().toISOString(),
          solarCycle: solarCycle.status === 'fulfilled' ? solarCycle.value : null,
          sunspotNumber: sunspotNumber.status === 'fulfilled' ? sunspotNumber.value : null,
          solarFlux: solarFlux.status === 'fulfilled' ? solarFlux.value : null,
          geomagneticActivity: geomagneticActivity.status === 'fulfilled' ? geomagneticActivity.value : null,
          activityLevel: this.calculateActivityLevel(
            sunspotNumber.status === 'fulfilled' ? sunspotNumber.value : null,
            solarFlux.status === 'fulfilled' ? solarFlux.value : null
          ),
        };
      });

      logger.info('Successfully fetched current solar status');
      return data;
    } catch (error) {
      logger.error('Failed to fetch current solar status', { error: error.message });
      throw new Error(`NOAA data fetch failed: ${error.message}`);
    }
  }

  /**
   * Fetch solar cycle progression data
   * @returns {Promise<Object>}
   */
  async fetchSolarCycleProgression() {
    try {
      const response = await this.client.get('/json/solar-cycle/observed-solar-cycle-indices.json');

      if (!response.data || response.data.length === 0) {
        throw new Error('No solar cycle data available');
      }

      // Get the most recent data point
      const latestData = response.data[response.data.length - 1];

      return {
        cycleNumber: 25, // Current solar cycle
        monthsSinceMinimum: this.calculateMonthsSinceMinimum(latestData['time-tag']),
        smoothedSunspotNumber: parseFloat(latestData['ssn']) || 0,
        date: latestData['time-tag'],
      };
    } catch (error) {
      logger.error('Failed to fetch solar cycle progression', { error: error.message });
      throw error;
    }
  }

  /**
   * Fetch current sunspot number
   * @returns {Promise<Object>}
   */
  async fetchSunspotNumber() {
    try {
      const response = await this.client.get('/json/solar-cycle/observed-solar-cycle-indices.json');

      if (!response.data || response.data.length === 0) {
        throw new Error('No sunspot data available');
      }

      const latestData = response.data[response.data.length - 1];

      return {
        daily: parseFloat(latestData['ssn']) || 0,
        smoothed: parseFloat(latestData['smoothed_ssn']) || 0,
        timestamp: latestData['time-tag'],
      };
    } catch (error) {
      logger.error('Failed to fetch sunspot number', { error: error.message });
      throw error;
    }
  }

  /**
   * Fetch solar flux (F10.7 cm)
   * @returns {Promise<Object>}
   */
  async fetchSolarFlux() {
    try {
      const response = await this.client.get('/json/solar-cycle/observed-solar-cycle-indices.json');

      if (!response.data || response.data.length === 0) {
        throw new Error('No solar flux data available');
      }

      const latestData = response.data[response.data.length - 1];

      return {
        observed: parseFloat(latestData['f10.7']) || 0,
        adjusted: parseFloat(latestData['f10.7']) || 0,
        timestamp: latestData['time-tag'],
      };
    } catch (error) {
      logger.error('Failed to fetch solar flux', { error: error.message });
      throw error;
    }
  }

  /**
   * Fetch geomagnetic activity (Kp index)
   * @returns {Promise<Object>}
   */
  async fetchGeomagneticActivity() {
    try {
      // NOAA provides planetary K-index data
      const response = await this.client.get('/products/noaa-planetary-k-index.json');

      if (!response.data || response.data.length === 0) {
        throw new Error('No geomagnetic data available');
      }

      // Get the most recent Kp value
      const latestData = response.data[response.data.length - 1];

      return {
        kpIndex: parseFloat(latestData.kp_index) || 0,
        timestamp: latestData.time_tag,
        condition: this.getGeomagneticCondition(parseFloat(latestData.kp_index)),
      };
    } catch (error) {
      logger.warn('Failed to fetch geomagnetic activity, using fallback', { error: error.message });
      // Return fallback data if geomagnetic endpoint fails
      return {
        kpIndex: 0,
        timestamp: new Date().toISOString(),
        condition: 'Unknown',
      };
    }
  }

  /**
   * Fetch solar events and alerts
   * @returns {Promise<Array>}
   */
  async fetchSolarEvents() {
    try {
      const data = await retryWithBackoff(async () => {
        const response = await this.client.get('/products/solar-wind/plasma-7-day.json');

        if (!response.data) {
          throw new Error('No solar events data available');
        }

        return this.parseSolarEvents(response.data);
      });

      logger.info('Successfully fetched solar events');
      return data;
    } catch (error) {
      logger.error('Failed to fetch solar events', { error: error.message });
      throw error;
    }
  }

  /**
   * Fetch historical sunspot data
   * @param {string} range - Time range (1y, 5y, cycle)
   * @returns {Promise<Array>}
   */
  async fetchHistoricalData(range = '1y') {
    try {
      const data = await retryWithBackoff(async () => {
        const response = await this.client.get('/json/solar-cycle/observed-solar-cycle-indices.json');

        if (!response.data) {
          throw new Error('No historical data available');
        }

        return this.filterDataByRange(response.data, range);
      });

      logger.info('Successfully fetched historical data', { range });
      return data;
    } catch (error) {
      logger.error('Failed to fetch historical data', { error: error.message, range });
      throw error;
    }
  }

  /**
   * Calculate months since solar minimum (Dec 2019)
   * @param {string} dateString
   * @returns {number}
   */
  calculateMonthsSinceMinimum(dateString) {
    const solarMinimum = new Date('2019-12-01');
    const currentDate = new Date(dateString);
    const months = (currentDate.getFullYear() - solarMinimum.getFullYear()) * 12 +
                   (currentDate.getMonth() - solarMinimum.getMonth());
    return months;
  }

  /**
   * Calculate activity level based on sunspot number and solar flux
   * @param {Object} sunspotData
   * @param {Object} solarFluxData
   * @returns {string}
   */
  calculateActivityLevel(sunspotData, solarFluxData) {
    if (!sunspotData || !solarFluxData) {
      return 'Unknown';
    }

    const ssn = sunspotData.daily;
    const flux = solarFluxData.observed;

    // Activity level thresholds
    if (ssn < 20 && flux < 80) return 'Very Low';
    if (ssn < 50 && flux < 100) return 'Low';
    if (ssn < 100 && flux < 150) return 'Moderate';
    if (ssn < 150 && flux < 200) return 'High';
    return 'Very High';
  }

  /**
   * Get geomagnetic condition based on Kp index
   * @param {number} kpIndex
   * @returns {string}
   */
  getGeomagneticCondition(kpIndex) {
    if (kpIndex < 2) return 'Quiet';
    if (kpIndex < 4) return 'Unsettled';
    if (kpIndex < 5) return 'Active';
    if (kpIndex < 6) return 'Minor Storm';
    if (kpIndex < 7) return 'Moderate Storm';
    if (kpIndex < 8) return 'Strong Storm';
    if (kpIndex < 9) return 'Severe Storm';
    return 'Extreme Storm';
  }

  /**
   * Parse solar events from raw data
   * @param {Array} rawData
   * @returns {Array}
   */
  parseSolarEvents(rawData) {
    // This is a simplified parser - adjust based on actual NOAA data format
    return rawData.slice(-10).map(event => ({
      timestamp: event[0],
      type: 'Solar Wind',
      description: `Density: ${event[1]}, Speed: ${event[2]} km/s`,
    }));
  }

  /**
   * Filter data by time range
   * @param {Array} data
   * @param {string} range
   * @returns {Array}
   */
  filterDataByRange(data, range) {
    const now = new Date();
    let startDate;

    switch (range) {
      case '1y':
        startDate = new Date(now.setFullYear(now.getFullYear() - 1));
        break;
      case '5y':
        startDate = new Date(now.setFullYear(now.getFullYear() - 5));
        break;
      case 'cycle':
        startDate = new Date('2019-12-01'); // Solar Cycle 25 minimum
        break;
      default:
        startDate = new Date(now.setFullYear(now.getFullYear() - 1));
    }

    return data.filter(item => new Date(item['time-tag']) >= startDate);
  }
}

module.exports = new NoaaService();
