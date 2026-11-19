import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

import 'edge_connection.dart';

/// Events emitted while Edge synthesizes a chunk of text.
sealed class EdgeTtsEvent {}

/// A chunk of MP3 audio (24 kHz, 48 kbit/s, mono).
class EdgeAudioEvent extends EdgeTtsEvent {
  EdgeAudioEvent(this.data);

  final Uint8List data;
}

/// Word-level timing. [offset] and [duration] are in 100-nanosecond units,
/// exactly as the service reports them.
class EdgeWordBoundaryEvent extends EdgeTtsEvent {
  EdgeWordBoundaryEvent({
    required this.offset,
    required this.duration,
    required this.text,
  });

  final int offset;
  final int duration;
  final String text;
}

/// The service closed the turn without producing any audio.
class EdgeNoAudioException implements Exception {
  const EdgeNoAudioException();

  @override
  String toString() => 'Edge TTS no devolvió audio.';
}

/// Dart client for Microsoft Edge's Read Aloud synthesis service.
///
/// The protocol is ported from the MIT-licensed Python `edge-tts` client
/// (https://github.com/rany2/edge-tts). The service is unofficial: it may
/// rate-limit, reject requests or disappear without notice.
class EdgeTtsClient {
  EdgeTtsClient({
    EdgeConnectionFactory? connectionFactory,
    this.requestDelay = const Duration(seconds: 1),
    DateTime Function()? clock,
    Future<Duration?> Function()? clockProbe,
  }) : _connect = connectionFactory ?? connectWebSocket,
       _clock = clock ?? DateTime.now,
       _probeClock = clockProbe ?? _probeServiceClock;

  static const trustedClientToken = '6A5AA1D4EAFF4E9FB37E23D68491D6F4';
  static const chromiumVersion = '143.0.3650.75';
  static const audioFormat = 'audio-24khz-48kbitrate-mono-mp3';

  static const _baseUrl =
      'speech.platform.bing.com/consumer/speech/synthesize/readaloud';
  static const _wssUrl = 'wss://$_baseUrl/edge/v1';
  static const _voicesUrl = 'https://$_baseUrl/voices/list';
  static const _winEpochMs = 11644473600000;
  static const _fiveMinutesIn100Ns = 5 * 60 * 10000000;
  static const _maxChunkBytes = 4096;

  final EdgeConnectionFactory _connect;
  final DateTime Function() _clock;
  final Future<Duration?> Function() _probeClock;
  final Duration requestDelay;

  Duration _clockSkew = Duration.zero;

  /// The service restarts word offsets on every request, so later chunks of a
  /// long text need the elapsed audio plus this small pad to stay in sync.
  static const chunkPadding100Ns = 8750000;

  /// Synthesizes [text] with [voice] (short name, e.g. `es-MX-JorgeNeural`).
  ///
  /// [rate] is a signed percentage such as `+10%` or `-10%`; [pitch] a signed
  /// Hz string such as `+0Hz`; [volume] a signed percentage. Long texts are
  /// split into service-sized chunks and word offsets arrive already
  /// accumulated across chunks.
  Stream<EdgeTtsEvent> synthesize({
    required String text,
    required String voice,
    required String rate,
    String pitch = '+0Hz',
    String volume = '+0%',
  }) async* {
    _validateParam(rate, RegExp(r'^[+-]\d+%$'), 'rate');
    _validateParam(pitch, RegExp(r'^[+-]\d+Hz$'), 'pitch');
    _validateParam(volume, RegExp(r'^[+-]\d+%$'), 'volume');
    final chunks = _splitText(text);
    var offsetCompensation = 0;
    for (var index = 0; index < chunks.length; index++) {
      var gotAudio = false;
      var lastOffset = 0;
      var lastDuration = 0;
      await for (final event in _synthesizeChunk(
        chunks[index],
        voice: voice,
        rate: rate,
        pitch: pitch,
        volume: volume,
        offsetCompensation: offsetCompensation,
      )) {
        if (event is EdgeAudioEvent) {
          gotAudio = true;
        } else if (event is EdgeWordBoundaryEvent) {
          lastOffset = event.offset;
          lastDuration = event.duration;
        }
        yield event;
      }
      if (!gotAudio) {
        throw const EdgeNoAudioException();
      }
      offsetCompensation = lastOffset + lastDuration + chunkPadding100Ns;
      if (index < chunks.length - 1) {
        await Future<void>.delayed(requestDelay);
      }
    }
  }

