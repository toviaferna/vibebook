import 'dart:async';
import 'dart:io';

/// A single established Edge TTS WebSocket.
///
/// The interface exists so [EdgeTtsClient] can be unit tested without
/// network access: the tests drive a fake connection frame by frame. The
/// connection itself is opened by the [EdgeConnectionFactory].
abstract class EdgeConnection {
  void add(String message);

  /// Text frames arrive as [String]; binary audio frames as [Uint8List].
  Stream<dynamic> get incoming;

  Future<void> close();
}

typedef EdgeConnectionFactory = Future<EdgeConnection> Function(
  Uri uri,
  Map<String, String> headers,
);

/// [EdgeConnection] over a plain `dart:io` WebSocket.
class WebSocketEdgeConnection implements EdgeConnection {
  WebSocketEdgeConnection(this._socket);

  final WebSocket _socket;

  @override
  void add(String message) => _socket.add(message);

  @override
  Stream<dynamic> get incoming => _socket;

  @override
  Future<void> close() => _socket.close();
}

/// Default factory used by [EdgeTtsClient] outside of tests.
Future<EdgeConnection> connectWebSocket(
  Uri uri,
  Map<String, String> headers,
) async {
  final socket = await WebSocket.connect(
    uri.toString(),
    headers: headers,
    compression: CompressionOptions.compressionDefault,
  );
  return WebSocketEdgeConnection(socket);
}
