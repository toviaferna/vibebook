import 'dart:async';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:collection/collection.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;

import '../../app/providers.dart';
import '../../core/design/tokens.dart';
import '../../domain/models.dart';
import '../../domain/timing.dart';

class ReaderPage extends ConsumerStatefulWidget {
  const ReaderPage({super.key, required this.bookId});

  final String bookId;

  @override
  ConsumerState<ReaderPage> createState() => _ReaderPageState();
}

class _ReaderPageState extends ConsumerState<ReaderPage> {
  final _scrollController = ScrollController();
  final _player = AudioPlayer();
  StreamSubscription<PlayerState>? _playerStateSubscription;
  StreamSubscription<Duration>? _positionSubscription;
  StreamSubscription<Duration>? _durationSubscription;
  int? _chapterIndex;
  int? _timingAttempted;
  ChapterTiming? _timing;
  String? _loadedAudioPath;
  bool _isPlaying = false;
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;

  @override
  void initState() {
    super.initState();
    _playerStateSubscription = _player.onPlayerStateChanged.listen((state) {
      if (mounted) {
        setState(() => _isPlaying = state == PlayerState.playing);
      }
    });
    _positionSubscription = _player.onPositionChanged.listen((position) {
      if (mounted) {
        setState(() => _position = position);
      }
    });
    _durationSubscription = _player.onDurationChanged.listen((duration) {
      if (mounted) {
        setState(() => _duration = duration);
      }
    });
  }

