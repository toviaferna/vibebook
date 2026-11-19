import 'dart:convert';

/// A single spoken segment of a chapter.
class Segment {
  const Segment({
    required this.id,
    required this.chapterIndex,
    required this.paragraphIndex,
    required this.text,
    this.chunkIndex = 0,
    this.sourceHref,
    this.sourceFragment,
    this.boundary = 'paragraph',
    this.continuation = false,
  });

  final String id;
  final int chapterIndex;
  final int paragraphIndex;
  final String text;
  final int chunkIndex;
  final String? sourceHref;
  final String? sourceFragment;
  final String boundary;
  final bool continuation;

  factory Segment.fromJson(
    Map<String, dynamic> json, {
    required int chapterIndex,
  }) {
    return Segment(
      id:
          json['id'] as String? ??
          _segmentId(
            chapterIndex,
            _int(json['paragraph_index'], 1),
            _int(json['chunk_index'], 0),
          ),
      chapterIndex: _int(json['chapter_index'], chapterIndex),
      paragraphIndex: _int(json['paragraph_index'], 1),
      text: json['text'] as String? ?? '',
      chunkIndex: _int(json['chunk_index'], 0),
      sourceHref: json['source_href'] as String?,
      sourceFragment: json['source_fragment'] as String?,
      boundary: json['boundary'] as String? ?? 'paragraph',
      continuation: json['continuation'] == true,
    );
  }

  static String _segmentId(int chapter, int paragraph, int chunk) {
    return 'c${chapter.toString().padLeft(3, '0')}'
        'p${paragraph.toString().padLeft(4, '0')}'
        's${chunk.toString().padLeft(2, '0')}';
  }
}

class Chapter {
  const Chapter({
    required this.index,
    required this.title,
    required this.segments,
    this.sourceHref,
    this.sourceFragment,
    this.level = 1,
    this.kind = 'chapter',
    this.number,
    this.generatedTitle = false,
    this.audio,
    this.timing,
    this.durationMs,
  });

  final int index;
  final String title;
  final List<Segment> segments;
  final String? sourceHref;
  final String? sourceFragment;
  final int level;
  final String kind;
  final int? number;
  final bool generatedTitle;
  final String? audio;
  final String? timing;
  final int? durationMs;

  factory Chapter.fromJson(
    Map<String, dynamic> json, {
    required int fallbackIndex,
  }) {
    final index = _int(json['index'], fallbackIndex);
    final segments = <Segment>[];
    final rawSegments = json['segments'];
    if (rawSegments is List) {
      for (final item in rawSegments) {
        if (item is Map<String, dynamic> && item['text'] is String) {
          segments.add(Segment.fromJson(item, chapterIndex: index));
        }
      }
    }
    return Chapter(
      index: index,
      title: json['title'] as String? ?? 'Capítulo $index',
      segments: segments,
      sourceHref: json['source_href'] as String?,
      sourceFragment: json['source_fragment'] as String?,
      level: _int(json['level'], 1),
      kind: json['kind'] as String? ?? 'chapter',
      number: json['number'] is num ? (json['number'] as num).toInt() : null,
      generatedTitle: json['generated_title'] == true,
      audio: json['audio'] as String?,
      timing: json['timing'] as String?,
      durationMs: json['duration_ms'] is num
          ? (json['duration_ms'] as num).toInt()
          : null,
    );
  }

  String get text => segments.map((segment) => segment.text).join('\n\n');
}

class TocNode {
  const TocNode({
    required this.title,
    this.level = 1,
    this.chapterIndex,
    this.kind = 'chapter',
    this.children = const [],
  });

  final String title;
  final int level;
  final int? chapterIndex;
  final String kind;
  final List<TocNode> children;

  factory TocNode.fromJson(Map<String, dynamic> json) {
    final children = <TocNode>[];
    final raw = json['children'];
    if (raw is List) {
      for (final item in raw) {
        if (item is Map<String, dynamic> && item['title'] is String) {
          children.add(TocNode.fromJson(item));
        }
      }
    }
    return TocNode(
      title: json['title'] as String? ?? '',
      level: _int(json['level'], 1),
      chapterIndex: json['chapter_index'] is num
          ? (json['chapter_index'] as num).toInt()
          : null,
      kind: json['kind'] as String? ?? 'chapter',
      children: children,
    );
  }
}

