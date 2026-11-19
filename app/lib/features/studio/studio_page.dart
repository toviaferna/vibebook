import 'dart:io';
import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/form_controls.dart';
import '../../core/design/tokens.dart';
import '../../data/ambience/ambience_analyzer.dart';
import '../../data/ambience/ambience_library.dart';
import '../../data/ambience/ambience_plan_repository.dart';
import '../../data/m4b_exporter.dart';
import '../../data/tts/chapter_synthesizer.dart';
import '../../data/tts/edge/edge_client.dart';
import '../../data/tts/edge/edge_synthesizer.dart';
import '../../data/tts/edge/edge_voices.dart';
import '../../data/tts/piper_models.dart';
import '../../data/tts/tts_chapter_worker.dart';
import '../../data/tts/tts_conversion.dart';
import '../../data/tts/wav_writer.dart';
import '../../domain/ambience.dart';
import '../../domain/ambience_plan.dart';
import '../../domain/models.dart';
import 'voice_download_dialog.dart';

class StudioPage extends ConsumerStatefulWidget {
  const StudioPage({super.key, required this.bookId});

  final String bookId;

  @override
  ConsumerState<StudioPage> createState() => _StudioPageState();
}

class _StudioPageState extends ConsumerState<StudioPage> {
  final _previewController = TextEditingController(
    text: 'La casa de los Ferrer se levantaba sobre una loma que olía a sal.',
  );
  AudioPlayer? _previewPlayer;
  bool _converting = false;
  bool _cancelRequested = false;
  bool _exporting = false;
  bool _previewing = false;
  bool _analyzingAmbience = false;
  AmbiencePlan? _ambiencePlan;
  double _progress = 0;
  String? _progressMessage;
  String? _error;
  String? _exportMessage;
  String? _previewMessage;

  @override
  void dispose() {
    _previewController.dispose();
    _previewPlayer?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final book = ref.watch(bookProvider(widget.bookId));
    return book.when(
      data: (value) {
        if (value == null) {
          return Scaffold(
            appBar: AppBar(
              leading: BackButton(onPressed: () => context.go('/')),
            ),
            body: const ErrorView(message: 'No encontré este libro.'),
          );
        }
        return _buildStudio(value);
      },
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (error, stackTrace) => Scaffold(
        appBar: AppBar(leading: BackButton(onPressed: () => context.go('/'))),
        body: ErrorView(message: '$error'),
      ),
    );
  }

