import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/form_controls.dart';
import '../../core/design/tokens.dart';

/// VEP plugin management: add, test, list and remove HTTP/JSON engines.
class PluginsPanel extends ConsumerStatefulWidget {
  const PluginsPanel({super.key});

  @override
  ConsumerState<PluginsPanel> createState() => _PluginsPanelState();
}

class _PluginsPanelState extends ConsumerState<PluginsPanel> {
  final _url = TextEditingController();
  final _token = TextEditingController();
  final _messages = <String, String>{};
  bool _adding = false;
  String? _error;

  @override
  void dispose() {
    _url.dispose();
    _token.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final plugins = ref.watch(vepPluginsProvider);
    return BibliotecaSection(
      title: 'Plugins VEP',
      description:
          'Conectá un motor HTTP/JSON que cumpla vep/1. Vibebook muestra '
          'licencia y fuente; no instala ni descarga código automáticamente. '
          'Los plugins remotos deben usar HTTPS; los locales, loopback.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _url,
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(
              labelText: 'URL del plugin',
              hintText: 'http://127.0.0.1:9001',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _token,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            decoration: const InputDecoration(
              labelText: 'Token opcional',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: _adding ? null : _add,
              icon: _adding
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.add_link, size: 18),
              label: const Text('Agregar y probar'),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(
              _error!,
              style: Theme.of(context).textTheme.bodySmall
                  ?.copyWith(color: colors.danger),
            ),
          ],
          const SizedBox(height: 14),
          plugins.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stackTrace) =>
                Text('No se pudieron leer los plugins: $error'),
            data: (items) {
              if (items.isEmpty) {
                return Text(
                  'Todavía no hay plugins registrados.',
                  style: Theme.of(context).textTheme.bodySmall,
                );
              }
              return Column(
                children: [
                  for (final plugin in items) ...[
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: colors.surface,
                        borderRadius: BibliotecaRadii.md,
                        border: Border.all(color: colors.line),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  plugin.name,
                                  style: Theme.of(context)
                                      .textTheme
                                      .titleMedium,
                                ),
                              ),
                              StatusPill(
                                label: plugin.tokenSet ? 'TOKEN' : 'SIN TOKEN',
                                color: plugin.tokenSet
                                    ? colors.audio
                                    : colors.inkFaint,
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'v${plugin.version} · ${plugin.license} · '
                            '${plugin.voices.length} voces · '
                            '${plugin.timings}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          if (plugin.source.isNotEmpty) ...[
                            const SizedBox(height: 2),
                            InkWell(
                              onTap: () => _open(plugin.source),
                              child: Text(
                                plugin.source,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: Theme.of(context).textTheme.bodySmall
                                    ?.copyWith(color: colors.accent),
                              ),
                            ),
                          ],
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              OutlinedButton.icon(
                                onPressed: () => _test(plugin.id),
                                icon: const Icon(Icons.bolt_outlined, size: 18),
                                label: const Text('Probar'),
                              ),
                              TextButton.icon(
                                onPressed: () => _remove(plugin.id),
                                icon: const Icon(
                                  Icons.delete_outline,
                                  size: 18,
                                ),
                                label: const Text('Eliminar'),
                              ),
                            ],
                          ),
                          if (_messages[plugin.id] != null) ...[
                            const SizedBox(height: 6),
                            Text(
                              _messages[plugin.id]!,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                  ],
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  Future<void> _add() async {
    final url = _url.text.trim();
    if (url.isEmpty) {
      setState(() => _error = 'Escribí la URL del plugin.');
      return;
    }
    setState(() {
      _adding = true;
      _error = null;
    });
    try {
      final plugin = await ref
          .read(vepPluginRepositoryProvider)
          .add(url, token: _token.text);
      _url.clear();
      _token.clear();
      ref.invalidate(vepPluginsProvider);
      if (mounted) {
        setState(() {
          _messages[plugin.id] = 'Plugin agregado y verificado.';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() => _error = 'No se pudo agregar el plugin: $error');
      }
    } finally {
      if (mounted) {
        setState(() => _adding = false);
      }
    }
  }

  Future<void> _test(String id) async {
    setState(() => _messages.remove(id));
    final result = await ref.read(vepPluginRepositoryProvider).test(id);
    if (mounted) {
      setState(() {
        _messages[id] = '${result.ok ? '✓' : '✕'} ${result.message}';
      });
    }
  }

  Future<void> _remove(String id) async {
    await ref.read(vepPluginRepositoryProvider).remove(id);
    ref.invalidate(vepPluginsProvider);
    if (mounted) {
      setState(() => _messages.remove(id));
    }
  }

  Future<void> _open(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
