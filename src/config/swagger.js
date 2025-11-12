const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Solar Cycle API',
      version: '1.0.0',
      description: 'Backend API for Solar Cycle Mobile App - Real-time solar activity monitoring',
      contact: {
        name: 'Solar Cycle Team',
        email: 'support@solarcycle.app',
      },
      license: {
        name: 'MIT',
        url: 'https://opensource.org/licenses/MIT',
      },
    },
    servers: [
      {
        url: `http://localhost:${process.env.PORT || 3000}`,
        description: 'Development server',
      },
      {
        url: 'https://api.solarcycle.app',
        description: 'Production server',
      },
    ],
    tags: [
      {
        name: 'Solar Data',
        description: 'Solar cycle and space weather data endpoints',
      },
      {
        name: 'Machine Learning',
        description: 'AI-powered predictions and anomaly detection',
      },
      {
        name: 'Health',
        description: 'System health and monitoring',
      },
    ],
    components: {
      schemas: {
        CurrentStatus: {
          type: 'object',
          properties: {
            timestamp: {
              type: 'string',
              format: 'date-time',
              description: 'Data timestamp',
            },
            solarCycle: {
              type: 'object',
              properties: {
                cycleNumber: { type: 'integer' },
                monthsSinceMinimum: { type: 'integer' },
                smoothedSunspotNumber: { type: 'number' },
              },
            },
            sunspotNumber: {
              type: 'object',
              properties: {
                daily: { type: 'number' },
                smoothed: { type: 'number' },
              },
            },
            solarFlux: {
              type: 'object',
              properties: {
                observed: { type: 'number' },
                adjusted: { type: 'number' },
              },
            },
            geomagneticActivity: {
              type: 'object',
              properties: {
                kpIndex: { type: 'number' },
                condition: { type: 'string' },
              },
            },
            activityLevel: {
              type: 'string',
              enum: ['Very Low', 'Low', 'Moderate', 'High', 'Very High'],
            },
          },
        },
        Error: {
          type: 'object',
          properties: {
            success: { type: 'boolean', example: false },
            error: {
              type: 'object',
              properties: {
                message: { type: 'string' },
              },
            },
            timestamp: { type: 'string', format: 'date-time' },
          },
        },
      },
      responses: {
        BadRequest: {
          description: 'Bad request - invalid parameters',
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/Error' },
            },
          },
        },
        NotFound: {
          description: 'Resource not found',
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/Error' },
            },
          },
        },
        InternalError: {
          description: 'Internal server error',
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/Error' },
            },
          },
        },
        TooManyRequests: {
          description: 'Rate limit exceeded',
          content: {
            'application/json': {
              schema: { $ref: '#/components/schemas/Error' },
            },
          },
        },
      },
    },
  },
  apis: ['./src/routes/*.js'], // Path to the API routes
};

const swaggerSpec = swaggerJsdoc(options);

module.exports = {
  swaggerUi,
  swaggerSpec,
};
