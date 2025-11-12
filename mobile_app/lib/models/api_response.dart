/// Generic API response wrapper
class ApiResponse<T> {
  final bool success;
  final T data;
  final bool cached;
  final DateTime timestamp;
  final int? count;

  ApiResponse({
    required this.success,
    required this.data,
    required this.cached,
    required this.timestamp,
    this.count,
  });

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(dynamic) fromJsonT,
  ) {
    return ApiResponse<T>(
      success: json['success'] as bool,
      data: fromJsonT(json['data']),
      cached: json['cached'] as bool,
      timestamp: DateTime.parse(json['timestamp'] as String),
      count: json['count'] as int?,
    );
  }
}

/// Time range options for historical data
enum TimeRange {
  oneYear('1y', 'Last Year', 365),
  fiveYears('5y', 'Last 5 Years', 1825),
  cycle('cycle', 'Current Cycle', null),
  all('all', 'All Data', null);

  final String value;
  final String label;
  final int? days;

  const TimeRange(this.value, this.label, this.days);
}

/// Smoothing options for data
enum SmoothingOption {
  none('None', null),
  daily('Daily', 1),
  weekly('Weekly', 7),
  monthly('Monthly', 30);

  final String label;
  final int? windowSize;

  const SmoothingOption(this.label, this.windowSize);
}

/// Chart data point for plotting
class ChartDataPoint {
  final DateTime x;
  final double y;
  final String? label;
  final Map<String, dynamic>? metadata;

  ChartDataPoint({
    required this.x,
    required this.y,
    this.label,
    this.metadata,
  });

  @override
  String toString() => 'ChartDataPoint(x: $x, y: $y)';
}
