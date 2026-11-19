import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../../domain/jobs.dart';

/// Durable job history stored at `<library>/.vibebook/jobs.json`.
///
/// The library directory already travels with the books; keeping jobs there
/// means a copied library also carries its interrupted conversions. The
/// library scanner skips hidden directories, so `.vibebook` is invisible.
class JobRepository {
  JobRepository({required this.rootResolver});

  final Future<String> Function() rootResolver;
  static const _version = 1;
  static const _maxJobs = 100;

  /// Serializes read-modify-write cycles. The runner writes progress from
  /// several async callbacks; without this chain the temp file is clobbered.
  Future<void> _chain = Future<void>.value();

  Future<File> _file() async {
    final root = await rootResolver();
    final directory = Directory(p.join(root, '.vibebook'));
    await directory.create(recursive: true);
    return File(p.join(directory.path, 'jobs.json'));
  }

  Future<List<ConversionJob>> load() async {
    final file = await _file();
    if (!await file.exists()) {
      return <ConversionJob>[];
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic>) {
        return <ConversionJob>[];
      }
      final raw = decoded['jobs'];
      if (raw is! List) {
        return <ConversionJob>[];
      }
      final jobs = <ConversionJob>[];
      for (final item in raw) {
        if (item is Map<String, dynamic> && item['id'] is String) {
          jobs.add(ConversionJob.fromJson(item));
        }
      }
      return jobs;
    } on FormatException {
      return <ConversionJob>[];
    } on FileSystemException {
      return <ConversionJob>[];
    }
  }

  Future<void> save(ConversionJob job) {
    return _enqueue(() async {
      final jobs = await load();
      final index = jobs.indexWhere((item) => item.id == job.id);
      if (index >= 0) {
        jobs[index] = job;
      } else {
        jobs.add(job);
      }
      while (jobs.length > _maxJobs) {
        jobs.removeAt(0);
      }
      await _write(jobs);
    });
  }

  Future<List<ConversionJob>> markInterrupted() {
    return _enqueue(() async {
      final jobs = await load();
      var changed = false;
      final now = DateTime.now().toUtc().toIso8601String();
      for (var index = 0; index < jobs.length; index++) {
        final job = jobs[index];
        if (job.status == 'running' ||
            job.status == 'queued' ||
            job.status == 'cancelling') {
          jobs[index] = job.copyWith(
            status: 'interrupted',
            stage: 'error',
            message:
                'La app se cerró durante la conversión. Podés reanudarla desde '
                'el Estudio.',
            updatedAt: now,
          );
          changed = true;
        }
      }
      if (changed) {
        await _write(jobs);
      }
      return jobs;
    });
  }

  Future<void> clear({String? bookId}) {
    return _enqueue(() async {
      final jobs = await load();
      jobs.removeWhere((job) => bookId == null || job.bookId == bookId);
      await _write(jobs);
    });
  }

  Future<T> _enqueue<T>(Future<T> Function() action) {
    final next = _chain.then((_) => action());
    _chain = next.then<void>(
      (_) {},
      onError: (Object error, StackTrace stackTrace) {},
    );
    return next;
  }

  Future<void> _write(List<ConversionJob> jobs) async {
    final file = await _file();
    final temporary = File(
      '${file.path}.${DateTime.now().microsecondsSinceEpoch}.part',
    );
    try {
      await temporary.writeAsString(
        const JsonEncoder.withIndent('  ').convert({
          'version': _version,
          'jobs': jobs.map((job) => job.toJson()).toList(growable: false),
        }),
        flush: true,
      );
      if (await file.exists()) {
        await file.delete();
      }
      await temporary.rename(file.path);
    } finally {
      if (await temporary.exists()) {
        await temporary.delete();
      }
    }
  }
}
