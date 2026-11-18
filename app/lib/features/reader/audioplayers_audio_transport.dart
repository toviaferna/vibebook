import 'dart:async';

import 'package:audioplayers/audioplayers.dart';

import 'audio_transport.dart';

/// [AudioTransport] backed by a single `audioplayers` player.
///
/// `play()` maps to `resume()`: the reader sets the source once and then
/// resumes it, which is how the page worked before the controller existed.
class AudioplayersAudioTransport implements AudioTransport {
  AudioplayersAudioTransport() {
    _stateSubscription = _player.onPlayerStateChanged.listen((state) {
      _states.add(_mapState(state));
    });
  }

  final AudioPlayer _player = AudioPlayer();
  final _states = StreamController<AudioTransportState>.broadcast();
  StreamSubscription<PlayerState>? _stateSubscription;

  static AudioTransportState _mapState(PlayerState state) {
    return switch (state) {
      PlayerState.playing => AudioTransportState.playing,
      PlayerState.paused => AudioTransportState.paused,
      PlayerState.completed => AudioTransportState.completed,
      _ => AudioTransportState.stopped,
    };
  }

  @override
  Stream<AudioTransportState> get onStateChanged => _states.stream;

  @override
  Stream<Duration> get onPositionChanged => _player.onPositionChanged;

  @override
  Stream<Duration> get onDurationChanged => _player.onDurationChanged;

  @override
  Future<void> setSourceFile(String path) =>
      _player.setSource(DeviceFileSource(path));

  @override
  Future<void> play() => _player.resume();

  @override
  Future<void> pause() => _player.pause();

  @override
  Future<void> stop() => _player.stop();

  @override
  Future<void> seek(Duration position) => _player.seek(position);

  @override
  Future<void> setVolume(double volume) => _player.setVolume(volume);

  @override
  Future<void> setPlaybackRate(double rate) => _player.setPlaybackRate(rate);

  @override
  Future<void> setLooping(bool looping) =>
      _player.setReleaseMode(looping ? ReleaseMode.loop : ReleaseMode.stop);

  @override
  Future<void> dispose() async {
    await _stateSubscription?.cancel();
    await _player.dispose();
    await _states.close();
  }
}
