import 'package:freezed_annotation/freezed_annotation.dart';

part 'api_models.freezed.dart';
part 'api_models.g.dart';

// Current Status Response
@freezed
class CurrentStatusResponse with _$CurrentStatusResponse {
  const factory CurrentStatusResponse({
    required bool success,
    required CurrentStatusData data,
    required bool cached,
    required String timestamp,
  }) = _CurrentStatusResponse;

  factory CurrentStatusResponse.fromJson(Map<String, dynamic> json) =>
      _$CurrentStatusResponseFromJson(json);
}

@freezed
class CurrentStatusData with _$CurrentStatusData {
  const factory CurrentStatusData({
    required String timestamp,
    required SolarCycle solarCycle,
    required SunspotNumber sunspotNumber,
    required SolarFlux solarFlux,
    required GeomagneticActivity geomagneticActivity,
    required String activityLevel,
  }) = _CurrentStatusData;

  factory CurrentStatusData.fromJson(Map<String, dynamic> json) =>
      _$CurrentStatusDataFromJson(json);
}

@freezed
class SolarCycle with _$SolarCycle {
  const factory SolarCycle({
    required int cycleNumber,
    required int monthsSinceMinimum,
    required double smoothedSunspotNumber,
  }) = _SolarCycle;

  factory SolarCycle.fromJson(Map<String, dynamic> json) =>
      _$SolarCycleFromJson(json);
}

@freezed
class SunspotNumber with _$SunspotNumber {
  const factory SunspotNumber({
    required double daily,
    required double smoothed,
  }) = _SunspotNumber;

  factory SunspotNumber.fromJson(Map<String, dynamic> json) =>
      _$SunspotNumberFromJson(json);
}

@freezed
class SolarFlux with _$SolarFlux {
  const factory SolarFlux({
    required double observed,
    required double adjusted,
  }) = _SolarFlux;

  factory SolarFlux.fromJson(Map<String, dynamic> json) =>
      _$SolarFluxFromJson(json);
}

@freezed
class GeomagneticActivity with _$GeomagneticActivity {
  const factory GeomagneticActivity({
    required double kpIndex,
    required String condition,
  }) = _GeomagneticActivity;

  factory GeomagneticActivity.fromJson(Map<String, dynamic> json) =>
      _$GeomagneticActivityFromJson(json);
}

// Sunspot History Response
@freezed
class SunspotHistoryResponse with _$SunspotHistoryResponse {
  const factory SunspotHistoryResponse({
    required bool success,
    required List<SunspotData> data,
    required int total,
    required bool cached,
    required String timestamp,
  }) = _SunspotHistoryResponse;

  factory SunspotHistoryResponse.fromJson(Map<String, dynamic> json) =>
      _$SunspotHistoryResponseFromJson(json);
}

@freezed
class SunspotData with _$SunspotData {
  const factory SunspotData({
    required String date,
    required double sunspotNumber,
    required double? smoothedSunspotNumber,
  }) = _SunspotData;

  factory SunspotData.fromJson(Map<String, dynamic> json) =>
      _$SunspotDataFromJson(json);
}

// Alerts Response
@freezed
class AlertsResponse with _$AlertsResponse {
  const factory AlertsResponse({
    required bool success,
    required List<AlertData> data,
    required bool cached,
    required String timestamp,
  }) = _AlertsResponse;

  factory AlertsResponse.fromJson(Map<String, dynamic> json) =>
      _$AlertsResponseFromJson(json);
}

@freezed
class AlertData with _$AlertData {
  const factory AlertData({
    required String id,
    required String eventType,
    required String severity,
    required String description,
    required String timestamp,
    String? expectedImpact,
  }) = _AlertData;

  factory AlertData.fromJson(Map<String, dynamic> json) =>
      _$AlertDataFromJson(json);
}

// Forecast Response
@freezed
class ForecastResponse with _$ForecastResponse {
  const factory ForecastResponse({
    required bool success,
    required List<ForecastData> data,
    required bool cached,
    required String timestamp,
  }) = _ForecastResponse;

  factory ForecastResponse.fromJson(Map<String, dynamic> json) =>
      _$ForecastResponseFromJson(json);
}

@freezed
class ForecastData with _$ForecastData {
  const factory ForecastData({
    required String date,
    required double predictedSunspotNumber,
    required double confidence,
  }) = _ForecastData;

  factory ForecastData.fromJson(Map<String, dynamic> json) =>
      _$ForecastDataFromJson(json);
}

// ML Prediction Request
@freezed
class MlPredictionRequest with _$MlPredictionRequest {
  const factory MlPredictionRequest({
    required int daysAhead,
    String? modelType,
  }) = _MlPredictionRequest;

  factory MlPredictionRequest.fromJson(Map<String, dynamic> json) =>
      _$MlPredictionRequestFromJson(json);
}

// ML Prediction Response
@freezed
class MlPredictionResponse with _$MlPredictionResponse {
  const factory MlPredictionResponse({
    required bool success,
    required MlPredictionData data,
    required String timestamp,
  }) = _MlPredictionResponse;

  factory MlPredictionResponse.fromJson(Map<String, dynamic> json) =>
      _$MlPredictionResponseFromJson(json);
}

@freezed
class MlPredictionData with _$MlPredictionData {
  const factory MlPredictionData({
    required String predictionType,
    required List<PredictionPoint> predictions,
    required double confidence,
    required String modelVersion,
  }) = _MlPredictionData;

  factory MlPredictionData.fromJson(Map<String, dynamic> json) =>
      _$MlPredictionDataFromJson(json);
}

@freezed
class PredictionPoint with _$PredictionPoint {
  const factory PredictionPoint({
    required String date,
    required double value,
    required double confidenceInterval,
  }) = _PredictionPoint;

  factory PredictionPoint.fromJson(Map<String, dynamic> json) =>
      _$PredictionPointFromJson(json);
}

// Anomaly Response
@freezed
class AnomalyResponse with _$AnomalyResponse {
  const factory AnomalyResponse({
    required bool success,
    required List<AnomalyData> data,
    required bool cached,
    required String timestamp,
  }) = _AnomalyResponse;

  factory AnomalyResponse.fromJson(Map<String, dynamic> json) =>
      _$AnomalyResponseFromJson(json);
}

@freezed
class AnomalyData with _$AnomalyData {
  const factory AnomalyData({
    required String timestamp,
    required String metric,
    required double value,
    required double expectedValue,
    required double deviationScore,
    required String severity,
  }) = _AnomalyData;

  factory AnomalyData.fromJson(Map<String, dynamic> json) =>
      _$AnomalyDataFromJson(json);
}

// API Error Response
@freezed
class ApiError with _$ApiError {
  const factory ApiError({
    required bool success,
    required String error,
    String? message,
    int? statusCode,
  }) = _ApiError;

  factory ApiError.fromJson(Map<String, dynamic> json) =>
      _$ApiErrorFromJson(json);
}
