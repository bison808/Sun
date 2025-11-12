const redis = require('redis');
const logger = require('../utils/logger');

const redisClient = redis.createClient({
  socket: {
    host: process.env.REDIS_HOST || 'localhost',
    port: process.env.REDIS_PORT || 6379,
  },
  password: process.env.REDIS_PASSWORD || undefined,
  database: parseInt(process.env.REDIS_DB) || 0,
});

redisClient.on('connect', () => {
  logger.info('Redis connection established');
});

redisClient.on('error', (err) => {
  logger.error('Redis error', { error: err.message });
});

redisClient.on('reconnecting', () => {
  logger.warn('Redis reconnecting...');
});

const connectRedis = async () => {
  try {
    await redisClient.connect();
    logger.info('Redis client connected successfully');
    return true;
  } catch (err) {
    logger.error('Failed to connect to Redis', { error: err.message });
    return false;
  }
};

const cacheService = {
  get: async (key) => {
    try {
      const data = await redisClient.get(key);
      return data ? JSON.parse(data) : null;
    } catch (err) {
      logger.error('Redis GET error', { key, error: err.message });
      return null;
    }
  },

  set: async (key, value, ttl = parseInt(process.env.CACHE_TTL) || 3600) => {
    try {
      await redisClient.setEx(key, ttl, JSON.stringify(value));
      return true;
    } catch (err) {
      logger.error('Redis SET error', { key, error: err.message });
      return false;
    }
  },

  del: async (key) => {
    try {
      await redisClient.del(key);
      return true;
    } catch (err) {
      logger.error('Redis DEL error', { key, error: err.message });
      return false;
    }
  },

  flush: async () => {
    try {
      await redisClient.flushDb();
      logger.info('Redis cache flushed');
      return true;
    } catch (err) {
      logger.error('Redis FLUSH error', { error: err.message });
      return false;
    }
  },
};

module.exports = {
  redisClient,
  connectRedis,
  cacheService,
};