  @override
  void dispose() {
    _playerStateSubscription?.cancel();
    _positionSubscription?.cancel();
    _durationSubscription?.cancel();
    _player.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bookAsync = ref.watch(bookProvider(widget.bookId));
    final settings = ref.watch(settingsProvider).value;
    final preferences = settings?.reader ?? const ReaderPreferences();
    final palette = ReaderPalette.byName(preferences.palette);
    return bookAsync.when(
      data: (book) {
        if (book == null) {
          return Scaffold(
            appBar: AppBar(leading: BackButton(onPressed: () => context.go('/'))),
            body: const Center(child: Text('No encontré este libro.')),
          );
        }
        final queryChapter = int.tryParse(GoRouterState.of(context).uri.queryParameters['chapter'] ?? '');
        final selected = _chapterIndex ??
            queryChapter ??
            settings?.lastChapterIndex ??
            (book.chapters.isNotEmpty ? book.chapters.first.index : 1);
        final chapter = book.chapters.firstWhere(
          (item) => item.index == selected,
          orElse: () => book.chapters.first,
        );
        if (chapter.audio != null && _loadedAudioPath == null) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              _loadAudio(book, chapter);
            }
          });
        }
        if (_timingAttempted != chapter.index) {
          _timingAttempted = chapter.index;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              _loadTiming(book, chapter);
            }
          });
        }
        if (settings?.lastBookId != book.id || settings?.lastChapterIndex != chapter.index) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              ref.read(settingsProvider.notifier).rememberBook(book.id, chapter.index);
            }
          });
        }
        return Scaffold(
          backgroundColor: palette.paper,
          appBar: AppBar(
            backgroundColor: palette.paper,
            foregroundColor: palette.ink,
            elevation: 0,
            scrolledUnderElevation: 0,
            leading: IconButton(
              tooltip: 'Volver al libro',
              onPressed: () => context.push('/books/${book.id}'),
              icon: const Icon(Icons.arrow_back),
            ),
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(book.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: palette.ink, fontSize: 16, fontWeight: FontWeight.w600)),
                Text(chapter.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: palette.inkFaint, fontSize: 11)),
              ],
            ),
            actions: [
              IconButton(
                tooltip: 'Índice',
                onPressed: () => _showToc(context, book, palette, chapter.index),
                icon: Icon(Icons.list, color: palette.inkSoft),
              ),
              IconButton(
                tooltip: 'Ajustes de lectura',
                onPressed: () => _showSettings(context, preferences, palette),
                icon: Icon(Icons.text_fields, color: palette.inkSoft),
              ),
            ],
          ),
          body: Column(
            children: [
              Expanded(
                child: Scrollbar(
                  controller: _scrollController,
                  child: SingleChildScrollView(
                    controller: _scrollController,
                    padding: const EdgeInsets.fromLTRB(24, 24, 24, 48),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 720),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              chapter.title,
                              style: TextStyle(
                                fontFamily: 'serif',
                                fontSize: preferences.fontSize + 12,
                                height: 1.15,
                                fontWeight: FontWeight.w600,
                                color: palette.ink,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Container(width: 44, height: 2, color: palette.accent),
                            const SizedBox(height: 24),
                            for (final image in book.images.where((image) => image.chapterIndex == chapter.index))
                              _ReaderImage(
                                book: book,
                                image: image,
                                palette: palette,
                              ),
                            for (final segment in chapter.segments)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 18),
                                child: Text.rich(
                                  _segmentSpan(
                                    segment,
                                    palette: palette,
                                    preferences: preferences,
                                    positionMs: _position.inMilliseconds,
                                  ),
                                ),
                              ),
                            if (chapter.segments.isEmpty)
                              Text(
                                'Este capítulo no tiene texto legible.',
                                style: TextStyle(color: palette.inkSoft),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              _ReaderFooter(
                palette: palette,
                chapter: chapter,
                book: book,
                hasAudio: chapter.audio != null,
                isPlaying: _isPlaying,
                position: _position,
                duration: _duration,
                onPlayPause: chapter.audio == null ? null : _togglePlay,
                onSeekBack: chapter.audio == null ? null : () => _seek(Duration(seconds: -15)),
                onSeekForward: chapter.audio == null ? null : () => _seek(const Duration(seconds: 15)),
                onConvert: chapter.audio == null ? () => context.push('/books/${book.id}/studio') : null,
                onPrevious: chapter.index > book.chapters.first.index
                    ? () => _goToChapter(book, chapter.index - 1)
                    : null,
                onNext: chapter.index < book.chapters.last.index
                    ? () => _goToChapter(book, chapter.index + 1)
                    : null,
              ),
            ],
          ),
        );
      },
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (error, stackTrace) => Scaffold(
        appBar: AppBar(leading: BackButton(onPressed: () => context.go('/'))),
        body: Center(child: Text('$error')),
      ),
    );
  }

  Future<void> _loadAudio(Book book, Chapter chapter) async {
    final relative = chapter.audio;
    final directory = book.directoryPath;
    if (relative == null || directory == null) {
      return;
    }
    final path = p.join(directory, relative);
    if (_loadedAudioPath == path) {
      return;
    }
    if (!File(path).existsSync()) {
      return;
    }
    _loadedAudioPath = path;
    await _player.stop();
    await _player.setSource(DeviceFileSource(path));
    await _player.setReleaseMode(ReleaseMode.stop);
    if (mounted) {
      setState(() {
        _position = Duration.zero;
        _duration = Duration.zero;
      });
    }
  }

  Future<void> _loadTiming(Book book, Chapter chapter) async {
    final directory = book.directoryPath;
    if (directory == null) {
      return;
    }
    final relative = chapter.timing ??
        'timings/chapter_${chapter.index.toString().padLeft(3, '0')}.json';
    final path = p.isAbsolute(relative) ? relative : p.join(directory, relative);
    final file = File(path);
    if (!await file.exists()) {
      if (mounted) {
        setState(() => _timing = null);
      }
      return;
    }
    try {
      final timing = ChapterTiming.fromJsonString(await file.readAsString());
      if (mounted) {
        setState(() => _timing = timing);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _timing = null);
      }
    }
  }

  TextSpan _segmentSpan(
    Segment segment, {
    required ReaderPalette palette,
    required ReaderPreferences preferences,
    required int positionMs,
  }) {
    final baseStyle = TextStyle(
      fontFamily: preferences.fontFamily,
      fontSize: preferences.fontSize,
      height: 1.72,
      color: palette.ink,
    );
    final timingSegment = _timing?.segments.firstWhereOrNull((item) => item.id == segment.id);
    final segmentActive = timingSegment != null &&
        positionMs >= timingSegment.startMs &&
        positionMs < timingSegment.endMs;
    final words = RegExp(r'\S+').allMatches(segment.text).toList(growable: false);
    if (!preferences.karaoke || timingSegment == null || timingSegment.words.isEmpty) {
      return TextSpan(
        text: segment.text,
        style: baseStyle.copyWith(
          backgroundColor: segmentActive ? palette.highlight : null,
        ),
      );
    }
    final spans = <TextSpan>[];
    var cursor = 0;
    for (var index = 0; index < words.length; index++) {
      final match = words[index];
      if (match.start > cursor) {
        spans.add(TextSpan(text: segment.text.substring(cursor, match.start), style: baseStyle));
      }
      final wordTiming = index < timingSegment.words.length ? timingSegment.words[index] : null;
      final wordActive = wordTiming != null &&
          positionMs >= wordTiming.startMs &&
          positionMs < wordTiming.endMs;
      spans.add(
        TextSpan(
          text: match.group(0),
          style: baseStyle.copyWith(
            backgroundColor: wordActive
                ? palette.highlightWord
                : segmentActive
                    ? palette.highlight
                    : null,
            fontWeight: wordActive ? FontWeight.w600 : null,
          ),
        ),
      );
      cursor = match.end;
    }
    if (cursor < segment.text.length) {
      spans.add(TextSpan(text: segment.text.substring(cursor), style: baseStyle));
    }
    return TextSpan(style: baseStyle, children: spans);
  }

  Future<void> _togglePlay() async {
    if (_isPlaying) {
      await _player.pause();
    } else {
      await _player.resume();
    }
  }

  Future<void> _seek(Duration delta) async {
    final target = _position + delta;
    final max = _duration;
    final clamped = target < Duration.zero
        ? Duration.zero
        : (max > Duration.zero && target > max ? max : target);
    await _player.seek(clamped);
  }

  void _goToChapter(Book book, int index) {
    setState(() => _chapterIndex = index);
    _player.stop();
    final chapter = book.chapters.firstWhere(
      (item) => item.index == index,
      orElse: () => book.chapters.first,
    );
    _loadedAudioPath = null;
    _timing = null;
    _timingAttempted = null;
    _loadAudio(book, chapter);
    _loadTiming(book, chapter);
    if (_scrollController.hasClients) {
      _scrollController.jumpTo(0);
    }
  }

  Future<void> _showToc(BuildContext context, Book book, ReaderPalette palette, int current) async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: palette.surface,
      isScrollControlled: true,
      builder: (context) {
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.7,
          maxChildSize: 0.9,
          builder: (context, controller) {
            return ListView.builder(
              controller: controller,
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
              itemCount: book.chapters.length + 1,
              itemBuilder: (context, index) {
                if (index == 0) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text('Índice', style: TextStyle(fontFamily: 'serif', fontSize: 24, fontWeight: FontWeight.w600, color: palette.ink)),
                  );
                }
                final chapter = book.chapters[index - 1];
                final active = chapter.index == current;
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(
                    chapter.title,
                    style: TextStyle(
                      color: active ? palette.accent : palette.ink,
                      fontWeight: active ? FontWeight.w600 : FontWeight.w400,
                    ),
                  ),
                  subtitle: Text('Capítulo ${chapter.index}', style: TextStyle(color: palette.inkFaint, fontSize: 11)),
                  trailing: active ? Icon(Icons.bookmark, size: 18, color: palette.accent) : null,
                  onTap: () {
                    Navigator.of(context).pop();
                    _goToChapter(book, chapter.index);
                  },
                );
              },
            );
          },
        );
      },
    );
  }

  Future<void> _showSettings(BuildContext context, ReaderPreferences preferences, ReaderPalette palette) async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: palette.surface,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            final current = ref.read(readerPreferencesProvider);
            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('Lectura', style: TextStyle(fontFamily: 'serif', fontSize: 24, fontWeight: FontWeight.w600, color: palette.ink)),
                  const SizedBox(height: 18),
                  Text('Paleta', style: TextStyle(color: palette.inkSoft, fontSize: 12)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final entry in const {'paper': 'Papel', 'sepia': 'Sepia', 'night': 'Noche'}.entries)
                        ChoiceChip(
                          label: Text(entry.value),
                          selected: current.palette == entry.key,
                          onSelected: (_) {
                            ref.read(settingsProvider.notifier).updateReader(current.copyWith(palette: entry.key));
                            setModalState(() {});
                          },
                        ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Text('Tamaño', style: TextStyle(color: palette.inkSoft, fontSize: 12)),
                  Slider(
                    value: current.fontSize,
                    min: 15,
                    max: 28,
                    divisions: 13,
                    label: '${current.fontSize.round()}',
                    onChanged: (value) {
                      ref.read(settingsProvider.notifier).updateReader(current.copyWith(fontSize: value));
                      setModalState(() {});
                    },
                  ),
                  const SizedBox(height: 8),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('Karaoke', style: TextStyle(color: palette.ink)),
                    value: current.karaoke,
                    onChanged: (value) {
                      ref.read(settingsProvider.notifier).updateReader(current.copyWith(karaoke: value));
                      setModalState(() {});
                    },
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _ReaderImage extends StatelessWidget {
  const _ReaderImage({required this.book, required this.image, required this.palette});

  final Book book;
  final BookImage image;
  final ReaderPalette palette;

  @override
  Widget build(BuildContext context) {
    final directory = book.directoryPath;
    final relative = image.path;
    if (directory == null || relative == null || relative.isEmpty) {
      return const SizedBox.shrink();
    }
    final file = File(p.join(directory, relative));
    if (!file.existsSync()) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BibliotecaRadii.md,
            child: Image.file(
              file,
              fit: BoxFit.contain,
              errorBuilder: (context, error, stackTrace) => const SizedBox.shrink(),
            ),
          ),
          if (image.caption != null && image.caption!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              image.caption!,
              style: TextStyle(color: palette.inkFaint, fontSize: 11, fontStyle: FontStyle.italic),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReaderFooter extends StatelessWidget {
  const _ReaderFooter({
    required this.palette,
    required this.chapter,
    required this.book,
    required this.hasAudio,
    required this.isPlaying,
    required this.position,
    required this.duration,
    this.onPlayPause,
    this.onSeekBack,
    this.onSeekForward,
    this.onConvert,
    this.onPrevious,
    this.onNext,
  });

  final ReaderPalette palette;
  final Chapter chapter;
  final Book book;
  final bool hasAudio;
  final bool isPlaying;
  final Duration position;
  final Duration duration;
  final VoidCallback? onPlayPause;
  final VoidCallback? onSeekBack;
  final VoidCallback? onSeekForward;
  final VoidCallback? onConvert;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;

  @override
  Widget build(BuildContext context) {
    final progress = duration.inMilliseconds <= 0
        ? 0.0
        : (position.inMilliseconds / duration.inMilliseconds).clamp(0.0, 1.0);
    return Container(
      decoration: BoxDecoration(
        color: palette.surface,
        border: Border(top: BorderSide(color: palette.line)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (hasAudio)
                Row(
                  children: [
                    IconButton(
                      tooltip: 'Retroceder 15 segundos',
                      onPressed: onSeekBack,
                      icon: Icon(Icons.replay_10, color: palette.inkSoft),
                    ),
                    IconButton(
                      tooltip: isPlaying ? 'Pausar' : 'Reproducir',
                      onPressed: onPlayPause,
                      icon: Icon(isPlaying ? Icons.pause_circle : Icons.play_circle, size: 34, color: palette.accent),
                    ),
                    IconButton(
                      tooltip: 'Avanzar 15 segundos',
                      onPressed: onSeekForward,
                      icon: Icon(Icons.forward_10, color: palette.inkSoft),
                    ),
                    Expanded(
                      child: Column(
                        children: [
                          ClipRRect(
                            borderRadius: const BorderRadius.all(Radius.circular(2)),
                            child: LinearProgressIndicator(
                              value: progress,
                              minHeight: 3,
                              backgroundColor: palette.line,
                              color: palette.accent,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(_duration(position), style: TextStyle(color: palette.inkFaint, fontSize: 10)),
                              Text(_duration(duration), style: TextStyle(color: palette.inkFaint, fontSize: 10)),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                )
              else
                Row(
                  children: [
                    Icon(Icons.graphic_eq, size: 18, color: palette.inkFaint),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Este capítulo todavía no tiene audio.',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                    ),
                    TextButton(
                      onPressed: onConvert,
                      child: const Text('Convertir'),
                    ),
                  ],
                ),
              Row(
                children: [
                  IconButton(
                    tooltip: 'Capítulo anterior',
                    onPressed: onPrevious,
                    icon: Icon(Icons.chevron_left, color: palette.inkSoft),
                  ),
                  Expanded(
                    child: Column(
                      children: [
                        Text(
                          chapter.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: palette.ink, fontSize: 12, fontWeight: FontWeight.w600),
                        ),
                        Text(
                          '${chapter.index} / ${book.chapterCount}',
                          style: TextStyle(color: palette.inkFaint, fontSize: 10),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Capítulo siguiente',
                    onPressed: onNext,
                    icon: Icon(Icons.chevron_right, color: palette.inkSoft),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _duration(Duration value) {
    final minutes = value.inMinutes;
    final seconds = value.inSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }
}
