import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../../models/solar_observation.dart';
import '../../models/api_response.dart';
import '../../utils/chart_data_processor.dart';

/// High-performance Sunspot Number Time Series Chart
///
/// Features:
/// - Pinch to zoom / pan navigation
/// - Tap for data point tooltips with haptic feedback
/// - Multiple time ranges (1y, 5y, cycle, all)
/// - Smoothing options (daily, weekly, monthly)
/// - Smooth animations for data updates
/// - Performance optimized for 10,000+ data points
class SunspotTimeSeriesChart extends StatefulWidget {
  final List<SolarObservation> data;
  final TimeRange initialTimeRange;
  final SmoothingOption initialSmoothing;
  final bool showSmoothedLine;
  final Color lineColor;
  final Color smoothedLineColor;
  final Color tooltipBackgroundColor;
  final VoidCallback? onExportPressed;
  final Function(TimeRange)? onTimeRangeChanged;
  final Function(SmoothingOption)? onSmoothingChanged;

  const SunspotTimeSeriesChart({
    super.key,
    required this.data,
    this.initialTimeRange = TimeRange.oneYear,
    this.initialSmoothing = SmoothingOption.none,
    this.showSmoothedLine = true,
    this.lineColor = const Color(0xFF4A90E2),
    this.smoothedLineColor = const Color(0xFFE24A4A),
    this.tooltipBackgroundColor = const Color(0xFF2C3E50),
    this.onExportPressed,
    this.onTimeRangeChanged,
    this.onSmoothingChanged,
  });

  @override
  State<SunspotTimeSeriesChart> createState() => _SunspotTimeSeriesChartState();
}

