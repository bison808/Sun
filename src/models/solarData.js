const db = require('../config/database');
const logger = require('../utils/logger');

class SolarDataModel {
  /**
   * Create solar data tables
   */
  static async createTables() {
    const queries = [
      // Solar cycle observations table
      `CREATE TABLE IF NOT EXISTS solar_observations (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL,
        cycle_number INTEGER NOT NULL,
        sunspot_number_daily REAL,
        sunspot_number_smoothed REAL,
        solar_flux_observed REAL,
        solar_flux_adjusted REAL,
        kp_index REAL,
        activity_level VARCHAR(50),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(timestamp)
      )`,

      // Solar events table
      `CREATE TABLE IF NOT EXISTS solar_events (
        id SERIAL PRIMARY KEY,
        event_type VARCHAR(100) NOT NULL,
        event_time TIMESTAMPTZ NOT NULL,
        description TEXT,
        severity VARCHAR(50),
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
      )`,

      // ML predictions table
      `CREATE TABLE IF NOT EXISTS ml_predictions (
        id SERIAL PRIMARY KEY,
        prediction_type VARCHAR(50) NOT NULL,
        prediction_time TIMESTAMPTZ NOT NULL,
        predicted_value REAL,
        confidence_score REAL,
        model_version VARCHAR(50),
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
      )`,

      // Anomaly detections table
      `CREATE TABLE IF NOT EXISTS anomaly_detections (
        id SERIAL PRIMARY KEY,
        detection_time TIMESTAMPTZ NOT NULL,
        anomaly_type VARCHAR(100),
        anomaly_score REAL,
        description TEXT,
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
      )`,

      // Create indexes
      `CREATE INDEX IF NOT EXISTS idx_solar_obs_timestamp ON solar_observations(timestamp DESC)`,
      `CREATE INDEX IF NOT EXISTS idx_solar_events_time ON solar_events(event_time DESC)`,
      `CREATE INDEX IF NOT EXISTS idx_ml_predictions_time ON ml_predictions(prediction_time DESC)`,
      `CREATE INDEX IF NOT EXISTS idx_anomaly_detections_time ON anomaly_detections(detection_time DESC)`,
    ];

    try {
      for (const query of queries) {
        await db.query(query);
      }
      logger.info('Database tables created successfully');
    } catch (error) {
      logger.error('Failed to create database tables', { error: error.message });
      throw error;
    }
  }

  /**
   * Save solar observation data
   */
  static async saveObservation(data) {
    const query = `
      INSERT INTO solar_observations (
        timestamp, cycle_number, sunspot_number_daily, sunspot_number_smoothed,
        solar_flux_observed, solar_flux_adjusted, kp_index, activity_level
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      ON CONFLICT (timestamp) DO UPDATE SET
        cycle_number = EXCLUDED.cycle_number,
        sunspot_number_daily = EXCLUDED.sunspot_number_daily,
        sunspot_number_smoothed = EXCLUDED.sunspot_number_smoothed,
        solar_flux_observed = EXCLUDED.solar_flux_observed,
        solar_flux_adjusted = EXCLUDED.solar_flux_adjusted,
        kp_index = EXCLUDED.kp_index,
        activity_level = EXCLUDED.activity_level
      RETURNING id
    `;

    const values = [
      data.timestamp,
      data.cycleNumber || 25,
      data.sunspotNumber?.daily,
      data.sunspotNumber?.smoothed,
      data.solarFlux?.observed,
      data.solarFlux?.adjusted,
      data.geomagneticActivity?.kpIndex,
      data.activityLevel,
    ];

    try {
      const result = await db.query(query, values);
      logger.info('Solar observation saved', { id: result.rows[0].id });
      return result.rows[0];
    } catch (error) {
      logger.error('Failed to save solar observation', { error: error.message });
      throw error;
    }
  }

  /**
   * Get latest solar observation
   */
  static async getLatestObservation() {
    const query = `
      SELECT * FROM solar_observations
      ORDER BY timestamp DESC
      LIMIT 1
    `;

    try {
      const result = await db.query(query);
      return result.rows[0] || null;
    } catch (error) {
      logger.error('Failed to get latest observation', { error: error.message });
      throw error;
    }
  }

  /**
   * Get historical observations
   */
  static async getHistoricalObservations(range = '1y', limit = 1000) {
    const intervals = {
      '1y': '1 year',
      '5y': '5 years',
      'cycle': '6 years', // Approximate solar cycle length
    };

    const interval = intervals[range] || intervals['1y'];

    const query = `
      SELECT * FROM solar_observations
      WHERE timestamp >= NOW() - INTERVAL '${interval}'
      ORDER BY timestamp DESC
      LIMIT $1
    `;

    try {
      const result = await db.query(query, [limit]);
      return result.rows;
    } catch (error) {
      logger.error('Failed to get historical observations', { error: error.message });
      throw error;
    }
  }

  /**
   * Save solar event
   */
  static async saveEvent(event) {
    const query = `
      INSERT INTO solar_events (event_type, event_time, description, severity, metadata)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING id
    `;

    const values = [
      event.type,
      event.timestamp,
      event.description,
      event.severity || 'info',
      JSON.stringify(event.metadata || {}),
    ];

    try {
      const result = await db.query(query, values);
      return result.rows[0];
    } catch (error) {
      logger.error('Failed to save solar event', { error: error.message });
      throw error;
    }
  }

  /**
   * Get recent solar events
   */
  static async getRecentEvents(limit = 50) {
    const query = `
      SELECT * FROM solar_events
      ORDER BY event_time DESC
      LIMIT $1
    `;

    try {
      const result = await db.query(query, [limit]);
      return result.rows;
    } catch (error) {
      logger.error('Failed to get recent events', { error: error.message });
      throw error;
    }
  }

  /**
   * Save ML prediction
   */
  static async savePrediction(prediction) {
    const query = `
      INSERT INTO ml_predictions (
        prediction_type, prediction_time, predicted_value, confidence_score, model_version, metadata
      ) VALUES ($1, $2, $3, $4, $5, $6)
      RETURNING id
    `;

    const values = [
      prediction.type,
      prediction.time,
      prediction.value,
      prediction.confidence,
      prediction.modelVersion || '1.0',
      JSON.stringify(prediction.metadata || {}),
    ];

    try {
      const result = await db.query(query, values);
      return result.rows[0];
    } catch (error) {
      logger.error('Failed to save prediction', { error: error.message });
      throw error;
    }
  }

  /**
   * Save anomaly detection
   */
  static async saveAnomaly(anomaly) {
    const query = `
      INSERT INTO anomaly_detections (
        detection_time, anomaly_type, anomaly_score, description, metadata
      ) VALUES ($1, $2, $3, $4, $5)
      RETURNING id
    `;

    const values = [
      anomaly.time,
      anomaly.type,
      anomaly.score,
      anomaly.description,
      JSON.stringify(anomaly.metadata || {}),
    ];

    try {
      const result = await db.query(query, values);
      return result.rows[0];
    } catch (error) {
      logger.error('Failed to save anomaly', { error: error.message });
      throw error;
    }
  }

  /**
   * Get current anomalies
   */
  static async getCurrentAnomalies(limit = 10) {
    const query = `
      SELECT * FROM anomaly_detections
      WHERE detection_time >= NOW() - INTERVAL '24 hours'
      ORDER BY detection_time DESC
      LIMIT $1
    `;

    try {
      const result = await db.query(query, [limit]);
      return result.rows;
    } catch (error) {
      logger.error('Failed to get current anomalies', { error: error.message });
      throw error;
    }
  }
}

module.exports = SolarDataModel;
