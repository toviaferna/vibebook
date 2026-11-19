import 'dart:async';
import 'dart:io';

import 'audio_transport.dart';
import '../../domain/ambience.dart';

/// Owns the reader's voice and ambience players.
///
/// Every playback operation goes through this controller so the lifecycle is
/// serialized and safe to leave at any moment:
///
/// - A stale chapter load never overwrites the chapter that replaced it
///   (generation tokens).
/// - Ambience operations run on a single queue: no interleaved fades, no
///   double beds, and nothing touches a transport after [dispose].
/// - Ambience failures retry a bounded number of times and then surface in
///   [ambienceError] instead of dying silently.
class ReaderPlaybackController {
  ReaderPlaybackController({
    required ReaderTransports transports,
    required Future<File> Function(AmbiencePreset preset) ambienceResolver,
    this.fadeStep = const Duration(milliseconds: 70),
    this.fadeSteps = 8,
    this.retryDelay = const Duration(milliseconds: 400),
  }) : _voice = transports.voice,
       _ambience = transports.ambience,
       _resolveAmbience = ambienceResolver {
    _voiceStateSubscription = _voice.onStateChanged.listen(_handleVoiceState);
    _voicePositionSubscription = _voice.onPositionChanged.listen(
      (position) => _position = position,
    );
    _voiceDurationSubscription = _voice.onDurationChanged.listen(
      (duration) => _duration = duration,
    );
    _ambienceStateSubscription = _ambience.onStateChanged.listen(
      _handleAmbienceState,
    );
  }

  static const maxAmbienceFailures = 3;

  final AudioTransport _voice;
  final AudioTransport _ambience;
  final Future<File> Function(AmbiencePreset preset) _resolveAmbience;

  /// Pause between ambience fade steps.
  final Duration fadeStep;

  /// Steps of each ambience fade; values below 1 are treated as 1.
  final int fadeSteps;

  /// Wait before an automatic ambience retry.
  final Duration retryDelay;

  StreamSubscription<AudioTransportState>? _voiceStateSubscription;
  StreamSubscription<Duration>? _voicePositionSubscription;
  StreamSubscription<Duration>? _voiceDurationSubscription;
  StreamSubscription<AudioTransportState>? _ambienceStateSubscription;

  AudioTransportState _voiceState = AudioTransportState.stopped;
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;
  int _loadGeneration = 0;
  bool _loadInFlight = false;
  int? _loadedChapterIndex;
  bool _disposed = false;

  AmbiencePreset? _ambiencePreset;
  String? _ambiencePresetId;
  double _ambienceVolume = 0;
  double _ambienceVolumeSetting = 0.35;
  double _ambienceDucking = 0.3;
  bool _ambienceExpected = false;
  bool _ambienceBusy = false;
  int _ambienceFailures = 0;
  int _ambienceGeneration = 0;
  String? _ambienceError;
  Future<void> _ambienceQueue = Future<void>.value();
  Timer? _fadeTimer;
  Completer<void>? _fadeGate;

  // ------------------------------------------------------------- voice state

  /// Raw voice state stream; the page uses it for the play button and the
  /// end-of-chapter auto-advance.
  Stream<AudioTransportState> get onVoiceStateChanged => _voice.onStateChanged;

  Stream<Duration> get onPositionChanged => _voice.onPositionChanged;

  Stream<Duration> get onDurationChanged => _voice.onDurationChanged;

  AudioTransportState get voiceState => _voiceState;

  bool get isPlaying => _voiceState == AudioTransportState.playing;

  bool get isLoading => _loadInFlight;

  int? get loadedChapterIndex => _loadedChapterIndex;

  // ------------------------------------------------------------ chapter load

  /// Loads [audioPath] as the voice of [chapterIndex].
  ///
  /// The chapter is marked as loaded immediately (like the old reader) so a
  /// broken file does not retry on every rebuild; the generation token makes
  /// sure a load that lost the race to a newer chapter is abandoned.
  Future<void> loadChapter({
    required int chapterIndex,
    String? audioPath,
    int? startAtMs,
    required double volume,
    required double rate,
  }) async {
    _loadedChapterIndex = chapterIndex;
    if (_disposed || audioPath == null) {
      return;
    }
    final generation = ++_loadGeneration;
    _loadInFlight = true;
    try {
      await _voice.stop();
      if (_staleLoad(generation)) return;
      await _voice.setSourceFile(audioPath);
      if (_staleLoad(generation)) return;
      await _voice.setPlaybackRate(rate);
      await _voice.setVolume(volume);
      if (_staleLoad(generation)) return;
      if (startAtMs != null && startAtMs > 0) {
        await _voice.seek(Duration(milliseconds: startAtMs));
      }
    } catch (_) {
      // A failed load must not break the reader; the state stream re-syncs
      // whatever the platform managed to play.
    } finally {
      if (generation == _loadGeneration) {
        _loadInFlight = false;
      }
    }
  }

