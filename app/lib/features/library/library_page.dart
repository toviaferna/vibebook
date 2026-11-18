import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/tokens.dart';

class LibraryPage extends ConsumerWidget {
  const LibraryPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final books = ref.watch(filteredBooksProvider);
    final query = ref.watch(searchQueryProvider);
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return PageScaffold(
      eyebrow: 'Biblioteca',
      title: 'Tu estantería',
      subtitle: books.value == null ? null : '${books.value!.length} libros en este equipo',
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
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: TextField(
              onChanged: (value) => ref.read(searchQueryProvider.notifier).setQuery(value),
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
          const SizedBox(height: 24),
          books.when(
            data: (items) {
              if (items.isEmpty) {
                return EmptyState(
                  icon: Icons.menu_book_outlined,
                  title: query.isEmpty ? 'Tu estante está vacío' : 'No encontré ese libro',
                  message: query.isEmpty
                      ? 'Importá un EPUB para empezar. La biblioteca se guarda en tu equipo.'
                      : 'Probá con otro título, autor o idioma.',
                  action: query.isEmpty
                      ? FilledButton.icon(
                          onPressed: () => context.go('/import'),
                          icon: const Icon(Icons.add, size: 18),
                          label: const Text('Importar EPUB'),
                        )
                      : OutlinedButton(
                          onPressed: () => ref.read(searchQueryProvider.notifier).setQuery(''),
                          child: const Text('Limpiar búsqueda'),
                        ),
                );
              }
              return LayoutBuilder(
                builder: (context, constraints) {
                  final columns = constraints.maxWidth < 620
                      ? 2
                      : constraints.maxWidth < 980
                          ? 3
                          : constraints.maxWidth < 1320
                              ? 4
                              : 5;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: items.length,
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: columns,
                      crossAxisSpacing: 18,
                      mainAxisSpacing: 24,
                      childAspectRatio: 0.62,
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
                    Text('Leyendo la biblioteca…', style: Theme.of(context).textTheme.bodyMedium),
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