  Stream<EdgeTtsEvent> _synthesizeChunk(
    String chunk, {
    required String voice,
    required String rate,
    required String pitch,
    required String volume,
    required int offsetCompensation,
  }) async* {
    final connection = await _connectWithRetry();
    try {
      connection.add(_configMessage());
      connection.add(
        _ssmlMessage(
          chunk,
          voice: voice,
          rate: rate,
          pitch: pitch,
          volume: volume,
        ),
      );
      await for (final frame in connection.incoming) {
        if (frame is String) {
          final events = _parseTextFrame(frame, offsetCompensation);
          if (events == null) {
            return;
          }
          for (final event in events) {
            yield event;
          }
        } else if (frame is Uint8List) {
          final audio = _parseBinaryFrame(frame);
          if (audio != null && audio.isNotEmpty) {
            yield EdgeAudioEvent(audio);
          }
        }
      }
    } finally {
      unawaited(connection.close().catchError((_) {}));
    }
  }

  Future<EdgeConnection> _connectWithRetry() async {
    try {
      return await _connect(_buildUri(), _wssHeaders);
    } catch (_) {
      // A rejection here usually means clock skew: the Sec-MS-GEC token is
      // time-based. Sync the clock from the service and try once more.
      final skew = await _probeClock();
      if (skew != null) {
        _clockSkew = skew;
      }
      return _connect(_buildUri(), _wssHeaders);
    }
  }

  /// Asks the voice list endpoint for its clock so the token can be rebuilt.
  static Future<Duration?> _probeServiceClock() async {
    final client = HttpClient();
    try {
      final uri = Uri.parse(
        '$_voicesUrl?trustedclienttoken=$trustedClientToken'
        '&Sec-MS-GEC=1-$chromiumVersion',
      );
      final request = await client.headUrl(uri);
      request.headers.set('User-Agent', userAgent);
      final response = await request.close();
      final date = response.headers.value(HttpHeaders.dateHeader);
      await response.drain<void>();
      if (date == null) {
        return null;
      }
      return HttpDate.parse(date).difference(DateTime.now().toUtc());
    } catch (_) {
      // Best effort: a stale token simply fails again upstream.
      return null;
    } finally {
      client.close();
    }
  }

  static Map<String, String> get _wssHeaders => {
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'Origin': 'chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold',
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': userAgent,
  };

  /// Identifies this client as a recent Chromium/Edge build.
  static String get userAgent =>
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/$chromiumVersion Safari/537.36 '
      'Edg/$chromiumVersion';

  Uri _buildUri() {
    return Uri.parse(
      '$_wssUrl?TrustedClientToken=$trustedClientToken'
      '&ConnectionId=${_uuidHex()}'
      '&Sec-MS-GEC=${_secMsGec()}'
      '&Sec-MS-GEC-Version=1-$chromiumVersion',
    );
  }

  /// Sec-MS-GEC: SHA-256 of the trusted token plus the Windows file time
  /// rounded down to five minutes.
  String _secMsGec() {
    final now = _clock().toUtc().add(_clockSkew);
    final ticks = (now.millisecondsSinceEpoch + _winEpochMs) * 10000;
    final rounded = ticks - (ticks % _fiveMinutesIn100Ns);
    return sha256
        .convert(utf8.encode('$trustedClientToken$rounded'))
        .toString()
        .toUpperCase();
  }

  String _configMessage() {
    return 'X-Timestamp:${_timestamp()}\r\n'
        'Content-Type:application/json; charset=utf-8\r\n'
        'Path:speech.config\r\n'
        '\r\n'
        '{"context":{"synthesis":{"audio":{"metadataoptions":'
        '{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"true"}'
        ',"outputFormat":"$audioFormat"}}}}';
  }

  String _ssmlMessage(
    String chunk, {
    required String voice,
    required String rate,
    required String pitch,
    required String volume,
  }) {
    return 'X-RequestId:${_uuidHex()}\r\n'
        'Content-Type:application/ssml+xml\r\n'
        'X-Timestamp:${_timestamp()}Z\r\n'
        'Path:ssml\r\n'
        '\r\n'
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
        "xml:lang='en-US'>"
        "<voice name='${_voiceLongName(voice)}'>"
        "<prosody pitch='$pitch' rate='$rate' volume='$volume'>"
        '${_xmlEscape(chunk)}'
        '</prosody></voice></speak>';
  }