  bool _staleLoad(int generation) => _disposed || generation != _loadGeneration;

  Future<void> togglePlayPause() async {
    if (_disposed) return;
    try {
      if (_voiceState == AudioTransportState.playing) {
        await _voice.pause();
      } else {
        await _voice.play();
      }
    } catch (_) {
      // Transport hiccups surface through the state stream.
    }
  }

  /// Starts the voice regardless of the tracked state. Auto-advance uses it
  /// right after loading the next chapter, when the "stopped" event of the
  /// previous load may still be in flight.
  Future<void> startPlayback() async {
    if (_disposed) return;
    try {
      await _voice.play();
    } catch (_) {}
  }

  Future<void> seekBy(Duration delta) async {
    if (_disposed) return;
    var target = _position + delta;
    if (target < Duration.zero) {
      target = Duration.zero;
    }
    if (_duration > Duration.zero && target > _duration) {
      target = _duration;
    }
    try {
      await _voice.seek(target);
    } catch (_) {}
  }

  Future<void> setVoiceVolume(double volume) async {
    if (_disposed) return;
    try {
      await _voice.setVolume(volume);
    } catch (_) {}
  }

  Future<void> setVoiceRate(double rate) async {
    if (_disposed) return;
    try {
      await _voice.setPlaybackRate(rate);
    } catch (_) {}
  }

  // ---------------------------------------------------------------- ambience

  /// Last ambience failure, shown by the reader sheet with a retry button.
  String? get ambienceError => _ambienceError;

  bool get isAmbienceActive => _ambiencePresetId != null;

  /// Tail of the serialized ambience queue; exposed for tests and so callers
  /// can await a full settle.
  Future<void> get ambienceQueue => _ambienceQueue;

  void _enqueueAmbience(Future<void> Function() operation) {
    _ambienceQueue = _ambienceQueue
        .then((_) => operation())
        .then((_) {}, onError: (_) {});
  }

  /// Applies the requested ambience. A manual call resets the failure budget,
  /// which is what the sheet's retry button uses.
  Future<void> syncAmbience({
    required bool enabled,
    required AmbiencePreset preset,
    required double volume,
    required double ducking,
  }) {
    _ambienceVolumeSetting = volume;
    _ambienceDucking = ducking;
    if (!enabled) {
      _ambienceExpected = false;
      _ambiencePreset = null;
      _ambienceError = null;
      _ambienceFailures = 0;
      _enqueueAmbience(_stopAmbience);
      return _ambienceQueue;
    }
    _ambienceExpected = true;
    _ambienceError = null;
    _ambienceFailures = 0;
    if (_ambiencePresetId == preset.id) {
      _ambiencePreset = preset;
      _enqueueAmbience(_applyAmbienceVolume);
    } else {
      _ambiencePreset = preset;
      _enqueueAmbience(() => _startAmbience(preset));
    }
    return _ambienceQueue;
  }

  /// Live volume change while the user drags a slider: applies immediately
  /// without touching the persisted settings.
  Future<void> setAmbienceVolumeLive({
    required double volume,
    required double ducking,
  }) {
    _ambienceVolumeSetting = volume;
    _ambienceDucking = ducking;
    if (_ambienceExpected) {
      _enqueueAmbience(_applyAmbienceVolume);
    }
    return _ambienceQueue;
  }

  Future<void> _applyAmbienceVolume() async {
    if (_disposed || !_ambienceExpected) return;
    final target = _targetAmbienceVolume();
    if (target == _ambienceVolume) return;
    _ambienceVolume = target;
    try {
      await _ambience.setVolume(target);
    } catch (_) {}
  }

  double _targetAmbienceVolume() {
    final factor = _voiceState == AudioTransportState.playing
        ? _ambienceDucking
        : 1.0;
    return (_ambienceVolumeSetting * factor).clamp(0.0, 1.0).toDouble();
  }

  Future<void> _startAmbience(AmbiencePreset preset) async {
    if (_disposed || !_ambienceExpected) return;
    _ambienceBusy = true;
    final generation = ++_ambienceGeneration;
    try {
      if (_ambiencePresetId != null) {
        await _fadeTo(0, generation);
        await _ambience.stop();
        if (_staleAmbience(generation)) return;
      }
      final file = await _resolveAmbience(preset);
      if (_staleAmbience(generation)) return;
      await _ambience.setLooping(true);
      _ambienceVolume = 0;
      await _ambience.setVolume(0);
      if (_staleAmbience(generation)) return;
      await _ambience.setSourceFile(file.path);
      if (_staleAmbience(generation)) return;
      await _ambience.play();
      _ambiencePresetId = preset.id;
      _ambienceFailures = 0;
      _ambienceError = null;
      await _fadeTo(_targetAmbienceVolume(), generation);
    } catch (_) {
      _ambiencePresetId = null;
      _ambienceFailures += 1;
      if (_ambienceFailures >= maxAmbienceFailures) {
        _ambienceError = 'No se pudo iniciar el ambiente.';
        _ambienceExpected = false;
        return;
      }
      await Future<void>.delayed(retryDelay);
      if (!_disposed && _ambienceExpected) {
        await _startAmbience(preset);
      }
    } finally {
      _ambienceBusy = false;
    }
  }