class BookImage {
  const BookImage({
    required this.id,
    this.path,
    this.alt = '',
    this.caption,
    this.role = 'illustration',
    this.chapterIndex,
    this.paragraphIndex = 0,
    this.position = 'after',
    this.width,
    this.height,
  });

  final String id;
  final String? path;
  final String alt;
  final String? caption;
  final String role;
  final int? chapterIndex;
  final int paragraphIndex;
  final String position;
  final int? width;
  final int? height;

  factory BookImage.fromJson(Map<String, dynamic> json) {
    return BookImage(
      id: json['id'] as String? ?? '',
      path: json['path'] as String?,
      alt: json['alt'] as String? ?? '',
      caption: json['caption'] as String?,
      role: json['role'] as String? ?? 'illustration',
      chapterIndex: json['chapter_index'] is num
          ? (json['chapter_index'] as num).toInt()
          : null,
      paragraphIndex: _int(json['paragraph_index'], 0),
      position: json['position'] as String? ?? 'after',
      width: json['width'] is num ? (json['width'] as num).toInt() : null,
      height: json['height'] is num ? (json['height'] as num).toInt() : null,
    );
  }
}

class Book {
  const Book({
    required this.id,
    required this.title,
    required this.author,
    required this.language,
    required this.chapters,
    this.declaredLanguage,
    this.toc = const [],
    this.images = const [],
    this.cover,
    this.sourceEpub,
    this.voice,
    this.engine,
    this.style,
    this.rate,
    this.status = 'imported',
    this.durationMs,
    this.m4b,
    this.manifestPath,
    this.directoryPath,
  });

  final String id;
  final String title;
  final String author;
  final String language;
  final String? declaredLanguage;
  final List<Chapter> chapters;
  final List<TocNode> toc;
  final List<BookImage> images;
  final String? cover;
  final String? sourceEpub;
  final String? voice;
  final String? engine;
  final String? style;
  final String? rate;
  final String status;
  final int? durationMs;
  final String? m4b;
  final String? manifestPath;
  final String? directoryPath;

  bool get hasAudio => chapters.any((chapter) => chapter.audio != null);

  factory Book.fromManifest(
    Map<String, dynamic> json, {
    String? id,
    String? manifestPath,
    String? directoryPath,
  }) {
    final chapters = <Chapter>[];
    final rawChapters = json['chapters'];
    if (rawChapters is List) {
      for (var i = 0; i < rawChapters.length; i++) {
        final item = rawChapters[i];
        if (item is Map<String, dynamic>) {
          chapters.add(Chapter.fromJson(item, fallbackIndex: i + 1));
        }
      }
    }
    final toc = <TocNode>[];
    final rawToc = json['toc'];
    if (rawToc is List) {
      for (final item in rawToc) {
        if (item is Map<String, dynamic> && item['title'] is String) {
          toc.add(TocNode.fromJson(item));
        }
      }
    }
    final images = <BookImage>[];
    final rawImages = json['images'];
    if (rawImages is List) {
      for (final item in rawImages) {
        if (item is Map<String, dynamic> && item['id'] is String) {
          images.add(BookImage.fromJson(item));
        }
      }
    }
    return Book(
      id: id ?? json['id'] as String? ?? '',
      title: json['title'] as String? ?? 'Sin título',
      author: json['author'] as String? ?? 'Desconocido',
      language: json['language'] as String? ?? 'es',
      declaredLanguage: json['language_declared'] as String?,
      chapters: chapters,
      toc: toc,
      images: images,
      cover: json['cover'] as String?,
      sourceEpub: json['source_epub'] as String?,
      voice: json['voice'] as String?,
      engine: json['engine'] as String?,
      style: json['style'] as String?,
      rate: json['rate'] as String?,
      status:
          json['status'] as String? ??
          (chapters.any((c) => c.audio != null) ? 'ready' : 'imported'),
      durationMs: json['duration_ms'] is num
          ? (json['duration_ms'] as num).toInt()
          : null,
      m4b: json['m4b'] as String?,
      manifestPath: manifestPath,
      directoryPath: directoryPath,
    );
  }

