import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../shared/services/solar_api_service.dart';
import '../../../../shared/services/api_models.dart';

// Dashboard State
class DashboardState {
  final CurrentStatusData? currentStatus;
  final List<AlertData> alerts;
  final bool isLoading;
  final String? error;
  final DateTime? lastUpdated;

  DashboardState({
    this.currentStatus,
    this.alerts = const [],
    this.isLoading = false,
    this.error,
    this.lastUpdated,
  });

  DashboardState copyWith({
    CurrentStatusData? currentStatus,
    List<AlertData>? alerts,
    bool? isLoading,
    String? error,
    DateTime? lastUpdated,
  }) {
    return DashboardState(
      currentStatus: currentStatus ?? this.currentStatus,
      alerts: alerts ?? this.alerts,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }
}

// Dashboard Provider
class DashboardNotifier extends StateNotifier<DashboardState> {
  final SolarApiService _apiService;

  DashboardNotifier(this._apiService) : super(DashboardState());

  Future<void> loadDashboardData() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      // Load current status and alerts in parallel
      final results = await Future.wait([
        _apiService.getCurrentStatus(),
        _apiService.getAlerts(limit: 5),
      ]);

      final currentStatus = results[0] as CurrentStatusResponse;
      final alerts = results[1] as AlertsResponse;

      state = state.copyWith(
        currentStatus: currentStatus.data,
        alerts: alerts.data,
        isLoading: false,
        lastUpdated: DateTime.now(),
      );
    } on ApiException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.message,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'An unexpected error occurred',
      );
    }
  }

  Future<void> refresh() async {
    await loadDashboardData();
  }
}

// Dashboard Provider
final dashboardProvider =
    StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
  final apiService = ref.watch(solarApiServiceProvider);
  return DashboardNotifier(apiService);
});

// Auto-load provider
final dashboardAutoLoadProvider = FutureProvider<void>((ref) async {
  final notifier = ref.read(dashboardProvider.notifier);
  await notifier.loadDashboardData();
});
