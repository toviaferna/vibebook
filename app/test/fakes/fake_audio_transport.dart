import 'dart:async';

import 'package:vibebook_app/features/reader/audio_transport.dart';

/// In-memory [AudioTransport] used by the playback tests.
///
/// Every call is recorded in [calls]; a [gate] can pause the calls matching
/// [gatePrefix] until the test releases it. A call that arrives after
/// [dispose] is recorded as `used-after-dispose:<call>` instead of throwing,
/// so the tests can assert that the controller never touches a dead
/// transport.
class FakeAudioTransport implements AudioTransport {
  FakeAudioTransport({
    AudioTransportState initialState = AudioTransportState.stopped,
  }) : _state = initialState;

  final List<String> calls = [];

  /// When set, calls whose name starts with [gatePrefix] (all calls when
  /// [gatePrefix] is null) wait until the completer finishes.
  Completer<void>? gate;
  String? gatePrefix;

  bool disposed = false;
  double volume = 1.0;
  String? sourcePath;

  AudioTransportState _state;

  final _stateController = StreamController<AudioTransportState>.broadcast();
  final _positionController = StreamController<Duration>.broadcast();
  final _durationController = StreamController<Duration>.broadcast();

  @override
  Stream<AudioTransportState> get onStateChanged => _stateController.stream;

  @override
  Stream<Duration> get onPositionChanged => _positionController.stream;

  @override
  Stream<Duration> get onDurationChanged => _durationController.stream;

  AudioTransportState get state => _state;

  void emitState(AudioTransportState state) {
    _state = state;
    _stateController.add(state);
  }

  void emitPosition(Duration position) => _positionController.add(position);

  void emitDuration(Duration duration) => _durationController.add(duration);

  void _record(String call) {
    if (disposed) {
      calls.add('used-after-dispose:$call');
    } else {
      calls.add(call);
    }
  }

  Future<void> _maybeGate(String call) {
    final pending = gate;
    if (pending == null) {
      return Future<void>.value();
    }
    final prefix = gatePrefix;
    if (prefix != null && !call.startsWith(prefix)) {
      return Future<void>.value();
    }
    return pending.future;
  }

  @override
  Future<void> setSourceFile(String path) {
    _record('setSourceFile:$path');
    sourcePath = path;
    return _maybeGate('setSourceFile:');
  }

  @override
  Future<void> play() {
    _record('play');
    return _maybeGate('play');
  }

  @override
  Future<void> pause() {
    _record('pause');
    return _maybeGate('pause');
  }

  @override
  Future<void> stop() {
    _record('stop');
    return _maybeGate('stop');
  }

  @override
  Future<void> seek(Duration position) {
    _record('seek:${position.inMilliseconds}');
    return _maybeGate('seek:');
  }

  @override
  Future<void> setVolume(double value) {
    _record('setVolume:$value');
    volume = value;
    return _maybeGate('setVolume:');
  }

  @override
  Future<void> setPlaybackRate(double rate) {
    _record('setPlaybackRate:$rate');
    return _maybeGate('setPlaybackRate:');
  }

  @override
  Future<void> setLooping(bool looping) {
    _record('setLooping:$looping');
    return _maybeGate('setLooping:');
  }

  @override
  Future<void> dispose() {
    _record('dispose');
    disposed = true;
    return Future<void>.value();
  }
}
