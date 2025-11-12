import 'package:collection/collection.dart';
import '../models/solar_observation.dart';
import '../models/api_response.dart';

/// Utilities for processing chart data
class ChartDataProcessor {
  /// Downsample data using Largest Triangle Three Buckets (LTTB) algorithm
  /// for optimal visualization performance with large datasets
  ///
  /// [data] - Original data points
  /// [threshold] - Target number of points after downsampling
  static List<SolarObservation> downsample(
    List<SolarObservation> data,
    int threshold,
  ) {
    if (data.length <= threshold || threshold < 3) {
      return data;
    }

    final downsampled = <SolarObservation>[];

    // Always keep first point
    downsampled.add(data.first);

    final bucketSize = (data.length - 2) / (threshold - 2);

    var a = 0; // Initially a is the first point in the triangle

    for (var i = 0; i < threshold - 2; i++) {
      // Calculate point average for next bucket
      var avgX = 0.0;
      var avgY = 0.0;
      final avgRangeStart = ((i + 1) * bucketSize).floor() + 1;
      var avgRangeEnd = ((i + 2) * bucketSize).floor() + 1;
      avgRangeEnd = avgRangeEnd < data.length ? avgRangeEnd : data.length;

      final avgRangeLength = avgRangeEnd - avgRangeStart;

      for (; avgRangeStart < avgRangeEnd; avgRangeStart++) {
        avgX += data[avgRangeStart].timestamp.millisecondsSinceEpoch;
        avgY += data[avgRangeStart].sunspotNumberDaily ?? 0;
      }
      avgX /= avgRangeLength;
      avgY /= avgRangeLength;

      // Get the range for this bucket
      final rangeOffs = (i * bucketSize).floor() + 1;
      final rangeTo = ((i + 1) * bucketSize).floor() + 1;

      // Point a
      final pointAx = data[a].timestamp.millisecondsSinceEpoch.toDouble();
      final pointAy = data[a].sunspotNumberDaily ?? 0;

      var maxArea = -1.0;
      var maxAreaPoint = 0;

      for (var j = rangeOffs; j < rangeTo; j++) {
        // Calculate triangle area
        final pointX = data[j].timestamp.millisecondsSinceEpoch.toDouble();
        final pointY = data[j].sunspotNumberDaily ?? 0;

        final area = ((pointAx - avgX) * (pointY - pointAy) -
                (pointAx - pointX) * (avgY - pointAy))
            .abs();

        if (area > maxArea) {
          maxArea = area;
          maxAreaPoint = j;
        }
      }

      downsampled.add(data[maxAreaPoint]);
      a = maxAreaPoint; // This point is the next a
    }

    // Always keep last point
    downsampled.add(data.last);

    return downsampled;
  }

  /// Apply moving average smoothing to data
  ///
  /// [data] - Original data points
  /// [windowSize] - Number of points to average
  static List<ChartDataPoint> applyMovingAverage(
    List<SolarObservation> data,
    int windowSize,
  ) {
    if (windowSize <= 1 || data.isEmpty) {
      return data
          .map((obs) => ChartDataPoint(
                x: obs.timestamp,
                y: obs.sunspotNumberDaily ?? 0,
              ))
          .toList();
    }

    final smoothed = <ChartDataPoint>[];
    final halfWindow = windowSize ~/ 2;

    for (var i = 0; i < data.length; i++) {
      final start = (i - halfWindow).clamp(0, data.length - 1);
      final end = (i + halfWindow + 1).clamp(0, data.length);

      var sum = 0.0;
      var count = 0;

      for (var j = start; j < end; j++) {
        if (data[j].sunspotNumberDaily != null) {
          sum += data[j].sunspotNumberDaily!;
          count++;
        }
      }

      smoothed.add(ChartDataPoint(
        x: data[i].timestamp,
        y: count > 0 ? sum / count : 0,
      ));
    }

    return smoothed;
  }

  /// Convert observations to chart data points
  ///
  /// [useSmoothed] - If true, use smoothed values instead of daily
  static List<ChartDataPoint> toChartDataPoints(
    List<SolarObservation> data, {
    bool useSmoothed = false,
  }) {
    return data
        .where((obs) => useSmoothed
            ? obs.sunspotNumberSmoothed != null
            : obs.sunspotNumberDaily != null)
        .map((obs) => ChartDataPoint(
              x: obs.timestamp,
              y: useSmoothed
                  ? obs.sunspotNumberSmoothed!
                  : obs.sunspotNumberDaily!,
              metadata: {
                'cycleNumber': obs.cycleNumber,
                'activityLevel': obs.activityLevel,
              },
            ))
        .toList();
  }

  /// Calculate min and max values for chart bounds
  static ({double min, double max}) calculateBounds(
    List<ChartDataPoint> data, {
    double padding = 0.1,
  }) {
    if (data.isEmpty) {
      return (min: 0.0, max: 100.0);
    }

    final yValues = data.map((p) => p.y).toList();
    final min = yValues.min;
    final max = yValues.max;
    final range = max - min;

    return (
      min: (min - range * padding).clamp(0.0, double.infinity),
      max: max + range * padding,
    );
  }

  /// Filter data by date range
  static List<SolarObservation> filterByDateRange(
    List<SolarObservation> data,
    DateTime startDate,
    DateTime endDate,
  ) {
    return data
        .where((obs) =>
            obs.timestamp.isAfter(startDate) &&
            obs.timestamp.isBefore(endDate))
        .toList();
  }

  /// Get data for specific time range
  static List<SolarObservation> getDataForTimeRange(
    List<SolarObservation> data,
    TimeRange range,
  ) {
    final now = DateTime.now();

    switch (range) {
      case TimeRange.oneYear:
        final startDate = now.subtract(const Duration(days: 365));
        return filterByDateRange(data, startDate, now);

      case TimeRange.fiveYears:
        final startDate = now.subtract(const Duration(days: 1825));
        return filterByDateRange(data, startDate, now);

      case TimeRange.cycle:
        // Solar Cycle 25 started in December 2019
        final cycleStart = DateTime(2019, 12, 1);
        return filterByDateRange(data, cycleStart, now);

      case TimeRange.all:
        return data;
    }
  }

  /// Calculate statistics for data
  static Map<String, double> calculateStats(List<ChartDataPoint> data) {
    if (data.isEmpty) {
      return {
        'mean': 0,
        'median': 0,
        'min': 0,
        'max': 0,
        'stdDev': 0,
      };
    }

    final yValues = data.map((p) => p.y).toList()..sort();
    final mean = yValues.average;
    final median = yValues[yValues.length ~/ 2];
    final min = yValues.first;
    final max = yValues.last;

    final variance = yValues.map((y) => (y - mean) * (y - mean)).average;
    final stdDev = variance.squareRoot;

    return {
      'mean': mean,
      'median': median,
      'min': min,
      'max': max,
      'stdDev': stdDev,
    };
  }
}

extension _ListStats on List<double> {
  double get average => isEmpty ? 0 : reduce((a, b) => a + b) / length;

  double get squareRoot {
    if (length == 1) return first.abs();
    return reduce((a, b) => a * a + b * b) / length;
  }
}