  Widget _buildStudio(Book book) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final settings = ref.watch(settingsProvider).value;
    final models = ref.watch(piperModelsProvider);
    final selected = ref.watch(selectedPiperModelProvider);
    final engine = settings?.ttsEngine ?? 'piper';
    final rate = engine == 'edge'
        ? (settings?.edgeRate ?? 0)
        : (settings?.piperRate ?? -10);
    final modelsRoot = ref.watch(modelsRootProvider);
    final savedAmbiencePlan = ref.watch(ambiencePlanProvider(book.id)).value;
    final ambiencePlan = _ambiencePlan ?? savedAmbiencePlan;
    return PageScaffold(
      eyebrow: 'Estudio',
      title: book.title,
      subtitle:
          'Voz local, sin cuenta ni nube. La síntesis corre en este equipo.',
      maxContentWidth: 860,
      actions: [
        IconButton(
          tooltip: 'Volver al libro',
          onPressed: () {
            if (context.canPop()) {
              context.pop();
            } else {
              context.go('/books/${book.id}');
            }
          },
          icon: const Icon(Icons.arrow_back),
        ),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (book.hasAudio)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: colors.surface,
                border: Border(left: BorderSide(color: colors.brass, width: 2)),
                borderRadius: BibliotecaRadii.md,
              ),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final message = Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.check_circle_outline, color: colors.brass),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Este libro ya tiene audio. Podés volver a convertirlo o abrir el lector.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  );
                  final action = OutlinedButton(
                    onPressed: () => context.push('/books/${book.id}/read'),
                    child: const Text('Abrir lector'),
                  );
                  if (constraints.maxWidth < 560) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [message, const SizedBox(height: 12), action],
                    );
                  }
                  return Row(
                    children: [
                      Expanded(child: message),
                      const SizedBox(width: 12),
                      action,
                    ],
                  );
                },
              ),
            ),
          const SizedBox(height: 24),
          BibliotecaSection(
            title: 'Voz y motor',
            description:
                'Piper corre en este equipo; Edge es online y no oficial.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                BibliotecaSelect<String>(
                  label: 'Motor',
                  value: engine,
                  options: const [
                    BibliotecaSelectOption(
                      value: 'piper',
                      label: 'Piper (local)',
                      description: 'Sin cuenta ni nube. La síntesis corre acá.',
                    ),
                    BibliotecaSelectOption(
                      value: 'edge',
                      label: 'Edge (online, experimental)',
                      description: 'Voces neuronales de Microsoft vía red.',
                    ),
                  ],
                  onChanged: _converting
                      ? null
                      : (value) => ref
                            .read(settingsProvider.notifier)
                            .updateTtsEngine(engine: value),
                ),
                const SizedBox(height: 14),
                if (engine == 'edge') ...[
                  BibliotecaSelect<String>(
                    label: 'Voz Edge',
                    value: settings?.edgeVoiceId ?? defaultEdgeVoiceId,
                    options: [
                      for (final voice in edgeVoices)
                        BibliotecaSelectOption(
                          value: voice.id,
                          label: voice.name,
                          description:
                              '${voice.locale.toUpperCase()} · ${voice.gender}',
                        ),
                    ],
                    onChanged: _converting
                        ? null
                        : (value) => ref
                              .read(settingsProvider.notifier)
                              .updateTtsEngine(edgeVoice: value),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'El texto se envía a Microsoft y el servicio puede fallar, '
                    'limitarse o cambiar sin aviso. No sirve sin conexión.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ] else ...[
                  models.when(
                    data: (items) {
                      if (items.isEmpty) {
                        return _NoModels(
                          root: modelsRoot.value,
                          onChoose: _chooseModelsFolder,
                          onRefresh: () => ref.invalidate(piperModelsProvider),
                        );
                      }
                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          BibliotecaSelect<String>(
                            label: 'Modelo Piper',
                            value: selected?.id ?? items.first.id,
                            options: [
                              for (final model in items)
                                BibliotecaSelectOption(
                                  value: model.id,
                                  label: model.name,
                                  description:
                                      '${model.language.toUpperCase()} · ${(model.sampleRate / 1000).toStringAsFixed(1)} kHz',
                                ),
                            ],
                            onChanged: _converting
                                ? null
                                : (value) {
                                    ref
                                        .read(settingsProvider.notifier)
                                        .selectPiperModel(value);
                                  },
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              OutlinedButton.icon(
                                onPressed: _converting
                                    ? null
                                    : _chooseModelsFolder,
                                icon: const Icon(Icons.folder_open, size: 18),
                                label: const Text('Carpeta de modelos'),
                              ),
                              OutlinedButton.icon(
                                onPressed: _converting
                                    ? null
                                    : () => showVoiceDownloadDialog(context),
                                icon: const Icon(Icons.download, size: 18),
                                label: const Text('Agregar voz'),
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          _ModelDetails(model: selected),
                        ],
                      );
                    },
                    loading: () => const Padding(
                      padding: EdgeInsets.symmetric(vertical: 20),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                    error: (error, stackTrace) =>
                        Text('No se pudieron leer los modelos: $error'),
                  ),
                ],
                const SizedBox(height: 16),
                TextField(
                  controller: _previewController,
                  maxLines: 2,
                  minLines: 1,
                  decoration: const InputDecoration(
                    labelText: 'Probar la voz',
                    hintText: 'Escribí una frase para escucharla.',
                  ),
                ),
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: _converting || _previewing
                        ? null
                        : () => _previewAny(),
                    icon: Icon(
                      _previewing ? Icons.hourglass_top : Icons.play_arrow,
                      size: 18,
                    ),
                    label: Text(
                      _previewing ? 'Generando muestra…' : 'Escuchar muestra',
                    ),
                  ),
                ),
                if (_previewMessage != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    _previewMessage!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 18),
          BibliotecaSection(
            title: 'Lectura y salida',
            child: BibliotecaFormRow(
              title: 'Velocidad de síntesis',
              subtitle: 'Se guarda y se aplica a todas las conversiones.',
              controlWidth: 280,
              child: Row(
                children: [
                  Expanded(
                    child: Slider(
                      value: rate,
                      min: -30,
                      max: 30,
                      divisions: 12,
                      label: '${rate.round()}%',
                      onChanged: _converting
                          ? null
                          : (value) {
                              if (engine == 'edge') {
                                ref
                                    .read(settingsProvider.notifier)
                                    .updateTtsEngine(edgeRate: value);
                              } else {
                                ref
                                    .read(settingsProvider.notifier)
                                    .setPiperRate(value);
                              }
                            },
                    ),
                  ),
                  SizedBox(
                    width: 44,
                    child: Text(
                      '${rate.round()}%',
                      textAlign: TextAlign.end,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          BibliotecaSection(
            title: 'Ambiente global',
            description: 'Se usa en los capítulos que no tienen un paisaje propio en el plan.',
            child: Align(
              alignment: Alignment.centerLeft,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 380),
                child: BibliotecaSelect<String>(
                  label: 'Paisaje sonoro',
                  value: settings?.ambiencePreset ?? 'rain',
                  options: [
                    for (final preset in AmbiencePreset.values)
                      BibliotecaSelectOption(
                        value: preset.id,
                        label: preset.label,
                        description: preset.description,
                      ),
                  ],
                  onChanged: _converting || _exporting
                      ? null
                      : (preset) {
                          ref
                              .read(settingsProvider.notifier)
                              .updateAmbience(preset: preset);
                        },
                ),
              ),
            ),
          ),
          const SizedBox(height: 18),
          BibliotecaSection(
            title: 'Plan por capítulo',
            description:
                'Analiza el texto y asigna un paisaje a cada capítulo. '
                'Se guarda en ambience/plan_flutter.json y el lector lo usa automáticamente.',
            actions: [
              OutlinedButton.icon(
                onPressed: _analyzingAmbience || book.chapterCount == 0
                    ? null
                    : () => _analyzeAmbience(book),
                icon: Icon(
                  _analyzingAmbience ? Icons.hourglass_top : Icons.auto_awesome,
                  size: 18,
                ),
                label: Text(
                  _analyzingAmbience ? 'Analizando…' : 'Analizar capítulos',
                ),
              ),
            ],
            child: ambiencePlan == null || ambiencePlan.chapters.isEmpty
                ? Text(
                    'Todavía no hay un plan. Sin plan, el lector usa el paisaje global.',
                    style: Theme.of(context).textTheme.bodySmall,
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        '${ambiencePlan.detectedChapters} de ${book.chapterCount} capítulos '
                        'tienen un paisaje detectado.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 8),
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxHeight: 340),
                        child: SingleChildScrollView(
                          child: Column(
                            children: [
                              for (final chapter in book.chapters)
                                _ChapterAmbienceRow(
                                  chapter: chapter,
                                  plan: ambiencePlan.forChapter(chapter.index),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: colors.danger.withValues(alpha: 0.08),
                border: Border(
                  left: BorderSide(color: colors.danger, width: 2),
                ),
              ),
              child: Text(_error!),
            ),
          ],
          if (_converting) ...[
            const SizedBox(height: 18),
            LinearProgressIndicator(value: _progress == 0 ? null : _progress),
            const SizedBox(height: 8),
            Text(_progressMessage ?? 'Preparando la síntesis…'),
          ],
          const SizedBox(height: 22),
          Wrap(
            spacing: 12,
            runSpacing: 10,
            children: [
              FilledButton.icon(
                onPressed:
                    _converting ||
                        _exporting ||
                        (engine == 'piper' && selected == null)
                    ? null
                    : () => _convertCurrent(book, engine, selected, rate),
                icon: const Icon(Icons.graphic_eq, size: 18),
                label: Text(
                  _converting
                      ? 'Convirtiendo…'
                      : engine == 'edge'
                      ? 'Convertir con Edge'
                      : 'Convertir con Piper',
                ),
              ),
              if (_converting)
                OutlinedButton.icon(
                  onPressed: () => setState(() => _cancelRequested = true),
                  icon: const Icon(Icons.stop, size: 18),
                  label: const Text('Detener al final del capítulo'),
                ),
              OutlinedButton.icon(
                onPressed: _exporting || _converting || !book.hasAudio
                    ? null
                    : () => _exportM4bWithAmbience(
                        book,
                        AmbiencePresetDetails.byId(settings?.ambiencePreset),
                      ),
                icon: const Icon(Icons.forest, size: 18),
                label: Text(
                  _exporting ? 'Exportando…' : 'Exportar M4B ambientado',
                ),
              ),
              OutlinedButton.icon(
                onPressed: _exporting || _converting || !book.hasAudio
                    ? null
                    : () => _exportM4b(book),
                icon: const Icon(Icons.audio_file, size: 18),
                label: Text(_exporting ? 'Exportando…' : 'Exportar M4B'),
              ),
            ],
          ),
          if (_exportMessage != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: colors.surface,
                border: Border(left: BorderSide(color: colors.brass, width: 2)),
              ),
              child: Text(
                _exportMessage!,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          ],
          const SizedBox(height: 24),
          Text(
            'La voz se sintetiza en un isolate aparte: la interfaz sigue respondiendo. '
            'Los timings de karaoke se estiman a partir de la duración real de cada segmento.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Future<void> _analyzeAmbience(Book book) async {
    final directory = book.directoryPath;
    if (directory == null) {
      setState(() => _error = 'El libro no tiene una carpeta de biblioteca.');
      return;
    }
    setState(() {
      _analyzingAmbience = true;
      _error = null;
    });
    try {
      final plan = const AmbienceAnalyzer().analyze(book);
      await const AmbiencePlanRepository().save(directory, plan);
      ref.invalidate(ambiencePlanProvider(book.id));
      if (mounted) {
        setState(() {
          _ambiencePlan = plan;
          _analyzingAmbience = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Plan listo: ${plan.detectedChapters} de ${book.chapterCount} capítulos.',
            ),
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _analyzingAmbience = false;
          _error = 'No se pudo analizar el ambiente: $error';
        });
      }
    }
  }

  Future<void> _chooseModelsFolder() async {
    final path = await getDirectoryPath(confirmButtonText: 'Usar esta carpeta');
    if (path == null) {
      return;
    }
    await ref.read(settingsProvider.notifier).setModelsPath(path);
    ref.invalidate(piperModelsProvider);
    ref.invalidate(modelsRootProvider);
  }

  Future<void> _preview(PiperModel model, double rate) async {
    final text = _previewController.text.trim();
    if (text.isEmpty) {
      return;
    }
    setState(() {
      _previewing = true;
      _previewMessage = null;
      _error = null;
    });
    try {
      final espeak = await ensurePiperEspeakData();
      final result = await renderChapterInBackground({
        'model': {
          'model': model.modelPath,
          'tokens': model.tokensPath,
          'voice': model.espeakVoice,
          'noise_scale': model.noiseScale,
          'noise_w': model.noiseScaleW,
          'length_scale': model.lengthScale,
        },
        'espeak_data_path': espeak,
        'speed': 1 + rate / 100,
        'segments': [
          {'id': 'preview', 'text': text, 'pause_after_ms': 0},
        ],
      });
      final samples = result['samples'] as Float32List;
      final sampleRate =
          (result['sample_rate'] as num?)?.toInt() ?? model.sampleRate;
      if (samples.isEmpty) {
        throw StateError('La voz no generó audio.');
      }
      final temp = await getTemporaryDirectory();
      final file = File(p.join(temp.path, 'vibebook-preview.wav'));
      await file.writeAsBytes(
        const WavWriter().encode(samples, sampleRate),
        flush: true,
      );
      final player = _previewPlayer ??= AudioPlayer();
      await player.stop();
      await player.play(DeviceFileSource(file.path));
      if (mounted) {
        setState(() {
          _previewing = false;
          _previewMessage =
              'Muestra lista · ${(samples.length / sampleRate).toStringAsFixed(1)} s · ${sampleRate / 1000} kHz';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _previewing = false;
          _error = 'No se pudo probar la voz: $error';
        });
      }
    }
  }

  /// Probes the phrase with the selected engine.
  Future<void> _previewAny() {
    final settings = ref.read(settingsProvider).value;
    if (settings?.ttsEngine == 'edge') {
      return _previewEdge(settings?.edgeVoiceId ?? defaultEdgeVoiceId);
    }
    final model = ref.read(selectedPiperModelProvider);
    if (model == null) {
      return Future.value();
    }
    return _preview(model, settings?.piperRate ?? -10);
  }

  Future<void> _previewEdge(String voiceId) async {
    final text = _previewController.text.trim();
    if (text.isEmpty) {
      return;
    }
    final rate = ref.read(settingsProvider).value?.edgeRate ?? 0;
    final percent = rate.round();
    setState(() {
      _previewing = true;
      _previewMessage = null;
      _error = null;
    });
    try {
      final bytes = BytesBuilder(copy: false);
      await for (final event in EdgeTtsClient().synthesize(
        text: text,
        voice: voiceId,
        rate: '${percent >= 0 ? '+' : ''}$percent%',
      )) {
        if (event is EdgeAudioEvent) {
          bytes.add(event.data);
        }
      }
      final data = bytes.takeBytes();
      if (data.isEmpty) {
        throw const EdgeNoAudioException();
      }
      final temp = await getTemporaryDirectory();
      final file = File(p.join(temp.path, 'vibebook-edge-preview.mp3'));
      await file.writeAsBytes(data, flush: true);
      final player = _previewPlayer ??= AudioPlayer();
      await player.stop();
      await player.play(DeviceFileSource(file.path));
      if (mounted) {
        setState(() {
          _previewing = false;
          _previewMessage =
              'Muestra lista · ${(data.length / 1024).round()} KB · online';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _previewing = false;
          _error = 'No se pudo consultar Edge: $error';
        });
      }
    }
  }

  /// Chooses the engine and runs the conversion with it.
  Future<void> _convertCurrent(
    Book book,
    String engine,
    PiperModel? model,
    double rate,
  ) async {
    if (engine == 'edge') {
      final voiceId =
          ref.read(settingsProvider).value?.edgeVoiceId ?? defaultEdgeVoiceId;
      await _runConversion(
        book,
        synthesizer: EdgeSynthesizer(client: EdgeTtsClient(), voiceId: voiceId),
        extra: const {},
        rate: rate,
        preparing: 'Consultando el servicio de Edge…',
      );
      return;
    }
    if (model == null) {
      return;
    }
    if (!model.isValid) {
      setState(() => _error = 'El modelo Piper no está completo.');
      return;
    }
    final espeak = await ensurePiperEspeakData();
    await _runConversion(
      book,
      synthesizer: PiperSynthesizer(model: model, espeakDataPath: espeak),
      extra: {'tts_model': model.id, 'tts_model_path': model.directory},
      rate: rate,
      preparing: 'Preparando espeak-ng…',
    );
  }

  Future<void> _runConversion(
    Book book, {
    required ChapterSynthesizer synthesizer,
    required Map<String, String> extra,
    required double rate,
    required String preparing,
  }) async {
    setState(() {
      _converting = true;
      _cancelRequested = false;
      _progress = 0;
      _progressMessage = preparing;
      _error = null;
      _exportMessage = null;
    });
    try {
      final updated = await const TtsConversionService().convert(
        book,
        synthesizer: synthesizer,
        manifestExtra: extra,
        speed: 1 + rate / 100,
        isCancelled: () => _cancelRequested,
        onProgress: (progress) {
          if (mounted) {
            setState(() {
              _progress = progress.fraction;
              _progressMessage =
                  '${progress.message} (${progress.chapterIndex}/${progress.chapterTotal})';
            });
          }
        },
      );
      ref.invalidate(bookProvider(book.id));
      ref.invalidate(libraryProvider);
      if (mounted) {
        setState(() {
          _converting = false;
          _progress = 1;
          _progressMessage = 'Audio listo.';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Audio listo para ${updated.title}.')),
        );
      }
    } on TtsConversionCancelled {
      if (mounted) {
        setState(() {
          _converting = false;
          _progress = 0;
          _progressMessage =
              'Conversión detenida. Los capítulos terminados se conservaron.';
        });
        ref.invalidate(bookProvider(book.id));
        ref.invalidate(libraryProvider);
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _converting = false;
          _progress = 0;
          _error = 'No se pudo convertir: $error';
        });
      }
    }
  }

  Future<void> _exportM4b(Book book) async {
    setState(() {
      _exporting = true;
      _error = null;
      _exportMessage = null;
    });
    try {
      final result = await const M4bExporter().export(book);
      if (mounted) {
        setState(() {
          _exporting = false;
          _exportMessage = 'M4B exportado en ${result.path}';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _exporting = false;
          _error = 'No se pudo exportar el M4B: $error';
        });
      }
    }
  }

  Future<void> _exportM4bWithAmbience(Book book, AmbiencePreset preset) async {
    setState(() {
      _exporting = true;
      _error = null;
      _exportMessage = 'Generando ambiente…';
    });
    try {
      final library = const AmbienceLibrary();
      final globalBed = await library.ensurePreset(preset);
      final plan =
          _ambiencePlan ?? ref.read(ambiencePlanProvider(book.id)).value;
      final chapterBeds = <int, String>{};
      if (plan != null) {
        final cache = <String, String>{};
        for (final chapter in plan.chapters) {
          final presetId = chapter.presetId;
          if (presetId == null) {
            continue;
          }
          final path = cache[presetId] ??= (await library.ensurePreset(
            AmbiencePresetDetails.byId(presetId),
          )).path;
          chapterBeds[chapter.chapterIndex] = path;
        }
      }
      final result = await const M4bExporter().exportWithAmbience(
        book,
        bedPath: globalBed.path,
        chapterBeds: chapterBeds,
        onProgress: (chapter, total) {
          if (mounted) {
            setState(() {
              _exportMessage = 'Mezclando capítulo $chapter de $total…';
            });
          }
        },
      );
      if (mounted) {
        setState(() {
          _exporting = false;
          _exportMessage = 'M4B ambientado exportado en ${result.path}';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _exporting = false;
          _error = 'No se pudo exportar el M4B ambientado: $error';
        });
      }
    }
  }
}

class _ChapterAmbienceRow extends StatelessWidget {
  const _ChapterAmbienceRow({required this.chapter, required this.plan});

  final Chapter chapter;
  final AmbienceChapterPlan? plan;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final presetId = plan?.presetId;
    final preset = presetId == null
        ? null
        : AmbiencePresetDetails.byId(presetId);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 32,
            child: Text(
              chapter.index.toString().padLeft(2, '0'),
              style: Theme.of(context).textTheme.labelMedium,
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  chapter.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodyMedium
                      ?.copyWith(color: colors.ink),
                ),
                if (plan != null && plan!.reason.isNotEmpty)
                  Text(
                    '${plan!.reason} · ${(plan!.confidence * 100).round()}%',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          if (preset == null)
            Text('Sin ambiente', style: Theme.of(context).textTheme.labelSmall)
          else
            StatusPill(label: preset.label.toUpperCase(), color: colors.audio),
        ],
      ),
    );
  }
}

