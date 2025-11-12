import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/constants/app_constants.dart';
import 'api_models.dart';

class SolarApiService {
  final Dio _dio;

  SolarApiService(this._dio) {
    _dio.options = BaseOptions(
      baseUrl: AppConstants.baseUrl,
      connectTimeout: AppConstants.connectTimeout,
      receiveTimeout: AppConstants.receiveTimeout,
      sendTimeout: AppConstants.sendTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );
  }

  // Get current solar status
  Future<CurrentStatusResponse> getCurrentStatus() async {
    try {
      final response = await _dio.get(AppConstants.currentStatusEndpoint);
      return CurrentStatusResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // Get sunspot history
  Future<SunspotHistoryResponse> getSunspotHistory({
    String range = '1y',
    int limit = 100,
  }) async {
    try {
      final response = await _dio.get(
        AppConstants.sunspotHistoryEndpoint,
        queryParameters: {
          'range': range,
          'limit': limit,
        },
      );
      return SunspotHistoryResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // Get solar alerts
  Future<AlertsResponse> getAlerts({int limit = 20}) async {
    try {
      final response = await _dio.get(
        AppConstants.alertsEndpoint,
        queryParameters: {'limit': limit},
      );
      return AlertsResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // Get solar forecast
  Future<ForecastResponse> getForecast({int days = 30}) async {
    try {
      final response = await _dio.get(
        AppConstants.forecastEndpoint,
        queryParameters: {'days': days},
      );
      return ForecastResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // Get ML short-term prediction
  Future<MlPredictionResponse> getShortTermPrediction({
    required int daysAhead,
    String? modelType,
  }) async {
    try {
      final response = await _dio.post(
        AppConstants.mlShortTermEndpoint,
        data: {
          'daysAhead': daysAhead,
          if (modelType != null) 'modelType': modelType,
        },
      );
      return MlPredictionResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // Get ML long-term prediction
  Future<MlPredictionResponse> getLongTermPrediction({
    required int daysAhead,
    String? modelType,
  }) async {
    try {
      final response = await _dio.post(
        AppConstants.mlLongTermEndpoint,
        data: {
          'daysAhead': daysAhead,
          if (modelType != null) 'modelType': modelType,
        },
      );
      return MlPredictionResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // Get current anomalies
  Future<AnomalyResponse> getCurrentAnomalies() async {
    try {
      final response = await _dio.get(AppConstants.anomalyCurrentEndpoint);
      return AnomalyResponse.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  // Error handler
  ApiException _handleError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException(
          message: 'Connection timeout. Please try again.',
          statusCode: error.response?.statusCode,
        );
      case DioExceptionType.badResponse:
        return ApiException(
          message: error.response?.data['message'] ?? 'Server error occurred',
          statusCode: error.response?.statusCode,
        );
      case DioExceptionType.cancel:
        return ApiException(
          message: 'Request cancelled',
          statusCode: error.response?.statusCode,
        );
      case DioExceptionType.unknown:
        if (error.error.toString().contains('SocketException')) {
          return ApiException(
            message: 'No internet connection',
            statusCode: error.response?.statusCode,
          );
        }
        return ApiException(
          message: 'An unexpected error occurred',
          statusCode: error.response?.statusCode,
        );
      default:
        return ApiException(
          message: 'An error occurred',
          statusCode: error.response?.statusCode,
        );
    }
  }
}

// API Exception class
class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException({
    required this.message,
    this.statusCode,
  });

  @override
  String toString() => message;
}

// Provider for Dio instance
final dioProvider = Provider<Dio>((ref) {
  return Dio();
});

// Provider for Solar API Service
final solarApiServiceProvider = Provider<SolarApiService>((ref) {
  final dio = ref.watch(dioProvider);
  return SolarApiService(dio);
});