class _SunspotTimeSeriesChartState extends State<SunspotTimeSeriesChart>
    with SingleTickerProviderStateMixin {
  late TimeRange _selectedTimeRange;
  late SmoothingOption _selectedSmoothing;
  late AnimationController _animationController;
  late Animation<double> _animation;

  // Chart interaction state
  double _minX = 0;
  double _maxX = 0;
  double _minY = 0;
  double _maxY = 100;

  // Zoom and pan state
  double _currentZoom = 1.0;
  double _panOffset = 0.0;

  // Tooltip state
  int? _touchedIndex;
  Offset? _touchedPosition;

  // Processed data
  List<ChartDataPoint> _chartData = [];
  List<ChartDataPoint> _smoothedData = [];

  @override
  void initState() {
    super.initState();
    _selectedTimeRange = widget.initialTimeRange;
    _selectedSmoothing = widget.initialSmoothing;

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    _animation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOutCubic,
    );

    _processData();
    _animationController.forward();
  }

  @override
  void didUpdateWidget(SunspotTimeSeriesChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data != widget.data) {
      _processData();
      _animationController.forward(from: 0.0);
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _processData() {
    // Filter by time range
    final filteredData = ChartDataProcessor.getDataForTimeRange(
      widget.data,
      _selectedTimeRange,
    );

    if (filteredData.isEmpty) {
      setState(() {
        _chartData = [];
        _smoothedData = [];
      });
      return;
    }

    // Downsample if needed (target: 2000 points for 60fps performance)
    final downsampledData = filteredData.length > 2000
        ? ChartDataProcessor.downsample(filteredData, 2000)
        : filteredData;

    // Convert to chart data points
    var chartData = ChartDataProcessor.toChartDataPoints(
      downsampledData,
      useSmoothed: false,
    );

    // Apply custom smoothing if selected
    if (_selectedSmoothing != SmoothingOption.none &&
        _selectedSmoothing.windowSize != null) {
      chartData = ChartDataProcessor.applyMovingAverage(
        downsampledData,
        _selectedSmoothing.windowSize!,
      );
    }

    // Get smoothed data from backend
    final smoothedData = ChartDataProcessor.toChartDataPoints(
      downsampledData,
      useSmoothed: true,
    );

    // Calculate bounds
    final allPoints = [...chartData, ...smoothedData];
    final bounds = ChartDataProcessor.calculateBounds(allPoints);

    setState(() {
      _chartData = chartData;
      _smoothedData = smoothedData;
      _minY = bounds.min;
      _maxY = bounds.max;

      if (chartData.isNotEmpty) {
        _minX = chartData.first.x.millisecondsSinceEpoch.toDouble();
        _maxX = chartData.last.x.millisecondsSinceEpoch.toDouble();
      }
    });
  }

  void _handleTimeRangeChange(TimeRange range) {
    setState(() {
      _selectedTimeRange = range;
      _currentZoom = 1.0;
      _panOffset = 0.0;
    });
    _processData();
    widget.onTimeRangeChanged?.call(range);
  }

  void _handleSmoothingChange(SmoothingOption option) {
    setState(() {
      _selectedSmoothing = option;
    });
    _processData();
    widget.onSmoothingChanged?.call(option);
  }

  void _handleZoom(double scale) {
    setState(() {
      _currentZoom = (_currentZoom * scale).clamp(1.0, 10.0);
    });
  }

  void _handlePan(double delta) {
    final range = _maxX - _minX;
    final maxOffset = range * (_currentZoom - 1) / _currentZoom;

    setState(() {
      _panOffset = (_panOffset + delta).clamp(-maxOffset, 0.0);
    });
  }

  void _handleDoubleTap() {
    setState(() {
      _currentZoom = 1.0;
      _panOffset = 0.0;
    });
  }

  void _handleTap(int index, Offset position) {
    HapticFeedback.selectionClick();
    setState(() {
      _touchedIndex = index;
      _touchedPosition = position;
    });

    // Auto-hide tooltip after 3 seconds
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted && _touchedIndex == index) {
        setState(() {
          _touchedIndex = null;
          _touchedPosition = null;
        });
      }
    });
  }

  List<FlSpot> _getFlSpots(List<ChartDataPoint> data) {
    return data.asMap().entries.map((entry) {
      final index = entry.key.toDouble();
      final point = entry.value;
      return FlSpot(index, point.y);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _buildControls(),
        Expanded(
          child: _buildChart(),
        ),
        if (_touchedIndex != null) _buildTooltip(),
      ],
    );
  }

  Widget _buildControls() {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Time Range Selector
          Row(
            children: [
              const Text(
                'Range:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: TimeRange.values
                        .map((range) => Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: ChoiceChip(
                                label: Text(range.label),
                                selected: _selectedTimeRange == range,
                                onSelected: (_) => _handleTimeRangeChange(range),
                              ),
                            ))
                        .toList(),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Smoothing Selector
          Row(
            children: [
              const Text(
                'Smoothing:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: SmoothingOption.values
                        .map((option) => Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: ChoiceChip(
                                label: Text(option.label),
                                selected: _selectedSmoothing == option,
                                onSelected: (_) => _handleSmoothingChange(option),
                              ),
                            ))
                        .toList(),
                  ),
                ),
              ),
              if (widget.onExportPressed != null)
                IconButton(
                  icon: const Icon(Icons.download),
                  onPressed: widget.onExportPressed,
                  tooltip: 'Export as Image',
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildChart() {
    if (_chartData.isEmpty) {
      return const Center(
        child: Text('No data available for the selected range'),
      );
    }

    return GestureDetector(
      onScaleUpdate: (details) {
        if (details.scale != 1.0) {
          _handleZoom(details.scale);
        } else if (details.focalPointDelta.dx != 0) {
          _handlePan(details.focalPointDelta.dx);
        }
      },
      onDoubleTap: _handleDoubleTap,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: AnimatedBuilder(
          animation: _animation,
          builder: (context, child) {
            return LineChart(
              _buildLineChartData(),
              duration: const Duration(milliseconds: 300),
            );
          },
        ),
      ),
    );
  }

  LineChartData _buildLineChartData() {
    final visibleRange = (_maxX - _minX) / _currentZoom;
    final visibleMinX = _minX + _panOffset;
    final visibleMaxX = visibleMinX + visibleRange;

    return LineChartData(
      minX: 0,
      maxX: _chartData.length.toDouble() - 1,
      minY: _minY,
      maxY: _maxY,
      lineBarsData: [
        // Daily/Custom smoothed data
        LineChartBarData(
          spots: _getFlSpots(_chartData),
          isCurved: true,
          color: widget.lineColor,
          barWidth: 2,
          isStrokeCapRound: true,
          dotData: FlDotData(
            show: _chartData.length < 100,
            getDotPainter: (spot, percent, barData, index) {
              return FlDotCirclePainter(
                radius: 3,
                color: widget.lineColor,
                strokeWidth: 1,
                strokeColor: Colors.white,
              );
            },
          ),
          belowBarData: BarAreaData(
            show: true,
            color: widget.lineColor.withOpacity(0.1 * _animation.value),
          ),
        ),

        // Smoothed line (13-month from backend)
        if (widget.showSmoothedLine && _smoothedData.isNotEmpty)
          LineChartBarData(
            spots: _getFlSpots(_smoothedData),
            isCurved: true,
            color: widget.smoothedLineColor,
            barWidth: 2,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            dashArray: [5, 5],
          ),
      ],
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 50,
            getTitlesWidget: (value, meta) {
              return Text(
                value.toInt().toString(),
                style: const TextStyle(fontSize: 12),
              );
            },
          ),
          axisNameWidget: const Text(
            'Sunspot Number',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
        rightTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        topTitles: const AxisTitles(
          sideTitles: SideTitles(showTitles: false),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
            interval: _chartData.length / 6,
            getTitlesWidget: (value, meta) {
              final index = value.toInt();
              if (index < 0 || index >= _chartData.length) {
                return const SizedBox.shrink();
              }

              final date = _chartData[index].x;
              final format = _selectedTimeRange == TimeRange.oneYear
                  ? DateFormat('MMM')
                  : DateFormat('MMM yy');

              return Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  format.format(date),
                  style: const TextStyle(fontSize: 11),
                ),
              );
            },
          ),
        ),
      ),
      gridData: FlGridData(
        show: true,
        drawVerticalLine: true,
        horizontalInterval: (_maxY - _minY) / 5,
        getDrawingHorizontalLine: (value) {
          return FlLine(
            color: Colors.grey.withOpacity(0.2),
            strokeWidth: 1,
          );
        },
        getDrawingVerticalLine: (value) {
          return FlLine(
            color: Colors.grey.withOpacity(0.2),
            strokeWidth: 1,
          );
        },
      ),
      borderData: FlBorderData(
        show: true,
        border: Border.all(color: Colors.grey.withOpacity(0.3)),
      ),
      lineTouchData: LineTouchData(
        enabled: true,
        touchCallback: (FlTouchEvent event, LineTouchResponse? response) {
          if (event is FlTapUpEvent && response != null) {
            final spot = response.lineBarSpots?.firstOrNull;
            if (spot != null) {
              final index = spot.x.toInt();
              _handleTap(index, event.localPosition);
            }
          }
        },
        touchTooltipData: LineTouchTooltipData(
          tooltipBgColor: widget.tooltipBackgroundColor.withOpacity(0.8),
          getTooltipItems: (List<LineBarSpot> touchedSpots) {
            return touchedSpots.map((spot) {
              final index = spot.x.toInt();
              if (index >= _chartData.length) return null;

              final dataPoint = _chartData[index];
              final dateStr = DateFormat('MMM dd, yyyy').format(dataPoint.x);

              return LineTooltipItem(
                '$dateStr\n${spot.y.toStringAsFixed(1)} SSN',
                const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              );
            }).toList();
          },
        ),
      ),
    );
  }

  Widget _buildTooltip() {
    if (_touchedIndex == null || _touchedIndex! >= _chartData.length) {
      return const SizedBox.shrink();
    }

    final dataPoint = _chartData[_touchedIndex!];
    final dateStr = DateFormat('MMMM dd, yyyy').format(dataPoint.x);

    return Container(
      padding: const EdgeInsets.all(16),
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: widget.tooltipBackgroundColor,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            dateStr,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Sunspot Number: ${dataPoint.y.toStringAsFixed(1)}',
            style: const TextStyle(color: Colors.white),
          ),
          if (dataPoint.metadata?['activityLevel'] != null) ...[
            const SizedBox(height: 4),
            Text(
              'Activity: ${dataPoint.metadata!['activityLevel']}',
              style: const TextStyle(color: Colors.white70),
            ),
          ],
          if (dataPoint.metadata?['cycleNumber'] != null) ...[
            const SizedBox(height: 4),
            Text(
              'Cycle: ${dataPoint.metadata!['cycleNumber']}',
              style: const TextStyle(color: Colors.white70),
            ),
          ],
        ],
      ),
    );
  }
}
