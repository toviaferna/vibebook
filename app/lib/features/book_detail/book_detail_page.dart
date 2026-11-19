import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/tokens.dart';
import '../../domain/models.dart';

class BookDetailPage extends ConsumerWidget {
  const BookDetailPage({super.key, required this.bookId});

  final String bookId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final book = ref.watch(bookProvider(bookId));
    return book.when(
      data: (value) {
        if (value == null) {
          return Scaffold(
            appBar: AppBar(
              leading: BackButton(onPressed: () => context.go('/')),
            ),
            body: const ErrorView(
              message: 'No encontré este libro en la biblioteca.',
            ),
          );
        }
        return _BookDetailView(book: value);
      },
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (error, stackTrace) => Scaffold(
        appBar: AppBar(leading: BackButton(onPressed: () => context.go('/'))),
        body: ErrorView(message: '$error'),
      ),
    );
  }
}

class _BookDetailView extends ConsumerWidget {
  const _BookDetailView({required this.book});

  final Book book;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final width = MediaQuery.sizeOf(context).width;
    final wide = width >= 900;
    final cover = BookCover(book: book, width: wide ? 220 : 160);
    final info = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(book.title, style: Theme.of(context).textTheme.headlineLarge),
        const SizedBox(height: 6),
        Text(
          book.author,
          style: Theme.of(context).textTheme.titleMedium
              ?.copyWith(color: colors.inkSoft),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 10,
          runSpacing: 8,
          children: [
            StatusPill(label: book.language.toUpperCase(), color: colors.audio),
            StatusPill(
              label: book.status == 'ready' ? 'AUDIO LISTO' : 'SIN AUDIO',
              color: book.status == 'ready' ? colors.brass : colors.inkFaint,
            ),
            if (book.durationMs != null)
              StatusPill(
                label: book.progressLabel.toUpperCase(),
                color: colors.accent,
              ),
          ],
        ),
        const SizedBox(height: 22),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            FilledButton.icon(
              onPressed: () => context.push('/books/${book.id}/read'),
              icon: const Icon(Icons.menu_book, size: 18),
              label: const Text('Leer ahora'),
            ),
            OutlinedButton.icon(
              onPressed: () => context.push('/books/${book.id}/studio'),
              icon: const Icon(Icons.graphic_eq, size: 18),
              label: const Text('Estudio'),
            ),
          ],
        ),
        const SizedBox(height: 28),
        Row(
          children: [
            Expanded(
              child: Metric(label: 'Capítulos', value: '${book.chapterCount}'),
            ),
            Expanded(
              child: Metric(label: 'Segmentos', value: '${book.segmentCount}'),
            ),
            Expanded(
              child: Metric(
                label: 'Motor',
                value: book.status == 'ready' ? (book.engine ?? '—') : '—',
              ),
            ),
          ],
        ),
        if (book.status != 'ready') ...[
          const SizedBox(height: 22),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: colors.surface,
              border: Border(left: BorderSide(color: colors.brass, width: 2)),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, size: 18, color: colors.brass),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Este libro todavía no tiene audio. Podés leerlo ahora o convertirlo en el Estudio.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
    return PageScaffold(
      eyebrow: 'Biblioteca',
      title: 'Ficha del libro',
      maxContentWidth: 1000,
      actions: [
        IconButton(
          tooltip: 'Volver a la biblioteca',
          onPressed: () {
            if (context.canPop()) {
              context.pop();
            } else {
              context.go('/');
            }
          },
          icon: const Icon(Icons.arrow_back),
        ),
        PopupMenuButton<String>(
          tooltip: 'Más opciones',
          onSelected: (value) {
            if (value == 'delete') {
              _confirmDelete(context, ref, book);
            }
          },
          itemBuilder: (context) => const [
            PopupMenuItem(
              value: 'delete',
              height: 44,
              child: Row(
                children: [
                  Icon(Icons.delete_outline, size: 18),
                  SizedBox(width: 10),
                  Text('Eliminar libro'),
                ],
              ),
            ),
          ],
        ),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (wide)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                cover,
                const SizedBox(width: 28),
                Expanded(child: info),
              ],
            )
          else ...[
            Center(child: cover),
            const SizedBox(height: 22),
            info,
          ],
          const SizedBox(height: 34),
          SectionLabel('Capítulos', trailing: Text('${book.chapterCount}')),
          const SizedBox(height: 10),
          for (final chapter in book.chapters)
            Material(
              color: Colors.transparent,
              child: InkWell(
                borderRadius: BibliotecaRadii.sm,
                onTap: () => context.push(
                  '/books/${book.id}/read?chapter=${chapter.index}',
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 12,
                  ),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 36,
                        child: Text(
                          chapter.index.toString().padLeft(2, '0'),
                          style: Theme.of(context).textTheme.labelMedium,
                        ),
                      ),
                      Expanded(
                        child: Text(
                          chapter.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        chapter.durationMs == null
                            ? '—'
                            : _duration(chapter.durationMs!),
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                      const SizedBox(width: 6),
                      Icon(
                        Icons.chevron_right,
                        size: 18,
                        color: colors.inkFaint,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          Divider(color: colors.line),
          const SizedBox(height: 20),
          SectionLabel('Ficha'),
          const SizedBox(height: 12),
          Wrap(
            spacing: 32,
            runSpacing: 18,
            children: [
              Metric(label: 'Idioma', value: book.language.toUpperCase()),
              if (book.declaredLanguage != null &&
                  book.declaredLanguage != book.language)
                Metric(label: 'Declarado', value: book.declaredLanguage!),
              Metric(
                label: 'Voz',
                value: book.status == 'ready' ? (book.voice ?? '—') : '—',
              ),
              Metric(
                label: 'Velocidad',
                value: book.status == 'ready' ? (book.rate ?? '—') : '—',
              ),
              Metric(label: 'Archivo', value: book.sourceEpub ?? '—'),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    Book book,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Eliminar este libro?'),
        content: const Text(
          'Se borrarán el texto, el audio, los timings y los marcadores de este libro. '
          'No se puede deshacer.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }
    try {
      await ref.read(libraryProvider.notifier).deleteBook(book.id);
      if (context.mounted) {
        context.go('/');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Libro eliminado: ${book.title}.')),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo eliminar el libro: $error')),
        );
      }
    }
  }

  String _duration(int milliseconds) {
    final minutes = (milliseconds / 60000).round();
    final hours = minutes ~/ 60;
    final rest = minutes % 60;
    return hours > 0 ? '${hours}h ${rest}m' : '${rest}m';
  }
}
