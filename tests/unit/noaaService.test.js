const noaaService = require('../../src/services/noaaService');

describe('NoaaService', () => {
  describe('calculateActivityLevel', () => {
    it('should return "Very Low" for low values', () => {
      const sunspotData = { daily: 10 };
      const solarFluxData = { observed: 70 };
      const result = noaaService.calculateActivityLevel(sunspotData, solarFluxData);
      expect(result).toBe('Very Low');
    });

    it('should return "Moderate" for medium values', () => {
      const sunspotData = { daily: 75 };
      const solarFluxData = { observed: 120 };
      const result = noaaService.calculateActivityLevel(sunspotData, solarFluxData);
      expect(result).toBe('Moderate');
    });

    it('should return "Very High" for high values', () => {
      const sunspotData = { daily: 200 };
      const solarFluxData = { observed: 250 };
      const result = noaaService.calculateActivityLevel(sunspotData, solarFluxData);
      expect(result).toBe('Very High');
    });

    it('should return "Unknown" for null data', () => {
      const result = noaaService.calculateActivityLevel(null, null);
      expect(result).toBe('Unknown');
    });
  });

  describe('getGeomagneticCondition', () => {
    it('should return "Quiet" for Kp < 2', () => {
      expect(noaaService.getGeomagneticCondition(1)).toBe('Quiet');
    });

    it('should return "Active" for Kp = 4', () => {
      expect(noaaService.getGeomagneticCondition(4)).toBe('Active');
    });

    it('should return "Severe Storm" for Kp = 8', () => {
      expect(noaaService.getGeomagneticCondition(8)).toBe('Severe Storm');
    });

    it('should return "Extreme Storm" for Kp >= 9', () => {
      expect(noaaService.getGeomagneticCondition(9)).toBe('Extreme Storm');
    });
  });

  describe('calculateMonthsSinceMinimum', () => {
    it('should calculate correct months since Dec 2019', () => {
      const result = noaaService.calculateMonthsSinceMinimum('2020-12-01');
      expect(result).toBe(12);
    });

    it('should handle current date', () => {
      const now = new Date();
      const dateString = now.toISOString().split('T')[0];
      const result = noaaService.calculateMonthsSinceMinimum(dateString);
      expect(result).toBeGreaterThan(0);
    });
  });
});
