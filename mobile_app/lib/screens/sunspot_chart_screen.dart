import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/solar_observation.dart';
import '../models/api_response.dart';
import '../services/solar_api_service.dart';
import '../widgets/charts/sunspot_timeseries_chart.dart';
import '../widgets/charts/exportable_chart.dart';

/// Screen displaying the Sunspot Time Series Chart
class SunspotChartScreen extends StatefulWidget {
  const SunspotChartScreen({super.key});

  @override
  State<SunspotChartScreen> createState() => _SunspotChartScreenState();
}

class _SunspotChartScreenState extends State<SunspotChartScreen> {
  final SolarApiService _apiService = SolarApiService();
  List<SolarObservation> _observations = [];
  bool _isLoading = true;
  String? _error;
  TimeRange _currentTimeRange = TimeRange.oneYear;
  bool _isLiveUpdateEnabled = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _apiService.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final data = await _apiService.getSunspotHistory(
        range: _currentTimeRange.value,
        limit: 10000, // Request large dataset for local processing
      );

      setState(() {
        _observations = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _toggleLiveUpdates() {
    setState(() {
      _isLiveUpdateEnabled = !_isLiveUpdateEnabled;
    });

    if (_isLiveUpdateEnabled) {
      _apiService.connectToLiveUpdates().listen(
        (observation) {
          setState(() {
            // Add or update the latest observation
            final existingIndex = _observations.indexWhere(
              (obs) => obs.timestamp == observation.timestamp,
            );

            if (existingIndex >= 0) {
              _observations[existingIndex] = observation;
            } else {
              _observations.add(observation);
              _observations.sort((a, b) => a.timestamp.compareTo(b.timestamp));
            }
          });
        },
        onError: (error) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Live update error: $error'),
              backgroundColor: Colors.orange,
            ),
          );
        },
      );
    } else {
      _apiService.disconnectLiveUpdates();
    }
  }

  void _handleTimeRangeChanged(TimeRange range) {
    setState(() {
      _currentTimeRange = range;
    });
    _loadData();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sunspot Time Series'),
        actions: [
          IconButton(
            icon: Icon(
              _isLiveUpdateEnabled ? Icons.pause : Icons.play_arrow,
              color: _isLiveUpdateEnabled ? Colors.red : null,
            ),
            onPressed: _toggleLiveUpdates,
            tooltip: _isLiveUpdateEnabled
                ? 'Disable Live Updates'
                : 'Enable Live Updates',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
            tooltip: 'Refresh Data',
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading solar data...'),
          ],
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            const SizedBox(height: 16),
            Text(
              'Error loading data',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _loadData,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_observations.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.info_outline,
              size: 64,
              color: Colors.grey,
            ),
            SizedBox(height: 16),
            Text('No data available'),
          ],
        ),
      );
    }

    return Column(
      children: [
        _buildStatsBar(),
        Expanded(
          child: ExportableChart(
            chartName: 'sunspot_timeseries',
            child: SunspotTimeSeriesChart(
              data: _observations,
              initialTimeRange: _currentTimeRange,
              onTimeRangeChanged: _handleTimeRangeChanged,
              showSmoothedLine: true,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStatsBar() {
    if (_observations.isEmpty) return const SizedBox.shrink();

    final latest = _observations.last;
    final dailySSN = latest.sunspotNumberDaily ?? 0;
    final smoothedSSN = latest.sunspotNumberSmoothed ?? 0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).primaryColor.withOpacity(0.1),
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).dividerColor,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem(
            'Current SSN',
            dailySSN.toStringAsFixed(1),
            Icons.wb_sunny,
          ),
          _buildStatItem(
            'Smoothed SSN',
            smoothedSSN.toStringAsFixed(1),
            Icons.show_chart,
          ),
          _buildStatItem(
            'Activity',
            latest.activityLevel ?? 'N/A',
            Icons.analytics,
          ),
          _buildStatItem(
            'Cycle',
            latest.cycleNumber.toString(),
            Icons.loop,
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 20, color: Theme.of(context).primaryColor),
        const SizedBox(height: 4),
        Text(
          value,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}
