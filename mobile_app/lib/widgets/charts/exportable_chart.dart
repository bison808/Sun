import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:screenshot/screenshot.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Wrapper widget that adds export functionality to any chart
class ExportableChart extends StatefulWidget {
  final Widget child;
  final String chartName;
  final bool showExportButton;

  const ExportableChart({
    super.key,
    required this.child,
    this.chartName = 'chart',
    this.showExportButton = true,
  });

  @override
  State<ExportableChart> createState() => _ExportableChartState();
}

class _ExportableChartState extends State<ExportableChart> {
  final ScreenshotController _screenshotController = ScreenshotController();
  bool _isExporting = false;

  Future<void> _exportChart() async {
    setState(() => _isExporting = true);

    try {
      // Capture screenshot
      final Uint8List? imageBytes = await _screenshotController.capture(
        pixelRatio: 3.0, // High quality export
      );

      if (imageBytes == null) {
        throw Exception('Failed to capture chart');
      }

      // Save to temporary directory
      final directory = await getTemporaryDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final fileName = '${widget.chartName}_$timestamp.png';
      final filePath = '${directory.path}/$fileName';

      final file = File(filePath);
      await file.writeAsBytes(imageBytes);

      // Share the file
      await Share.shareXFiles(
        [XFile(filePath)],
        text: 'Solar Cycle ${widget.chartName}',
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Chart exported successfully'),
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Export failed: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      setState(() => _isExporting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Screenshot(
          controller: _screenshotController,
          child: Container(
            color: Theme.of(context).scaffoldBackgroundColor,
            child: widget.child,
          ),
        ),
        if (widget.showExportButton)
          Positioned(
            top: 16,
            right: 16,
            child: FloatingActionButton.small(
              onPressed: _isExporting ? null : _exportChart,
              tooltip: 'Export Chart',
              child: _isExporting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.download),
            ),
          ),
      ],
    );
  }
}
