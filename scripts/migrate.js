#!/usr/bin/env node

/**
 * Database migration script
 * Run with: npm run db:migrate
 */

require('dotenv').config();
const SolarDataModel = require('../src/models/solarData');
const logger = require('../src/utils/logger');
const { testConnection } = require('../src/config/database');

async function runMigrations() {
  try {
    logger.info('Starting database migrations...');

    // Test connection
    const connected = await testConnection();
    if (!connected) {
      throw new Error('Database connection failed');
    }

    // Create tables
    await SolarDataModel.createTables();

    logger.info('Database migrations completed successfully');
    process.exit(0);
  } catch (error) {
    logger.error('Migration failed', { error: error.message });
    process.exit(1);
  }
}

// Run migrations
runMigrations();
