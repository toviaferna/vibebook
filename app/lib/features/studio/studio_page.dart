import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/tokens.dart';
import '../../data/demo_conversion.dart';
import '../../domain/models.dart';

class StudioPage extends ConsumerStatefulWidget {
  const StudioPage({super.key, required this.bookId});

  final String bookId;

  @override
  ConsumerState<StudioPage> createState() => _StudioPageState();
}

class _StudioPageState extends ConsumerState<StudioPage> {
  String _engine = 'demo';
  String _voice = 'es-MX-JorgeNeural';
  double _rate = -10;
  bool _converting = false;
  int _completed = 0;
  int _total = 0;
  String? _error;

  static const _engines = {
    'demo': 'Demo local (silencio)',
    'piper': 'Piper local',
    'edge': 'Edge TTS',
    'gemini': 'Gemini TTS',
    'elevenlabs': 'ElevenLabs',
    'azure': 'Azure Speech',
  };

  static const _voices = {
    'demo': 'es-MX-JorgeNeural',
    'piper': 'es_MX-ald-medium',
    'edge': 'es-MX-JorgeNeural',
    'gemini': 'Kore',
    'elevenlabs': 'pNInz6obpgDQGcFmaJgB',
    'azure': 'es-MX-JorgeNeural',
  };

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
    return PageScaffold(
      eyebrow: 'Estudio',
      title: book.title,
      subtitle: 'Elegí motor, voz y velocidad. La conversión corre en este equipo.',
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
          if (book.status == 'ready')
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
                      'Este libro ya tiene audio de demostración. Podés volver a convertirlo o abrir el lector.',
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
            title: 'Motor',
            child: RadioGroup<String>(
              groupValue: _engine,
              onChanged: _converting
                  ? (_) {}
                  : (value) {
                      if (value == null) {
                        return;
                      }
                      setState(() {
                        _engine = value;
                        _voice = _voices[value] ?? _voices['demo']!;
                      });
                    },
              child: Column(
                children: [
                  for (final entry in _engines.entries)
                    RadioListTile<String>(
                      contentPadding: EdgeInsets.zero,
                      value: entry.key,
                      title: Text(entry.value),
                      subtitle: entry.key == 'demo'
                          ? const Text('Genera audio de silencio para validar el pipeline. No es TTS real.')
                          : Text(_engineDescription(entry.key)),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          _Panel(
            title: 'Voz y salida',
            child: Column(
              children: [
                DropdownButtonFormField<String>(
                  initialValue: _voice,
                  decoration: const InputDecoration(labelText: 'Voz'),
                  items: [
                    DropdownMenuItem(value: _voice, child: Text(_voice)),
                  ],
                  onChanged: _converting ? null : (_) {},
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Text('Velocidad', style: Theme.of(context).textTheme.titleSmall),
                    Expanded(
                      child: Slider(
                        value: _rate,
                        min: -30,
                        max: 30,
                        divisions: 12,
                        label: '${_rate.round()}%',
                        onChanged: _converting
                            ? null
                            : (value) => setState(() => _rate = value),
                      ),
                    ),
                    Text('${_rate.round()}%'),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          if (_error != null)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: colors.danger.withValues(alpha: 0.08),
                border: Border(left: BorderSide(color: colors.danger, width: 2)),
              ),
              child: Text(_error!),
            ),
          if (_converting) ...[
            const SizedBox(height: 18),
            LinearProgressIndicator(value: _total == 0 ? null : _completed / _total),
            const SizedBox(height: 8),
            Text('Generando audio de demostración: $_completed / $_total capítulos'),
          ],
          const SizedBox(height: 22),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: _converting ? null : () => _convert(book),
              icon: const Icon(Icons.graphic_eq, size: 18),
              label: Text(_converting ? 'Convirtiendo…' : 'Convertir'),
            ),
          ),
          const SizedBox(height: 28),
          Text(
            'Modo demo: el pipeline de capítulos, manifiesto y archivos ya está conectado. '
            'La síntesis real (Piper/Kokoro/cloud) y el M4B se agregan en la próxima fase.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Future<void> _convert(Book book) async {
    setState(() {
      _converting = true;
      _completed = 0;
      _total = book.chapterCount;
      _error = null;
    });
    try {
      final updated = await const DemoConversionService().convert(
        book,
        engine: _engine,
        voice: _voice,
        rate: '${_rate.round()}%',
        onProgress: (chapter, total) {
          if (mounted) {
            setState(() {
              _completed = chapter;
              _total = total;
            });
          }
        },
      );
      ref.invalidate(bookProvider(book.id));
      ref.invalidate(libraryProvider);
      if (mounted) {
        setState(() {
          _converting = false;
          _completed = _total;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Audio de demostración listo para ${updated.title}.')),
        );
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _converting = false;
          _error = 'No se pudo convertir: $error';
        });
      }
    }
  }

  String _engineDescription(String engine) {
    return switch (engine) {
      'piper' => 'TTS local en CPU. Requiere modelo y runtime nativo.',
      'edge' => 'Voces gratuitas de Microsoft; requiere internet.',
      'gemini' => 'Requiere clave de Google AI Studio.',
      'elevenlabs' => 'Requiere clave y créditos.',
      'azure' => 'Requiere clave y región.',
      _ => '',
    };
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
