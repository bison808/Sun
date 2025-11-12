const request = require('supertest');
const { app } = require('../../src/server');

describe('API Integration Tests', () => {
  describe('GET /', () => {
    it('should return API information', async () => {
      const response = await request(app).get('/');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('name');
      expect(response.body).toHaveProperty('version');
      expect(response.body).toHaveProperty('endpoints');
    });
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health');

      expect(response.status).toBeGreaterThanOrEqual(200);
      expect(response.body).toHaveProperty('status');
      expect(response.body).toHaveProperty('services');
      expect(response.body).toHaveProperty('timestamp');
    });
  });

  describe('GET /api/current-status', () => {
    it('should return current solar status', async () => {
      const response = await request(app).get('/api/current-status');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body).toHaveProperty('timestamp');
    }, 30000); // Increase timeout for external API call
  });

  describe('GET /api/sunspot-history', () => {
    it('should return historical data with default range', async () => {
      const response = await request(app).get('/api/sunspot-history');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body).toHaveProperty('range');
    }, 30000);

    it('should accept range parameter', async () => {
      const response = await request(app).get('/api/sunspot-history?range=5y');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.range).toBe('5y');
    }, 30000);

    it('should reject invalid range parameter', async () => {
      const response = await request(app).get('/api/sunspot-history?range=invalid');

      expect(response.status).toBe(400);
      expect(response.body).toHaveProperty('success', false);
    });
  });

  describe('GET /api/forecast', () => {
    it('should return solar forecast', async () => {
      const response = await request(app).get('/api/forecast');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
    });
  });

  describe('POST /api/ml/predict/short-term', () => {
    it('should return short-term prediction', async () => {
      const response = await request(app)
        .post('/api/ml/predict/short-term')
        .send({ horizon: 7 });

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('success', true);
      expect(response.body.data).toHaveProperty('predictions');
    });
  });

  describe('404 handler', () => {
    it('should return 404 for unknown routes', async () => {
      const response = await request(app).get('/api/unknown-route');

      expect(response.status).toBe(404);
      expect(response.body).toHaveProperty('success', false);
      expect(response.body.error).toHaveProperty('message', 'Route not found');
    });
  });
});
