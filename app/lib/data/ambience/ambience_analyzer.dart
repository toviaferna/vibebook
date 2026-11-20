import '../../domain/ambience.dart';
import '../../domain/ambience_plan.dart';
import '../../domain/models.dart';

/// Chooses an ambience preset per chapter from explicit scene cues.
///
/// It deliberately returns no preset when the text has no strong cues instead
/// of imposing a generic background on every chapter.
class AmbienceAnalyzer {
  const AmbienceAnalyzer();

  static const _keywords = <AmbiencePreset, Set<String>>{
    AmbiencePreset.sea: {
      'mar',
      'marea',
      'olas',
      'ola',
      'oceano',
      'playa',
      'puerto',
      'barco',
      'barca',
      'sal',
      'arena',
      'costa',
      'orilla',
      'muelle',
      'faro',
      'navegar',
      'sea',
      'ocean',
      'wave',
      'beach',
      'harbor',
      'boat',
      'salt',
      'tide',
      'shore',
    },
    AmbiencePreset.rain: {
      'lluvia',
      'llover',
      'llueve',
      'tormenta',
      'trueno',
      'relampago',
      'paraguas',
      'gotas',
      'aguacero',
      'chaparron',
      'rain',
      'storm',
      'thunder',
      'downpour',
      'drizzle',
    },
    AmbiencePreset.wind: {
      'viento',
      'brisa',
      'rafaga',
      'ventisca',
      'silbido',
      'wind',
      'breeze',
      'gust',
      'gale',
    },
    AmbiencePreset.fire: {
      'fuego',
      'chimenea',
      'llama',
      'llamas',
      'brasa',
      'hoguera',
      'crepitar',
      'ceniza',
      'fire',
      'fireplace',
      'flame',
      'ember',
      'hearth',
    },
    AmbiencePreset.night: {
      'noche',
      'nocturno',
      'oscuridad',
      'luna',
      'estrellas',
      'grillos',
      'silencio',
      'night',
      'moon',
      'stars',
      'crickets',
      'dark',
    },
    AmbiencePreset.forest: {
      'bosque',
      'selva',
      'arbol',
      'arboles',
      'hojas',
      'pajaros',
      'pajaro',
      'vegetacion',
      'forest',
      'jungle',
      'trees',
      'birds',
      'leaves',
      'woods',
    },
  };

  AmbiencePlan analyze(Book book) {
    final chapters = <AmbienceChapterPlan>[];
    for (final chapter in book.chapters) {
      final title = _fold(chapter.title);
      final body = _fold(
        chapter.segments.map((segment) => segment.text).join(' '),
      );
      final titleTokens = _tokens(title).toSet();
      final bodyTokens = _tokens(body).toSet();
      AmbiencePreset? bestPreset;
      var bestScore = 0;
      var bestMatches = <String>[];
      for (final entry in _keywords.entries) {
        final matches = <String>[];
        var score = 0;
        for (final keyword in entry.value) {
          if (titleTokens.contains(keyword)) {
            score += 2;
            matches.add(keyword);
          } else if (bodyTokens.contains(keyword)) {
            score += 1;
            matches.add(keyword);
          }
        }
        if (score > bestScore) {
          bestScore = score;
          bestPreset = entry.key;
          bestMatches = matches;
        }
      }
      final detected = bestPreset != null && bestScore >= 2;
      chapters.add(
        AmbienceChapterPlan(
          chapterIndex: chapter.index,
          presetId: detected ? bestPreset.id : null,
          confidence: detected ? (0.45 + bestScore * 0.08).clamp(0.0, 0.95) : 0,
          reason: detected ? bestMatches.take(4).join(', ') : '',
        ),
      );
    }
    return AmbiencePlan(chapters: chapters);
  }

  Iterable<String> _tokens(String value) {
    return RegExp(r'[a-z0-9]+')
        .allMatches(value)
        .map((match) => match.group(0)!)
        .where((token) => token.length > 1);
  }

  String _fold(String value) {
    var result = value.toLowerCase();
    const replacements = {
      'á': 'a',
      'à': 'a',
      'ä': 'a',
      'â': 'a',
      'ã': 'a',
      'é': 'e',
      'è': 'e',
      'ë': 'e',
      'ê': 'e',
      'í': 'i',
      'ì': 'i',
      'ï': 'i',
      'î': 'i',
      'ó': 'o',
      'ò': 'o',
      'ö': 'o',
      'ô': 'o',
      'õ': 'o',
      'ú': 'u',
      'ù': 'u',
      'ü': 'u',
      'û': 'u',
      'ñ': 'n',
      'ç': 'c',
    };
    for (final entry in replacements.entries) {
      result = result.replaceAll(entry.key, entry.value);
    }
    return result;
  }
}
