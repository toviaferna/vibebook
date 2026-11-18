import 'dart:io';
import 'dart:isolate';

import 'package:archive/archive.dart';
import 'package:dio/dio.dart';
import 'package:path/path.dart' as p;

import 'piper_catalog.dart';
import 'piper_models.dart';

class PiperDownloadProgress {
  const PiperDownloadProgress({required this.value, required this.stage});

  final double value;
  final String stage;
}

class PiperDownloadException implements Exception {
  const PiperDownloadException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// Downloads, extracts and validates Piper voices.
class PiperDownloader {
  const PiperDownloader();

  Future<PiperModel> installFromCatalog(
    PiperCatalogEntry entry, {
    required String rootPath,
    CancelToken? cancelToken,
    void Function(PiperDownloadProgress progress)? onProgress,
  }) async {
    final root = Directory(rootPath);
    await root.create(recursive: true);
    final installed = await _findInstalled(rootPath, entryId: entry.id);
    if (installed != null) {
      return installed;
    }
    final work = Directory(p.join(rootPath, '.download-${entry.id}'));
    if (await work.exists()) {
      await work.delete(recursive: true);
    }
    await work.create(recursive: true);
    final archive = File(p.join(work.path, '${entry.id}.tar.bz2'));
    try {
      onProgress?.call(
        const PiperDownloadProgress(value: 0, stage: 'Descargando voz…'),
      );
      final dio = Dio(
        BaseOptions(
          connectTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(minutes: 15),
          followRedirects: true,
          maxRedirects: 5,
        ),
      );
      await dio.download(
        entry.url,
        archive.path,
        deleteOnError: true,
        cancelToken: cancelToken,
        onReceiveProgress: (received, total) {
          if (total <= 0) {
            return;
          }
          final fraction = (received / total).clamp(0.0, 1.0);
          onProgress?.call(
            PiperDownloadProgress(
              value: fraction * 0.88,
              stage: 'Descargando voz… ${(fraction * 100).round()}%',
            ),
          );
        },
      );
      if (!await archive.exists() || await archive.length() < 1024 * 1024) {
        throw const PiperDownloadException('La descarga quedó incompleta.');
      }
      return await _installArchive(
        archive,
        rootPath: rootPath,
        work: work,
        onProgress: onProgress,
      );
    } on PiperDownloadException {
      rethrow;
    } on DioException catch (error) {
      if (CancelToken.isCancel(error)) {
        throw const PiperDownloadException('Descarga cancelada.');
      }
      throw PiperDownloadException(
        'No se pudo descargar la voz: ${error.message ?? error}',
      );
    } catch (error) {
      throw PiperDownloadException('No se pudo descargar la voz: $error');
    } finally {
      await _deleteQuietly(work);
    }
  }

  Future<PiperModel> installFromFile(
    File archive, {
    required String rootPath,
    void Function(PiperDownloadProgress progress)? onProgress,
  }) async {
    final root = Directory(rootPath);
    await root.create(recursive: true);
    final work = Directory(
      p.join(rootPath, '.import-${DateTime.now().microsecondsSinceEpoch}'),
    );
    await work.create(recursive: true);
    try {
      final copy = File(p.join(work.path, p.basename(archive.path)));
      await archive.copy(copy.path);
      return await _installArchive(
        copy,
        rootPath: rootPath,
        work: work,
        onProgress: onProgress,
      );
    } on PiperDownloadException {
      rethrow;
    } catch (error) {
      throw PiperDownloadException('No se pudo instalar la voz: $error');
    } finally {
      await _deleteQuietly(work);
    }
  }

  Future<PiperModel> _installArchive(
    File archive, {
    required String rootPath,
    required Directory work,
    void Function(PiperDownloadProgress progress)? onProgress,
  }) async {
    onProgress?.call(
      const PiperDownloadProgress(value: 0.9, stage: 'Extrayendo voz…'),
    );
    final extract = Directory(p.join(work.path, 'extract'));
    await extract.create(recursive: true);
    final archivePath = archive.path;
    final extractPath = extract.path;
    await Isolate.run(() => _extractTarBz2(archivePath, extractPath));
    final modelDirectory = await _findModelDirectory(extract);
    if (modelDirectory == null) {
      throw const PiperDownloadException(
        'El archivo no contiene un modelo Piper válido.',
      );
    }
    final target = Directory(p.join(rootPath, p.basename(modelDirectory.path)));
    if (await target.exists()) {
      await target.delete(recursive: true);
    }
    await modelDirectory.rename(target.path);
    onProgress?.call(
      const PiperDownloadProgress(value: 1, stage: 'Voz instalada.'),
    );
    final installed = await _findInstalled(
      rootPath,
      entryId: p.basename(target.path),
    );
    if (installed == null) {
      throw const PiperDownloadException(
        'La voz se extrajo pero no se pudo validar.',
      );
    }
    return installed;
  }

  Future<PiperModel?> _findInstalled(String rootPath, {String? entryId}) async {
    final models = await PiperModelStore(rootPath: rootPath).scan();
    if (entryId == null) {
      return models.isEmpty ? null : models.first;
    }
    for (final model in models) {
      if (model.id == entryId || p.basename(model.directory) == entryId) {
        return model;
      }
    }
    return null;
  }

  Future<Directory?> _findModelDirectory(Directory root) async {
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is File && entity.path.toLowerCase().endsWith('.onnx')) {
        final directory = entity.parent;
        final tokens = File(p.join(directory.path, 'tokens.txt'));
        if (await tokens.exists()) {
          return directory;
        }
      }
    }
    return null;
  }
}

Future<void> _deleteQuietly(Directory directory) async {
  try {
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  } catch (_) {
    // A leftover temp directory is harmless.
  }
}

void _extractTarBz2(String archivePath, String targetPath) {
  final bytes = File(archivePath).readAsBytesSync();
  final decompressed = BZip2Decoder().decodeBytes(bytes);
  final archive = TarDecoder().decodeBytes(decompressed, verify: true);
  final target = Directory(targetPath);
  for (final file in archive) {
    if (!file.isFile) {
      continue;
    }
    final name = file.name.replaceAll('\\', '/');
    final normalized = p.posix.normalize(name);
    if (normalized.startsWith('/') ||
        normalized.startsWith('../') ||
        normalized.contains('/../')) {
      continue;
    }
    final output = File(p.join(target.path, normalized));
    output.parent.createSync(recursive: true);
    output.writeAsBytesSync(file.content, flush: true);
  }
}
