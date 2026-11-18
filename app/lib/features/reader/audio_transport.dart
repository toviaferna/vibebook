/// Playback state reported by an [AudioTransport].
enum AudioTransportState { playing, paused, completed, stopped }

/// A single audio player used by the reader page.
///
/// The interface keeps [ReaderPlaybackController] free of platform channels,
/// so chapter loads, ambience fades and teardown can be unit tested.
abstract class AudioTransport {
  Stream<AudioTransportState> get onStateChanged;
  Stream<Duration> get onPositionChanged;
  Stream<Duration> get onDurationChanged;

  Future<void> setSourceFile(String path);
  Future<void> play();
  Future<void> pause();
  Future<void> stop();
  Future<void> seek(Duration position);
  Future<void> setVolume(double volume);
  Future<void> setPlaybackRate(double rate);
  Future<void> setLooping(bool looping);
  Future<void> dispose();
}

/// The transports a reader page owns: the audiobook voice and the ambience
/// bed.
class ReaderTransports {
  ReaderTransports({required this.voice, required this.ambience});

  final AudioTransport voice;
  final AudioTransport ambience;
}
