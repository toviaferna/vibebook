import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

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

/// A minimal RFC 6455 WebSocket client over a raw socket.
///
/// `dart:io`'s WebSocket is unusable here: it prepends its own User-Agent
/// ("Dart/x (dart:io), …") to any custom one, and the Edge service rejects
/// the resulting header. Speaking the protocol directly keeps the upgrade
/// request byte-for-byte under our control.
class RawEdgeConnection implements EdgeConnection {
  RawEdgeConnection._(this._socket, this._incoming, this._closed);

  final Socket _socket;
  final StreamController<dynamic> _incoming;
  final StreamController<void> _closed;
  late final StreamSubscription<Uint8List> _subscription;
  final _outgoing = BytesBuilder(copy: false);
  bool _closeSent = false;

  static Future<EdgeConnection> connect(
    Uri uri,
    Map<String, String> headers,
  ) async {
    final secure = uri.scheme == 'wss' || uri.scheme == 'https';
    final port = uri.hasPort ? uri.port : (secure ? 443 : 80);
    final socket = secure
        ? await SecureSocket.connect(
            uri.host,
            port,
            timeout: const Duration(seconds: 30),
          )
        : await Socket.connect(
            uri.host,
            port,
            timeout: const Duration(seconds: 30),
          );
    try {
      final connection = await _handshake(socket, uri, headers);
      return connection;
    } catch (_) {
      socket.destroy();
      rethrow;
    }
  }

  static Future<RawEdgeConnection> _handshake(
    Socket socket,
    Uri uri,
    Map<String, String> headers,
  ) async {
    final key = base64Encode(
      List<int>.generate(16, (_) => math.Random.secure().nextInt(256)),
    );
    final request = [
      'GET ${uri.hasQuery ? '${uri.path}?${uri.query}' : uri.path} HTTP/1.1',
      'Host: ${uri.host}${uri.hasPort ? ':${uri.port}' : ''}',
      'Connection: Upgrade',
      'Upgrade: websocket',
      'Sec-WebSocket-Key: $key',
      'Sec-WebSocket-Version: 13',
      for (final header in headers.entries) '${header.key}: ${header.value}',
      '',
      '',
    ].join('\r\n');
    socket.write(request);

    final incoming = StreamController<dynamic>.broadcast();
    final closed = StreamController<void>.broadcast();
    final pending = BytesBuilder(copy: false);

    final connection = RawEdgeConnection._(socket, incoming, closed);

    // The 101 response arrives before any frame; read it from the same
    // stream and then hand the rest to the frame decoder.
    final done = Completer<void>();
    late StreamSubscription<Uint8List> subscription;
    subscription = socket.cast<Uint8List>().listen(
      (data) {
        if (!done.isCompleted) {
          pending.add(data);
          final text = utf8.decode(pending.takeBytes(), allowMalformed: true);
          final separator = text.indexOf('\r\n\r\n');
          if (separator < 0) {
            pending.add(utf8.encode(text));
            return;
          }
          final header = text.substring(0, separator);
          if (!header.contains('101')) {
            done.completeError(
              WebSocketException('El upgrade no fue aceptado: $header'),
            );
            return;
          }
          done.complete();
          final rest = utf8.encode(text.substring(separator + 4));
          if (rest.isNotEmpty) {
            connection._handleData(Uint8List.fromList(rest));
          }
        } else {
          connection._handleData(data);
        }
      },
      onError: (Object error) {
        if (!done.isCompleted) {
          done.completeError(error);
        } else if (!incoming.isClosed) {
          incoming.addError(error);
        }
      },
      onDone: () {
        if (!done.isCompleted) {
          done.completeError(
            const WebSocketException('El servidor cerró durante el upgrade.'),
          );
        } else if (!closed.isClosed) {
          closed.add(null);
          closed.close();
        }
      },
      cancelOnError: true,
    );
    connection._subscription = subscription;
    await done.future;
    return connection;
  }

  void _handleData(Uint8List data) {
    _outgoing.add(data);
    _decodeFrames();
  }

  void _decodeFrames() {
    final buffer = _outgoing.takeBytes();
    var offset = 0;
    while (true) {
      if (buffer.length - offset < 2) {
        break;
      }
      final first = buffer[offset];
      final second = buffer[offset + 1];
      final opcode = first & 0x0F;
      final masked = (second & 0x80) != 0;
      var length = second & 0x7F;
      var headerLength = 2;
      if (length == 126) {
        if (buffer.length - offset < 4) {
          break;
        }
        length = (buffer[offset + 2] << 8) | buffer[offset + 3];
        headerLength = 4;
      } else if (length == 127) {
        if (buffer.length - offset < 10) {
          break;
        }
        var big = 0;
        for (var index = 0; index < 8; index++) {
          big = big * 256 + buffer[offset + 2 + index];
        }
        length = big;
        headerLength = 10;
      }
      final maskLength = masked ? 4 : 0;
      if (buffer.length - offset < headerLength + maskLength + length) {
        break;
      }
      var payload = Uint8List.sublistView(
        buffer,
        offset + headerLength + maskLength,
        offset + headerLength + maskLength + length,
      );
      if (masked) {
        final mask = buffer.sublist(
          offset + headerLength,
          offset + headerLength + 4,
        );
        final unmasked = Uint8List(length);
        for (var index = 0; index < length; index++) {
          unmasked[index] = payload[index] ^ mask[index % 4];
        }
        payload = unmasked;
      }
      offset += headerLength + maskLength + length;
      switch (opcode) {
        case 0x1:
          _incoming.add(utf8.decode(payload, allowMalformed: true));
        case 0x2:
          _incoming.add(payload);
        case 0x8:
          unawaited(close());
        case 0x9:
          _sendFrame(0xA, payload);
        default:
          break;
      }
    }
    if (offset < buffer.length) {
      _outgoing.add(buffer.sublist(offset));
    }
  }

  void _sendFrame(int opcode, List<int> payload) {
    final frame = BytesBuilder(copy: false);
    frame.addByte(0x80 | opcode);
    final mask = List<int>.generate(
      4,
      (_) => math.Random.secure().nextInt(256),
    );
    var length = payload.length;
    if (length < 126) {
      frame.addByte(0x80 | length);
    } else if (length < 65536) {
      frame.addByte(0x80 | 126);
      frame.addByte((length >> 8) & 0xFF);
      frame.addByte(length & 0xFF);
    } else {
      frame.addByte(0x80 | 127);
      for (var shift = 56; shift >= 0; shift -= 8) {
        frame.addByte((length >> shift) & 0xFF);
      }
    }
    frame.add(mask);
    final masked = Uint8List(length);
    for (var index = 0; index < length; index++) {
      masked[index] = payload[index] ^ mask[index % 4];
    }
    frame.add(masked);
    _socket.add(frame.takeBytes());
  }

  @override
  void add(String message) {
    if (!_closeSent) {
      _sendFrame(0x1, utf8.encode(message));
    }
  }

  @override
  Stream<dynamic> get incoming => _incoming.stream;

  @override
  Future<void> close() async {
    if (_closeSent) {
      return;
    }
    _closeSent = true;
    try {
      _sendFrame(0x8, [0x03, 0xE8]); // 1000: normal closure
    } catch (_) {
      // The socket may already be gone.
    }
    await _subscription.cancel();
    await _incoming.close();
    if (!_closed.isClosed) {
      await _closed.close();
    }
    _socket.destroy();
  }
}

/// Default factory used by [EdgeTtsClient] outside of tests.
Future<EdgeConnection> connectWebSocket(Uri uri, Map<String, String> headers) {
  return RawEdgeConnection.connect(uri, headers);
}
