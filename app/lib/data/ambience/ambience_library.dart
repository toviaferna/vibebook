import 'dart:io';

import 'package:flutter/services.dart' show rootBundle;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../../domain/ambience.dart';

/// Bundled field recordings. The assets are copied to the app support
/// directory once because FFmpegKit needs real file paths for the export.
class AmbienceLibrary {
  const AmbienceLibrary();

  static const assetRoot = 'assets/ambience';

  Future<File> ensurePreset(AmbiencePreset preset) async {
    final support = await getApplicationSupportDirectory();
    final directory = Directory(p.join(support.path, 'ambience'));
    await directory.create(recursive: true);
    final file = File(p.join(directory.path, '${preset.id}.mp3'));
    final data = await rootBundle.load('$assetRoot/${preset.id}.mp3');
    final bytes = data.buffer.asUint8List(
      data.offsetInBytes,
      data.lengthInBytes,
    );
    if (await file.exists() && await file.length() == bytes.length) {
      return file;
    }
    await file.writeAsBytes(bytes, flush: true);
    return file;
  }
}
