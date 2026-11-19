import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/form_controls.dart';
import '../../core/design/tokens.dart';
import '../../domain/providers.dart';

/// Cloud provider keys: save, test, delete and never echo the key.
class ProvidersPanel extends ConsumerStatefulWidget {
  const ProvidersPanel({super.key});

  @override
  ConsumerState<ProvidersPanel> createState() => _ProvidersPanelState();
}

class _ProvidersPanelState extends ConsumerState<ProvidersPanel> {
  final _keys = <String, TextEditingController>{};
  final _regions = <String, TextEditingController>{};
  final _messages = <String, String>{};
  final _busy = <String>{};
  final _testing = <String>{};

  @override
  void dispose() {
    for (final controller in _keys.values) {
      controller.dispose();
    }
    for (final controller in _regions.values) {
      controller.dispose();
    }
    super.dispose();
  }

  TextEditingController _keyController(String id) {
    return _keys.putIfAbsent(id, TextEditingController.new);
  }

  TextEditingController _regionController(String id, String? initial) {
    return _regions.putIfAbsent(
      id,
      () => TextEditingController(text: initial ?? ''),
    );
  }

  @override
  Widget build(BuildContext context) {
    final statuses = ref.watch(providerStatusesProvider);
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return BibliotecaSection(
      title: 'Proveedores en la nube',
      description:
          'Las claves se guardan en este equipo y nunca se devuelven a la '
          'interfaz. También podés definirlas con variables de entorno. '
          'Después de guardar, elegí el motor en el Estudio.',
      child: statuses.when(
        loading: () => const Padding(
          padding: EdgeInsets.symmetric(vertical: 16),
          child: Center(child: CircularProgressIndicator()),
        ),
        error: (error, stackTrace) =>
            ErrorView(message: 'No se pudieron leer los proveedores: $error'),
        data: (items) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (var index = 0; index < items.length; index++) ...[
              if (index > 0) const SizedBox(height: 18),
              _providerCard(items[index], colors),
            ],
          ],
        ),
      ),
    );
  }

  Widget _providerCard(ProviderStatus status, BibliotecaColors colors) {
    final info = status.info;
    final keyController = _keyController(info.id);
    final regionController = _regionController(info.id, status.region);
    final busy = _busy.contains(info.id);
    final testing = _testing.contains(info.id);
    final statusLabel = status.configured
        ? status.source == 'env'
              ? 'ENTORNO'
              : 'CONFIGURADA'
        : 'SIN CONFIGURAR';
    final statusColor = status.configured
        ? status.source == 'env'
              ? colors.audio
              : colors.brass
        : colors.inkFaint;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BibliotecaRadii.md,
        border: Border.all(color: colors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      info.label,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      info.description,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              StatusPill(label: statusLabel, color: statusColor),
            ],
          ),
          if (status.hint != null) ...[
            const SizedBox(height: 8),
            Text(
              'Clave guardada: ${status.hint}',
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
          const SizedBox(height: 12),
          TextField(
            controller: keyController,
            obscureText: true,
            autocorrect: false,
            enableSuggestions: false,
            decoration: InputDecoration(
              labelText: 'Clave de ${info.label}',
              hintText: 'Pegá la clave acá',
              border: const OutlineInputBorder(),
            ),
          ),
          if (info.requiresRegion) ...[
            const SizedBox(height: 10),
            TextField(
              controller: regionController,
              autocorrect: false,
              enableSuggestions: false,
              decoration: const InputDecoration(
                labelText: 'Región de Azure',
                hintText: 'westeurope',
                border: OutlineInputBorder(),
              ),
            ),
          ],
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(
                onPressed: busy
                    ? null
                    : () => _save(info, keyController, regionController),
                icon: busy
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.save_outlined, size: 18),
                label: const Text('Guardar'),
              ),
              OutlinedButton.icon(
                onPressed: testing ? null : () => _test(info),
                icon: testing
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.bolt_outlined, size: 18),
                label: const Text('Probar'),
              ),
              if (status.configured)
                TextButton.icon(
                  onPressed: busy ? null : () => _delete(info),
                  icon: const Icon(Icons.delete_outline, size: 18),
                  label: const Text('Eliminar'),
                ),
              TextButton(
                onPressed: () => _open(info.keyUrl),
                child: Text('Obtener clave'),
              ),
              TextButton(
                onPressed: () => _open(info.docsUrl),
                child: const Text('Documentación'),
              ),
            ],
          ),
          if (_messages[info.id] != null) ...[
            const SizedBox(height: 8),
            Text(
              _messages[info.id]!,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _save(
    ProviderInfo info,
    TextEditingController key,
    TextEditingController region,
  ) async {
    setState(() {
      _busy.add(info.id);
      _messages.remove(info.id);
    });
    try {
      await ref
          .read(providerKeyStoreProvider)
          .save(
            info.id,
            apiKey: key.text,
            region: info.requiresRegion ? region.text : null,
          );
      key.clear();
      ref.invalidate(providerStatusesProvider);
      if (mounted) {
        setState(() {
          _messages[info.id] = 'Clave guardada.';
        });
      }
    } on ProviderKeyException catch (error) {
      if (mounted) {
        setState(() => _messages[info.id] = error.message);
      }
    } catch (error) {
      if (mounted) {
        setState(() => _messages[info.id] = 'No se pudo guardar: $error');
      }
    } finally {
      if (mounted) {
        setState(() => _busy.remove(info.id));
      }
    }
  }

  Future<void> _delete(ProviderInfo info) async {
    setState(() {
      _busy.add(info.id);
      _messages.remove(info.id);
    });
    try {
      await ref.read(providerKeyStoreProvider).delete(info.id);
      ref.invalidate(providerStatusesProvider);
      if (mounted) {
        setState(() => _messages[info.id] = 'Clave eliminada.');
      }
    } catch (error) {
      if (mounted) {
        setState(() => _messages[info.id] = 'No se pudo eliminar: $error');
      }
    } finally {
      if (mounted) {
        setState(() => _busy.remove(info.id));
      }
    }
  }

  Future<void> _test(ProviderInfo info) async {
    setState(() {
      _testing.add(info.id);
      _messages.remove(info.id);
    });
    try {
      final result = await ref.read(providerKeyStoreProvider).test(info.id);
      if (mounted) {
        setState(() {
          _messages[info.id] = '${result.ok ? '✓' : '✕'} ${result.message}';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() => _messages[info.id] = 'No se pudo probar: $error');
      }
    } finally {
      if (mounted) {
        setState(() => _testing.remove(info.id));
      }
    }
  }

  Future<void> _open(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
