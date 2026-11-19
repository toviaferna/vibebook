import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../app/providers.dart';
import '../../data/covers/cover_search.dart';
import '../../domain/models.dart';

class CoverSearchDialog extends ConsumerStatefulWidget {
  const CoverSearchDialog({super.key, required this.book});

  final Book book;

  @override
  ConsumerState<CoverSearchDialog> createState() => _CoverSearchDialogState();
}

class _CoverSearchDialogState extends ConsumerState<CoverSearchDialog> {
  final _service = CoverSearchService();
  List<CoverHit>? _hits;
  String? _error;
  String? _busyUrl;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _search();
  }

  Future<void> _search() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final hits = await _service.search(
        title: widget.book.title,
        author: widget.book.author,
      );
      if (mounted) {
        setState(() {
          _hits = hits;
          _loading = false;
        });
      }
    } on CoverSearchException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _loading = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = 'No se pudo buscar la portada: $error';
          _loading = false;
        });
      }
    }
  }

  Future<void> _use(CoverHit hit) async {
    setState(() {
      _busyUrl = hit.coverUrl;
      _error = null;
    });
    try {
      final bytes = await _service.download(hit.coverUrl);
      final extension = _extension(hit.coverUrl);
      await ref
          .read(libraryRepositoryProvider)
          .setCover(widget.book.id, bytes, extension: extension);
      ref.invalidate(bookProvider(widget.book.id));
      ref.invalidate(libraryProvider);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Portada actualizada: ${hit.title}.')),
        );
      }
    } on CoverSearchException catch (error) {
      if (mounted) {
        setState(() {
          _busyUrl = null;
          _error = error.message;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _busyUrl = null;
          _error = 'No se pudo guardar la portada: $error';
        });
      }
    }
  }

  String _extension(String url) {
    final path = Uri.tryParse(url)?.path.toLowerCase() ?? '';
    if (path.endsWith('.png')) {
      return 'png';
    }
    if (path.endsWith('.webp')) {
      return 'webp';
    }
    if (path.endsWith('.gif')) {
      return 'gif';
    }
    return 'jpg';
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      clipBehavior: Clip.antiAlias,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 860, maxHeight: 640),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Buscar portada',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${widget.book.title} · ${widget.book.author}',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Cerrar',
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (_error != null)
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.errorContainer
                        .withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(_error!),
                ),
              if (_error != null) const SizedBox(height: 8),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator())
                    : (_hits == null || _hits!.isEmpty)
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.image_search, size: 42),
                              const SizedBox(height: 10),
                              Text(
                                'No encontramos portadas para este libro.',
                                textAlign: TextAlign.center,
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                              const SizedBox(height: 12),
                              OutlinedButton(
                                onPressed: _search,
                                child: const Text('Volver a buscar'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : GridView.builder(
                        gridDelegate:
                            const SliverGridDelegateWithMaxCrossAxisExtent(
                              maxCrossAxisExtent: 210,
                              mainAxisSpacing: 12,
                              crossAxisSpacing: 12,
                              childAspectRatio: 0.52,
                            ),
                        itemCount: _hits!.length,
                        itemBuilder: (context, index) {
                          final hit = _hits![index];
                          return _CoverCard(
                            hit: hit,
                            busy: _busyUrl == hit.coverUrl,
                            disabled: _busyUrl != null,
                            onUse: () => _use(hit),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CoverCard extends StatelessWidget {
  const _CoverCard({
    required this.hit,
    required this.busy,
    required this.disabled,
    required this.onUse,
  });

  final CoverHit hit;
  final bool busy;
  final bool disabled;
  final VoidCallback onUse;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: Image.network(
              hit.coverUrl,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) => Container(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                alignment: Alignment.center,
                child: const Icon(Icons.broken_image_outlined),
              ),
              loadingBuilder: (context, child, progress) {
                if (progress == null) {
                  return child;
                }
                return const Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                );
              },
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  hit.title,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 2),
                Text(
                  hit.author,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                Text(
                  '${hit.source}${hit.year == null ? '' : ' · ${hit.year}'} · ${(hit.score * 100).round()}%',
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                const SizedBox(height: 6),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: disabled ? null : onUse,
                    child: busy
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Usar'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
