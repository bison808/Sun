import 'package:flutter_test/flutter_test.dart';
import 'package:solar_cycle_app/models/solar_observation.dart';

void main() {
  group('SolarObservation', () {
    final testJson = {
      'id': 1,
      'timestamp': '2024-01-15T12:00:00Z',
      'cycle_number': 25,
      'sunspot_number_daily': 75.5,
      'sunspot_number_smoothed': 70.2,
      'solar_flux_observed': 150.3,
      'solar_flux_adjusted': 148.7,
      'kp_index': 3.5,
      'activity_level': 'Moderate',
      'created_at': '2024-01-15T12:05:00Z',
    };

    test('should parse JSON correctly', () {
      final observation = SolarObservation.fromJson(testJson);

      expect(observation.id, equals(1));
      expect(observation.cycleNumber, equals(25));
      expect(observation.sunspotNumberDaily, equals(75.5));
      expect(observation.sunspotNumberSmoothed, equals(70.2));
      expect(observation.solarFluxObserved, equals(150.3));
      expect(observation.solarFluxAdjusted, equals(148.7));
      expect(observation.kpIndex, equals(3.5));
      expect(observation.activityLevel, equals('Moderate'));
    });

    test('should handle null optional fields', () {
      final minimalJson = {
        'id': 1,
        'timestamp': '2024-01-15T12:00:00Z',
        'cycle_number': 25,
      };

      final observation = SolarObservation.fromJson(minimalJson);

      expect(observation.id, equals(1));
      expect(observation.cycleNumber, equals(25));
      expect(observation.sunspotNumberDaily, isNull);
      expect(observation.sunspotNumberSmoothed, isNull);
      expect(observation.solarFluxObserved, isNull);
      expect(observation.solarFluxAdjusted, isNull);
      expect(observation.kpIndex, isNull);
      expect(observation.activityLevel, isNull);
    });

    test('should convert to JSON correctly', () {
      final observation = SolarObservation.fromJson(testJson);
      final json = observation.toJson();

      expect(json['id'], equals(1));
      expect(json['cycle_number'], equals(25));
      expect(json['sunspot_number_daily'], equals(75.5));
      expect(json['sunspot_number_smoothed'], equals(70.2));
      expect(json['activity_level'], equals('Moderate'));
    });

    test('should parse timestamps correctly', () {
      final observation = SolarObservation.fromJson(testJson);

      expect(observation.timestamp, isA<DateTime>());
      expect(observation.timestamp.year, equals(2024));
      expect(observation.timestamp.month, equals(1));
      expect(observation.timestamp.day, equals(15));
    });

    test('should have correct toString representation', () {
      final observation = SolarObservation.fromJson(testJson);
      final string = observation.toString();

      expect(string, contains('timestamp'));
      expect(string, contains('sunspotDaily'));
      expect(string, contains('sunspotSmoothed'));
    });

    test('should handle integer values for float fields', () {
      final jsonWithIntegers = {
        'id': 1,
        'timestamp': '2024-01-15T12:00:00Z',
        'cycle_number': 25,
        'sunspot_number_daily': 75, // Integer instead of double
        'kp_index': 3, // Integer instead of double
      };

      final observation = SolarObservation.fromJson(jsonWithIntegers);

      expect(observation.sunspotNumberDaily, equals(75.0));
      expect(observation.kpIndex, equals(3.0));
    });
  });
}
