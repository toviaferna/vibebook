import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/tokens.dart';
import '../../domain/models.dart';
import 'library_view.dart';

class LibraryPage extends ConsumerWidget {
  const LibraryPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final books = ref.watch(filteredBooksProvider);
    final library = ref.watch(libraryProvider);
    final query = ref.watch(searchQueryProvider);
    final filter = ref.watch(libraryFilterProvider);
    final sort = ref.watch(librarySortProvider);
    final settings = ref.watch(settingsProvider).value;
    Book? lastBook;
    final lastId = settings?.lastBookId;
    if (lastId != null) {
      for (final book in library.value ?? const <Book>[]) {
        if (book.id == lastId) {
          lastBook = book;
          break;
        }
      }
    }
    final lastChapter = settings?.lastChapterIndex ?? 1;
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return PageScaffold(
      eyebrow: 'Biblioteca',
      title: 'Tu estantería',
      maxContentWidth: 1120,
      subtitle: library.value == null
          ? null
          : library.value!.length == 1
          ? '1 libro en este equipo'
          : '${library.value!.length} libros en este equipo',
      actions: [
        OutlinedButton.icon(
          onPressed: () => context.go('/import'),
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Importar'),
        ),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (lastBook != null) ...[
            _ContinueCard(
              book: lastBook,
              chapterIndex: lastChapter,
              onOpen: () => context.push(
                '/books/${lastBook!.id}/read?chapter=$lastChapter',
              ),
            ),
            const SizedBox(height: 18),
          ],
          Align(
            alignment: Alignment.centerLeft,
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: TextField(
                onChanged: (value) =>
                    ref.read(searchQueryProvider.notifier).setQuery(value),
                decoration: InputDecoration(
                  hintText: 'Buscar por título, autor o idioma…',
                  prefixIcon: const Icon(Icons.search, size: 20),
                  suffixIcon: query.isEmpty
                      ? null
                      : IconButton(
                          tooltip: 'Limpiar búsqueda',
                          onPressed: () {
                            ref.read(searchQueryProvider.notifier).setQuery('');
                            FocusScope.of(context).unfocus();
                          },
                          icon: const Icon(Icons.close, size: 18),
                        ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              for (final entry in libraryFilters.entries)
                ChoiceChip(
                  label: Text(entry.value),
                  selected: filter == entry.key,
                  onSelected: (_) => ref
                      .read(libraryFilterProvider.notifier)
                      .setFilter(entry.key),
                ),
              const SizedBox(width: 8),
              PopupMenuButton<String>(
                tooltip: 'Ordenar la biblioteca',
                onSelected: (value) =>
                    ref.read(librarySortProvider.notifier).setSort(value),
                itemBuilder: (context) => [
                  for (final entry in librarySorts.entries)
                    CheckedPopupMenuItem(
                      value: entry.key,
                      checked: sort == entry.key,
                      child: Text(entry.value),
                    ),
                ],
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.sort, size: 18, color: colors.inkSoft),
                    const SizedBox(width: 6),
                    Text(
                      'Orden: ${librarySorts[sort]}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          books.when(
            data: (items) {
              if (items.isEmpty) {
                final filtered = query.isNotEmpty || filter != 'all';
                return EmptyState(
                  icon: Icons.menu_book_outlined,
                  title: filtered
                      ? 'No encontré libros'
                      : 'Tu estante está vacío',
                  message: !filtered
                      ? 'Importá un EPUB para empezar. La biblioteca se guarda en tu equipo.'
                      : query.isNotEmpty
                      ? 'Probá con otro título, autor o idioma.'
                      : 'Probá con otro filtro.',
                  action: !filtered
                      ? FilledButton.icon(
                          onPressed: () => context.go('/import'),
                          icon: const Icon(Icons.add, size: 18),
                          label: const Text('Importar EPUB'),
                        )
                      : query.isNotEmpty
                      ? OutlinedButton(
                          onPressed: () => ref
                              .read(searchQueryProvider.notifier)
                              .setQuery(''),
                          child: const Text('Limpiar búsqueda'),
                        )
                      : OutlinedButton(
                          onPressed: () => ref
                              .read(libraryFilterProvider.notifier)
                              .setFilter('all'),
                          child: const Text('Ver todos'),
                        ),
                );
              }
              return LayoutBuilder(
                builder: (context, constraints) {
                  final columns = constraints.maxWidth < 620
                      ? 2
                      : constraints.maxWidth < 980
                      ? 3
                      : 4;
                  const gap = 18.0;
                  final itemWidth =
                      (constraints.maxWidth - gap * (columns - 1)) / columns;
                  final itemHeight = itemWidth * 1.25 + 86;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: items.length,
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: columns,
                      crossAxisSpacing: gap,
                      mainAxisSpacing: 24,
                      mainAxisExtent: itemHeight,
                    ),
                    itemBuilder: (context, index) {
                      final book = items[index];
                      return BookCard(
                        book: book,
                        onTap: () => context.push('/books/${book.id}'),
                      );
                    },
                  );
                },
              );
            },
            loading: () => Padding(
              padding: const EdgeInsets.symmetric(vertical: 64),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: colors.accent),
                    const SizedBox(height: 16),
                    Text(
                      'Leyendo la biblioteca…',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ),
            error: (error, stackTrace) => ErrorView(
              message: '$error',
              onRetry: () => ref.read(libraryProvider.notifier).refresh(),
            ),
          ),
        ],
      ),
    );
  }
}

class _ContinueCard extends StatelessWidget {
  const _ContinueCard({
    required this.book,
    required this.chapterIndex,
    required this.onOpen,
  });

  final Book book;
  final int chapterIndex;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BibliotecaRadii.md,
        border: Border.all(color: colors.line),
      ),
      child: Row(
        children: [
          BookCover(book: book, width: 64),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Continuar',
                  style: Theme.of(context).textTheme.labelSmall
                      ?.copyWith(color: colors.brass, letterSpacing: 1.4),
                ),
                const SizedBox(height: 2),
                Text(
                  book.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Text(
                  '${book.author} · Capítulo $chapterIndex',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          FilledButton.icon(
            onPressed: onOpen,
            icon: const Icon(Icons.play_arrow, size: 18),
            label: const Text('Seguir'),
          ),
        ],
      ),
    );
  }
}
