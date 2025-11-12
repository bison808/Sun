const Joi = require('joi');

/**
 * Validation middleware factory
 */
const validate = (schema) => {
  return (req, res, next) => {
    const { error } = schema.validate(req.query, {
      abortEarly: false,
      stripUnknown: true,
    });

    if (error) {
      const errors = error.details.map(detail => ({
        field: detail.path.join('.'),
        message: detail.message,
      }));

      return res.status(400).json({
        success: false,
        error: {
          message: 'Validation failed',
          details: errors,
        },
      });
    }

    next();
  };
};

/**
 * Query parameter schemas
 */
const schemas = {
  historyRange: Joi.object({
    range: Joi.string().valid('1y', '5y', 'cycle').default('1y'),
    limit: Joi.number().integer().min(1).max(10000).default(1000),
  }),

  eventLimit: Joi.object({
    limit: Joi.number().integer().min(1).max(100).default(50),
  }),

  predictionParams: Joi.object({
    horizon: Joi.number().integer().min(1).max(365).default(30),
  }),
};

module.exports = {
  validate,
  schemas,
};
