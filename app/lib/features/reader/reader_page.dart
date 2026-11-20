import 'dart:async';
import 'dart:io';

import 'package:collection/collection.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:path/path.dart' as p;

import '../../app/providers.dart';
import '../../core/design/theme.dart';
import '../../core/design/tokens.dart';
import '../../data/ambience/ambience_library.dart';
import '../../domain/ambience.dart';
import '../../domain/bookmarks.dart';
import '../../domain/models.dart';
import '../../domain/timing.dart';
import 'audio_transport.dart';
import 'book_reader.dart';
import 'original_reader.dart';
import 'reader_playback.dart';
import 'reader_search.dart';
import 'reader_view_mode.dart';

class ReaderPage extends ConsumerStatefulWidget {
  const ReaderPage({super.key, required this.bookId});

  final String bookId;

  @override
  ConsumerState<ReaderPage> createState() => _ReaderPageState();
}

class _ReaderPageState extends ConsumerState<ReaderPage> {
  final _scrollController = ScrollController();
  ReaderPlaybackController? _playback;
  StreamSubscription<AudioTransportState>? _playingSubscription;
  StreamSubscription<Duration>? _positionSubscription;
  StreamSubscription<Duration>? _durationSubscription;
  int? _chapterIndex;
  int? _timingAttempted;
  int? _pendingSeekMs;
  int? _currentChapterIndex;
  int _lastSavedSecond = -1;
  ChapterTiming? _timing;
  String? _bookDirectory;
  String? _ambienceChapterPreset;
  bool _ambiencePlanSuppressed = false;
  bool _restored = false;
  bool _ambienceSynced = false;
  bool _isPlaying = false;
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;
  Timer? _sleepTimer;
  DateTime? _sleepDeadline;
  int? _sleepMinutes;
  bool _immersive = false;
  int _readingCharOffset = 0;

  @override
  void initState() {
    super.initState();
    final transports = ref.read(readerTransportsFactoryProvider)();
    _playback = ReaderPlaybackController(
      transports: transports,
      ambienceResolver: (preset) =>
          const AmbienceLibrary().ensurePreset(preset),
    );
    _playingSubscription = _playback!.onVoiceStateChanged.listen((state) {
      if (mounted) {
        setState(() => _isPlaying = state == AudioTransportState.playing);
        if (state == AudioTransportState.completed) {
          unawaited(_autoAdvanceIfNeeded());
        }
      }
    });
    _positionSubscription = _playback!.onPositionChanged.listen((position) {
      if (mounted) {
        setState(() => _position = position);
        if (position.inSeconds > 0 &&
            position.inSeconds != _lastSavedSecond &&
            position.inSeconds % 5 == 0) {
          _lastSavedSecond = position.inSeconds;
          unawaited(_saveReadingState());
        }
      }
    });
    _durationSubscription = _playback!.onDurationChanged.listen((duration) {
      if (mounted) {
        setState(() => _duration = duration);
      }
    });
  }

