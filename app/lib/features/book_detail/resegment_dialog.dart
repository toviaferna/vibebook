import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../app/providers.dart';
import '../../data/repair/resegment.dart';
import '../../domain/models.dart';

class ResegmentDialog extends ConsumerStatefulWidget {
  const ResegmentDialog({super.key, required this.book});

  final Book book;

  @override
  ConsumerState<ResegmentDialog> createState() => _ResegmentDialogState();
}

class _ResegmentDialogState extends ConsumerState<ResegmentDialog> {
  static const _service = ResegmentService();
  ResegmentPlan? _plan;
  List<ResegmentBackup> _backups = const [];
  String? _error;
  String? _message;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final plan = await _service.analyze(widget.book);
      final backups = await _service.backups(widget.book);
      if (mounted) {
        setState(() {
          _plan = plan;
          _backups = backups;
          _busy = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = 'No se pudo analizar la segmentación: $error';
          _busy = false;
        });
      }
    }
  }

  Future<void> _apply() async {
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final result = await _service.apply(widget.book);
      ref.invalidate(bookProvider(widget.book.id));
      ref.invalidate(libraryProvider);
      final backups = await _service.backups(widget.book);
      if (mounted) {
        setState(() {
          _backups = backups;
          _busy = false;
          _message = result.changed
              ? 'Segmentación actualizada. Abrí el Estudio y reanudá la '
                    'conversión para regenerar el audio de los capítulos '
                    'cambiados.'
              : 'La segmentación ya estaba al día.';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = 'No se pudo aplicar: $error';
        });
      }
    }
  }

  Future<void> _restore() async {
    if (_backups.isEmpty) {
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      await _service.restore(widget.book, _backups.first.id);
      ref.invalidate(bookProvider(widget.book.id));
      ref.invalidate(libraryProvider);
      if (mounted) {
        setState(() {
          _busy = false;
          _message = 'Copia restaurada: ${_backups.first.id}.';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = 'No se pudo restaurar: $error';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620, maxHeight: 620),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Segmentación del audio',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Cerrar',
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Compara el manifiesto con el EPUB fuente y marca los '
                'capítulos cuyo texto cambió.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 14),
              if (_busy) const LinearProgressIndicator(),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              if (_message != null) ...[
                const SizedBox(height: 10),
                Text(_message!),
              ],
              if (_plan != null) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 18,
                  runSpacing: 8,
                  children: [
                    _metric('Segmentos actuales', '${_plan!.oldSegments}'),
                    _metric('Segmentos nuevos', '${_plan!.newSegments}'),
                    _metric('Cambiados', '${_plan!.changedSegments}'),
                    _metric(
                      'Versión',
                      '${_plan!.currentVersion ?? '—'} → '
                          '${_plan!.targetVersion}',
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (!_plan!.canRepair)
                  Text(
                    _plan!.reason ?? 'No se puede reparar este libro.',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  )
                else if (!_plan!.needsRepair)
                  const Text('La segmentación ya está al día.')
                else
                  Flexible(
                    child: ListView(
                      shrinkWrap: true,
                      children: [
                        for (final chapter in _plan!.chapters)
                          if (chapter.changed)
                            ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              leading: CircleAvatar(
                                radius: 14,
                                child: Text('${chapter.index}'),
                              ),
                              title: Text(chapter.title),
                              subtitle: Text(
                                '${chapter.changedSegments} cambiados · '
                                '${chapter.addedSegments} nuevos · '
                                '${chapter.removedSegments} eliminados',
                              ),
                            ),
                      ],
                    ),
                  ),
              ],
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton.icon(
                    onPressed:
                        _busy ||
                            _plan == null ||
                            !_plan!.canRepair ||
                            !_plan!.needsRepair
                        ? null
                        : _apply,
                    icon: const Icon(Icons.build_outlined, size: 18),
                    label: const Text('Aplicar y marcar para re-síntesis'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _busy || _backups.isEmpty ? null : _restore,
                    icon: const Icon(Icons.restore, size: 18),
                    label: Text(
                      _backups.isEmpty
                          ? 'Sin copias'
                          : 'Restaurar ${_backups.first.id}',
                    ),
                  ),
                  TextButton(
                    onPressed: _busy ? null : _load,
                    child: const Text('Volver a analizar'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _metric(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelSmall),
        Text(value, style: Theme.of(context).textTheme.titleMedium),
      ],
    );
  }
}
