/// Solar observation data model
/// Represents a single data point from the solar_observations table
class SolarObservation {
  final int id;
  final DateTime timestamp;
  final int cycleNumber;
  final double? sunspotNumberDaily;
  final double? sunspotNumberSmoothed;
  final double? solarFluxObserved;
  final double? solarFluxAdjusted;
  final double? kpIndex;
  final String? activityLevel;
  final DateTime? createdAt;

  SolarObservation({
    required this.id,
    required this.timestamp,
    required this.cycleNumber,
    this.sunspotNumberDaily,
    this.sunspotNumberSmoothed,
    this.solarFluxObserved,
    this.solarFluxAdjusted,
    this.kpIndex,
    this.activityLevel,
    this.createdAt,
  });

  factory SolarObservation.fromJson(Map<String, dynamic> json) {
    return SolarObservation(
      id: json['id'] as int,
      timestamp: DateTime.parse(json['timestamp'] as String),
      cycleNumber: json['cycle_number'] as int,
      sunspotNumberDaily: json['sunspot_number_daily'] != null
          ? (json['sunspot_number_daily'] as num).toDouble()
          : null,
      sunspotNumberSmoothed: json['sunspot_number_smoothed'] != null
          ? (json['sunspot_number_smoothed'] as num).toDouble()
          : null,
      solarFluxObserved: json['solar_flux_observed'] != null
          ? (json['solar_flux_observed'] as num).toDouble()
          : null,
      solarFluxAdjusted: json['solar_flux_adjusted'] != null
          ? (json['solar_flux_adjusted'] as num).toDouble()
          : null,
      kpIndex: json['kp_index'] != null
          ? (json['kp_index'] as num).toDouble()
          : null,
      activityLevel: json['activity_level'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'timestamp': timestamp.toIso8601String(),
      'cycle_number': cycleNumber,
      'sunspot_number_daily': sunspotNumberDaily,
      'sunspot_number_smoothed': sunspotNumberSmoothed,
      'solar_flux_observed': solarFluxObserved,
      'solar_flux_adjusted': solarFluxAdjusted,
      'kp_index': kpIndex,
      'activity_level': activityLevel,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  @override
  String toString() {
    return 'SolarObservation(timestamp: $timestamp, sunspotDaily: $sunspotNumberDaily, sunspotSmoothed: $sunspotNumberSmoothed)';
  }
}
