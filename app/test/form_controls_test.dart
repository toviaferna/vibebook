import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:vibebook_app/core/design/form_controls.dart';
import 'package:vibebook_app/core/design/theme.dart';

void main() {
  testWidgets('el selector abre un menú acotado y devuelve la opción', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1400, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    String? selected;
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBibliotecaTheme(dark: true),
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 700,
              child: BibliotecaSelect<String>(
                label: 'Modelo',
                value: 'a',
                options: const [
                  BibliotecaSelectOption(value: 'a', label: 'Modelo A'),
                  BibliotecaSelectOption(value: 'b', label: 'Modelo B'),
                ],
                onChanged: (value) => selected = value,
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('Modelo A'));
    await tester.pumpAndSettle();
    expect(find.text('Modelo B'), findsOneWidget);
    expect(tester.takeException(), isNull);

    final menuItems = find.byWidgetPredicate(
      (widget) => widget is PopupMenuItem,
    );
    expect(menuItems, findsNWidgets(2));
    final menuWidth = tester.getSize(menuItems.first).width;
    expect(menuWidth, lessThanOrEqualTo(420));

    await tester.tap(find.text('Modelo B').last);
    await tester.pumpAndSettle();
    expect(selected, 'b');
  });

  testWidgets('el selector se apila en una hoja en pantallas angostas', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(390, 844));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    String? selected;
    await tester.pumpWidget(
      MaterialApp(
        theme: buildBibliotecaTheme(dark: false),
        home: Scaffold(
          body: BibliotecaSelect<String>(
            label: 'Modelo',
            value: 'a',
            options: const [
              BibliotecaSelectOption(value: 'a', label: 'Modelo A'),
              BibliotecaSelectOption(value: 'b', label: 'Modelo B'),
            ],
            onChanged: (value) => selected = value,
          ),
        ),
      ),
    );

    await tester.tap(find.text('Modelo A'));
    await tester.pumpAndSettle();
    expect(find.text('Modelo B'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('Modelo B').last);
    await tester.pumpAndSettle();
    expect(selected, 'b');
  });
}
