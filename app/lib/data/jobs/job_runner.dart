import '../../domain/jobs.dart';
import '../../domain/models.dart';
import '../tts/chapter_synthesizer.dart';
import '../tts/tts_conversion.dart';
import 'job_repository.dart';

/// Runs one conversion and keeps its [ConversionJob] persisted.
class JobRunner {
  JobRunner({
    required this.repository,
    this.service = const TtsConversionService(),
  });

  final JobRepository repository;
  final TtsConversionService service;
  bool _cancelRequested = false;
  ConversionJob? _current;

  bool get isRunning => _current?.isRunning ?? false;

  void cancel() {
    _cancelRequested = true;
    final current = _current;
    if (current != null && current.status == 'running') {
      final next = current.copyWith(
        status: 'cancelling',
        message: 'Deteniendo al final del capítulo…',
        updatedAt: _now(),
      );
      _current = next;
      repository.save(next);
    }
  }

  Future<ConversionJob> start({
    required Book book,
    required ChapterSynthesizer synthesizer,
    required String engine,
    required String voice,
    required String style,
    required double rate,
    Map<String, String> extra = const {},
    bool resume = true,
    int? maxChapters,
    void Function(ConversionJob job)? onUpdate,
  }) async {
    if (isRunning) {
      throw StateError('Ya hay una conversión en curso.');
    }
    _cancelRequested = false;
    final now = _now();
    final normalizedRate = rate.roundToDouble();
    var job = ConversionJob(
      id: '${book.id}-${DateTime.now().microsecondsSinceEpoch}',
      bookId: book.id,
      bookTitle: book.title,
      status: 'queued',
      stage: 'preparing',
      completedSegments: 0,
      totalSegments: book.segmentCount,
      engine: engine,
      voice: voice,
      style: style,
      rate: normalizedRate,
      createdAt: now,
      updatedAt: now,
      startedAt: now,
      message: 'Preparando la síntesis…',
    );
    _current = job;
    await repository.save(job);
    onUpdate?.call(job);

    void update(ConversionJob next) {
      _current = next;
      onUpdate?.call(next);
      repository.save(next);
    }

    try {
      final updatedBook = await service.convert(
        book,
        synthesizer: synthesizer,
        manifestExtra: extra,
        speed: 1 + normalizedRate / 100,
        maxChapters: maxChapters,
        resume: resume,
        style: style,
        isCancelled: () => _cancelRequested,
        onProgress: (progress) {
          final completed = (progress.fraction * job.totalSegments)
              .round()
              .clamp(0, job.totalSegments);
          String? chapterTitle;
          for (final chapter in book.chapters) {
            if (chapter.index == progress.chapterIndex) {
              chapterTitle = chapter.title;
              break;
            }
          }
          job = job.copyWith(
            status: 'running',
            stage: 'synthesizing',
            completedSegments: completed,
            chapterIndex: progress.chapterIndex,
            chapterTitle: chapterTitle,
            message: progress.message,
            updatedAt: _now(),
            clearError: true,
          );
          update(job);
        },
      );
      final done = job.copyWith(
        status: 'completed',
        stage: 'done',
        completedSegments: job.totalSegments,
        message: 'Audio listo para ${updatedBook.title}.',
        updatedAt: _now(),
        finishedAt: _now(),
        clearError: true,
      );
      update(done);
      await repository.save(done);
      return done;
    } on TtsConversionCancelled {
      final cancelled = job.copyWith(
        status: 'cancelled',
        stage: 'cancelled',
        message:
            'Conversión detenida. Los capítulos terminados se conservaron.',
        updatedAt: _now(),
        finishedAt: _now(),
        clearError: true,
      );
      update(cancelled);
      await repository.save(cancelled);
      return cancelled;
    } catch (error) {
      final failed = job.copyWith(
        status: 'failed',
        stage: 'error',
        message: 'La conversión falló.',
        error: '$error',
        updatedAt: _now(),
        finishedAt: _now(),
      );
      update(failed);
      await repository.save(failed);
      return failed;
    } finally {
      _current = null;
    }
  }

  String _now() => DateTime.now().toUtc().toIso8601String();
}
