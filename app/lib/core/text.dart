import 'dart:convert';
import 'dart:math' as math;

import 'package:crypto/crypto.dart';

String slugify(String value) {
  final normalized = value
      .toLowerCase()
      .replaceAll(RegExp(r'[áàäâã]'), 'a')
      .replaceAll(RegExp(r'[éèëê]'), 'e')
      .replaceAll(RegExp(r'[íìïî]'), 'i')
      .replaceAll(RegExp(r'[óòöôõ]'), 'o')
      .replaceAll(RegExp(r'[úùüû]'), 'u')
      .replaceAll(RegExp(r'[ñ]'), 'n')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
  return normalized.isEmpty ? 'libro' : normalized;
}

String shortHash(List<int> bytes) {
  final digest = sha256.convert(bytes).toString();
  return digest.substring(0, 8);
}

String decodeTextBytes(List<int> bytes) {
  if (bytes.isEmpty) {
    return '';
  }
  if (bytes.length >= 3 &&
      bytes[0] == 0xEF &&
      bytes[1] == 0xBB &&
      bytes[2] == 0xBF) {
    return utf8.decode(bytes.sublist(3), allowMalformed: true);
  }
  if (bytes.length >= 2 && bytes[0] == 0xFF && bytes[1] == 0xFE) {
    return _decodeUtf16(bytes.sublist(2), littleEndian: true);
  }
  if (bytes.length >= 2 && bytes[0] == 0xFE && bytes[1] == 0xFF) {
    return _decodeUtf16(bytes.sublist(2), littleEndian: false);
  }
  final head = ascii.decode(
    bytes.take(math.min(bytes.length, 2048)).toList(),
    allowInvalid: true,
  );
  final charset = RegExp(
    r'''charset\s*=\s*["']?([a-zA-Z0-9_-]+)''',
    caseSensitive: false,
  ).firstMatch(head)?.group(1)?.toLowerCase();
  if (charset != null &&
      (charset.contains('1252') ||
          charset.contains('latin1') ||
          charset.contains('iso-8859-1'))) {
    return _decodeWindows1252(bytes);
  }
  try {
    return utf8.decode(bytes);
  } on FormatException {
    return _decodeWindows1252(bytes);
  }
}

String _decodeUtf16(List<int> bytes, {required bool littleEndian}) {
  final units = <int>[];
  for (var i = 0; i + 1 < bytes.length; i += 2) {
    units.add(
      littleEndian
          ? bytes[i] | (bytes[i + 1] << 8)
          : (bytes[i] << 8) | bytes[i + 1],
    );
  }
  return String.fromCharCodes(units);
}

String _decodeWindows1252(List<int> bytes) {
  const high = {
    0x80: 0x20AC,
    0x82: 0x201A,
    0x83: 0x0192,
    0x84: 0x201E,
    0x85: 0x2026,
    0x86: 0x2020,
    0x87: 0x2021,
    0x88: 0x02C6,
    0x89: 0x2030,
    0x8A: 0x0160,
    0x8B: 0x2039,
    0x8C: 0x0152,
    0x8E: 0x017D,
    0x91: 0x2018,
    0x92: 0x2019,
    0x93: 0x201C,
    0x94: 0x201D,
    0x95: 0x2022,
    0x96: 0x2013,
    0x97: 0x2014,
    0x98: 0x02DC,
    0x99: 0x2122,
    0x9A: 0x0161,
    0x9B: 0x203A,
    0x9C: 0x0153,
    0x9E: 0x017E,
    0x9F: 0x0178,
  };
  final codes = bytes.map((byte) => byte >= 0x80 ? (high[byte] ?? byte) : byte);
  return String.fromCharCodes(codes);
}

String normalizeWhitespace(String value) {
  return value.replaceAll(RegExp(r'[\t\r\n ]+'), ' ').trim();
}

List<String> chunkText(String text, {int maxChars = 400}) {
  final trimmed = normalizeWhitespace(text);
  if (trimmed.isEmpty) {
    return const [];
  }
  if (trimmed.length <= maxChars) {
    return [trimmed];
  }
  final sentences = trimmed.split(RegExp(r'(?<=[.!?…])\s+'));
  final chunks = <String>[];
  var current = '';
  for (final sentence in sentences) {
    final candidate = current.isEmpty ? sentence : '$current $sentence';
    if (candidate.length <= maxChars) {
      current = candidate;
      continue;
    }
    if (current.isNotEmpty) {
      chunks.add(current.trim());
      current = '';
    }
    if (sentence.length <= maxChars) {
      current = sentence;
      continue;
    }
    var buffer = '';
    for (final word in sentence.split(RegExp(r'\s+'))) {
      final next = buffer.isEmpty ? word : '$buffer $word';
      if (next.length <= maxChars) {
        buffer = next;
      } else {
        if (buffer.isNotEmpty) {
          chunks.add(buffer.trim());
        }
        buffer = word;
      }
    }
    current = buffer;
  }
  if (current.trim().isNotEmpty) {
    chunks.add(current.trim());
  }
  return chunks.where((chunk) => chunk.isNotEmpty).toList(growable: false);
}