  factory Book.fromJsonString(
    String source, {
    String? id,
    String? manifestPath,
    String? directoryPath,
  }) {
    final decoded = jsonDecode(source);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('El manifiesto no es un objeto JSON.');
    }
    return Book.fromManifest(
      decoded,
      id: id,
      manifestPath: manifestPath,
      directoryPath: directoryPath,
    );
  }

  int get chapterCount => chapters.length;

  int get segmentCount =>
      chapters.fold(0, (sum, chapter) => sum + chapter.segments.length);

  String get progressLabel {
    if (durationMs == null || durationMs == 0) {
      return status == 'ready' ? 'Listo' : 'Importado';
    }
    final minutes = (durationMs! / 60000).round();
    final hours = minutes ~/ 60;
    final rest = minutes % 60;
    return hours > 0 ? '${hours}h ${rest}m' : '${rest}m';
  }
}

class ReaderPreferences {
  const ReaderPreferences({
    this.palette = 'paper',
    this.fontSize = 19,
    this.fontFamily = 'Literata',
    this.karaoke = true,
    this.autoAdvance = true,
    this.playbackRate = 1.0,
    this.volume = 1.0,
  });

  final String palette;
  final double fontSize;
  final String fontFamily;
  final bool karaoke;
  final bool autoAdvance;
  final double playbackRate;
  final double volume;

  ReaderPreferences copyWith({
    String? palette,
    double? fontSize,
    String? fontFamily,
    bool? karaoke,
    bool? autoAdvance,
    double? playbackRate,
    double? volume,
  }) {
    return ReaderPreferences(
      palette: palette ?? this.palette,
      fontSize: fontSize ?? this.fontSize,
      fontFamily: fontFamily ?? this.fontFamily,
      karaoke: karaoke ?? this.karaoke,
      autoAdvance: autoAdvance ?? this.autoAdvance,
      playbackRate: playbackRate ?? this.playbackRate,
      volume: volume ?? this.volume,
    );
  }

  Map<String, dynamic> toJson() => {
    'palette': palette,
    'fontSize': fontSize,
    'fontFamily': fontFamily,
    'karaoke': karaoke,
    'autoAdvance': autoAdvance,
    'playbackRate': playbackRate,
    'volume': volume,
  };

  factory ReaderPreferences.fromJson(Map<String, dynamic> json) {
    return ReaderPreferences(
      palette: json['palette'] as String? ?? 'paper',
      fontSize: (json['fontSize'] as num?)?.toDouble() ?? 19,
      fontFamily: json['fontFamily'] as String? ?? 'Literata',
      karaoke: json['karaoke'] as bool? ?? true,
      autoAdvance: json['autoAdvance'] as bool? ?? true,
      playbackRate: (json['playbackRate'] as num?)?.toDouble() ?? 1.0,
      volume: (json['volume'] as num?)?.toDouble() ?? 1.0,
    );
  }
}

class AppSettings {
  const AppSettings({
    this.themeMode = 'system',
    this.libraryPath,
    this.modelsPath,
    this.piperModelId,
    this.piperRate = -10,
    this.ttsEngine = 'piper',
    this.edgeVoiceId = 'es-MX-JorgeNeural',
    this.edgeRate = 0,
    this.ambienceEnabled = false,
    this.ambiencePreset = 'rain',
    this.ambienceVolume = 0.35,
    this.ambienceDucking = 0.3,
    this.reader = const ReaderPreferences(),
    this.lastBookId,
    this.lastChapterIndex = 1,
  });

  final String themeMode;
  final String? libraryPath;
  final String? modelsPath;
  final String? piperModelId;
  final double piperRate;

