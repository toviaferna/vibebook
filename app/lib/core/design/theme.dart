import 'package:material_ui/material_ui.dart';

import 'tokens.dart';

ThemeData buildBibliotecaTheme({required bool dark}) {
  final colors = dark ? BibliotecaColors.dark : BibliotecaColors.light;
  final colorScheme = ColorScheme(
    brightness: dark ? Brightness.dark : Brightness.light,
    primary: colors.accent,
    onPrimary: colors.onAccent,
    secondary: colors.brass,
    onSecondary: colors.onAccent,
    error: colors.danger,
    onError: colors.onAccent,
    surface: colors.surface,
    onSurface: colors.ink,
    surfaceContainerHighest: colors.surfaceRaised,
    onSurfaceVariant: colors.inkSoft,
    outline: colors.line,
    outlineVariant: colors.lineStrong,
    shadow: Colors.black,
    scrim: Colors.black,
    inverseSurface: colors.ink,
    onInverseSurface: colors.paper,
    inversePrimary: colors.accentStrong,
  );
  final base = ThemeData(
    useMaterial3: true,
    brightness: dark ? Brightness.dark : Brightness.light,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: colors.paper,
    canvasColor: colors.paper,
    fontFamily: 'sans-serif',
    visualDensity: VisualDensity.standard,
    splashFactory: InkRipple.splashFactory,
  );
  final textTheme = base.textTheme.copyWith(
    displayLarge: base.textTheme.displayLarge?.copyWith(
      fontFamily: 'serif',
      fontWeight: FontWeight.w600,
      letterSpacing: -1.4,
      color: colors.ink,
    ),
    displayMedium: base.textTheme.displayMedium?.copyWith(
      fontFamily: 'serif',
      fontWeight: FontWeight.w600,
      letterSpacing: -1.0,
      color: colors.ink,
    ),
    displaySmall: base.textTheme.displaySmall?.copyWith(
      fontFamily: 'serif',
      fontWeight: FontWeight.w600,
      color: colors.ink,
    ),
    headlineLarge: base.textTheme.headlineLarge?.copyWith(
      fontFamily: 'serif',
      fontWeight: FontWeight.w600,
      color: colors.ink,
    ),
    headlineMedium: base.textTheme.headlineMedium?.copyWith(
      fontFamily: 'serif',
      fontWeight: FontWeight.w600,
      color: colors.ink,
    ),
    headlineSmall: base.textTheme.headlineSmall?.copyWith(
      fontFamily: 'serif',
      fontWeight: FontWeight.w600,
      color: colors.ink,
    ),
    titleLarge: base.textTheme.titleLarge?.copyWith(
      fontFamily: 'serif',
      fontWeight: FontWeight.w600,
      color: colors.ink,
    ),
    titleMedium: base.textTheme.titleMedium?.copyWith(
      fontWeight: FontWeight.w600,
      color: colors.ink,
    ),
    titleSmall: base.textTheme.titleSmall?.copyWith(
      fontWeight: FontWeight.w600,
      color: colors.ink,
    ),
    bodyLarge: base.textTheme.bodyLarge?.copyWith(
      fontSize: 16,
      height: 1.55,
      color: colors.ink,
    ),
    bodyMedium: base.textTheme.bodyMedium?.copyWith(
      fontSize: 14,
      height: 1.45,
      color: colors.inkSoft,
    ),
    bodySmall: base.textTheme.bodySmall?.copyWith(
      fontSize: 12,
      color: colors.inkFaint,
    ),
    labelLarge: base.textTheme.labelLarge?.copyWith(
      fontWeight: FontWeight.w600,
      letterSpacing: 0.1,
    ),
    labelMedium: base.textTheme.labelMedium?.copyWith(
      fontFamily: 'monospace',
      fontSize: 11,
      letterSpacing: 1.1,
      color: colors.inkFaint,
    ),
    labelSmall: base.textTheme.labelSmall?.copyWith(
      fontFamily: 'monospace',
      fontSize: 10,
      letterSpacing: 1.2,
      color: colors.inkFaint,
    ),
  );
  return base.copyWith(
    textTheme: textTheme,
    extensions: [colors],
    appBarTheme: AppBarTheme(
      backgroundColor: colors.paper,
      foregroundColor: colors.ink,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: textTheme.titleMedium,
    ),
    dividerTheme: DividerThemeData(
      color: colors.line,
      thickness: 1,
      space: 1,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: colors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BibliotecaRadii.md,
        borderSide: BorderSide(color: colors.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BibliotecaRadii.md,
        borderSide: BorderSide(color: colors.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BibliotecaRadii.md,
        borderSide: BorderSide(color: colors.focus, width: 2),
      ),
      hintStyle: TextStyle(color: colors.inkFaint),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: colors.accent,
        foregroundColor: colors.onAccent,
        minimumSize: const Size(44, 44),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
        shape: const RoundedRectangleBorder(borderRadius: BibliotecaRadii.md),
        textStyle: textTheme.labelLarge,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: colors.ink,
        minimumSize: const Size(44, 44),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
        side: BorderSide(color: colors.lineStrong),
        shape: const RoundedRectangleBorder(borderRadius: BibliotecaRadii.md),
        textStyle: textTheme.labelLarge,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: colors.accent,
        minimumSize: const Size(44, 44),
        shape: const RoundedRectangleBorder(borderRadius: BibliotecaRadii.md),
        textStyle: textTheme.labelLarge,
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(
        foregroundColor: colors.inkSoft,
        minimumSize: const Size(44, 44),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: colors.ink,
      contentTextStyle: TextStyle(color: colors.paper),
      behavior: SnackBarBehavior.floating,
      shape: const RoundedRectangleBorder(borderRadius: BibliotecaRadii.md),
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: colors.ink,
        borderRadius: BibliotecaRadii.sm,
      ),
      textStyle: TextStyle(color: colors.paper, fontSize: 12),
    ),
  );
}
