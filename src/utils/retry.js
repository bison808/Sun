const logger = require('./logger');

/**
 * Retry a function with exponential backoff
 * @param {Function} fn - Async function to retry
 * @param {Object} options - Retry options
 * @returns {Promise} - Result of the function
 */
async function retryWithBackoff(fn, options = {}) {
  const {
    maxAttempts = parseInt(process.env.RETRY_MAX_ATTEMPTS) || 3,
    delayMs = parseInt(process.env.RETRY_DELAY_MS) || 2000,
    exponential = true,
    onRetry = null,
  } = options;

  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxAttempts) {
        logger.error('Max retry attempts reached', {
          attempts: maxAttempts,
          error: error.message,
        });
        break;
      }

      const delay = exponential ? delayMs * Math.pow(2, attempt - 1) : delayMs;

      logger.warn('Retry attempt', {
        attempt,
        maxAttempts,
        nextRetryIn: delay,
        error: error.message,
      });

      if (onRetry) {
        await onRetry(error, attempt);
      }

      await sleep(delay);
    }
  }

  throw lastError;
}

/**
 * Sleep for a specified duration
 * @param {number} ms - Milliseconds to sleep
 * @returns {Promise}
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

module.exports = {
  retryWithBackoff,
  sleep,
};
