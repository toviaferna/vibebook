import 'dart:io';

import 'package:dio/dio.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/tokens.dart';
import '../../data/tts/piper_catalog.dart';
import '../../data/tts/piper_downloader.dart';
import '../../data/tts/piper_models.dart';

Future<void> showVoiceDownloadDialog(BuildContext context) {
  return showDialog<void>(
    context: context,
    builder: (context) => const _VoiceDownloadDialog(),
  );
}

class _VoiceDownloadDialog extends ConsumerStatefulWidget {
  const _VoiceDownloadDialog();

  @override
  ConsumerState<_VoiceDownloadDialog> createState() =>
      _VoiceDownloadDialogState();
}

class _VoiceDownloadDialogState extends ConsumerState<_VoiceDownloadDialog> {
  String? _busyId;
  double _progress = 0;
  String? _stage;
  String? _error;
  CancelToken? _cancelToken;

  @override
  void dispose() {
    _cancelToken?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final models = ref.watch(piperModelsProvider).value ?? const <PiperModel>[];
    final installedIds = models.map((model) => model.id).toSet();
    final busy = _busyId != null;
    return Dialog(
      backgroundColor: colors.surface,
      insetPadding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: 640,
          maxHeight: MediaQuery.sizeOf(context).height * 0.82,
        ),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Voces Piper',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Se descargan una vez y quedan en tu equipo. La síntesis es local.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Cerrar',
                    onPressed: busy ? null : () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (busy) ...[
                LinearProgressIndicator(
                  value: _progress == 0 ? null : _progress,
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(child: Text(_stage ?? 'Instalando…')),
                    if (_cancelToken != null)
                      TextButton(
                        onPressed: () {
                          _cancelToken?.cancel('Cancelado');
                          setState(() {
                            _busyId = null;
                            _cancelToken = null;
                            _stage = null;
                          });
                        },
                        child: const Text('Cancelar'),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
              ],
              if (_error != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: colors.danger.withValues(alpha: 0.08),
                    border: Border(
                      left: BorderSide(color: colors.danger, width: 2),
                    ),
                  ),
                  child: Text(
                    _error!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
                const SizedBox(height: 8),
              ],
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: piperCatalog.length,
                  separatorBuilder: (context, index) =>
                      Divider(color: colors.line),
                  itemBuilder: (context, index) {
                    final entry = piperCatalog[index];
                    final installed = installedIds.contains(entry.id);
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 44,
                            height: 44,
                            decoration: BoxDecoration(
                              color: colors.accentSoft,
                              borderRadius: BibliotecaRadii.md,
                            ),
                            child: Icon(
                              Icons.record_voice_over,
                              color: colors.accent,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  '${entry.name} · ${entry.language}',
                                  style: Theme.of(context).textTheme.titleSmall,
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  entry.description,
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                                const SizedBox(height: 4),
                                Wrap(
                                  spacing: 10,
                                  children: [
                                    Text(
                                      entry.sizeLabel,
                                      style: Theme.of(context)
                                          .textTheme
                                          .labelSmall,
                                    ),
                                    InkWell(
                                      onTap: () => launchUrl(
                                        Uri.parse(entry.licenseUrl),
                                      ),
                                      child: Text(
                                        entry.license,
                                        style: Theme.of(context)
                                            .textTheme
                                            .labelSmall
                                            ?.copyWith(
                                              color: colors.audio,
                                              decoration:
                                                  TextDecoration.underline,
                                            ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          if (installed)
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: StatusPill(
                                label: 'INSTALADA',
                                color: colors.brass,
                              ),
                            )
                          else
                            FilledButton(
                              onPressed: busy ? null : () => _download(entry),
                              child: const Text('Descargar'),
                            ),
                        ],
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 12),
              Divider(color: colors.line),
              const SizedBox(height: 10),
              LayoutBuilder(
                builder: (context, constraints) {
                  final message = Text(
                    '¿Ya tenés un .tar.bz2 de Piper? Podés instalarlo sin conexión.',
                    style: Theme.of(context).textTheme.bodySmall,
                  );
                  final button = OutlinedButton.icon(
                    onPressed: busy ? null : _importFile,
                    icon: const Icon(Icons.folder_open, size: 18),
                    label: const Text('Importar archivo'),
                  );
                  if (constraints.maxWidth < 560) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [message, const SizedBox(height: 10), button],
                    );
                  }
                  return Row(
                    children: [
                      Expanded(child: message),
                      const SizedBox(width: 12),
                      button,
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _download(PiperCatalogEntry entry) async {
    final token = CancelToken();
    setState(() {
      _cancelToken = token;
    });
    await _install(
      action: (root) => ref
          .read(piperDownloaderProvider)
          .installFromCatalog(
            entry,
            rootPath: root,
            cancelToken: token,
            onProgress: _updateProgress,
          ),
    );
  }

  Future<void> _importFile() async {
    const group = XTypeGroup(label: 'Piper', extensions: ['bz2']);
    final file = await openFile(acceptedTypeGroups: [group]);
    if (file == null) {
      return;
    }
    await _install(
      action: (root) => ref
          .read(piperDownloaderProvider)
          .installFromFile(
            File(file.path),
            rootPath: root,
            onProgress: _updateProgress,
          ),
    );
  }

  Future<void> _install({
    required Future<PiperModel> Function(String root) action,
  }) async {
    setState(() {
      _error = null;
      _busyId = 'working';
      _progress = 0;
      _stage = 'Preparando…';
      _cancelToken ??= CancelToken();
    });
    try {
      final root = await ref.read(modelsRootProvider.future);
      final model = await action(root);
      ref.invalidate(piperModelsProvider);
      ref.invalidate(modelsRootProvider);
      await ref.read(settingsProvider.notifier).selectPiperModel(model.id);
      if (mounted) {
        setState(() {
          _busyId = null;
          _cancelToken = null;
          _progress = 1;
          _stage = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Voz instalada: ${model.name}.')),
        );
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _busyId = null;
          _cancelToken = null;
          _stage = null;
          _error = '$error';
        });
      }
    }
  }

  void _updateProgress(PiperDownloadProgress progress) {
    if (!mounted) {
      return;
    }
    setState(() {
      _progress = progress.value;
      _stage = progress.stage;
    });
  }
}
