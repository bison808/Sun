import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../../core/widgets/solar_card.dart';
import '../../../../core/widgets/loading_widget.dart';
import '../../../../core/widgets/error_widget.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../providers/dashboard_provider.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    // Load data when screen initializes
    Future.microtask(() {
      ref.read(dashboardProvider.notifier).loadDashboardData();
    });
  }

  Future<void> _onRefresh() async {
    await ref.read(dashboardProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Solar Cycle Monitor'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _onRefresh,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        child: _buildBody(dashboardState, theme),
      ),
    );
  }

  Widget _buildBody(DashboardState state, ThemeData theme) {
    if (state.isLoading && state.currentStatus == null) {
      return const LoadingWidget(message: 'Loading solar data...');
    }

    if (state.error != null && state.currentStatus == null) {
      return ErrorDisplayWidget(
        message: state.error!,
        onRetry: () => ref.read(dashboardProvider.notifier).loadDashboardData(),
      );
    }

    return ListView(
      padding: const EdgeInsets.symmetric(vertical: AppConstants.defaultPadding),
      children: [
        // Last Updated
        if (state.lastUpdated != null)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppConstants.defaultPadding,
            ),
            child: Text(
              'Last updated: ${DateFormat(AppConstants.dateFormatFull).format(state.lastUpdated!)}',
              style: theme.textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ),
        const SizedBox(height: AppConstants.defaultPadding),

        // Solar Activity Status Card
        if (state.currentStatus != null)
          SolarStatusCard(
            activityLevel: state.currentStatus!.activityLevel,
            sunspotNumber: state.currentStatus!.sunspotNumber.daily,
            solarFlux: state.currentStatus!.solarFlux.observed,
            kpIndex: state.currentStatus!.geomagneticActivity.kpIndex,
          ),

        // Solar Cycle Info
        if (state.currentStatus != null) ...[
          const SizedBox(height: AppConstants.smallPadding),
          SolarCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Solar Cycle ${state.currentStatus!.solarCycle.cycleNumber}',
                  style: theme.textTheme.titleLarge,
                ),
                const SizedBox(height: AppConstants.defaultPadding),
                Row(
                  children: [
                    Expanded(
                      child: _buildInfoItem(
                        context,
                        'Months Since Minimum',
                        state.currentStatus!.solarCycle.monthsSinceMinimum
                            .toString(),
                        Icons.calendar_today,
                      ),
                    ),
                    Expanded(
                      child: _buildInfoItem(
                        context,
                        'Smoothed SSN',
                        state.currentStatus!.solarCycle.smoothedSunspotNumber
                            .toStringAsFixed(1),
                        Icons.show_chart,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],

        // Geomagnetic Activity
        if (state.currentStatus != null) ...[
          const SizedBox(height: AppConstants.smallPadding),
          SolarInfoCard(
            title: 'Geomagnetic Condition',
            value: state.currentStatus!.geomagneticActivity.condition,
            subtitle:
                'Kp Index: ${state.currentStatus!.geomagneticActivity.kpIndex.toStringAsFixed(1)}',
            icon: Icons.language,
            iconColor: _getKpIndexColor(
              state.currentStatus!.geomagneticActivity.kpIndex,
            ),
          ),
        ],

        // Recent Alerts
        if (state.alerts.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.all(AppConstants.defaultPadding),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Recent Alerts',
                  style: theme.textTheme.titleLarge,
                ),
                TextButton(
                  onPressed: () {
                    // Navigate to alerts screen
                  },
                  child: const Text('View All'),
                ),
              ],
            ),
          ),
          ...state.alerts.take(3).map((alert) => _buildAlertCard(alert)),
        ],

        // Quick Actions
        Padding(
          padding: const EdgeInsets.all(AppConstants.defaultPadding),
          child: Text(
            'Explore',
            style: theme.textTheme.titleLarge,
          ),
        ),
        _buildQuickActions(),
      ],
    );
  }

  Widget _buildInfoItem(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 16,
              color: theme.textTheme.bodySmall?.color,
            ),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                label,
                style: theme.textTheme.bodySmall,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildAlertCard(dynamic alert) {
    final theme = Theme.of(context);
    final severityColor = _getSeverityColor(alert.severity);

    return SolarCard(
      onTap: () {
        // Navigate to alert details
      },
      child: Row(
        children: [
          Container(
            width: 4,
            height: 60,
            decoration: BoxDecoration(
              color: severityColor,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: AppConstants.defaultPadding),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        alert.eventType,
                        style: theme.textTheme.titleMedium,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: severityColor.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        alert.severity,
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: severityColor,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  alert.description,
                  style: theme.textTheme.bodySmall,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  DateFormat(AppConstants.dateFormatFull).format(
                    DateTime.parse(alert.timestamp),
                  ),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.textTheme.bodySmall?.color?.withOpacity(0.7),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActions() {
    return SolarCard(
      child: Column(
        children: [
          _buildQuickActionItem(
            icon: Icons.show_chart,
            title: 'Historical Charts',
            subtitle: 'View sunspot history',
            onTap: () {
              // Navigate to charts screen
            },
          ),
          const Divider(),
          _buildQuickActionItem(
            icon: Icons.psychology,
            title: 'AI Predictions',
            subtitle: 'ML-powered forecasts',
            onTap: () {
              // Navigate to predictions screen
            },
          ),
          const Divider(),
          _buildQuickActionItem(
            icon: Icons.school,
            title: 'Learn About Solar Cycles',
            subtitle: 'Educational content',
            onTap: () {
              // Navigate to education screen
            },
          ),
        ],
      ),
    );
  }

  Widget _buildQuickActionItem({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppConstants.smallPadding),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                icon,
                color: theme.colorScheme.primary,
              ),
            ),
            const SizedBox(width: AppConstants.defaultPadding),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleMedium,
                  ),
                  Text(
                    subtitle,
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              color: theme.textTheme.bodySmall?.color,
            ),
          ],
        ),
      ),
    );
  }

  Color _getKpIndexColor(double kpIndex) {
    if (kpIndex < 4) return AppColors.solarLow;
    if (kpIndex < 5) return AppColors.solarModerate;
    if (kpIndex < 6) return AppColors.solarHigh;
    if (kpIndex < 7) return AppColors.solarVeryHigh;
    return AppColors.solarExtreme;
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toLowerCase()) {
      case 'low':
        return AppColors.solarLow;
      case 'moderate':
        return AppColors.solarModerate;
      case 'high':
        return AppColors.solarHigh;
      case 'severe':
        return AppColors.solarVeryHigh;
      case 'extreme':
        return AppColors.solarExtreme;
      default:
        return AppColors.solarModerate;
    }
  }
}
