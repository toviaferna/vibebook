import 'dart:async';
import 'dart:typed_data';

import 'package:vibebook_app/data/tts/edge/edge_connection.dart';

/// Scripted [EdgeConnection] for the client tests.
///
/// [onSsml] returns the frames the fake answers with for each SSML request:
/// [String] frames are text, [Uint8List] frames are binary audio.
class FakeEdgeConnection implements EdgeConnection {
  FakeEdgeConnection({this.onSsml});

  final List<dynamic> Function(String ssml)? onSsml;
  final List<String> sent = [];
  bool closed = false;

  final _incoming = StreamController<dynamic>.broadcast();

  @override
  void add(String message) {
    sent.add(message);
    if (!message.contains('Path:ssml')) {
      return;
    }
    final frames = onSsml?.call(message) ?? const [];
    // El cliente se suscribe justo después de enviar el SSML; un broadcast
    // stream no guarda eventos, así que la respuesta va al menos un microtask
    // después para que la suscripción ya exista.
    scheduleMicrotask(() {
      for (final frame in frames) {
        _incoming.add(frame);
      }
    });
  }

  @override
  Stream<dynamic> get incoming => _incoming.stream;

  @override
  Future<void> close() async {
    closed = true;
  }
}

/// Builds a binary audio frame the way the service sends them.
Uint8List audioFrame(List<int> payload) {
  final header =
      'X-RequestId:test Path:audio\r\n'
      'Content-Type:audio/mpeg\r\n';
  final headerBytes = header.codeUnits;
  final bytes = BytesBuilder(copy: false)
    ..add([(headerBytes.length >> 8) & 0xff, headerBytes.length & 0xff])
    ..add(headerBytes)
    ..add(payload);
  return bytes.toBytes();
}

/// Builds a text metadata frame with one WordBoundary.
String metadataFrame({
  required int offset,
  required int duration,
  required String word,
}) {
  final body =
      '{"Metadata":[{"Type":"WordBoundary","Data":{"Offset":$offset,'
      '"Duration":$duration,"text":{"Text":"$word"}}}]}';
  return 'X-RequestId:test\r\n'
      'Content-Type:application/json; charset=utf-8\r\n'
      'Path:audio.metadata\r\n'
      '\r\n'
      '$body';
}

const turnEndFrame = 'X-RequestId:test\r\nPath:turn.end\r\n\r\n';
