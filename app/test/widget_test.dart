import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:vibebook_app/core/design/components.dart';
import 'package:vibebook_app/core/design/theme.dart';
import 'package:vibebook_app/domain/models.dart';

void main() {
  testWidgets('la tarjeta de libro muestra título y autor', (tester) async {
    const book = Book(
      id: 'el-gato-negro',
      title: 'El gato negro',
      author: 'Edgar Allan Poe',
      language: 'es',
      chapters: [],
      status: 'imported',
    );
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: buildBibliotecaTheme(dark: false),
          home: Scaffold(
            body: SizedBox(
              width: 220,
              child: BookCard(book: book, onTap: () {}),
            ),
          ),
        ),
      ),
    );
    expect(find.text('El gato negro'), findsAtLeastNWidgets(1));
    expect(find.text('Edgar Allan Poe'), findsOneWidget);
    expect(find.text('ES'), findsOneWidget);
  });
}
