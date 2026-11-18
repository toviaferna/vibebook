import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/core/text.dart';

void main() {
  group('slugify', () {
    test('normaliza espacios y mayusculas', () {
      expect(slugify('El gato negro'), 'el-gato-negro');
      expect(slugify('  La casa  '), 'la-casa');
    });
  });

  group('decodeTextBytes', () {
    test('conserva UTF-8', () {
      final bytes = utf8.encode('La casa olia a sal y a romero.');
      expect(decodeTextBytes(bytes), contains('olia'));
    });

    test('cae a Windows-1252 sin perder la enie', () {
      final bytes = [0x4C, 0x61, 0x20, 0x63, 0x61, 0x73, 0x61, 0x20, 0xF1];
      expect(decodeTextBytes(bytes), contains(String.fromCharCode(0xF1)));
    });
  });

  group('detectLanguage', () {
    test('detecta espanol', () {
      const text =
          'La casa de los Ferrer se levantaba sobre una loma que olia a sal. '
          'Desde la ventana se veia el puerto y una linea de barcos que entraban y salian.';
      expect(detectLanguage(text), 'es');
    });

    test('detecta ingles', () {
      const text =
          'The house of the Ferrer family stood on a hill that smelled of salt. '
          'From the window you could see the harbor and a line of boats that came and went.';
      expect(detectLanguage(text), 'en');
    });

    test('no inventa idioma con texto corto', () {
      expect(detectLanguage('hola mundo'), isNull);
    });
  });

  group('chunkText', () {
    test('divide texto largo sin perder palabras', () {
      final text = List.filled(80, 'palabra').join(' ');
      final chunks = chunkText(text, maxChars: 100);
      expect(chunks.length, greaterThan(1));
      expect(chunks.join(' '), text);
      expect(chunks.every((chunk) => chunk.length <= 100), isTrue);
    });
  });
}
