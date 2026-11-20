import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;

import '../../domain/ambience_plan.dart';

class AmbiencePlanRepository {
  const AmbiencePlanRepository();

  File _file(String bookDirectory) {
    return File(p.join(bookDirectory, 'ambience', 'plan_flutter.json'));
  }

  Future<AmbiencePlan?> load(String bookDirectory) async {
    final file = _file(bookDirectory);
    if (!await file.exists()) {
      return null;
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is Map<String, dynamic>) {
        return AmbiencePlan.fromJson(decoded);
      }
    } on FormatException {
      // A corrupt plan should not prevent reading.
    }
    return null;
  }

  Future<void> save(String bookDirectory, AmbiencePlan plan) async {
    final file = _file(bookDirectory);
    await file.parent.create(recursive: true);
    final temporary = File('${file.path}.tmp');
    await temporary.writeAsString(
      const JsonEncoder.withIndent('  ').convert(plan.toJson()),
      flush: true,
    );
    if (await file.exists()) {
      await file.delete();
    }
    await temporary.rename(file.path);
  }
}