  /// Active conversion engine: `piper` (local) or `edge` (online).
  final String ttsEngine;
  final String edgeVoiceId;
  final double edgeRate;
  final bool ambienceEnabled;
  final String ambiencePreset;
  final double ambienceVolume;
  final double ambienceDucking;
  final ReaderPreferences reader;
  final String? lastBookId;
  final int lastChapterIndex;

  AppSettings copyWith({
    String? themeMode,
    String? libraryPath,
    String? modelsPath,
    String? piperModelId,
    double? piperRate,
    String? ttsEngine,
    String? edgeVoiceId,
    double? edgeRate,
    bool? ambienceEnabled,
    String? ambiencePreset,
    double? ambienceVolume,
    double? ambienceDucking,
    ReaderPreferences? reader,
    String? lastBookId,
    int? lastChapterIndex,
    bool clearPiperModel = false,
    bool clearModelsPath = false,
  }) {
    return AppSettings(
      themeMode: themeMode ?? this.themeMode,
      libraryPath: libraryPath ?? this.libraryPath,
      modelsPath: clearModelsPath ? null : (modelsPath ?? this.modelsPath),
      piperModelId: clearPiperModel
          ? null
          : (piperModelId ?? this.piperModelId),
      piperRate: piperRate ?? this.piperRate,
      ttsEngine: ttsEngine ?? this.ttsEngine,
      edgeVoiceId: edgeVoiceId ?? this.edgeVoiceId,
      edgeRate: edgeRate ?? this.edgeRate,
      ambienceEnabled: ambienceEnabled ?? this.ambienceEnabled,
      ambiencePreset: ambiencePreset ?? this.ambiencePreset,
      ambienceVolume: ambienceVolume ?? this.ambienceVolume,
      ambienceDucking: ambienceDucking ?? this.ambienceDucking,
      reader: reader ?? this.reader,
      lastBookId: lastBookId ?? this.lastBookId,
      lastChapterIndex: lastChapterIndex ?? this.lastChapterIndex,
    );
  }

  Map<String, dynamic> toJson() => {
    'themeMode': themeMode,
    'libraryPath': libraryPath,
    'modelsPath': modelsPath,
    'piperModelId': piperModelId,
    'piperRate': piperRate,
    'ttsEngine': ttsEngine,
    'edgeVoiceId': edgeVoiceId,
    'edgeRate': edgeRate,
    'ambienceEnabled': ambienceEnabled,
    'ambiencePreset': ambiencePreset,
    'ambienceVolume': ambienceVolume,
    'ambienceDucking': ambienceDucking,
    'reader': reader.toJson(),
    'lastBookId': lastBookId,
    'lastChapterIndex': lastChapterIndex,
  };

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    return AppSettings(
      themeMode: json['themeMode'] as String? ?? 'system',
      libraryPath: json['libraryPath'] as String?,
      modelsPath: json['modelsPath'] as String?,
      piperModelId: json['piperModelId'] as String?,
      piperRate: (json['piperRate'] as num?)?.toDouble() ?? -10,
      ttsEngine: json['ttsEngine'] as String? ?? 'piper',
      edgeVoiceId: json['edgeVoiceId'] as String? ?? 'es-MX-JorgeNeural',
      edgeRate: (json['edgeRate'] as num?)?.toDouble() ?? 0,
      ambienceEnabled: json['ambienceEnabled'] as bool? ?? false,
      ambiencePreset: json['ambiencePreset'] as String? ?? 'rain',
      ambienceVolume: (json['ambienceVolume'] as num?)?.toDouble() ?? 0.35,
      ambienceDucking: (json['ambienceDucking'] as num?)?.toDouble() ?? 0.3,
      reader: json['reader'] is Map<String, dynamic>
          ? ReaderPreferences.fromJson(json['reader'] as Map<String, dynamic>)
          : const ReaderPreferences(),
      lastBookId: json['lastBookId'] as String?,
      lastChapterIndex: (json['lastChapterIndex'] as num?)?.toInt() ?? 1,
    );
  }
}

int _int(Object? value, int fallback) {
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? fallback;
  }
  return fallback;
}