  static String _voiceLongName(String shortName) {
    final match = RegExp(r'^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$')
        .firstMatch(shortName);
    if (match == null) {
      return shortName;
    }
    final locale = '${match.group(1)}-${match.group(2)}';
    return 'Microsoft Server Speech Text to Speech Voice '
        '($locale, ${match.group(3)})';
  }

  /// Returns null on turn.end, the parsed events otherwise.
  List<EdgeTtsEvent>? _parseTextFrame(String frame, int offsetCompensation) {
    final separator = frame.indexOf('\r\n\r\n');
    if (separator < 0) {
      return const [];
    }
    final headers = frame.substring(0, separator);
    final body = frame.substring(separator + 4);
    if (headers.contains('Path:turn.end')) {
      return null;
    }
    if (!headers.contains('Path:audio.metadata')) {
      return const [];
    }
    final decoded = jsonDecode(body);
    if (decoded is! Map<String, dynamic>) {
      return const [];
    }
    final metadata = decoded['Metadata'];
    if (metadata is! List) {
      return const [];
    }
    final events = <EdgeTtsEvent>[];
    for (final item in metadata) {
      if (item is! Map<String, dynamic> || item['Type'] != 'WordBoundary') {
        continue;
      }
      final data = item['Data'];
      if (data is! Map<String, dynamic>) {
        continue;
      }
      final text = data['text'];
      final word = text is Map<String, dynamic> ? text['Text'] : null;
      if (word is! String || word.trim().isEmpty) {
        continue;
      }
      events.add(
        EdgeWordBoundaryEvent(
          offset: ((data['Offset'] as num?)?.toInt() ?? 0) + offsetCompensation,
          duration: (data['Duration'] as num?)?.toInt() ?? 0,
          text: word,
        ),
      );
    }
    return events;
  }

  Uint8List? _parseBinaryFrame(Uint8List frame) {
    if (frame.length < 2) {
      return null;
    }
    final headerLength = (frame[0] << 8) | frame[1];
    final headerEnd = 2 + headerLength;
    if (headerEnd >= frame.length) {
      return null;
    }
    final header = utf8.decode(
      frame.sublist(2, headerEnd),
      allowMalformed: true,
    );
    if (!header.contains('Content-Type:audio/mpeg')) {
      return null;
    }
    return frame.sublist(headerEnd);
  }

  List<String> _splitText(String text) {
    final cleaned = text.replaceAll(
      RegExp(r'[\x00-\x08\x0b\x0c\x0e-\x1f]'),
      ' ',
    );
    if (cleaned.isEmpty) {
      return const [];
    }
    if (utf8.encode(cleaned).length <= _maxChunkBytes) {
      return [cleaned];
    }
    final chunks = <String>[];
    var remaining = cleaned;
    while (remaining.isNotEmpty) {
      var fit = remaining.length;
      if (utf8.encode(remaining).length > _maxChunkBytes) {
        var lo = 0;
        var hi = remaining.length;
        while (lo < hi) {
          final mid = (lo + hi + 1) ~/ 2;
          if (utf8.encode(remaining.substring(0, mid)).length <=
              _maxChunkBytes) {
            lo = mid;
          } else {
            hi = mid - 1;
          }
        }
        fit = lo;
      }
      final candidate = remaining.substring(0, fit);
      var splitAt = fit;
      final lastNewline = candidate.lastIndexOf('\n');
      if (lastNewline > 0) {
        splitAt = lastNewline + 1;
      } else {
        final lastSpace = candidate.lastIndexOf(' ');
        if (lastSpace > 0) {
          splitAt = lastSpace + 1;
        }
      }
      chunks.add(remaining.substring(0, splitAt));
      remaining = remaining.substring(splitAt);
    }
    return chunks;
  }

  void _validateParam(String value, RegExp pattern, String name) {
    if (!pattern.hasMatch(value)) {
      throw ArgumentError('Edge TTS: $name inválido: "$value"');
    }
  }

  String _xmlEscape(String text) {
    return text
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&apos;');
  }

  String _uuidHex() {
    final random = Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    return bytes.map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
  }

  static const _days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  static const _months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];

  /// Javascript-style timestamp, as the service expects it.
  String _timestamp() {
    final now = _clock().toUtc();
    final day = _days[now.weekday - 1];
    final month = _months[now.month - 1];
    String two(int value) => value.toString().padLeft(2, '0');
    return '$day $month ${two(now.day)} ${now.year} '
        '${two(now.hour)}:${two(now.minute)}:${two(now.second)} '
        'GMT+0000 (Coordinated Universal Time)';
  }
}