  @override
  void dispose() {
    unawaited(_saveReadingState());
    _sleepTimer?.cancel();
    _playingSubscription?.cancel();
    _positionSubscription?.cancel();
    _durationSubscription?.cancel();
    unawaited(_playback?.dispose());
    _scrollController.dispose();
    if (_immersive) {
      unawaited(SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge));
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bookAsync = ref.watch(bookProvider(widget.bookId));
    final bookmarkAsync = ref.watch(bookmarkDataProvider(widget.bookId));
    final ambiencePlanAsync = ref.watch(ambiencePlanProvider(widget.bookId));
    final settings = ref.watch(settingsProvider).value;
    final preferences = settings?.reader ?? const ReaderPreferences();
    final palette = ReaderPalette.byName(preferences.palette);
    final viewMode = ReaderViewMode.fromName(preferences.viewMode);
    return bookAsync.when(
      data: (book) {
        if (book == null) {
          return Scaffold(
            appBar: AppBar(
              leading: BackButton(onPressed: () => context.go('/')),
            ),
            body: const Center(child: Text('No encontré este libro.')),
          );
        }
        final queryChapter = int.tryParse(
          GoRouterState.of(context).uri.queryParameters['chapter'] ?? '',
        );
        final stored = bookmarkAsync.value;
        if (!_restored && stored != null) {
          _restored = true;
          final state = stored.readingState;
          if (queryChapter == null &&
              state != null &&
              book.chapters.any((item) => item.index == state.chapterIndex)) {
            _chapterIndex = state.chapterIndex;
            _pendingSeekMs = state.positionMs;
          }
        }
        final selected =
            _chapterIndex ??
            queryChapter ??
            settings?.lastChapterIndex ??
            (book.chapters.isNotEmpty ? book.chapters.first.index : 1);
        final chapter = book.chapters.firstWhere(
          (item) => item.index == selected,
          orElse: () => book.chapters.first,
        );
        _bookDirectory = book.directoryPath;
        _currentChapterIndex = chapter.index;
        final activeTiming = _timing?.segmentAt(_position.inMilliseconds);
        final activeSegmentId = activeTiming?.id;
        if (activeSegmentId != null) {
          final activeSegment = chapter.segments.firstWhereOrNull(
            (segment) => segment.id == activeSegmentId,
          );
          if (activeSegment != null) {
            final offset = chapter.text.indexOf(activeSegment.text);
            if (offset >= 0) {
              _readingCharOffset = offset;
            }
          }
        }
        final chapterPlan = ambiencePlanAsync.value?.forChapter(chapter.index);
        final chapterPreset = _ambiencePlanSuppressed
            ? null
            : chapterPlan?.presetId;
        if (settings != null &&
            (!_ambienceSynced || _ambienceChapterPreset != chapterPreset)) {
          _ambienceSynced = true;
          _ambienceChapterPreset = chapterPreset;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              _syncAmbienceFrom(settings, chapterPreset: chapterPreset);
            }
          });
        }
        if (chapter.audio != null &&
            _playback?.loadedChapterIndex != chapter.index) {
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
        if (settings?.lastBookId != book.id ||
            settings?.lastChapterIndex != chapter.index) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              ref
                  .read(settingsProvider.notifier)
                  .rememberBook(book.id, chapter.index);
            }
          });
        }
        return Theme(
          data: buildBibliotecaTheme(dark: palette.name == 'night'),
          child: Focus(
            autofocus: true,
            onKeyEvent: _onKeyEvent,
            child: Builder(
              builder: (context) {
                return PopScope<Object?>(
                  canPop: false,
                  onPopInvokedWithResult: (didPop, result) {
                    if (!didPop) {
                      unawaited(_leaveReader());
                    }
                  },
                  child: Scaffold(
                    backgroundColor: palette.paper,
                    appBar: _immersive
                        ? null
                        : AppBar(
                            backgroundColor: palette.paper,
                            foregroundColor: palette.ink,
                            elevation: 0,
                            scrolledUnderElevation: 0,
                            leading: IconButton(
                              tooltip: 'Volver al libro',
                              onPressed: () => unawaited(_leaveReader()),
                              icon: const Icon(Icons.arrow_back),
                            ),
                            title: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  book.title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: palette.ink,
                                    fontSize: 16,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Text(
                                  chapter.title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: palette.inkFaint,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                            actions: [
                              IconButton(
                                tooltip: 'Ambiente',
                                onPressed: () =>
                                    _showAmbience(context, palette),
                                icon: Icon(
                                  settings?.ambienceEnabled == true
                                      ? Icons.forest
                                      : Icons.forest_outlined,
                                  color: settings?.ambienceEnabled == true
                                      ? palette.accent
                                      : palette.inkSoft,
                                ),
                              ),
                              IconButton(
                                tooltip: 'Marcadores',
                                onPressed: () => _showBookmarks(
                                  context,
                                  book,
                                  chapter,
                                  palette,
                                ),
                                icon: Icon(
                                  Icons.bookmarks_outlined,
                                  color: palette.inkSoft,
                                ),
                              ),
                              IconButton(
                                tooltip: 'Índice',
                                onPressed: () => _showToc(
                                  context,
                                  book,
                                  palette,
                                  chapter.index,
                                ),
                                icon: Icon(Icons.list, color: palette.inkSoft),
                              ),
                              PopupMenuButton<ReaderViewMode>(
                                tooltip: 'Modo de lectura',
                                icon: Icon(
                                  _modeIcon(viewMode),
                                  color: palette.inkSoft,
                                ),
                                onSelected: (mode) {
                                  ref
                                      .read(settingsProvider.notifier)
                                      .updateReader(
                                        preferences.copyWith(
                                          viewMode: mode.name,
                                        ),
                                      );
                                },
                                itemBuilder: (context) => [
                                  for (final mode in ReaderViewMode.values)
                                    CheckedPopupMenuItem(
                                      value: mode,
                                      checked: viewMode == mode,
                                      child: Text(mode.label),
                                    ),
                                ],
                              ),
                              PopupMenuButton<int>(
                                tooltip: _sleepTooltip(),
                                icon: Icon(
                                  _sleepMinutes == null
                                      ? Icons.bedtime_outlined
                                      : Icons.bedtime,
                                  color: _sleepMinutes == null
                                      ? palette.inkSoft
                                      : palette.accent,
                                ),
                                onSelected: _setSleepTimer,
                                itemBuilder: (context) => [
                                  const PopupMenuItem(
                                    value: 0,
                                    child: Text('Sin temporizador'),
                                  ),
                                  for (final minutes in const [
                                    5,
                                    15,
                                    30,
                                    45,
                                    60,
                                  ])
                                    PopupMenuItem(
                                      value: minutes,
                                      child: Text('$minutes minutos'),
                                    ),
                                ],
                              ),
                              PopupMenuButton<String>(
                                tooltip: 'Más opciones',
                                onSelected: (value) {
                                  switch (value) {
                                    case 'search':
                                      _showSearch(book);
                                    case 'typography':
                                      _showSettings(
                                        context,
                                        preferences,
                                        palette,
                                      );
                                    case 'bookmark_page':
                                      unawaited(
                                        _addReadingBookmark(book, chapter),
                                      );
                                    case 'fullscreen':
                                      _toggleImmersive();
                                    case 'shortcuts':
                                      _showShortcuts(context);
                                  }
                                },
                                itemBuilder: (context) => const [
                                  PopupMenuItem(
                                    value: 'search',
                                    height: 44,
                                    child: Row(
                                      children: [
                                        Icon(Icons.search, size: 18),
                                        SizedBox(width: 10),
                                        Text('Buscar en el libro'),
                                      ],
                                    ),
                                  ),
                                  PopupMenuItem(
                                    value: 'bookmark_page',
                                    height: 44,
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.bookmark_add_outlined,
                                          size: 18,
                                        ),
                                        SizedBox(width: 10),
                                        Text('Marcar esta página'),
                                      ],
                                    ),
                                  ),
                                  PopupMenuItem(
                                    value: 'typography',
                                    height: 44,
                                    child: Row(
                                      children: [
                                        Icon(Icons.text_fields, size: 18),
                                        SizedBox(width: 10),
                                        Text('Ajustes de lectura'),
                                      ],
                                    ),
                                  ),
                                  PopupMenuItem(
                                    value: 'fullscreen',
                                    height: 44,
                                    child: Row(
                                      children: [
                                        Icon(Icons.fullscreen, size: 18),
                                        SizedBox(width: 10),
                                        Text('Pantalla completa'),
                                      ],
                                    ),
                                  ),
                                  PopupMenuItem(
                                    value: 'shortcuts',
                                    height: 44,
                                    child: Row(
                                      children: [
                                        Icon(Icons.keyboard_outlined, size: 18),
                                        SizedBox(width: 10),
                                        Text('Atajos de teclado'),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                    body: Stack(
                      children: [
                        Column(
                          children: [
                            Expanded(
                              child: switch (viewMode) {
                                ReaderViewMode.text => Scrollbar(
                                  controller: _scrollController,
                                  child: SingleChildScrollView(
                                    controller: _scrollController,
                                    padding: const EdgeInsets.fromLTRB(
                                      24,
                                      24,
                                      24,
                                      48,
                                    ),
                                    child: Center(
                                      child: ConstrainedBox(
                                        constraints: const BoxConstraints(
                                          maxWidth: 720,
                                        ),
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              chapter.title,
                                              style: TextStyle(
                                                fontFamily: 'serif',
                                                fontSize:
                                                    preferences.fontSize + 12,
                                                height: 1.15,
                                                fontWeight: FontWeight.w600,
                                                color: palette.ink,
                                              ),
                                            ),
                                            const SizedBox(height: 8),
                                            Container(
                                              width: 44,
                                              height: 2,
                                              color: palette.accent,
                                            ),
                                            const SizedBox(height: 24),
                                            for (final image
                                                in book.images.where(
                                                  (image) =>
                                                      image.chapterIndex ==
                                                      chapter.index,
                                                ))
                                              _ReaderImage(
                                                book: book,
                                                image: image,
                                                palette: palette,
                                              ),
                                            for (final segment
                                                in chapter.segments)
                                              Padding(
                                                padding: const EdgeInsets.only(
                                                  bottom: 18,
                                                ),
                                                child: Text.rich(
                                                  _segmentSpan(
                                                    segment,
                                                    palette: palette,
                                                    preferences: preferences,
                                                    positionMs: _position
                                                        .inMilliseconds,
                                                  ),
                                                ),
                                              ),
                                            if (chapter.segments.isEmpty)
                                              Text(
                                                'Este capítulo no tiene texto legible.',
                                                style: TextStyle(
                                                  color: palette.inkSoft,
                                                ),
                                              ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                                ReaderViewMode.book => BookReader(
                                  book: book,
                                  chapter: chapter,
                                  palette: palette,
                                  preferences: preferences,
                                  activeSegmentId: activeSegmentId,
                                ),
                                ReaderViewMode.original => OriginalReader(
                                  book: book,
                                  chapter: chapter,
                                  palette: palette,
                                  preferences: preferences,
                                  onChapterLink: (index) =>
                                      unawaited(_goToChapter(book, index)),
                                ),
                              },
                            ),
                            if (!_immersive)
                              _ReaderFooter(
                                palette: palette,
                                chapter: chapter,
                                book: book,
                                hasAudio: chapter.audio != null,
                                isPlaying: _isPlaying,
                                position: _position,
                                duration: _duration,
                                onPlayPause: chapter.audio == null
                                    ? null
                                    : () => unawaited(_togglePlay()),
                                onSeekBack: chapter.audio == null
                                    ? null
                                    : () => unawaited(
                                        _seek(Duration(seconds: -15)),
                                      ),
                                onSeekForward: chapter.audio == null
                                    ? null
                                    : () => unawaited(
                                        _seek(const Duration(seconds: 15)),
                                      ),
                                onConvert: chapter.audio == null
                                    ? () => context.push(
                                        '/books/${book.id}/studio',
                                      )
                                    : null,
                                onPrevious:
                                    chapter.index > book.chapters.first.index
                                    ? () =>
                                          _goToChapter(book, chapter.index - 1)
                                    : null,
                                onNext: chapter.index < book.chapters.last.index
                                    ? () =>
                                          _goToChapter(book, chapter.index + 1)
                                    : null,
                              ),
                          ],
                        ),
                        if (_immersive)
                          Positioned(
                            top: 8,
                            right: 8,
                            child: Material(
                              color: palette.paper.withValues(alpha: 0.9),
                              shape: const CircleBorder(),
                              child: IconButton(
                                tooltip: 'Salir de pantalla completa',
                                onPressed: _toggleImmersive,
                                icon: Icon(
                                  Icons.fullscreen_exit,
                                  color: palette.ink,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        );
      },
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (error, stackTrace) => Scaffold(
        appBar: AppBar(leading: BackButton(onPressed: () => context.go('/'))),
        body: Center(child: Text('$error')),
      ),
    );
  }

  IconData _modeIcon(ReaderViewMode mode) {
    return switch (mode) {
      ReaderViewMode.text => Icons.notes,
      ReaderViewMode.book => Icons.auto_stories,
      ReaderViewMode.original => Icons.chrome_reader_mode,
    };
  }

  String _sleepTooltip() {
    final minutes = _sleepMinutes;
    if (minutes == null) {
      return 'Temporizador';
    }
    final deadline = _sleepDeadline;
    final remaining = deadline == null
        ? minutes
        : deadline.difference(DateTime.now()).inMinutes;
    return 'Se pausa en ~${remaining < 1 ? 1 : remaining} min';
  }

  void _setSleepTimer(int minutes) {
    _sleepTimer?.cancel();
    if (minutes <= 0) {
      setState(() {
        _sleepMinutes = null;
        _sleepDeadline = null;
      });
      return;
    }
    final deadline = DateTime.now().add(Duration(minutes: minutes));
    setState(() {
      _sleepMinutes = minutes;
      _sleepDeadline = deadline;
    });
    _sleepTimer = Timer(Duration(minutes: minutes), () async {
      await _playback?.pause();
      if (mounted) {
        setState(() {
          _sleepMinutes = null;
          _sleepDeadline = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Temporizador: reproducción pausada.')),
        );
      }
    });
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('Se pausará en $minutes minutos.')));
  }

  void _toggleImmersive() {
    setState(() => _immersive = !_immersive);
    if (Platform.isAndroid || Platform.isIOS) {
      unawaited(
        SystemChrome.setEnabledSystemUIMode(
          _immersive ? SystemUiMode.immersiveSticky : SystemUiMode.edgeToEdge,
        ),
      );
    }
  }

  void _changeSpeed(double delta) {
    final settings = ref.read(settingsProvider).value;
    if (settings == null) {
      return;
    }
    final next = (settings.reader.playbackRate + delta).clamp(0.5, 2.5);
    ref
        .read(settingsProvider.notifier)
        .updateReader(settings.reader.copyWith(playbackRate: next));
    _playback?.setVoiceRate(next);
  }

  KeyEventResult _onKeyEvent(FocusNode node, KeyEvent event) {
    if (event is! KeyDownEvent) {
      return KeyEventResult.ignored;
    }
    final key = event.logicalKey;
    if (key == LogicalKeyboardKey.space) {
      unawaited(_togglePlay());
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.arrowLeft) {
      unawaited(_seek(const Duration(seconds: -15)));
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.arrowRight) {
      unawaited(_seek(const Duration(seconds: 15)));
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.keyJ || key == LogicalKeyboardKey.keyK) {
      final book = ref.read(bookProvider(widget.bookId)).value;
      final current = _currentChapterIndex;
      if (book != null && current != null) {
        final index = key == LogicalKeyboardKey.keyJ
            ? current - 1
            : current + 1;
        if (book.chapters.any((chapter) => chapter.index == index)) {
          unawaited(_goToChapter(book, index));
        }
      }
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.equal ||
        key == LogicalKeyboardKey.add ||
        key == LogicalKeyboardKey.numpadAdd) {
      _changeSpeed(0.25);
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.minus ||
        key == LogicalKeyboardKey.numpadSubtract) {
      _changeSpeed(-0.25);
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.keyT) {
      final book = ref.read(bookProvider(widget.bookId)).value;
      final settings = ref.read(settingsProvider).value;
      if (book != null) {
        final palette = ReaderPalette.byName(
          settings?.reader.palette ?? 'paper',
        );
        unawaited(
          _showToc(
            context,
            book,
            palette,
            _currentChapterIndex ?? settings?.lastChapterIndex ?? 1,
          ),
        );
      }
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.keyF) {
      _toggleImmersive();
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.slash &&
        HardwareKeyboard.instance.isShiftPressed) {
      _showShortcuts(context);
      return KeyEventResult.handled;
    }
    if (key == LogicalKeyboardKey.escape) {
      if (_immersive) {
        _toggleImmersive();
      } else {
        unawaited(_leaveReader());
      }
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  void _showShortcuts(BuildContext context) {
    const rows = [
      ('Espacio', 'Reproducir o pausar'),
      ('← / →', 'Retroceder o adelantar 15 s'),
      ('J / K', 'Capítulo anterior o siguiente'),
      ('+ / -', 'Cambiar velocidad'),
      ('T', 'Abrir el índice'),
      ('F', 'Pantalla completa'),
      ('?', 'Esta ayuda'),
      ('Esc', 'Salir del lector'),
    ];
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Leer sin soltar el teclado'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final row in rows)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 92,
                        child: Text(
                          row.$1,
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Expanded(child: Text(row.$2)),
                    ],
                  ),
                ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  Future<void> _addReadingBookmark(Book book, Chapter chapter) async {
    final directory = book.directoryPath;
    if (directory == null) {
      return;
    }
    final bookmark = ReadingBookmark(
      id: '${DateTime.now().microsecondsSinceEpoch}',
      chapterIndex: chapter.index,
      charOffset: _readingCharOffset,
      pageIndex: 0,
      createdAt: DateTime.now().toUtc().toIso8601String(),
    );
    await ref
        .read(bookmarkRepositoryProvider)
        .addReadingBookmark(directory, bookmark);
    ref.invalidate(bookmarkDataProvider(book.id));
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Página marcada.')));
    }
  }

  Future<void> _removeReadingBookmark(String id) async {
    final directory = _bookDirectory;
    if (directory == null) {
      return;
    }
    await ref
        .read(bookmarkRepositoryProvider)
        .removeReadingBookmark(directory, id);
    ref.invalidate(bookmarkDataProvider(widget.bookId));
  }

  Future<void> _loadAudio(Book book, Chapter chapter) async {
    final playback = _playback;
    if (playback == null) {
      return;
    }
    final relative = chapter.audio;
    final directory = book.directoryPath;
    if (relative == null || directory == null) {
      return;
    }
    final path = p.join(directory, relative);
    final reader = ref.read(readerPreferencesProvider);
    final startAtMs = _pendingSeekMs;
    _pendingSeekMs = null;
    await playback.loadChapter(
      chapterIndex: chapter.index,
      audioPath: File(path).existsSync() ? path : null,
      startAtMs: startAtMs,
      volume: reader.volume,
      rate: reader.playbackRate,
    );
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
    final relative =
        chapter.timing ??
        'timings/chapter_${chapter.index.toString().padLeft(3, '0')}.json';
    final path = p.isAbsolute(relative)
        ? relative
        : p.join(directory, relative);
    final file = File(path);
    if (!file.existsSync()) {
      if (mounted) {
        setState(() => _timing = null);
      }
      return;
    }
    try {
      final timing = ChapterTiming.fromJsonString(file.readAsStringSync());
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
    final timingSegment = _timing?.segments.firstWhereOrNull(
      (item) => item.id == segment.id,
    );
    final segmentActive =
        timingSegment != null &&
        positionMs >= timingSegment.startMs &&
        positionMs < timingSegment.endMs;
    final words = RegExp(r'\S+')
        .allMatches(segment.text)
        .toList(growable: false);
    if (!preferences.karaoke ||
        timingSegment == null ||
        timingSegment.words.isEmpty) {
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
        spans.add(
          TextSpan(
            text: segment.text.substring(cursor, match.start),
            style: baseStyle,
          ),
        );
      }
      final wordTiming = index < timingSegment.words.length
          ? timingSegment.words[index]
          : null;
      final wordActive =
          wordTiming != null &&
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
      spans.add(
        TextSpan(text: segment.text.substring(cursor), style: baseStyle),
      );
    }
    return TextSpan(style: baseStyle, children: spans);
  }

  /// Stops playback and only then leaves the reader. The old back button
  /// pushed a new detail page on top, leaving this one (and its audio) alive.
  Future<void> _leaveReader() async {
    await _playback?.stopAll();
    if (!mounted) {
      return;
    }
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/books/${widget.bookId}');
    }
  }

  Future<void> _togglePlay() async {
    await _playback?.togglePlayPause();
  }

  Future<void> _seek(Duration delta) async {
    await _playback?.seekBy(delta);
  }

  void _syncAmbienceFrom(AppSettings settings, {String? chapterPreset}) {
    final preset = AmbiencePresetDetails.byId(
      _ambiencePlanSuppressed ? null : chapterPreset ?? settings.ambiencePreset,
    );
    unawaited(
      _playback?.syncAmbience(
        enabled: settings.ambienceEnabled,
        preset: preset,
        volume: settings.ambienceVolume,
        ducking: settings.ambienceDucking,
      ),
    );
  }

  void _applyPlaybackPreferences() {
    final reader = ref.read(readerPreferencesProvider);
    _playback?.setVoiceRate(reader.playbackRate);
    _playback?.setVoiceVolume(reader.volume);
  }

  Future<void> _showAmbience(
    BuildContext context,
    ReaderPalette palette,
  ) async {
    final current = ref.read(settingsProvider).value ?? const AppSettings();
    var enabled = current.ambienceEnabled;
    var preset = AmbiencePresetDetails.byId(current.ambiencePreset);
    var volume = current.ambienceVolume;
    var ducking = current.ambienceDucking;
    final chapterIndex = _currentChapterIndex;
    final planPresetId = chapterIndex == null
        ? null
        : ref
              .read(ambiencePlanProvider(widget.bookId))
              .value
              ?.forChapter(chapterIndex)
              ?.presetId;
    var followingPlan = planPresetId != null && !_ambiencePlanSuppressed;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: palette.surface,
      isScrollControlled: true,
      builder: (context) {
        return SafeArea(
          child: SingleChildScrollView(
            padding: EdgeInsets.only(
              bottom: MediaQuery.viewInsetsOf(context).bottom,
            ),
            child: StatefulBuilder(
              builder: (context, setModalState) {
                final effective = followingPlan
                    ? AmbiencePresetDetails.byId(planPresetId)
                    : preset;
                Future<void> apply({
                  bool? enabledValue,
                  AmbiencePreset? presetValue,
                  double? volumeValue,
                  double? duckingValue,
                  bool? followPlan,
                }) async {
                  enabled = enabledValue ?? enabled;
                  preset = presetValue ?? preset;
                  volume = volumeValue ?? volume;
                  ducking = duckingValue ?? ducking;
                  if (followPlan != null) {
                    followingPlan = followPlan;
                    _ambiencePlanSuppressed = !followPlan;
                    _ambienceChapterPreset = followPlan ? planPresetId : null;
                  }
                  setModalState(() {});
                  await ref
                      .read(settingsProvider.notifier)
                      .updateAmbience(
                        enabled: enabled,
                        preset: preset.id,
                        volume: volume,
                        ducking: ducking,
                      );
                  final updated = ref.read(settingsProvider).value;
                  if (updated != null) {
                    _syncAmbienceFrom(
                      updated,
                      chapterPreset: followingPlan ? planPresetId : null,
                    );
                  }
                  if (mounted) {
                    setModalState(() {});
                  }
                }

                return Padding(
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              'Ambiente',
                              style: TextStyle(
                                fontFamily: 'serif',
                                fontSize: 24,
                                fontWeight: FontWeight.w600,
                                color: palette.ink,
                              ),
                            ),
                          ),
                          Switch(
                            value: enabled,
                            onChanged: (value) => apply(enabledValue: value),
                          ),
                        ],
                      ),
                      Text(
                        'Grabaciones de campo CC0. Se atenúan mientras suena la voz.',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                      if (planPresetId != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          followingPlan
                              ? 'Este capítulo usa ${AmbiencePresetDetails.byId(planPresetId).label} según el plan del libro.'
                              : 'Usás el paisaje global; el plan del libro no se aplica en este capítulo.',
                          style: TextStyle(
                            color: palette.inkFaint,
                            fontSize: 11,
                          ),
                        ),
                        if (!followingPlan)
                          Align(
                            alignment: Alignment.centerLeft,
                            child: TextButton(
                              onPressed: () =>
                                  apply(followPlan: true, enabledValue: true),
                              child: const Text('Volver al plan del libro'),
                            ),
                          ),
                      ],
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final item in AmbiencePreset.values)
                            ChoiceChip(
                              label: Text(item.label),
                              selected: effective == item,
                              onSelected: enabled
                                  ? (_) => apply(
                                      presetValue: item,
                                      enabledValue: true,
                                      followPlan: false,
                                    )
                                  : null,
                            ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Volumen',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                      Slider(
                        value: volume,
                        min: 0,
                        max: 1,
                        divisions: 20,
                        label: '${(volume * 100).round()}%',
                        onChanged: enabled
                            ? (value) {
                                setModalState(() => volume = value);
                                _playback?.setAmbienceVolumeLive(
                                  volume: value,
                                  ducking: ducking,
                                );
                              }
                            : null,
                        onChangeEnd: enabled
                            ? (value) => apply(volumeValue: value)
                            : null,
                      ),
                      Text(
                        'Atenuación con la voz',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                      Slider(
                        value: ducking,
                        min: 0,
                        max: 1,
                        divisions: 20,
                        label: '${(ducking * 100).round()}%',
                        onChanged: enabled
                            ? (value) {
                                setModalState(() => ducking = value);
                                _playback?.setAmbienceVolumeLive(
                                  volume: volume,
                                  ducking: value,
                                );
                              }
                            : null,
                        onChangeEnd: enabled
                            ? (value) => apply(duckingValue: value)
                            : null,
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              effective.description,
                              style: TextStyle(
                                color: palette.inkFaint,
                                fontSize: 11,
                              ),
                            ),
                          ),
                          TextButton(
                            onPressed: () => apply(enabledValue: false),
                            child: const Text('Detener'),
                          ),
                        ],
                      ),
                      if (_playback?.ambienceError != null) ...[
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                '${_playback!.ambienceError} Reintentá desde acá.',
                                style: TextStyle(
                                  color: palette.inkFaint,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                            TextButton(
                              onPressed: enabled
                                  ? () => apply(enabledValue: true)
                                  : null,
                              child: const Text('Reintentar'),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }

  Future<void> _goToChapter(
    Book book,
    int index, {
    int? positionMs,
    bool autoPlay = false,
  }) async {
    setState(() {
      _chapterIndex = index;
      _position = Duration.zero;
      _duration = Duration.zero;
    });
    _restored = true;
    _ambiencePlanSuppressed = false;
    final chapter = book.chapters.firstWhere(
      (item) => item.index == index,
      orElse: () => book.chapters.first,
    );
    _pendingSeekMs = positionMs;
    _timing = null;
    _timingAttempted = null;
    _currentChapterIndex = chapter.index;
    unawaited(_saveReadingState());
    await _loadAudio(book, chapter);
    if (autoPlay && chapter.audio != null) {
      await _playback?.startPlayback();
    }
    await _loadTiming(book, chapter);
    if (_scrollController.hasClients) {
      _scrollController.jumpTo(0);
    }
  }

  Future<void> _autoAdvanceIfNeeded() async {
    final preferences = ref.read(settingsProvider).value?.reader;
    if (preferences?.autoAdvance != true || _isPlaying) {
      return;
    }
    final book = ref.read(bookProvider(widget.bookId)).value;
    final currentIndex = _currentChapterIndex;
    if (book == null || currentIndex == null) {
      return;
    }
    final position = book.chapters.indexWhere(
      (chapter) => chapter.index == currentIndex,
    );
    if (position < 0 || position + 1 >= book.chapters.length) {
      return;
    }
    final next = book.chapters[position + 1];
    await _goToChapter(book, next.index, autoPlay: true);
  }

  Future<void> _saveReadingState() async {
    final directory = _bookDirectory;
    final chapter = _currentChapterIndex;
    if (directory == null || chapter == null) {
      return;
    }
    try {
      await ref
          .read(bookmarkRepositoryProvider)
          .saveReadingState(
            directory,
            ReadingState(
              chapterIndex: chapter,
              positionMs: _position.inMilliseconds,
              updatedAt: DateTime.now().toUtc().toIso8601String(),
            ),
          );
    } catch (_) {
      // A failed position save must not interrupt reading.
    }
  }

  Future<void> _addBookmark(Book book) async {
    final directory = book.directoryPath;
    final chapterIndex = _currentChapterIndex;
    if (directory == null || chapterIndex == null) {
      return;
    }
    final chapter = book.chapters.firstWhere(
      (item) => item.index == chapterIndex,
      orElse: () => book.chapters.first,
    );
    final bookmark = Bookmark(
      id: '${DateTime.now().microsecondsSinceEpoch}',
      chapterIndex: chapter.index,
      positionMs: _position.inMilliseconds,
      createdAt: DateTime.now().toUtc().toIso8601String(),
      chapterTitle: chapter.title,
    );
    await ref.read(bookmarkRepositoryProvider).addBookmark(directory, bookmark);
    ref.invalidate(bookmarkDataProvider(widget.bookId));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Marcador guardado: ${chapter.title}.')),
      );
    }
  }

  Future<void> _removeBookmark(String bookmarkId) async {
    final directory = _bookDirectory;
    if (directory == null) {
      return;
    }
    await ref
        .read(bookmarkRepositoryProvider)
        .removeBookmark(directory, bookmarkId);
    ref.invalidate(bookmarkDataProvider(widget.bookId));
  }

  String _formatPosition(int milliseconds) {
    if (milliseconds <= 0) {
      return 'Inicio del capítulo';
    }
    final minutes = milliseconds ~/ 60000;
    final seconds = (milliseconds % 60000) ~/ 1000;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  void _showSearch(Book book) {
    showSearch<ReaderSearchHit>(
      context: context,
      delegate: BookSearchDelegate(
        book: book,
        palette: ReaderPalette.byName(
          ref.read(settingsProvider).value?.reader.palette ?? 'paper',
        ),
        onSelect: (hit) {
          unawaited(_goToChapter(book, hit.chapterIndex));
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Encontrado en ${hit.chapterTitle}.')),
            );
          }
        },
      ),
    );
  }

  Future<void> _showBookmarks(
    BuildContext context,
    Book book,
    Chapter chapter,
    ReaderPalette palette,
  ) async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: palette.surface,
      isScrollControlled: true,
      builder: (context) {
        return Consumer(
          builder: (context, ref, child) {
            final data =
                ref.watch(bookmarkDataProvider(widget.bookId)).value ??
                BookmarkData.empty;
            final bookmarks = data.bookmarks.reversed.toList(growable: false);
            return DraggableScrollableSheet(
              expand: false,
              initialChildSize: 0.6,
              maxChildSize: 0.9,
              builder: (context, controller) {
                return ListView(
                  controller: controller,
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
                  children: [
                    Text(
                      'Marcadores',
                      style: TextStyle(
                        fontFamily: 'serif',
                        fontSize: 24,
                        fontWeight: FontWeight.w600,
                        color: palette.ink,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Guardá la posición actual para volver después.',
                      style: TextStyle(color: palette.inkSoft, fontSize: 12),
                    ),
                    const SizedBox(height: 14),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: FilledButton.icon(
                        onPressed: () => _addBookmark(book),
                        icon: const Icon(Icons.bookmark_add, size: 18),
                        label: const Text('Guardar esta posición'),
                      ),
                    ),
                    const SizedBox(height: 12),
                    if (bookmarks.isEmpty)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 28),
                        child: Text(
                          'Todavía no hay marcadores en este libro.',
                          style: TextStyle(color: palette.inkSoft),
                        ),
                      )
                    else
                      for (final bookmark in bookmarks)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(Icons.bookmark, color: palette.accent),
                          title: Text(
                            bookmark.chapterTitle ??
                                'Capítulo ${bookmark.chapterIndex}',
                            style: TextStyle(color: palette.ink),
                          ),
                          subtitle: Text(
                            _formatPosition(bookmark.positionMs),
                            style: TextStyle(
                              color: palette.inkFaint,
                              fontSize: 11,
                            ),
                          ),
                          trailing: IconButton(
                            tooltip: 'Eliminar marcador',
                            onPressed: () => _removeBookmark(bookmark.id),
                            icon: Icon(
                              Icons.delete_outline,
                              color: palette.inkFaint,
                            ),
                          ),
                          onTap: () {
                            Navigator.of(context).pop();
                            _goToChapter(
                              book,
                              bookmark.chapterIndex,
                              positionMs: bookmark.positionMs,
                            );
                          },
                        ),
                    const SizedBox(height: 24),
                    Text(
                      'Marcadores de lectura',
                      style: TextStyle(
                        fontFamily: 'serif',
                        fontSize: 20,
                        fontWeight: FontWeight.w600,
                        color: palette.ink,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Guardá la página actual para volver después.',
                      style: TextStyle(color: palette.inkSoft, fontSize: 12),
                    ),
                    const SizedBox(height: 10),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: OutlinedButton.icon(
                        onPressed: () => _addReadingBookmark(book, chapter),
                        icon: const Icon(Icons.bookmark_add_outlined, size: 18),
                        label: const Text('Marcar esta página'),
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (data.readingBookmarks.isEmpty)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 18),
                        child: Text(
                          'Todavía no hay marcadores de lectura.',
                          style: TextStyle(color: palette.inkSoft),
                        ),
                      )
                    else
                      for (final bookmark in data.readingBookmarks.reversed)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(
                            Icons.auto_stories_outlined,
                            color: palette.accent,
                          ),
                          title: Text(
                            'Capítulo ${bookmark.chapterIndex}',
                            style: TextStyle(color: palette.ink),
                          ),
                          subtitle: Text(
                            bookmark.note ?? 'Página ${bookmark.pageIndex + 1}',
                            style: TextStyle(
                              color: palette.inkFaint,
                              fontSize: 11,
                            ),
                          ),
                          trailing: IconButton(
                            tooltip: 'Eliminar marcador de lectura',
                            onPressed: () =>
                                _removeReadingBookmark(bookmark.id),
                            icon: Icon(
                              Icons.delete_outline,
                              color: palette.inkFaint,
                            ),
                          ),
                          onTap: () {
                            Navigator.of(context).pop();
                            _goToChapter(book, bookmark.chapterIndex);
                          },
                        ),
                  ],
                );
              },
            );
          },
        );
      },
    );
  }

  Future<void> _showToc(
    BuildContext context,
    Book book,
    ReaderPalette palette,
    int current,
  ) async {
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
                    child: Text(
                      'Índice',
                      style: TextStyle(
                        fontFamily: 'serif',
                        fontSize: 24,
                        fontWeight: FontWeight.w600,
                        color: palette.ink,
                      ),
                    ),
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
                  subtitle: Text(
                    'Capítulo ${chapter.index}',
                    style: TextStyle(color: palette.inkFaint, fontSize: 11),
                  ),
                  trailing: active
                      ? Icon(Icons.bookmark, size: 18, color: palette.accent)
                      : null,
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

  Future<void> _showSettings(
    BuildContext context,
    ReaderPreferences preferences,
    ReaderPalette palette,
  ) async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: palette.surface,
      isScrollControlled: true,
      builder: (context) {
        return SafeArea(
          child: SingleChildScrollView(
            padding: EdgeInsets.only(
              bottom: MediaQuery.viewInsetsOf(context).bottom,
            ),
            child: StatefulBuilder(
              builder: (context, setModalState) {
                final current = ref.read(readerPreferencesProvider);
                return Padding(
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Lectura',
                        style: TextStyle(
                          fontFamily: 'serif',
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                          color: palette.ink,
                        ),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Paleta',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final entry in const {
                            'paper': 'Papel',
                            'sepia': 'Sepia',
                            'night': 'Noche',
                          }.entries)
                            ChoiceChip(
                              label: Text(entry.value),
                              selected: current.palette == entry.key,
                              onSelected: (_) {
                                ref
                                    .read(settingsProvider.notifier)
                                    .updateReader(
                                      current.copyWith(palette: entry.key),
                                    );
                                setModalState(() {});
                              },
                            ),
                        ],
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Tamaño',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                      Slider(
                        value: current.fontSize,
                        min: 15,
                        max: 28,
                        divisions: 13,
                        label: '${current.fontSize.round()}',
                        onChanged: (value) {
                          ref
                              .read(settingsProvider.notifier)
                              .updateReader(current.copyWith(fontSize: value));
                          setModalState(() {});
                        },
                      ),
                      const SizedBox(height: 8),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          'Karaoke',
                          style: TextStyle(color: palette.ink),
                        ),
                        value: current.karaoke,
                        onChanged: (value) {
                          ref
                              .read(settingsProvider.notifier)
                              .updateReader(current.copyWith(karaoke: value));
                          setModalState(() {});
                        },
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Velocidad de audio',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final speed in const [0.75, 1.0, 1.25, 1.5, 2.0])
                            ChoiceChip(
                              label: Text('${speed}x'),
                              selected: current.playbackRate == speed,
                              onSelected: (_) {
                                ref
                                    .read(settingsProvider.notifier)
                                    .updateReader(
                                      current.copyWith(playbackRate: speed),
                                    );
                                _applyPlaybackPreferences();
                                setModalState(() {});
                              },
                            ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Volumen',
                        style: TextStyle(color: palette.inkSoft, fontSize: 12),
                      ),
                      Slider(
                        value: current.volume,
                        min: 0,
                        max: 1,
                        divisions: 20,
                        label: '${(current.volume * 100).round()}%',
                        onChanged: (value) {
                          ref
                              .read(settingsProvider.notifier)
                              .updateReader(current.copyWith(volume: value));
                          _applyPlaybackPreferences();
                          setModalState(() {});
                        },
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

class _ReaderImage extends StatelessWidget {
  const _ReaderImage({
    required this.book,
    required this.image,
    required this.palette,
  });

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
              errorBuilder: (context, error, stackTrace) =>
                  const SizedBox.shrink(),
            ),
          ),
          if (image.caption != null && image.caption!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              image.caption!,
              style: TextStyle(
                color: palette.inkFaint,
                fontSize: 11,
                fontStyle: FontStyle.italic,
              ),
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
                      icon: Icon(Icons.replay, color: palette.inkSoft),
                    ),
                    IconButton(
                      tooltip: isPlaying ? 'Pausar' : 'Reproducir',
                      onPressed: onPlayPause,
                      icon: Icon(
                        isPlaying ? Icons.pause_circle : Icons.play_circle,
                        size: 34,
                        color: palette.accent,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Avanzar 15 segundos',
                      onPressed: onSeekForward,
                      icon: Icon(Icons.forward, color: palette.inkSoft),
                    ),
                    Expanded(
                      child: Column(
                        children: [
                          ClipRRect(
                            borderRadius: const BorderRadius.all(
                              Radius.circular(2),
                            ),
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
                              Text(
                                _duration(position),
                                style: TextStyle(
                                  color: palette.inkFaint,
                                  fontSize: 10,
                                ),
                              ),
                              Text(
                                _duration(duration),
                                style: TextStyle(
                                  color: palette.inkFaint,
                                  fontSize: 10,
                                ),
                              ),
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
                          style: TextStyle(
                            color: palette.ink,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(
                          '${chapter.index} / ${book.chapterCount}',
                          style: TextStyle(
                            color: palette.inkFaint,
                            fontSize: 10,
                          ),
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
