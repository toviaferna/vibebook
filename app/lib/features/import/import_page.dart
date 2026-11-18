import 'package:collection/collection.dart';
import 'package:desktop_drop/desktop_drop.dart';
import 'package:file_selector/file_selector.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/tokens.dart';

class ImportPage extends ConsumerWidget {
  const ImportPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(importControllerProvider);
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return PageScaffold(
      eyebrow: 'Importar',
      title: 'Sumar un libro',
      subtitle: 'EPUB sin DRM. La app conserva acentos, índice e imágenes.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropTarget(
            onDragDone: (details) async {
              final file = details.files.firstOrNull;
              if (file == null) {
                return;
              }
              await _import(context, ref, file.path);
            },
            child: Container(
              padding: const EdgeInsets.all(36),
              decoration: BoxDecoration(
                color: colors.surface,
                borderRadius: BibliotecaRadii.lg,
                border: Border.all(color: colors.lineStrong),
              ),
              child: Column(
                children: [
                  Container(
                    width: 68,
                    height: 68,
                    decoration: BoxDecoration(
                      color: colors.accentSoft,
                      borderRadius: BibliotecaRadii.lg,
                    ),
                    child: Icon(Icons.upload_file, size: 30, color: colors.accent),
                  ),
                  const SizedBox(height: 18),
                  Text(
                    'Arrastrá un EPUB acá',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'o elegí un archivo desde tu equipo',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 20),
                  FilledButton.icon(
                    onPressed: state.status == ImportStatus.working
                        ? null
                        : () async {
                            const typeGroup = XTypeGroup(
                              label: 'EPUB',
                              extensions: ['epub'],
                              mimeTypes: ['application/epub+zip'],
                            );
                            final file = await openFile(acceptedTypeGroups: [typeGroup]);
                            if (file != null && context.mounted) {
                              await _import(context, ref, file.path);
                            }
                          },
                    icon: const Icon(Icons.folder_open, size: 18),
                    label: const Text('Elegir EPUB'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          if (state.status == ImportStatus.working)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: colors.surface,
                border: Border.all(color: colors.line),
                borderRadius: BibliotecaRadii.md,
              ),
              child: Row(
                children: [
                  const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: 14),
                  Expanded(child: Text(state.message ?? 'Importando…')),
                ],
              ),
            ),
          if (state.status == ImportStatus.error)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: colors.danger.withValues(alpha: 0.08),
                border: Border(left: BorderSide(color: colors.danger, width: 2)),
                borderRadius: BibliotecaRadii.md,
              ),
              child: Text(state.message ?? 'No se pudo importar el EPUB.'),
            ),
          if (state.status == ImportStatus.done && state.book != null)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: colors.surface,
                border: Border(left: BorderSide(color: colors.brass, width: 2)),
                borderRadius: BibliotecaRadii.md,
              ),
              child: Row(
                children: [
                  Icon(Icons.check_circle_outline, color: colors.brass),
                  const SizedBox(width: 12),
                  Expanded(child: Text(state.message ?? 'Importado.')),
                  OutlinedButton(
                    onPressed: () => context.push('/books/${state.book!.id}'),
                    child: const Text('Abrir libro'),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 32),
          SectionLabel('Qué se conserva'),
          const SizedBox(height: 12),
          const _ImportFeature(
            icon: Icons.text_fields,
            title: 'Acentos y ñ',
            message: 'Decodificación determinista: BOM, XML/meta charset, UTF-8 y Windows-1252.',
          ),
          const _ImportFeature(
            icon: Icons.account_tree_outlined,
            title: 'Índice y estructura',
            message: 'Partes, capítulos, títulos reales y portada del EPUB.',
          ),
          const _ImportFeature(
            icon: Icons.image_outlined,
            title: 'Ilustraciones',
            message: 'Se guardan junto al libro y aparecen en el lector.',
          ),
          const _ImportFeature(
            icon: Icons.language,
            title: 'Idioma real',
            message: 'Si el EPUB declara inglés pero el texto es español, la app usa español.',
          ),
        ],
      ),
    );
  }

  Future<void> _import(BuildContext context, WidgetRef ref, String path) async {
    final book = await ref.read(importControllerProvider.notifier).importEpub(path);
    if (book != null && context.mounted) {
      context.push('/books/${book.id}');
    }
  }
}

class _ImportFeature extends StatelessWidget {
  const _ImportFeature({required this.icon, required this.title, required this.message});

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: colors.accent),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 2),
                Text(message, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