  Future<void> _stopAmbience() async {
    if (_disposed) return;
    _ambienceBusy = true;
    final generation = ++_ambienceGeneration;
    _ambiencePresetId = null;
    try {
      await _fadeTo(0, generation);
      await _ambience.stop();
    } catch (_) {
      // Stopping must never break the queue.
    } finally {
      _ambienceBusy = false;
    }
  }

  bool _staleAmbience(int generation) =>
      _disposed || generation != _ambienceGeneration;

  Future<void> _fadeTo(double target, int generation) async {
    final steps = fadeSteps <= 0 ? 1 : fadeSteps;
    final start = _ambienceVolume;
    if (start == target) {
      return;
    }
    for (var step = 1; step <= steps; step++) {
      if (_staleAmbience(generation)) return;
      final value = (start + (target - start) * step / steps)
          .clamp(0.0, 1.0)
          .toDouble();
      _ambienceVolume = value;
      try {
        await _ambience.setVolume(value);
      } catch (_) {
        return;
      }
      final gate = Completer<void>();
      _fadeGate = gate;
      _fadeTimer = Timer(fadeStep, gate.complete);
      await gate.future;
      _fadeGate = null;
      _fadeTimer = null;
    }
  }

  /// Cancels the pending fade step so an in-flight fade aborts immediately
  /// instead of making [stopAll] or [dispose] queue behind it.
  void _releaseFadeGate() {
    _fadeTimer?.cancel();
    _fadeTimer = null;
    final gate = _fadeGate;
    _fadeGate = null;
    if (gate != null && !gate.isCompleted) {
      gate.complete();
    }
  }

  /// The platform stopped the bed mid-playback (audio focus, OS hiccup):
  /// restart it with the stored preset. Events caused by our own stop are
  /// ignored while an operation is in flight.
  void _handleAmbienceState(AudioTransportState state) {
    if (_disposed || !_ambienceExpected || _ambienceBusy) return;
    if (state != AudioTransportState.stopped &&
        state != AudioTransportState.completed) {
      return;
    }
    final preset = _ambiencePreset;
    if (preset == null) return;
    _enqueueAmbience(() => _startAmbience(preset));
  }

  void _handleVoiceState(AudioTransportState state) {
    if (_disposed) return;
    _voiceState = state;
    // Ducking depends on the voice: keep the bed in sync.
    if (_ambienceExpected) {
      _enqueueAmbience(_applyAmbienceVolume);
    }
  }

  // --------------------------------------------------------------- teardown

  /// Stops both players. Awaited by the reader before navigating back.
  Future<void> stopAll() async {
    _ambienceExpected = false;
    _ambiencePreset = null;
    _ambienceError = null;
    _ambienceFailures = 0;
    _ambienceGeneration++;
    _releaseFadeGate();
    final voiceStop = _quiet(() => _voice.stop());
    final ambienceStop = _enqueueAndWait(() async {
      _ambiencePresetId = null;
      await _quiet(() => _ambience.stop());
    });
    await Future.wait([voiceStop, ambienceStop]);
  }

  Future<void> _quiet(Future<void> Function() operation) async {
    if (_disposed) return;
    try {
      await operation();
    } catch (_) {}
  }

  Future<void> _enqueueAndWait(Future<void> Function() operation) {
    _enqueueAmbience(operation);
    return _ambienceQueue;
  }

  /// Marks the controller as dead, cancels its subscriptions and tears the
  /// transports down in order: stop, then dispose. The returned future
  /// completes when both transports are gone.
  Future<void> dispose() {
    if (_disposed) {
      return Future<void>.value();
    }
    _disposed = true;
    _ambienceExpected = false;
    _ambiencePreset = null;
    _ambienceGeneration++;
    _releaseFadeGate();
    _loadGeneration++;
    unawaited(_voiceStateSubscription?.cancel());
    unawaited(_voicePositionSubscription?.cancel());
    unawaited(_voiceDurationSubscription?.cancel());
    unawaited(_ambienceStateSubscription?.cancel());
    final voice = _voice;
    final ambience = _ambience;
    return () async {
      // Let the queued ambience operation observe the generation bump and
      // abort before the transports go away.
      await _ambienceQueue;
      try {
        await voice.stop();
      } catch (_) {}
      try {
        await ambience.stop();
      } catch (_) {}
      try {
        await voice.dispose();
      } catch (_) {}
      try {
        await ambience.dispose();
      } catch (_) {}
    }();
  }
}
