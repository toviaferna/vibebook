class AmbienceChapterPlan {
  const AmbienceChapterPlan({
    required this.chapterIndex,
    required this.presetId,
    required this.confidence,
    required this.reason,
  });

  final int chapterIndex;
  final String? presetId;
  final double confidence;
  final String reason;

  Map<String, dynamic> toJson() => {
    'chapter_index': chapterIndex,
    'preset': presetId,
    'confidence': confidence,
    'reason': reason,
  };

  factory AmbienceChapterPlan.fromJson(Map<String, dynamic> json) {
    return AmbienceChapterPlan(
      chapterIndex: (json['chapter_index'] as num?)?.toInt() ?? 1,
      presetId: json['preset'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      reason: json['reason'] as String? ?? '',
    );
  }
}

class AmbiencePlan {
  const AmbiencePlan({this.chapters = const []});

  final List<AmbienceChapterPlan> chapters;

  AmbienceChapterPlan? forChapter(int index) {
    for (final chapter in chapters) {
      if (chapter.chapterIndex == index) {
        return chapter;
      }
    }
    return null;
  }

  int get detectedChapters =>
      chapters.where((chapter) => chapter.presetId != null).length;

  Map<String, dynamic> toJson() => {
    'version': 1,
    'chapters': chapters
        .map((chapter) => chapter.toJson())
        .toList(growable: false),
  };

  factory AmbiencePlan.fromJson(Map<String, dynamic> json) {
    final raw = json['chapters'];
    final chapters = <AmbienceChapterPlan>[];
    if (raw is List) {
      for (final item in raw) {
        if (item is Map<String, dynamic>) {
          chapters.add(AmbienceChapterPlan.fromJson(item));
        }
      }
    }
    return AmbiencePlan(chapters: chapters);
  }
}
