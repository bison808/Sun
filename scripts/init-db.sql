-- Initialize Solar Cycle Database
-- This script runs automatically when the PostgreSQL container starts

-- Create extension for better JSON support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create tables (handled by the application)
-- This file is a placeholder for any initial database setup

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE solar_cycle_db TO postgres;

-- Log initialization
SELECT 'Solar Cycle Database initialized successfully' AS status;
