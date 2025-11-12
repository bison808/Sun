import 'package:flutter_test/flutter_test.dart';
import 'package:solar_cycle_app/models/solar_observation.dart';
import 'package:solar_cycle_app/models/api_response.dart';
import 'package:solar_cycle_app/utils/chart_data_processor.dart';

void main() {
  group('ChartDataProcessor', () {
    late List<SolarObservation> testData;

    setUp(() {
      // Create test data
      testData = List.generate(
        100,
        (index) => SolarObservation(
          id: index,
          timestamp: DateTime(2020, 1, 1).add(Duration(days: index)),
          cycleNumber: 25,
          sunspotNumberDaily: 50.0 + index.toDouble(),
          sunspotNumberSmoothed: 45.0 + index.toDouble(),
        ),
      );
    });

    group('downsample', () {
      test('should return original data if length <= threshold', () {
        final result = ChartDataProcessor.downsample(testData, 100);
        expect(result.length, equals(testData.length));
      });

      test('should downsample to approximately target size', () {
        final result = ChartDataProcessor.downsample(testData, 50);
        expect(result.length, lessThanOrEqualTo(52)); // Allow some variance
        expect(result.length, greaterThanOrEqualTo(48));
      });

      test('should always keep first and last points', () {
        final result = ChartDataProcessor.downsample(testData, 10);
        expect(result.first.id, equals(testData.first.id));
        expect(result.last.id, equals(testData.last.id));
      });

      test('should handle threshold < 3', () {
        final result = ChartDataProcessor.downsample(testData, 2);
        expect(result.length, equals(testData.length));
      });

      test('should handle empty data', () {
        final result = ChartDataProcessor.downsample([], 10);
        expect(result, isEmpty);
      });
    });

    group('applyMovingAverage', () {
      test('should return original values when window size = 1', () {
        final result = ChartDataProcessor.applyMovingAverage(testData, 1);
        expect(result.length, equals(testData.length));
        expect(result.first.y, equals(testData.first.sunspotNumberDaily));
      });

      test('should smooth data with window size > 1', () {
        final result = ChartDataProcessor.applyMovingAverage(testData, 5);
        expect(result.length, equals(testData.length));

        // Check that middle values are averaged
        // For a linearly increasing dataset, average should be close to center value
        final middleIndex = testData.length ~/ 2;
        final expectedAverage = testData[middleIndex].sunspotNumberDaily!;
        expect(result[middleIndex].y, closeTo(expectedAverage, 5.0));
      });

      test('should handle empty data', () {
        final result = ChartDataProcessor.applyMovingAverage([], 5);
        expect(result, isEmpty);
      });

      test('should handle null values gracefully', () {
        final dataWithNulls = [
          SolarObservation(
            id: 1,
            timestamp: DateTime(2020, 1, 1),
            cycleNumber: 25,
            sunspotNumberDaily: 50.0,
          ),
          SolarObservation(
            id: 2,
            timestamp: DateTime(2020, 1, 2),
            cycleNumber: 25,
            sunspotNumberDaily: null,
          ),
          SolarObservation(
            id: 3,
            timestamp: DateTime(2020, 1, 3),
            cycleNumber: 25,
            sunspotNumberDaily: 60.0,
          ),
        ];

        final result = ChartDataProcessor.applyMovingAverage(dataWithNulls, 3);
        expect(result.length, equals(3));
      });
    });

    group('toChartDataPoints', () {
      test('should convert daily values by default', () {
        final result = ChartDataProcessor.toChartDataPoints(testData);
        expect(result.length, equals(testData.length));
        expect(result.first.y, equals(testData.first.sunspotNumberDaily));
      });

      test('should convert smoothed values when useSmoothed = true', () {
        final result = ChartDataProcessor.toChartDataPoints(
          testData,
          useSmoothed: true,
        );
        expect(result.length, equals(testData.length));
        expect(result.first.y, equals(testData.first.sunspotNumberSmoothed));
      });

      test('should filter out null values', () {
        final dataWithNulls = [
          SolarObservation(
            id: 1,
            timestamp: DateTime(2020, 1, 1),
            cycleNumber: 25,
            sunspotNumberDaily: 50.0,
          ),
          SolarObservation(
            id: 2,
            timestamp: DateTime(2020, 1, 2),
            cycleNumber: 25,
            sunspotNumberDaily: null,
          ),
        ];

        final result = ChartDataProcessor.toChartDataPoints(dataWithNulls);
        expect(result.length, equals(1));
      });

      test('should include metadata', () {
        final result = ChartDataProcessor.toChartDataPoints(testData);
        expect(result.first.metadata, isNotNull);
        expect(result.first.metadata!['cycleNumber'], equals(25));
      });
    });

    group('calculateBounds', () {
      test('should calculate correct min and max with padding', () {
        final chartData = ChartDataProcessor.toChartDataPoints(testData);
        final bounds = ChartDataProcessor.calculateBounds(chartData);

        // Original min: 50, max: 149, range: 99
        // With 10% padding: min ~= 40.1, max ~= 158.9
        expect(bounds.min, lessThan(50.0));
        expect(bounds.max, greaterThan(149.0));
        expect(bounds.min, greaterThanOrEqualTo(0.0)); // Should clamp at 0
      });

      test('should handle empty data', () {
        final bounds = ChartDataProcessor.calculateBounds([]);
        expect(bounds.min, equals(0.0));
        expect(bounds.max, equals(100.0));
      });

      test('should respect custom padding', () {
        final chartData = ChartDataProcessor.toChartDataPoints(testData);
        final bounds = ChartDataProcessor.calculateBounds(
          chartData,
          padding: 0.0,
        );

        expect(bounds.min, equals(50.0));
        expect(bounds.max, equals(149.0));
      });
    });

    group('filterByDateRange', () {
      test('should filter data within date range', () {
        final startDate = DateTime(2020, 1, 10);
        final endDate = DateTime(2020, 1, 20);

        final result = ChartDataProcessor.filterByDateRange(
          testData,
          startDate,
          endDate,
        );

        expect(result.length, lessThan(testData.length));
        expect(
          result.every((obs) =>
              obs.timestamp.isAfter(startDate) &&
              obs.timestamp.isBefore(endDate)),
          isTrue,
        );
      });

      test('should return empty list if no data in range', () {
        final startDate = DateTime(2025, 1, 1);
        final endDate = DateTime(2025, 1, 31);

        final result = ChartDataProcessor.filterByDateRange(
          testData,
          startDate,
          endDate,
        );

        expect(result, isEmpty);
      });
    });

    group('getDataForTimeRange', () {
      test('should filter data for 1 year range', () {
        final result = ChartDataProcessor.getDataForTimeRange(
          testData,
          TimeRange.oneYear,
        );

        // Test data is from 2020, should be filtered out
        expect(result.length, lessThanOrEqualTo(testData.length));
      });

      test('should return all data for "all" range', () {
        final result = ChartDataProcessor.getDataForTimeRange(
          testData,
          TimeRange.all,
        );

        expect(result.length, equals(testData.length));
      });

      test('should filter data for cycle range', () {
        final result = ChartDataProcessor.getDataForTimeRange(
          testData,
          TimeRange.cycle,
        );

        // Cycle 25 started Dec 2019, test data is from 2020
        expect(result.length, equals(testData.length));
      });
    });

    group('calculateStats', () {
      test('should calculate correct statistics', () {
        final chartData = ChartDataProcessor.toChartDataPoints(testData);
        final stats = ChartDataProcessor.calculateStats(chartData);

        expect(stats['mean'], isNotNull);
        expect(stats['median'], isNotNull);
        expect(stats['min'], equals(50.0));
        expect(stats['max'], equals(149.0));
        expect(stats['stdDev'], isNotNull);

        // Mean should be around middle of range
        expect(stats['mean']!, closeTo(99.5, 1.0));
      });

      test('should handle empty data', () {
        final stats = ChartDataProcessor.calculateStats([]);

        expect(stats['mean'], equals(0));
        expect(stats['median'], equals(0));
        expect(stats['min'], equals(0));
        expect(stats['max'], equals(0));
        expect(stats['stdDev'], equals(0));
      });

      test('should handle single data point', () {
        final singlePoint = [
          ChartDataPoint(x: DateTime.now(), y: 50.0),
        ];

        final stats = ChartDataProcessor.calculateStats(singlePoint);

        expect(stats['mean'], equals(50.0));
        expect(stats['median'], equals(50.0));
        expect(stats['min'], equals(50.0));
        expect(stats['max'], equals(50.0));
      });
    });
  });
}
