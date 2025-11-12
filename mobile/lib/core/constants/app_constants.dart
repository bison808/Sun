class AppConstants {
  AppConstants._();

  // API Configuration
  static const String baseUrl = 'http://localhost:3000';
  static const String apiBasePath = '/api';
  static const String wsBasePath = '/ws';

  // API Endpoints
  static const String currentStatusEndpoint = '$apiBasePath/current-status';
  static const String sunspotHistoryEndpoint = '$apiBasePath/sunspot-history';
  static const String alertsEndpoint = '$apiBasePath/alerts';
  static const String forecastEndpoint = '$apiBasePath/forecast';
  static const String mlShortTermEndpoint = '$apiBasePath/ml/predict/short-term';
  static const String mlLongTermEndpoint = '$apiBasePath/ml/predict/long-term';
  static const String anomalyCurrentEndpoint = '$apiBasePath/ml/anomaly/current';
  static const String wsLiveEndpoint = '$wsBasePath/live';

  // Cache Keys
  static const String cacheCurrentStatus = 'cache_current_status';
  static const String cacheSunspotHistory = 'cache_sunspot_history';
  static const String cacheAlerts = 'cache_alerts';
  static const String cacheForecast = 'cache_forecast';
  static const String cacheThemeMode = 'cache_theme_mode';

  // Cache Duration (in minutes)
  static const int cacheCurrentStatusDuration = 15;
  static const int cacheSunspotHistoryDuration = 60;
  static const int cacheAlertsDuration = 15;
  static const int cacheForecastDuration = 60;

  // Timeout Durations
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);

  // Pagination
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  // Solar Activity Levels
  static const String activityLow = 'Low';
  static const String activityModerate = 'Moderate';
  static const String activityHigh = 'High';
  static const String activityVeryHigh = 'Very High';
  static const String activityExtreme = 'Extreme';

  // Date Formats
  static const String dateFormatFull = 'MMM dd, yyyy HH:mm';
  static const String dateFormatShort = 'MMM dd';
  static const String dateFormatTime = 'HH:mm';

  // Animation Durations
  static const Duration shortAnimationDuration = Duration(milliseconds: 150);
  static const Duration mediumAnimationDuration = Duration(milliseconds: 300);
  static const Duration longAnimationDuration = Duration(milliseconds: 500);

  // Refresh Intervals
  static const Duration autoRefreshInterval = Duration(minutes: 15);
  static const Duration wsReconnectDelay = Duration(seconds: 5);

  // UI Constants
  static const double defaultPadding = 16.0;
  static const double smallPadding = 8.0;
  static const double largePadding = 24.0;
  static const double borderRadius = 12.0;
  static const double cardElevation = 2.0;

  // Chart Constants
  static const int defaultChartDataPoints = 30;
  static const int maxChartDataPoints = 365;
}
