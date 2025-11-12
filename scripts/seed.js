#!/usr/bin/env node

/**
 * Database seed script
 * Run with: npm run db:seed
 */

require('dotenv').config();
const SolarDataModel = require('../src/models/solarData');
const logger = require('../src/utils/logger');
const { testConnection } = require('../src/config/database');

async function seedDatabase() {
  try {
    logger.info('Starting database seeding...');

    // Test connection
    const connected = await testConnection();
    if (!connected) {
      throw new Error('Database connection failed');
    }

    // Sample solar observations
    const sampleObservations = [
      {
        timestamp: new Date('2024-01-01T00:00:00Z'),
        cycleNumber: 25,
        sunspotNumber: { daily: 120, smoothed: 115.5 },
        solarFlux: { observed: 160.0, adjusted: 158.5 },
        geomagneticActivity: { kpIndex: 2.5 },
        activityLevel: 'Moderate',
      },
      {
        timestamp: new Date('2024-01-02T00:00:00Z'),
        cycleNumber: 25,
        sunspotNumber: { daily: 125, smoothed: 116.2 },
        solarFlux: { observed: 162.0, adjusted: 160.2 },
        geomagneticActivity: { kpIndex: 3.0 },
        activityLevel: 'Moderate',
      },
      {
        timestamp: new Date('2024-01-03T00:00:00Z'),
        cycleNumber: 25,
        sunspotNumber: { daily: 130, smoothed: 117.0 },
        solarFlux: { observed: 165.0, adjusted: 163.0 },
        geomagneticActivity: { kpIndex: 3.5 },
        activityLevel: 'Moderate',
      },
    ];

    // Insert sample observations
    for (const obs of sampleObservations) {
      await SolarDataModel.saveObservation(obs);
      logger.info('Inserted observation', { timestamp: obs.timestamp });
    }

    // Sample solar events
    const sampleEvents = [
      {
        type: 'Solar Flare',
        timestamp: new Date('2024-01-01T10:30:00Z'),
        description: 'C-class solar flare detected',
        severity: 'minor',
        metadata: { classification: 'C5.2' },
      },
      {
        type: 'Coronal Mass Ejection',
        timestamp: new Date('2024-01-02T14:20:00Z'),
        description: 'CME observed, Earth-directed',
        severity: 'moderate',
        metadata: { speed: '450 km/s' },
      },
    ];

    // Insert sample events
    for (const event of sampleEvents) {
      await SolarDataModel.saveEvent(event);
      logger.info('Inserted event', { type: event.type });
    }

    logger.info('Database seeding completed successfully');
    process.exit(0);
  } catch (error) {
    logger.error('Seeding failed', { error: error.message });
    process.exit(1);
  }
}

// Run seeding
seedDatabase();
