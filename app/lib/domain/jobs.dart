/// A conversion job persisted at `<library>/.vibebook/jobs.json`.
class ConversionJob {
  const ConversionJob({
    required this.id,
    required this.bookId,
    required this.bookTitle,
    required this.status,
    required this.stage,
    required this.completedSegments,
    required this.totalSegments,
    required this.engine,
    required this.voice,
    required this.style,
    required this.rate,
    required this.createdAt,
    required this.updatedAt,
    this.chapterIndex,
    this.chapterTitle,
    this.message,
    this.error,
    this.startedAt,
    this.finishedAt,
  });

  final String id;
  final String bookId;
  final String bookTitle;

  /// `queued`, `running`, `cancelling`, `completed`, `failed`, `cancelled`
  /// or `interrupted`.
  final String status;

  /// `preparing`, `synthesizing`, `assembling`, `finalizing`, `done`,
  /// `cancelled` or `error`.
  final String stage;
  final int completedSegments;
  final int totalSegments;
  final int? chapterIndex;
  final String? chapterTitle;
  final String? message;
  final String? error;
  final String engine;
  final String voice;
  final String style;
  final double rate;
  final String createdAt;
  final String updatedAt;
  final String? startedAt;
  final String? finishedAt;

  bool get isRunning =>
      status == 'queued' || status == 'running' || status == 'cancelling';
  bool get isTerminal =>
      status == 'completed' ||
      status == 'failed' ||
      status == 'cancelled' ||
      status == 'interrupted';
  bool get canResume =>
      status == 'interrupted' || status == 'cancelled' || status == 'failed';

  double get fraction {
    if (totalSegments <= 0) {
      return 0;
    }
    return (completedSegments / totalSegments).clamp(0.0, 1.0);
  }

  ConversionJob copyWith({
    String? status,
    String? stage,
    int? completedSegments,
    int? totalSegments,
    int? chapterIndex,
    String? chapterTitle,
    String? message,
    String? error,
    String? updatedAt,
    String? startedAt,
    String? finishedAt,
    bool clearError = false,
  }) {
    return ConversionJob(
      id: id,
      bookId: bookId,
      bookTitle: bookTitle,
      status: status ?? this.status,
      stage: stage ?? this.stage,
      completedSegments: completedSegments ?? this.completedSegments,
      totalSegments: totalSegments ?? this.totalSegments,
      chapterIndex: chapterIndex ?? this.chapterIndex,
      chapterTitle: chapterTitle ?? this.chapterTitle,
      message: message ?? this.message,
      error: clearError ? null : (error ?? this.error),
      engine: engine,
      voice: voice,
      style: style,
      rate: rate,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      startedAt: startedAt ?? this.startedAt,
      finishedAt: finishedAt ?? this.finishedAt,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'book_id': bookId,
    'book_title': bookTitle,
    'status': status,
    'stage': stage,
    'completed_segments': completedSegments,
    'total_segments': totalSegments,
    'chapter_index': chapterIndex,
    'chapter_title': chapterTitle,
    'message': message,
    'error': error,
    'engine': engine,
    'voice': voice,
    'style': style,
    'rate': rate,
    'created_at': createdAt,
    'updated_at': updatedAt,
    'started_at': startedAt,
    'finished_at': finishedAt,
  };

  factory ConversionJob.fromJson(Map<String, dynamic> json) {
    return ConversionJob(
      id: json['id'] as String? ?? '',
      bookId: json['book_id'] as String? ?? '',
      bookTitle: json['book_title'] as String? ?? '',
      status: json['status'] as String? ?? 'interrupted',
      stage: json['stage'] as String? ?? 'error',
      completedSegments: _int(json['completed_segments']),
      totalSegments: _int(json['total_segments']),
      chapterIndex: json['chapter_index'] is num
          ? (json['chapter_index'] as num).toInt()
          : null,
      chapterTitle: json['chapter_title'] as String?,
      message: json['message'] as String?,
      error: json['error'] as String?,
      engine: json['engine'] as String? ?? '',
      voice: json['voice'] as String? ?? '',
      style: json['style'] as String? ?? 'neutral',
      rate: (json['rate'] as num?)?.toDouble() ?? 0,
      createdAt: json['created_at'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
      startedAt: json['started_at'] as String?,
      finishedAt: json['finished_at'] as String?,
    );
  }
}

int _int(Object? value) {
  if (value is num) {
    return value.toInt();
  }
  if (value is String) {
    return int.tryParse(value) ?? 0;
  }
  return 0;
}

class JobState {
  const JobState({this.running = false, this.active, this.history = const []});

  final bool running;
  final ConversionJob? active;
  final List<ConversionJob> history;

  ConversionJob? latestFor(String bookId) {
    if (active?.bookId == bookId) {
      return active;
    }
    for (var index = history.length - 1; index >= 0; index--) {
      if (history[index].bookId == bookId) {
        return history[index];
      }
    }
    return null;
  }

  JobState copyWith({
    bool? running,
    ConversionJob? active,
    bool clearActive = false,
    List<ConversionJob>? history,
  }) {
    return JobState(
      running: running ?? this.running,
      active: clearActive ? null : (active ?? this.active),
      history: history ?? this.history,
    );
  }
}