const _spanishWords = {
  'a',
  'al',
  'algo',
  'algunas',
  'algunos',
  'ante',
  'antes',
  'como',
  'con',
  'contra',
  'cuando',
  'de',
  'del',
  'desde',
  'donde',
  'durante',
  'e',
  'el',
  'ella',
  'ellas',
  'ellos',
  'en',
  'entre',
  'era',
  'eran',
  'es',
  'esa',
  'esas',
  'ese',
  'eso',
  'esos',
  'esta',
  'estaba',
  'estaban',
  'estas',
  'este',
  'esto',
  'estos',
  'fue',
  'fueron',
  'ha',
  'habia',
  'han',
  'hasta',
  'hay',
  'la',
  'las',
  'le',
  'les',
  'lo',
  'los',
  'mas',
  'me',
  'mi',
  'mis',
  'mucho',
  'muy',
  'nada',
  'ni',
  'no',
  'nos',
  'nosotros',
  'o',
  'otra',
  'otras',
  'otro',
  'otros',
  'para',
  'pero',
  'poco',
  'por',
  'porque',
  'que',
  'quien',
  'quienes',
  'se',
  'sin',
  'sobre',
  'su',
  'sus',
  'tambien',
  'te',
  'tiene',
  'tienen',
  'todo',
  'todos',
  'tu',
  'tus',
  'un',
  'una',
  'uno',
  'unos',
  'y',
  'ya',
  'yo',
};

const _englishWords = {
  'a',
  'about',
  'after',
  'all',
  'also',
  'an',
  'and',
  'any',
  'are',
  'as',
  'at',
  'back',
  'be',
  'because',
  'been',
  'but',
  'by',
  'can',
  'could',
  'did',
  'do',
  'does',
  'for',
  'from',
  'get',
  'give',
  'go',
  'good',
  'had',
  'has',
  'have',
  'he',
  'her',
  'him',
  'his',
  'how',
  'i',
  'if',
  'in',
  'into',
  'is',
  'it',
  'its',
  'just',
  'know',
  'like',
  'look',
  'make',
  'me',
  'more',
  'most',
  'my',
  'new',
  'no',
  'not',
  'now',
  'of',
  'on',
  'one',
  'only',
  'or',
  'other',
  'our',
  'out',
  'over',
  'people',
  'say',
  'see',
  'she',
  'should',
  'so',
  'some',
  'such',
  'take',
  'than',
  'that',
  'the',
  'their',
  'them',
  'then',
  'there',
  'these',
  'they',
  'think',
  'this',
  'time',
  'to',
  'two',
  'up',
  'us',
  'use',
  'very',
  'want',
  'was',
  'way',
  'we',
  'well',
  'were',
  'what',
  'when',
  'which',
  'who',
  'will',
  'with',
  'work',
  'would',
  'year',
  'you',
  'your',
};

String? detectLanguage(String text, {int minimumTokens = 12}) {
  final tokens = RegExp(r"[a-záéíóúüñ]+")
      .allMatches(text.toLowerCase())
      .map((match) => match.group(0)!)
      .take(6000)
      .toList(growable: false);
  if (tokens.length < minimumTokens) {
    return null;
  }
  final spanish = tokens.where(_spanishWords.contains).length;
  final english = tokens.where(_englishWords.contains).length;
  final spanishRatio = spanish / tokens.length;
  final englishRatio = english / tokens.length;
  final accentBonus = RegExp(r'[áéíóúüñ¿¡]').hasMatch(text.toLowerCase())
      ? 0.03
      : 0.0;
  if (spanishRatio >= 0.02 &&
      spanishRatio + accentBonus > englishRatio * 1.25 + 0.005) {
    return 'es';
  }
  if (englishRatio >= 0.02 &&
      englishRatio > (spanishRatio + accentBonus) * 1.25 + 0.005) {
    return 'en';
  }
  return null;
}
