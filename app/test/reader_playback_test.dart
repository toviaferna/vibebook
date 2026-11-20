import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/domain/ambience.dart';
import 'package:vibebook_app/features/reader/audio_transport.dart';
import 'package:vibebook_app/features/reader/reader_playback.dart';

import 'fakes/fake_audio_transport.dart';

ReaderPlaybackController buildController({
  FakeAudioTransport? voice,
  FakeAudioTransport? ambience,
  Future<File> Function(AmbiencePreset preset)? resolver,
  Duration fadeStep = Duration.zero,
  int fadeSteps = 2,
}) {
  return ReaderPlaybackController(
    transports: ReaderTransports(
      voice: voice ?? FakeAudioTransport(),
      ambience: ambience ?? FakeAudioTransport(),
    ),
    ambienceResolver:
        resolver ?? (preset) async => File('/tmp/${preset.id}.mp3'),
    fadeStep: fadeStep,
    fadeSteps: fadeSteps,
    retryDelay: Duration.zero,
  );
}

void main() {
  test('una carga vieja no revierte el capítulo nuevo', () async {
    final voice = FakeAudioTransport();
    final controller = buildController(voice: voice);
    final gate = Completer<void>();
    voice.gate = gate;
    voice.gatePrefix = 'setSourceFile';

    final first = controller.loadChapter(
      chapterIndex: 1,
      audioPath: 'chapter_001.mp3',
      startAtMs: 900,
      volume: 1,
      rate: 1,
    );
    await pumpEventQueue();
    final second = controller.loadChapter(
      chapterIndex: 2,
      audioPath: 'chapter_002.mp3',
      startAtMs: 500,
      volume: 1,
      rate: 1,
    );
    gate.complete();
    await first;
    await second;

    expect(controller.loadedChapterIndex, 2);
    expect(voice.calls.where((call) => call.startsWith('seek:')), ['seek:500']);
    expect(
      voice.calls.where((call) => call.startsWith('setPlaybackRate:')),
      hasLength(1),
    );
    await controller.dispose();
  });

  test(
    'togglePlayPause pausa cuando suena y reanuda cuando está en pausa',
    () async {
      final voice = FakeAudioTransport();
      final controller = buildController(voice: voice);

      voice.emitState(AudioTransportState.playing);
      await pumpEventQueue();
      await controller.togglePlayPause();
      expect(voice.calls, contains('pause'));

      voice.emitState(AudioTransportState.paused);
      await pumpEventQueue();
      await controller.togglePlayPause();
      expect(voice.calls.where((call) => call == 'play'), hasLength(1));
      await controller.dispose();
    },
  );

  test('syncAmbience arranca el ambiente atenuado bajo la voz', () async {
    final voice = FakeAudioTransport();
    final ambience = FakeAudioTransport();
    final controller = buildController(voice: voice, ambience: ambience);
    voice.emitState(AudioTransportState.playing);

    await controller.syncAmbience(
      enabled: true,
      preset: AmbiencePreset.fire,
      volume: 0.8,
      ducking: 0.5,
    );

    expect(
      ambience.calls,
      containsAllInOrder([
        'setLooping:true',
        'setVolume:0.0',
        'setSourceFile:/tmp/fire.mp3',
        'play',
      ]),
    );
    expect(ambience.volume, closeTo(0.4, 0.001));
    expect(controller.isAmbienceActive, isTrue);
    await controller.dispose();
  });

  test('los cambios de preset se serializan sin intercalar', () async {
    final ambience = FakeAudioTransport();
    final gate = Completer<void>();
    ambience.gate = gate;
    ambience.gatePrefix = 'setSourceFile';
    final controller = buildController(ambience: ambience);

    controller.syncAmbience(
      enabled: true,
      preset: AmbiencePreset.rain,
      volume: 0.5,
      ducking: 0.3,
    );
    await pumpEventQueue();
    final second = controller.syncAmbience(
      enabled: true,
      preset: AmbiencePreset.wind,
      volume: 0.5,
      ducking: 0.3,
    );
    await pumpEventQueue();

    // Mientras la primera fuente está trabada, la segunda no arrancó.
    expect(ambience.calls.any((call) => call.contains('wind.mp3')), isFalse);

    gate.complete();
    await second;

    expect(
      ambience.calls,
      containsAllInOrder([
        'setSourceFile:/tmp/rain.mp3',
        'play',
        'stop',
        'setSourceFile:/tmp/wind.mp3',
        'play',
      ]),
    );
    await controller.dispose();
  });

  test('dispose durante un fade no vuelve a tocar los transports', () async {
    final ambience = FakeAudioTransport();
    final controller = buildController(
      ambience: ambience,
      fadeStep: const Duration(milliseconds: 30),
      fadeSteps: 8,
    );

    final syncing = controller.syncAmbience(
      enabled: true,
      preset: AmbiencePreset.night,
      volume: 0.8,
      ducking: 0.3,
    );
    await pumpEventQueue();
    controller.dispose();
    await syncing;
    await pumpEventQueue();

    expect(ambience.calls, contains('dispose'));
    expect(
      ambience.calls.where((call) => call.startsWith('used-after-dispose')),
      isEmpty,
    );
  });

  test('stopAll detiene voz y ambiente y no se relanza el ambiente', () async {
    final voice = FakeAudioTransport();
    final ambience = FakeAudioTransport();
    final controller = buildController(voice: voice, ambience: ambience);

    await controller.syncAmbience(
      enabled: true,
      preset: AmbiencePreset.fire,
      volume: 0.8,
      ducking: 0.3,
    );
    voice.emitState(AudioTransportState.playing);
    await controller.stopAll();

    expect(voice.calls, contains('stop'));
    expect(ambience.calls, contains('stop'));
    expect(controller.isAmbienceActive, isFalse);

    // Un evento tardío del propio stop no debe relanzar la cama.
    ambience.emitState(AudioTransportState.stopped);
    await pumpEventQueue();
    expect(ambience.calls.where((call) => call == 'play'), hasLength(1));
    await controller.dispose();
  });

  test(
    'tres fallos de ambiente exponen ambienceError y dejan de reintentar',
    () async {
      final ambience = FakeAudioTransport();
      var attempts = 0;
      final controller = buildController(
        ambience: ambience,
        resolver: (preset) async {
          attempts += 1;
          throw StateError('sin asset');
        },
      );

      await controller.syncAmbience(
        enabled: true,
        preset: AmbiencePreset.fire,
        volume: 0.8,
        ducking: 0.3,
      );
      expect(attempts, 3);
      expect(controller.ambienceError, isNotNull);
      expect(controller.isAmbienceActive, isFalse);

      // Un sync manual reinicia el presupuesto de fallos.
      attempts = 0;
      await controller.syncAmbience(
        enabled: true,
        preset: AmbiencePreset.fire,
        volume: 0.8,
        ducking: 0.3,
      );
      expect(attempts, 3);
      await controller.dispose();
    },
  );

  test('setAmbienceVolumeLive cambia el volumen en caliente', () async {
    final ambience = FakeAudioTransport();
    final controller = buildController(ambience: ambience);

    await controller.syncAmbience(
      enabled: true,
      preset: AmbiencePreset.fire,
      volume: 0.5,
      ducking: 1.0,
    );
    await controller.setAmbienceVolumeLive(volume: 0.9, ducking: 1.0);

    expect(ambience.volume, closeTo(0.9, 0.001));
    await controller.dispose();
  });

  test('tras dispose el controller no llama a los transports', () async {
    final voice = FakeAudioTransport();
    final ambience = FakeAudioTransport();
    final controller = buildController(voice: voice, ambience: ambience);
    await controller.dispose();

    await controller.togglePlayPause();
    await controller.stopAll();
    await controller.syncAmbience(
      enabled: false,
      preset: AmbiencePreset.fire,
      volume: 0.5,
      ducking: 0.3,
    );
    await controller.syncAmbience(
      enabled: true,
      preset: AmbiencePreset.fire,
      volume: 0.5,
      ducking: 0.3,
    );
    await pumpEventQueue();

    expect(
      voice.calls.where((call) => call.startsWith('used-after-dispose')),
      isEmpty,
    );
    expect(
      ambience.calls.where((call) => call.startsWith('used-after-dispose')),
      isEmpty,
    );
  });
}
