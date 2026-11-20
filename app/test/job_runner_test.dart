import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/jobs/job_repository.dart';
import 'package:vibebook_app/data/jobs/job_runner.dart';
import 'package:vibebook_app/data/tts/chapter_synthesizer.dart';
import 'package:vibebook_app/data/tts/tts_conversion.dart';
import 'package:vibebook_app/domain/jobs.dart';
import 'package:vibebook_app/domain/models.dart';

class _FakeSynthesizer implements ChapterSynthesizer {
  @override
  String get engineId => 'fake';

  @override
  String get voiceId => 'fake-voice';

  @override
  Future<ChapterSynthesis> synthesize(
    Chapter chapter, {
    required double speed,
    required bool Function() isCancelled,
  }) {
    throw UnimplementedError();
  }
}

class _FakeService extends TtsConversionService {
  _FakeService(this.behavior);

  final String behavior;

  @override
  Future<Book> convert(
    Book book, {
    required ChapterSynthesizer synthesizer,
    Map<String, String> manifestExtra = const {},
    double speed = 1.0,
    int? maxChapters,
    bool compressAudio = true,
    bool resume = false,
    String? style,
    bool Function()? isCancelled,
    void Function(TtsConversionProgress progress)? onProgress,
  }) async {
    onProgress?.call(
      const TtsConversionProgress(
        chapterIndex: 1,
        chapterTotal: 2,
        fraction: 0.5,
        message: 'Sintetizando capítulo 1 de 2…',
      ),
    );
    if (behavior == 'cancel' && (isCancelled?.call() ?? false)) {
      throw const TtsConversionCancelled();
    }
    if (behavior == 'fail') {
      throw StateError('boom');
    }
    onProgress?.call(
      const TtsConversionProgress(
        chapterIndex: 2,
        chapterTotal: 2,
        fraction: 1,
        message: 'Sintetizando capítulo 2 de 2…',
      ),
    );
    return book;
  }
}

Book _book() {
  return const Book(
    id: 'book-1',
    title: 'Un libro',
    author: 'Autora',
    language: 'es',
    chapters: [
      Chapter(
        index: 1,
        title: 'Uno',
        segments: [
          Segment(
            id: 'c001p0001s00',
            chapterIndex: 1,
            paragraphIndex: 1,
            text: 'Uno.',
          ),
          Segment(
            id: 'c001p0002s00',
            chapterIndex: 1,
            paragraphIndex: 2,
            text: 'Dos.',
          ),
        ],
      ),
      Chapter(
        index: 2,
        title: 'Dos',
        segments: [
          Segment(
            id: 'c002p0001s00',
            chapterIndex: 2,
            paragraphIndex: 1,
            text: 'Tres.',
          ),
          Segment(
            id: 'c002p0002s00',
            chapterIndex: 2,
            paragraphIndex: 2,
            text: 'Cuatro.',
          ),
        ],
      ),
    ],
  );
}

void main() {
  late Directory temp;

  setUp(() {
    temp = Directory.systemTemp.createTempSync('vibebook-runner-');
  });

  tearDown(() {
    if (temp.existsSync()) {
      temp.deleteSync(recursive: true);
    }
  });

  JobRunner runner(String behavior) {
    return JobRunner(
      repository: JobRepository(rootResolver: () async => temp.path),
      service: _FakeService(behavior),
    );
  }

  test('completa el trabajo y lo persiste', () async {
    final jobRunner = runner('complete');
    final updates = <ConversionJob>[];
    final job = await jobRunner.start(
      book: _book(),
      synthesizer: _FakeSynthesizer(),
      engine: 'fake',
      voice: 'fake-voice',
      style: 'neutral',
      rate: -10,
      onUpdate: updates.add,
    );
    expect(job.status, 'completed');
    expect(job.completedSegments, 4);
    expect(job.fraction, 1);
    expect(updates.any((item) => item.status == 'running'), isTrue);
    final persisted = await JobRepository(rootResolver: () async => temp.path)
        .load();
    expect(persisted.single.status, 'completed');
  });

  test('cancela entre capítulos y conserva el estado', () async {
    final jobRunner = runner('cancel');
    final job = await jobRunner.start(
      book: _book(),
      synthesizer: _FakeSynthesizer(),
      engine: 'fake',
      voice: 'fake-voice',
      style: 'neutral',
      rate: 0,
      onUpdate: (update) {
        if (update.status == 'running') {
          jobRunner.cancel();
        }
      },
    );
    expect(job.status, 'cancelled');
    expect(job.message, contains('detenida'));
    final persisted = await JobRepository(rootResolver: () async => temp.path)
        .load();
    expect(persisted.single.status, 'cancelled');
  });

  test('marca el trabajo como fallido con el error', () async {
    final jobRunner = runner('fail');
    final job = await jobRunner.start(
      book: _book(),
      synthesizer: _FakeSynthesizer(),
      engine: 'fake',
      voice: 'fake-voice',
      style: 'neutral',
      rate: 0,
    );
    expect(job.status, 'failed');
    expect(job.error, contains('boom'));
    expect(job.stage, 'error');
  });

  test('no acepta dos conversiones a la vez', () async {
    final jobRunner = runner('complete');
    final pending = jobRunner.start(
      book: _book(),
      synthesizer: _FakeSynthesizer(),
      engine: 'fake',
      voice: 'fake-voice',
      style: 'neutral',
      rate: 0,
    );
    await expectLater(
      jobRunner.start(
        book: _book(),
        synthesizer: _FakeSynthesizer(),
        engine: 'fake',
        voice: 'fake-voice',
        style: 'neutral',
        rate: 0,
      ),
      throwsA(isA<StateError>()),
    );
    await pending;
  });
}
