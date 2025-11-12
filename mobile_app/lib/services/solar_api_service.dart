import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/solar_observation.dart';
import '../models/api_response.dart';

/// Service for communicating with the Solar Cycle backend API
class SolarApiService {
  final String baseUrl;
  final http.Client _client;
  WebSocketChannel? _wsChannel;
  StreamController<SolarObservation>? _wsController;

  SolarApiService({
    this.baseUrl = 'http://localhost:3000',
    http.Client? client,
  }) : _client = client ?? http.Client();

  /// Get historical sunspot data with optional filters
  ///
  /// [range] - Time range: '1y', '5y', 'cycle', 'all'
  /// [limit] - Maximum number of records to return
  Future<List<SolarObservation>> getSunspotHistory({
    String range = '1y',
    int? limit,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/api/sunspot-history').replace(
        queryParameters: {
          'range': range,
          if (limit != null) 'limit': limit.toString(),
        },
      );

      final response = await _client.get(uri);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        final apiResponse = ApiResponse<List<dynamic>>.fromJson(
          jsonData,
          (data) => data as List<dynamic>,
        );

        return apiResponse.data
            .map((json) => SolarObservation.fromJson(json as Map<String, dynamic>))
            .toList();
      } else {
        throw Exception(
          'Failed to load sunspot history: ${response.statusCode} ${response.reasonPhrase}',
        );
      }
    } catch (e) {
      throw Exception('Error fetching sunspot history: $e');
    }
  }

  /// Get current solar status
  Future<SolarObservation?> getCurrentStatus() async {
    try {
      final response = await _client.get(
        Uri.parse('$baseUrl/api/current-status'),
      );

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        final apiResponse = ApiResponse<Map<String, dynamic>>.fromJson(
          jsonData,
          (data) => data as Map<String, dynamic>,
        );

        return SolarObservation.fromJson(apiResponse.data);
      } else if (response.statusCode == 404) {
        return null;
      } else {
        throw Exception(
          'Failed to load current status: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Error fetching current status: $e');
    }
  }

  /// Connect to WebSocket for real-time updates
  ///
  /// Returns a stream of [SolarObservation] updates
  Stream<SolarObservation> connectToLiveUpdates() {
    if (_wsController != null && !_wsController!.isClosed) {
      return _wsController!.stream;
    }

    _wsController = StreamController<SolarObservation>.broadcast(
      onCancel: () => disconnectLiveUpdates(),
    );

    try {
      final wsUrl = baseUrl.replaceFirst('http', 'ws');
      _wsChannel = WebSocketChannel.connect(
        Uri.parse('$wsUrl/ws/live'),
      );

      _wsChannel!.stream.listen(
        (message) {
          try {
            final data = json.decode(message as String);
            if (data['type'] == 'solar_update' && data['data'] != null) {
              final observation = SolarObservation.fromJson(
                data['data'] as Map<String, dynamic>,
              );
              _wsController!.add(observation);
            }
          } catch (e) {
            print('Error parsing WebSocket message: $e');
          }
        },
        onError: (error) {
          print('WebSocket error: $error');
          _wsController!.addError(error);
        },
        onDone: () {
          print('WebSocket connection closed');
          _wsController!.close();
        },
      );

      // Send subscribe message
      _wsChannel!.sink.add(json.encode({'type': 'subscribe'}));
    } catch (e) {
      print('Error connecting to WebSocket: $e');
      _wsController!.addError(e);
    }

    return _wsController!.stream;
  }

  /// Disconnect from WebSocket
  void disconnectLiveUpdates() {
    _wsChannel?.sink.close();
    _wsChannel = null;
    _wsController?.close();
    _wsController = null;
  }

  /// Close the service and cleanup resources
  void dispose() {
    disconnectLiveUpdates();
    _client.close();
  }
}
