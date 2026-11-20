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
import '../../data/tts/cloud/azure_tts.dart';
import '../../data/tts/cloud/cloud_synthesizer.dart';
import '../../data/tts/cloud/cloud_tts.dart';
import '../../data/tts/cloud/elevenlabs_tts.dart';
import '../../data/tts/cloud/gemini_tts.dart';
import '../../data/tts/edge/edge_client.dart';
import '../../data/tts/edge/edge_synthesizer.dart';
import '../../data/tts/edge/edge_voices.dart';
import '../../data/tts/piper_models.dart';
import '../../data/tts/plugins/vep_client.dart';
import '../../data/tts/tts_chapter_worker.dart';
import '../../data/tts/tts_engines.dart';
import '../../data/tts/wav_writer.dart';
import '../../domain/ambience.dart';
import '../../domain/ambience_plan.dart';
import '../../domain/jobs.dart';
import '../../domain/models.dart';
import '../../domain/providers.dart';
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
  bool _exporting = false;
  bool _previewing = false;
  String? _previewingVoiceId;
  bool _analyzingAmbience = false;
  AmbiencePlan? _ambiencePlan;
  double _progress = 0;
  String? _progressMessage;
  String? _error;
  String? _exportMessage;
  String? _previewMessage;
  ProviderSubscription<JobState>? _jobSubscription;

  @override
  void initState() {
    super.initState();
    _jobSubscription = ref.listenManual<JobState>(jobControllerProvider, (
      previous,
      next,
    ) {
      final job = next.latestFor(widget.bookId);
      if (!mounted) {
        return;
      }
      setState(() {
        _converting = job?.isRunning == true;
        if (job != null) {
          _progress = job.fraction;
          _progressMessage = job.message ?? _progressMessage;
          if (job.status == 'failed') {
            _error = job.error;
          }
        }
      });
    });
  }

  @override
  void dispose() {
    _jobSubscription?.close();
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
    final plugins = ref.watch(vepPluginsProvider).value ?? const <VepPlugin>[];
    final plugin = _pluginFor(engine, plugins);
    final spec = _engineSpec(engine, plugins);
    final providerStatuses =
        ref.watch(providerStatusesProvider).value ?? const <ProviderStatus>[];
    final cloudReady =
        plugin != null ||
        !spec.requiresKey ||
        providerStatuses.any(
          (status) => status.id == engine && status.configured,
        );
    final dynamicEngine = _isCloud(engine) || plugin != null;
    final rate = settings?.rateForEngine(engine) ?? -10;
    final voice = _voiceForEngine(engine, settings, plugins);
    final job = ref.watch(jobControllerProvider).latestFor(book.id);
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
                  options: _engineOptions(
                    providerStatuses,
                    hasPiper: models.value?.isNotEmpty == true,
                    plugins: plugins,
                  ),
                  onChanged: _converting
                      ? null
                      : (value) {
                          final target = _pluginFor(value, plugins);
                          ref
                              .read(settingsProvider.notifier)
                              .updateTtsEngine(
                                engine: value,
                                voice: target?.voices.isNotEmpty == true
                                    ? target!.voices.first.id
                                    : null,
                              );
                        },
                ),
                const SizedBox(height: 14),
                if (engine == 'edge') ...[
                  _EdgeVoicePicker(
                    voices: edgeVoices,
                    selected: settings?.edgeVoiceId ?? defaultEdgeVoiceId,
                    favorites: settings?.edgeFavorites ?? const [],
                    previewing: _previewingVoiceId,
                    bookLanguage: book.language,
                    onSelect: _converting
                        ? null
                        : (voiceId) => ref
                              .read(settingsProvider.notifier)
                              .updateTtsEngine(edgeVoice: voiceId),
                    onToggleFavorite: _converting
                        ? null
                        : (voiceId) {
                            final current =
                                settings?.edgeFavorites ?? const <String>[];
                            final next = current.contains(voiceId)
                                ? current
                                      .where((id) => id != voiceId)
                                      .toList(growable: false)
                                : [...current, voiceId];
                            ref
                                .read(settingsProvider.notifier)
                                .updateTtsEngine(edgeFavorites: next);
                          },
                    onPreview: _converting || _previewing
                        ? null
                        : (voiceId) => _previewEdge(voiceId),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final preset in _speedPresets)
                        ChoiceChip(
                          label: Text('${preset.label} (${preset.rate}%)'),
                          selected:
                              ((settings?.edgeRate ?? 0) - preset.rate).abs() <
                              0.01,
                          onSelected: _converting
                              ? null
                              : (_) => ref
                                    .read(settingsProvider.notifier)
                                    .updateTtsEngine(edgeRate: preset.rate),
                        ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Online y no oficial: el texto se envía a Microsoft y el '
                    'servicio puede fallar, limitarse o cambiar sin aviso. No '
                    'sirve sin conexión.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ] else if (engine == 'piper') ...[
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
                ] else if (dynamicEngine) ...[
                  if (!cloudReady)
                    _CloudMissing(
                      engine: engine,
                      onOpenSettings: () => context.push('/settings'),
                    )
                  else ...[
                    _CloudVoicePicker(
                      voices: _voicesFor(engine, plugins),
                      selected: voice,
                      favorites: settings?.voiceFavorites ?? const [],
                      previewing: _previewingVoiceId,
                      bookLanguage: book.language,
                      onSelect: _converting
                          ? null
                          : (voiceId) => ref
                                .read(settingsProvider.notifier)
                                .updateTtsEngine(voice: voiceId),
                      onToggleFavorite: _converting
                          ? null
                          : (voiceId) {
                              final current =
                                  settings?.voiceFavorites ?? const <String>[];
                              final next = current.contains(voiceId)
                                  ? current
                                        .where((id) => id != voiceId)
                                        .toList(growable: false)
                                  : [...current, voiceId];
                              ref
                                  .read(settingsProvider.notifier)
                                  .updateTtsEngine(favorites: next);
                            },
                      onPreview: _converting || _previewing
                          ? null
                          : (voiceId) => _previewCloud(engine, voiceId),
                    ),
                    if (spec.supportsStyles) ...[
                      const SizedBox(height: 12),
                      Text(
                        'Estilo de lectura',
                        style: Theme.of(context).textTheme.labelMedium,
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final style in _stylesFor(engine, plugins))
                            ChoiceChip(
                              label: Text(_styleLabel(style)),
                              selected:
                                  (settings?.ttsStyle ?? 'neutral') == style,
                              onSelected: _converting
                                  ? null
                                  : (_) => ref
                                        .read(settingsProvider.notifier)
                                        .updateTtsEngine(style: style),
                            ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final preset in _speedPresets)
                          ChoiceChip(
                            label: Text('${preset.label} (${preset.rate}%)'),
                            selected: (rate - preset.rate).abs() < 0.01,
                            onSelected: _converting
                                ? null
                                : (_) => ref
                                      .read(settingsProvider.notifier)
                                      .updateTtsEngine(rate: preset.rate),
                          ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Online: el texto se envía al proveedor y el servicio '
                      'puede fallar, limitarse o cambiar sin aviso. No sirve '
                      'sin conexión.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ] else ...[
                  _UnavailableEngine(spec: spec),
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
                          : (value) => ref
                                .read(settingsProvider.notifier)
                                .updateTtsEngine(rate: value),
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
          if (_converting || (job != null && job.isTerminal)) ...[
            const SizedBox(height: 18),
            if (_converting)
              LinearProgressIndicator(value: _progress == 0 ? null : _progress),
            if (_converting) ...[
              const SizedBox(height: 8),
              Text(_progressMessage ?? 'Preparando la síntesis…'),
            ],
            if (!_converting && job != null) ...[
              Text(
                job.message ??
                    (job.status == 'completed'
                        ? 'Audio listo.'
                        : 'La conversión se detuvo.'),
              ),
              if (job.error != null) ...[
                const SizedBox(height: 4),
                Text(job.error!, style: Theme.of(context).textTheme.bodySmall),
              ],
              if (job.canResume) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => _convertCurrent(
                    book,
                    job.engine,
                    selected,
                    job.rate,
                    resume: true,
                  ),
                  icon: const Icon(Icons.play_arrow, size: 18),
                  label: const Text('Reanudar conversión'),
                ),
              ],
            ],
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
                        !spec.implemented ||
                        !cloudReady ||
                        (engine == 'piper' && selected == null)
                    ? null
                    : () => _convertCurrent(book, engine, selected, rate),
                icon: const Icon(Icons.graphic_eq, size: 18),
                label: Text(
                  _converting
                      ? 'Convirtiendo…'
                      : 'Convertir con ${_engineShortName(engine, plugins)}',
                ),
              ),
              if (_converting)
                OutlinedButton.icon(
                  onPressed: () {
                    ref.read(jobControllerProvider.notifier).cancel();
                  },
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

  static bool _isCloud(String engine) {
    return engine == 'azure' || engine == 'gemini' || engine == 'elevenlabs';
  }

  VepPlugin? _pluginFor(String engine, List<VepPlugin> plugins) {
    for (final plugin in plugins) {
      if (plugin.id == engine) {
        return plugin;
      }
    }
    return null;
  }

  TtsEngineSpec _engineSpec(String engine, List<VepPlugin> plugins) {
    final plugin = _pluginFor(engine, plugins);
    if (plugin != null) {
      return TtsEngineSpec(
        id: plugin.id,
        label: plugin.name,
        description: '${plugin.license} · ${plugin.voices.length} voces · VEP',
        requiresNetwork: true,
        requiresKey: false,
        supportsStyles:
            plugin.styles.isNotEmpty ||
            plugin.voices.any((voice) => voice.styles.isNotEmpty),
        timing: plugin.timings,
        audioSuffix: '.wav',
        license: plugin.license,
        sourceUrl: plugin.source,
        maxChars: plugin.maxChars,
      );
    }
    return ttsEngine(engine);
  }

  String _voiceForEngine(
    String engine,
    AppSettings? settings,
    List<VepPlugin> plugins,
  ) {
    final plugin = _pluginFor(engine, plugins);
    if (plugin != null && plugin.voices.isNotEmpty) {
      final stored = settings?.voiceForEngine(engine);
      if (plugin.voices.any((voice) => voice.id == stored)) {
        return stored!;
      }
      return plugin.voices.first.id;
    }
    return settings?.voiceForEngine(engine) ?? defaultTtsVoice(engine);
  }

  List<TtsVoice> _voicesFor(String engine, List<VepPlugin> plugins) {
    final plugin = _pluginFor(engine, plugins);
    if (plugin == null) {
      return ttsVoicesFor(engine);
    }
    return [
      for (final voice in plugin.voices)
        TtsVoice(
          id: voice.id,
          name: voice.id,
          locale: voice.locale,
          gender: voice.gender,
          engine: plugin.id,
          detail: '${voice.locale} · ${voice.gender} · ${plugin.name}',
          styles: voice.styles,
        ),
    ];
  }

  List<BibliotecaSelectOption<String>> _engineOptions(
    List<ProviderStatus> statuses, {
    required bool hasPiper,
    List<VepPlugin> plugins = const [],
  }) {
    return [
      for (final engine in ttsEngines)
        BibliotecaSelectOption(
          value: engine.id,
          label: engine.label,
          description: _engineDescription(engine, statuses, hasPiper),
        ),
      for (final plugin in plugins)
        BibliotecaSelectOption(
          value: plugin.id,
          label: plugin.name,
          description:
              'Plugin VEP · ${plugin.license} · ${plugin.voices.length} voces',
        ),
    ];
  }

  String _engineDescription(
    TtsEngineSpec engine,
    List<ProviderStatus> statuses,
    bool hasPiper,
  ) {
    if (!engine.implemented) {
      return engine.description;
    }
    if (engine.id == 'piper') {
      return hasPiper
          ? 'Modelos locales detectados.'
          : 'No hay modelos instalados todavía.';
    }
    if (engine.id == 'edge') {
      return 'Online, sin clave.';
    }
    if (engine.requiresKey) {
      var configured = false;
      for (final status in statuses) {
        if (status.id == engine.id) {
          configured = status.configured;
          break;
        }
      }
      return configured
          ? 'Clave configurada.'
          : 'Falta configurar la clave en Ajustes.';
    }
    return engine.description;
  }

  List<String> _stylesFor(String engine, [List<VepPlugin> plugins = const []]) {
    final plugin = _pluginFor(engine, plugins);
    if (plugin != null) {
      final styles = <String>{'neutral', ...plugin.styles};
      for (final voice in plugin.voices) {
        styles.addAll(voice.styles);
      }
      return styles.toList(growable: false);
    }
    if (engine == 'azure') {
      return const [
        'neutral',
        'chat',
        'cheerful',
        'excited',
        'sad',
        'whispering',
      ];
    }
    return cloudStyles;
  }

  String _styleLabel(String style) {
    return switch (style) {
      'neutral' => 'Claro',
      'chat' => 'Cálido',
      'cheerful' => 'Alegre',
      'excited' => 'Emocionado',
      'sad' => 'Melancólico',
      'whispering' => 'Susurro',
      'epic' => 'Épico',
      'suspense' => 'Suspenso',
      _ => style,
    };
  }

  String _engineShortName(String engine, [List<VepPlugin> plugins = const []]) {
    final plugin = _pluginFor(engine, plugins);
    if (plugin != null) {
      return plugin.name;
    }
    return switch (engine) {
      'piper' => 'Piper',
      'edge' => 'Edge',
      'azure' => 'Azure',
      'gemini' => 'Gemini',
      'elevenlabs' => 'ElevenLabs',
      'kokoro' => 'Kokoro',
      'espeak' => 'eSpeak',
      _ => engine,
    };
  }

  Future<CloudTtsClient?> _cloudClient(String engine) async {
    final plugins = ref.read(vepPluginsProvider).value ?? const <VepPlugin>[];
    final plugin = _pluginFor(engine, plugins);
    if (plugin != null) {
      final token = await ref
          .read(vepPluginRepositoryProvider)
          .token(plugin.id);
      return VepTtsClient(
        client: ref.read(vepClientProvider),
        url: plugin.url,
        token: token,
      );
    }
    final store = ref.read(providerKeyStoreProvider);
    final key = await store.key(engine);
    if (key == null) {
      return null;
    }
    return switch (engine) {
      'azure' => AzureTtsClient(
        apiKey: key,
        region: await store.region(engine) ?? '',
      ),
      'gemini' => GeminiTtsClient(apiKey: key),
      'elevenlabs' => ElevenLabsTtsClient(apiKey: key),
      _ => null,
    };
  }

  Future<void> _previewCloud(String engine, String voiceId) async {
    final text = _previewController.text.trim();
    if (text.isEmpty) {
      return;
    }
    final plugins = ref.read(vepPluginsProvider).value ?? const <VepPlugin>[];
    setState(() {
      _previewing = true;
      _previewingVoiceId = voiceId;
      _previewMessage = null;
      _error = null;
    });
    try {
      final client = await _cloudClient(engine);
      if (client == null) {
        throw CloudTtsException(
          'Falta la clave de ${_engineShortName(engine, plugins)}. Configurala en '
          'Ajustes → Proveedores en la nube.',
        );
      }
      final style = ref.read(settingsProvider).value?.ttsStyle ?? 'neutral';
      final audio = await client.synthesize(
        text: text,
        voice: voiceId,
        style: style,
      );
      final temp = await getTemporaryDirectory();
      final file = File(
        p.join(temp.path, 'vibebook-cloud-preview.${audio.extension}'),
      );
      await file.writeAsBytes(audio.bytes, flush: true);
      final player = _previewPlayer ??= AudioPlayer();
      await player.stop();
      await player.play(DeviceFileSource(file.path));
      if (mounted) {
        setState(() {
          _previewing = false;
          _previewingVoiceId = null;
          _previewMessage =
              'Muestra de ${ttsVoiceById(voiceId)?.name ?? voiceId} lista · '
              '${(audio.bytes.length / 1024).round()} KB · '
              '${_engineShortName(engine, plugins)}';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _previewing = false;
          _previewingVoiceId = null;
          _error =
              'No se pudo consultar ${_engineShortName(engine, plugins)}: $error';
        });
      }
    }
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
    final engine = settings?.ttsEngine ?? 'piper';
    final plugins = ref.read(vepPluginsProvider).value ?? const <VepPlugin>[];
    if (engine == 'edge') {
      return _previewEdge(settings?.edgeVoiceId ?? defaultEdgeVoiceId);
    }
    if (_isCloud(engine) || _pluginFor(engine, plugins) != null) {
      return _previewCloud(engine, _voiceForEngine(engine, settings, plugins));
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
      _previewingVoiceId = voiceId;
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
        final voice = edgeVoiceById(voiceId);
        setState(() {
          _previewing = false;
          _previewingVoiceId = null;
          _previewMessage =
              'Muestra de ${voice?.name ?? voiceId} lista · '
              '${(data.length / 1024).round()} KB · online';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _previewing = false;
          _previewingVoiceId = null;
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
    double rate, {
    bool resume = false,
  }) async {
    final plugins = ref.read(vepPluginsProvider).value ?? const <VepPlugin>[];
    if (engine == 'edge') {
      final voiceId =
          ref.read(settingsProvider).value?.edgeVoiceId ?? defaultEdgeVoiceId;
      await _runConversion(
        book,
        synthesizer: EdgeSynthesizer(client: EdgeTtsClient(), voiceId: voiceId),
        extra: const {},
        rate: rate,
        resume: resume,
        preparing: 'Consultando el servicio de Edge…',
      );
      return;
    }
    if (_isCloud(engine) || _pluginFor(engine, plugins) != null) {
      final client = await _cloudClient(engine);
      if (client == null) {
        setState(() {
          _error =
              'Falta la clave de ${_engineShortName(engine, plugins)}. '
              'Configurala en Ajustes → Proveedores en la nube.';
        });
        return;
      }
      final settings = ref.read(settingsProvider).value;
      final voice = _voiceForEngine(engine, settings, plugins);
      final style = settings?.ttsStyle ?? 'neutral';
      await _runConversion(
        book,
        synthesizer: CloudChapterSynthesizer(
          client: client,
          voice: voice,
          engine: engine,
          style: style,
        ),
        extra: {'tts_style': style},
        rate: rate,
        resume: resume,
        preparing: 'Preparando ${_engineShortName(engine, plugins)}…',
      );
      return;
    }
    if (engine != 'piper') {
      setState(() {
        _error =
            '${_engineShortName(engine, plugins)} no está disponible en esta versión.';
      });
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
      resume: resume,
      preparing: 'Preparando espeak-ng…',
    );
  }

  Future<void> _runConversion(
    Book book, {
    required ChapterSynthesizer synthesizer,
    required Map<String, String> extra,
    required double rate,
    required String preparing,
    bool resume = false,
  }) async {
    setState(() {
      _converting = true;
      _progress = 0;
      _progressMessage = preparing;
      _error = null;
      _exportMessage = null;
    });
    try {
      final job = await ref
          .read(jobControllerProvider.notifier)
          .start(
            book: book,
            synthesizer: synthesizer,
            engine: synthesizer.engineId,
            voice: synthesizer.voiceId,
            style: ref.read(settingsProvider).value?.ttsStyle ?? 'neutral',
            rate: rate,
            extra: extra,
            resume: resume,
          );
      if (!mounted) {
        return;
      }
      setState(() {
        _converting = false;
        _progress = job?.fraction ?? 0;
        _progressMessage = job?.message ?? preparing;
        if (job?.status == 'failed') {
          _error = job?.error;
        }
      });
      if (job?.status == 'completed') {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Audio listo para ${book.title}.')),
        );
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

class _SpeedPreset {
  const _SpeedPreset({required this.label, required this.rate});

  final String label;
  final double rate;
}

const _speedPresets = [
  _SpeedPreset(label: 'Natural', rate: -5),
  _SpeedPreset(label: 'Pausado', rate: -15),
  _SpeedPreset(label: 'Lento', rate: -25),
  _SpeedPreset(label: 'Muy lento', rate: -35),
];

/// Grid de voces Edge con favoritas, preview por voz y aviso de idioma,
/// como el picker del Studio Tauri.
class _EdgeVoicePicker extends StatelessWidget {
  const _EdgeVoicePicker({
    required this.voices,
    required this.selected,
    required this.favorites,
    required this.previewing,
    required this.bookLanguage,
    this.onSelect,
    this.onToggleFavorite,
    this.onPreview,
  });

  final List<EdgeVoice> voices;
  final String selected;
  final List<String> favorites;
  final String? previewing;
  final String bookLanguage;
  final ValueChanged<String>? onSelect;
  final ValueChanged<String>? onToggleFavorite;
  final ValueChanged<String>? onPreview;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final ordered = [...voices]
      ..sort((left, right) {
        final leftFavorite = favorites.contains(left.id) ? 0 : 1;
        final rightFavorite = favorites.contains(right.id) ? 0 : 1;
        final byFavorite = leftFavorite.compareTo(rightFavorite);
        if (byFavorite != 0) {
          return byFavorite;
        }
        return left.id.compareTo(right.id);
      });
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth < 560 ? 2 : 3;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final voice in ordered)
              _voiceCard(context, voice, colors, columns),
          ],
        );
      },
    );
  }

  Widget _voiceCard(
    BuildContext context,
    EdgeVoice voice,
    BibliotecaColors colors,
    int columns,
  ) {
    final active = voice.id == selected;
    final favorite = favorites.contains(voice.id);
    final previewingThis = previewing == voice.id;
    final width = (MediaQuery.sizeOf(context).width - 120) / columns - 10;
    final voiceLocale = voice.locale.split('-').last.toLowerCase();
    final mismatch =
        bookLanguage.isNotEmpty &&
        voiceLocale.isNotEmpty &&
        !voiceLocale.startsWith(bookLanguage.split('-').first.toLowerCase());
    return SizedBox(
      width: width.clamp(160.0, 320.0),
      child: Material(
        color: active ? colors.accentSoft : colors.surface,
        borderRadius: BibliotecaRadii.md,
        child: InkWell(
          borderRadius: BibliotecaRadii.md,
          onTap: onSelect == null ? null : () => onSelect!(voice.id),
          child: Container(
            padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
            decoration: BoxDecoration(
              borderRadius: BibliotecaRadii.md,
              border: Border.all(
                color: active ? colors.accent : colors.line,
                width: active ? 2 : 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        voice.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: active ? colors.ink : colors.inkSoft,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    if (onToggleFavorite != null)
                      IconButton(
                        tooltip: favorite
                            ? 'Quitar de favoritas'
                            : 'Marcar como favorita',
                        visualDensity: VisualDensity.compact,
                        onPressed: () => onToggleFavorite!(voice.id),
                        icon: Icon(
                          favorite ? Icons.star : Icons.star_border,
                          size: 18,
                          color: favorite ? colors.brass : colors.inkFaint,
                        ),
                      ),
                    if (onPreview != null)
                      IconButton(
                        tooltip: 'Escuchar ${voice.name}',
                        visualDensity: VisualDensity.compact,
                        onPressed: previewingThis
                            ? null
                            : () => onPreview!(voice.id),
                        icon: previewingThis
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : Icon(
                                Icons.play_arrow,
                                size: 20,
                                color: colors.accent,
                              ),
                      ),
                  ],
                ),
                Text(
                  '${voice.locale.toUpperCase()} � ${voice.gender}',
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                if (mismatch) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Idioma del libro: $bookLanguage',
                    style: Theme.of(context).textTheme.labelSmall
                        ?.copyWith(color: colors.warning),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CloudVoicePicker extends StatelessWidget {
  const _CloudVoicePicker({
    required this.voices,
    required this.selected,
    required this.favorites,
    required this.previewing,
    required this.bookLanguage,
    this.onSelect,
    this.onToggleFavorite,
    this.onPreview,
  });

  final List<TtsVoice> voices;
  final String selected;
  final List<String> favorites;
  final String? previewing;
  final String bookLanguage;
  final ValueChanged<String>? onSelect;
  final ValueChanged<String>? onToggleFavorite;
  final ValueChanged<String>? onPreview;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final ordered = [...voices]
      ..sort((left, right) {
        final leftFavorite = favorites.contains(left.id) ? 0 : 1;
        final rightFavorite = favorites.contains(right.id) ? 0 : 1;
        final byFavorite = leftFavorite.compareTo(rightFavorite);
        if (byFavorite != 0) {
          return byFavorite;
        }
        return left.name.compareTo(right.name);
      });
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth < 560 ? 2 : 3;
        return Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final voice in ordered)
              _voiceCard(context, voice, colors, columns),
          ],
        );
      },
    );
  }

  Widget _voiceCard(
    BuildContext context,
    TtsVoice voice,
    BibliotecaColors colors,
    int columns,
  ) {
    final active = voice.id == selected;
    final favorite = favorites.contains(voice.id);
    final previewingThis = previewing == voice.id;
    final width = (MediaQuery.sizeOf(context).width - 120) / columns - 10;
    final mismatch = voiceLanguageMismatch(voice, bookLanguage);
    return SizedBox(
      width: width.clamp(160.0, 320.0),
      child: Material(
        color: active ? colors.accentSoft : colors.surface,
        borderRadius: BibliotecaRadii.md,
        child: InkWell(
          borderRadius: BibliotecaRadii.md,
          onTap: onSelect == null ? null : () => onSelect!(voice.id),
          child: Container(
            padding: const EdgeInsets.fromLTRB(12, 10, 6, 10),
            decoration: BoxDecoration(
              borderRadius: BibliotecaRadii.md,
              border: Border.all(
                color: active ? colors.accent : colors.line,
                width: active ? 2 : 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        voice.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: active ? colors.ink : colors.inkSoft,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    if (onToggleFavorite != null)
                      IconButton(
                        tooltip: favorite
                            ? 'Quitar de favoritas'
                            : 'Marcar como favorita',
                        visualDensity: VisualDensity.compact,
                        onPressed: () => onToggleFavorite!(voice.id),
                        icon: Icon(
                          favorite ? Icons.star : Icons.star_border,
                          size: 18,
                          color: favorite ? colors.brass : colors.inkFaint,
                        ),
                      ),
                    if (onPreview != null)
                      IconButton(
                        tooltip: 'Escuchar ${voice.name}',
                        visualDensity: VisualDensity.compact,
                        onPressed: previewingThis
                            ? null
                            : () => onPreview!(voice.id),
                        icon: previewingThis
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : Icon(
                                Icons.play_arrow,
                                size: 20,
                                color: colors.accent,
                              ),
                      ),
                  ],
                ),
                Text(
                  voice.detail,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                if (mismatch) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Idioma del libro: $bookLanguage',
                    style: Theme.of(context).textTheme.labelSmall
                        ?.copyWith(color: colors.warning),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CloudMissing extends StatelessWidget {
  const _CloudMissing({required this.engine, required this.onOpenSettings});

  final String engine;
  final VoidCallback onOpenSettings;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final name = switch (engine) {
      'azure' => 'Azure Speech',
      'gemini' => 'Gemini TTS',
      'elevenlabs' => 'ElevenLabs',
      _ => engine,
    };
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BibliotecaRadii.md,
        border: Border(left: BorderSide(color: colors.warning, width: 2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.key_off_outlined, color: colors.warning),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$name todav�a no tiene una clave configurada.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  'Peg� la clave en Ajustes ? Proveedores en la nube. '
                  'La clave se guarda en este equipo y no se muestra de nuevo.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: onOpenSettings,
                  icon: const Icon(Icons.settings_outlined, size: 18),
                  label: const Text('Abrir Ajustes'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _UnavailableEngine extends StatelessWidget {
  const _UnavailableEngine({required this.spec});

  final TtsEngineSpec spec;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BibliotecaRadii.md,
        border: Border(left: BorderSide(color: colors.brass, width: 2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, color: colors.brass),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${spec.label} todav�a no est� disponible en esta versi�n.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  '${spec.description} Mientras tanto, us� Piper, Edge o un '
                  'motor cloud configurado. La limitaci�n es visible a '
                  'prop�sito: no se degrada en silencio.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
