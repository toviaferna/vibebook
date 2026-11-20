import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/data/jobs/job_repository.dart';
import 'package:vibebook_app/domain/jobs.dart';

ConversionJob _job({
  String id = 'job-1',
  String status = 'running',
  String bookId = 'book-1',
}) {
  const now = '2026-11-19T00:00:00Z';
  return ConversionJob(
    id: id,
    bookId: bookId,
    bookTitle: 'Un libro',
    status: status,
    stage: 'synthesizing',
    completedSegments: 2,
    totalSegments: 10,
    engine: 'piper',
    voice: 'es_MX-ald-medium',
    style: 'neutral',
    rate: -10,
    createdAt: now,
    updatedAt: now,
  );
}

void main() {
  late Directory temp;

  setUp(() {
    temp = Directory.systemTemp.createTempSync('vibebook-jobs-');
  });

  tearDown(() {
    if (temp.existsSync()) {
      temp.deleteSync(recursive: true);
    }
  });

  JobRepository repository() {
    return JobRepository(rootResolver: () async => temp.path);
  }

  test('guarda y recupera trabajos', () async {
    final repo = repository();
    await repo.save(_job());
    final jobs = await repo.load();
    expect(jobs, hasLength(1));
    expect(jobs.single.status, 'running');
    expect(jobs.single.completedSegments, 2);
    expect(jobs.single.fraction, 0.2);
    expect(
      File(p.join(temp.path, '.vibebook', 'jobs.json')).existsSync(),
      isTrue,
    );
  });

  test('actualiza un trabajo existente por id', () async {
    final repo = repository();
    await repo.save(_job());
    await repo.save(_job(status: 'completed'));
    final jobs = await repo.load();
    expect(jobs, hasLength(1));
    expect(jobs.single.status, 'completed');
  });

  test('un archivo corrupto se trata como vacío', () async {
    final file = File(p.join(temp.path, '.vibebook', 'jobs.json'));
    file.parent.createSync(recursive: true);
    file.writeAsStringSync('{ not json');
    final repo = repository();
    expect(await repo.load(), isEmpty);
    await repo.save(_job());
    expect(await repo.load(), hasLength(1));
  });

  test(
    'marca como interrumpidos los trabajos que quedaron corriendo',
    () async {
      final repo = repository();
      await repo.save(_job(id: 'running', status: 'running'));
      await repo.save(_job(id: 'queued', status: 'queued'));
      await repo.save(_job(id: 'done', status: 'completed'));
      final jobs = await repo.markInterrupted();
      final byId = {for (final job in jobs) job.id: job};
      expect(byId['running']!.status, 'interrupted');
      expect(byId['queued']!.status, 'interrupted');
      expect(byId['done']!.status, 'completed');
      expect(byId['running']!.message, contains('app se cerró'));
      final persisted = await repo.load();
      expect(
        persisted.firstWhere((job) => job.id == 'running').status,
        'interrupted',
      );
    },
  );

  test('limita el historial a 100 trabajos', () async {
    final repo = repository();
    for (var index = 0; index < 105; index++) {
      await repo.save(_job(id: 'job-$index', status: 'completed'));
    }
    final jobs = await repo.load();
    expect(jobs, hasLength(100));
    expect(jobs.last.id, 'job-104');
  });

  test('el JSON guarda el formato esperado', () async {
    final repo = repository();
    await repo.save(_job());
    final raw = await File(p.join(temp.path, '.vibebook', 'jobs.json'))
        .readAsString();
    final decoded = jsonDecode(raw) as Map<String, dynamic>;
    expect(decoded['version'], 1);
    expect((decoded['jobs'] as List).single['book_id'], 'book-1');
  });
}
