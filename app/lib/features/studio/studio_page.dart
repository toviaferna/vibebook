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
import '../../core/design/tokens.dart';
import '../../data/ambience/ambience_generator.dart';
import '../../data/demo_conversion.dart';
import '../../data/m4b_exporter.dart';
import '../../data/tts/piper_models.dart';
import '../../data/tts/tts_chapter_worker.dart';
import '../../data/tts/tts_conversion.dart';
import '../../data/tts/wav_writer.dart';
import '../../domain/ambience.dart';
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
  final _previewPlayer = AudioPlayer();
  bool _converting = false;
  bool _cancelRequested = false;
  bool _exporting = false;
  bool _previewing = false;
  double _progress = 0;
  String? _progressMessage;
  String? _error;
  String? _exportMessage;
  String? _previewMessage;

  @override
  void dispose() {
    _previewController.dispose();
    _previewPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final book = ref.watch(bookProvider(widget.bookId));
    return book.when(
      data: (value) {
        if (value == null) {
          return Scaffold(
            appBar: AppBar(leading: BackButton(onPressed: () => context.go('/'))),
            body: const ErrorView(message: 'No encontré este libro.'),
          );
        }
        return _buildStudio(value);
      },
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
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
    final rate = settings?.piperRate ?? -10;
    final modelsRoot = ref.watch(modelsRootProvider);
    return PageScaffold(
      eyebrow: 'Estudio',
      title: book.title,
      subtitle: 'Voz local, sin cuenta ni nube. La síntesis corre en este equipo.',
      actions: [
        IconButton(
          tooltip: 'Volver al libro',
          onPressed: () => context.push('/books/${book.id}'),
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
              child: Row(
                children: [
                  Icon(Icons.check_circle_outline, color: colors.brass),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Este libro ya tiene audio. Podés volver a convertirlo o abrir el lector.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                  OutlinedButton(
                    onPressed: () => context.push('/books/${book.id}/read'),
                    child: const Text('Abrir lector'),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 24),
          _Panel(
            title: 'Voz local',
            child: models.when(
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
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: InputDecorator(
                            decoration: const InputDecoration(labelText: 'Modelo Piper'),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<String>(
                                isExpanded: true,
                                value: selected?.id ?? items.first.id,
                                items: [
                                  for (final model in items)
                                    DropdownMenuItem(
                                      value: model.id,
                                      child: Text('${model.name} · ${model.language}'),
                                    ),
                                ],
                                onChanged: _converting
                                    ? null
                                    : (value) {
                                        if (value != null) {
                                          ref
                                              .read(settingsProvider.notifier)
                                              .selectPiperModel(value);
                                        }
                                      },
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        OutlinedButton(
                          onPressed: _converting ? null : _chooseModelsFolder,
                          child: const Text('Carpeta'),
                        ),
                        const SizedBox(width: 8),
                        OutlinedButton(
                          onPressed: _converting ? null : () => showVoiceDownloadDialog(context),
                          child: const Text('Agregar voz'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    _ModelDetails(model: selected),
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
                        onPressed: _converting || _previewing || selected == null
                            ? null
                            : () => _preview(selected, rate),
                        icon: Icon(_previewing ? Icons.hourglass_top : Icons.play_arrow, size: 18),
                        label: Text(_previewing ? 'Generando muestra…' : 'Escuchar muestra'),
                      ),
                    ),
                    if (_previewMessage != null) ...[
                      const SizedBox(height: 8),
                      Text(_previewMessage!, style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ],
                );
              },
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (error, stackTrace) => Text('No se pudieron leer los modelos: $error'),
            ),
          ),
          const SizedBox(height: 18),
          _Panel(
            title: 'Lectura y salida',
            child: Column(
              children: [
                Row(
                  children: [
                    Text('Velocidad', style: Theme.of(context).textTheme.titleSmall),
                    Expanded(
                      child: Slider(
                        value: rate,
                        min: -30,
                        max: 30,
                        divisions: 12,
                        label: '${rate.round()}%',
                        onChanged: _converting
                            ? null
                            : (value) => ref.read(settingsProvider.notifier).setPiperRate(value),
                      ),
                    ),
                    Text('${rate.round()}%'),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'La velocidad se guarda y se aplica a todas las conversiones.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          _Panel(
            title: 'Ambiente',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Mezcla un paisaje sonoro sintetizado debajo de la voz al exportar.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                    const SizedBox(width: 12),
                    DropdownButton<String>(
                      value: settings?.ambiencePreset ?? 'rain',
                      underline: const SizedBox.shrink(),
                      items: [
                        for (final preset in AmbiencePreset.values)
                          DropdownMenuItem(value: preset.id, child: Text(preset.label)),
                      ],
                      onChanged: _converting || _exporting
                          ? null
                          : (preset) {
                              if (preset != null) {
                                ref.read(settingsProvider.notifier).updateAmbience(preset: preset);
                              }
                            },
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: _exporting || !book.hasAudio
                        ? null
                        : () => _exportM4bWithAmbience(
                              book,
                              AmbiencePresetDetails.byId(settings?.ambiencePreset),
                            ),
                    icon: const Icon(Icons.forest, size: 18),
                    label: Text(_exporting ? 'Exportando…' : 'Exportar M4B ambientado'),
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
                border: Border(left: BorderSide(color: colors.danger, width: 2)),
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
                onPressed: _converting || selected == null ? null : () => _convert(book, selected, rate),
                icon: const Icon(Icons.graphic_eq, size: 18),
                label: Text(_converting ? 'Convirtiendo…' : 'Convertir con Piper'),
              ),
              if (_converting)
                OutlinedButton.icon(
                  onPressed: () => setState(() => _cancelRequested = true),
                  icon: const Icon(Icons.stop, size: 18),
                  label: const Text('Detener al final del capítulo'),
                ),
              OutlinedButton.icon(
                onPressed: _exporting || !book.hasAudio ? null : () => _exportM4b(book),
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
              child: Text(_exportMessage!, style: Theme.of(context).textTheme.bodySmall),
            ),
          ],
          const SizedBox(height: 24),
          Text(
            'La voz se sintetiza en un isolate aparte: la interfaz sigue respondiendo. '
            'Los timings de karaoke se estiman a partir de la duración real de cada segmento.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 30),
          ExpansionTile(
            tilePadding: EdgeInsets.zero,
            childrenPadding: EdgeInsets.zero,
            title: Text('Avanzado', style: Theme.of(context).textTheme.titleSmall),
            children: [
              _DemoFallback(book: book, onDone: _refreshBook),
            ],
          ),
        ],
      ),
    );
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
      final sampleRate = (result['sample_rate'] as num?)?.toInt() ?? model.sampleRate;
      if (samples.isEmpty) {
        throw StateError('La voz no generó audio.');
      }
      final temp = await getTemporaryDirectory();
      final file = File(p.join(temp.path, 'vibebook-preview.wav'));
      await file.writeAsBytes(const WavWriter().encode(samples, sampleRate), flush: true);
      await _previewPlayer.stop();
      await _previewPlayer.play(DeviceFileSource(file.path));
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

  Future<void> _convert(Book book, PiperModel model, double rate) async {
    setState(() {
      _converting = true;
      _cancelRequested = false;
      _progress = 0;
      _progressMessage = 'Preparando espeak-ng…';
      _error = null;
      _exportMessage = null;
    });
    try {
      final espeak = await ensurePiperEspeakData();
      final updated = await const TtsConversionService().convert(
        book,
        model: model,
        espeakDataPath: espeak,
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
          _progressMessage = 'Conversión detenida. Los capítulos terminados se conservaron.';
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
      final bed = await const AmbienceGenerator().ensurePreset(preset);
      final result = await const M4bExporter().exportWithAmbience(
        book,
        bedPath: bed.path,
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

  void _refreshBook() {
    ref.invalidate(bookProvider(widget.bookId));
    ref.invalidate(libraryProvider);
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
  const _NoModels({required this.root, required this.onChoose, required this.onRefresh});

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
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: colors.inkFaint),
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

class _DemoFallback extends ConsumerStatefulWidget {
  const _DemoFallback({required this.book, required this.onDone});

  final Book book;
  final VoidCallback onDone;

  @override
  ConsumerState<_DemoFallback> createState() => _DemoFallbackState();
}

class _DemoFallbackState extends ConsumerState<_DemoFallback> {
  bool _working = false;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        children: [
          Expanded(
            child: Text(
              'Generar silencio de prueba reemplaza el audio actual. Usalo solo para validar la interfaz.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
          const SizedBox(width: 12),
          OutlinedButton(
            onPressed: _working ? null : _run,
            child: Text(_working ? 'Generando…' : 'Audio de prueba'),
          ),
        ],
      ),
    );
  }

  Future<void> _run() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Reemplazar el audio?'),
        content: const Text('Se generará silencio y se perderá el audio actual de este libro.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Reemplazar')),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }
    setState(() => _working = true);
    try {
      await const DemoConversionService().convert(
        widget.book,
        engine: 'demo',
        voice: 'demo',
        rate: '0%',
      );
      widget.onDone();
    } finally {
      if (mounted) {
        setState(() => _working = false);
      }
    }
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border.all(color: colors.line),
        borderRadius: BibliotecaRadii.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SectionLabel(title),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}