class _ModelDetails extends StatelessWidget {
  const _ModelDetails({required this.model});

  final PiperModel? model;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    if (model == null) {
      return const SizedBox.shrink();
    }
    return Wrap(
      spacing: 18,
      runSpacing: 8,
      children: [
        StatusPill(label: model!.language.toUpperCase(), color: colors.audio),
        Text(
          '${(model!.sampleRate / 1000).toStringAsFixed(1)} kHz · ${model!.numSpeakers} voz',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        Text(
          p.basename(model!.directory),
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

class _NoModels extends StatelessWidget {
  const _NoModels({
    required this.root,
    required this.onChoose,
    required this.onRefresh,
  });

  final String? root;
  final VoidCallback onChoose;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Todavía no hay una voz Piper instalada.',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 6),
        Text(
          'Descargá un modelo Piper (archivo .onnx + tokens.txt) y elegí la carpeta que lo contiene. '
          'La app lo detecta automáticamente.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        if (root != null) ...[
          const SizedBox(height: 8),
          Text(
            'Carpeta de modelos: $root',
            style: Theme.of(context).textTheme.bodySmall
                ?.copyWith(color: colors.inkFaint),
          ),
        ],
        const SizedBox(height: 14),
        Wrap(
          spacing: 8,
          children: [
            FilledButton.icon(
              onPressed: onChoose,
              icon: const Icon(Icons.folder_open, size: 18),
              label: const Text('Elegir carpeta'),
            ),
            OutlinedButton.icon(
              onPressed: () => showVoiceDownloadDialog(context),
              icon: const Icon(Icons.download, size: 18),
              label: const Text('Descargar voz'),
            ),
            OutlinedButton(
              onPressed: onRefresh,
              child: const Text('Volver a detectar'),
            ),
          ],
        ),
      ],
    );
  }
}
