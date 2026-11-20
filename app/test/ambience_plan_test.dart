import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:vibebook_app/data/ambience/ambience_analyzer.dart';
import 'package:vibebook_app/data/ambience/ambience_plan_repository.dart';
import 'package:vibebook_app/domain/ambience.dart';
import 'package:vibebook_app/domain/ambience_plan.dart';
import 'package:vibebook_app/domain/models.dart';

Book _book() {
  return const Book(
    id: 'test',
    title: 'Prueba',
    author: 'Autor',
    language: 'es',
    chapters: [
      Chapter(
        index: 1,
        title: 'El mapa de las mareas',
        segments: [
          Segment(
            id: 'a',
            chapterIndex: 1,
            paragraphIndex: 1,
            text: 'El mar golpeaba las olas contra la costa y el puerto.',
          ),
        ],
      ),
      Chapter(
        index: 2,
        title: 'La casa del relojero',
        segments: [
          Segment(
            id: 'b',
            chapterIndex: 2,
            paragraphIndex: 1,
            text: 'La chimenea crepitaba y el fuego iluminaba la sala.',
          ),
        ],
      ),
      Chapter(
        index: 3,
        title: 'Caminata',
        segments: [
          Segment(
            id: 'c',
            chapterIndex: 3,
            paragraphIndex: 1,
            text: 'Caminó sin rumbo durante varias horas.',
          ),
        ],
      ),
    ],
  );
}

void main() {
  test('detecta mar, fuego y deja los capítulos neutros sin ambiente', () {
    final plan = const AmbienceAnalyzer().analyze(_book());
    expect(plan.chapters, hasLength(3));
    expect(plan.forChapter(1)?.presetId, AmbiencePreset.sea.id);
    expect(plan.forChapter(2)?.presetId, AmbiencePreset.fire.id);
    expect(plan.forChapter(3)?.presetId, isNull);
    expect(plan.detectedChapters, 2);
  });

  test('el plan y el repositorio conservan los datos', () async {
    final directory = await Directory.systemTemp.createTemp('vibebook-plan-');
    addTearDown(() async {
      if (await directory.exists()) {
        await directory.delete(recursive: true);
      }
    });
    final plan = const AmbienceAnalyzer().analyze(_book());
    const repository = AmbiencePlanRepository();
    await repository.save(directory.path, plan);
    final loaded = await repository.load(directory.path);
    expect(loaded, isNotNull);
    expect(loaded!.forChapter(1)?.presetId, AmbiencePreset.sea.id);
    expect(loaded.forChapter(3)?.presetId, isNull);
    expect(
      File(p.join(directory.path, 'ambience', 'plan_flutter.json'))
          .existsSync(),
      isTrue,
    );
    final json = loaded.toJson();
    expect(AmbiencePlan.fromJson(json).detectedChapters, 2);
  });
}
