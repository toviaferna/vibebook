import 'package:material_ui/material_ui.dart';

@immutable
class BibliotecaColors extends ThemeExtension<BibliotecaColors> {
  const BibliotecaColors({
    required this.paper,
    required this.paperDeep,
    required this.surface,
    required this.surfaceRaised,
    required this.ink,
    required this.inkSoft,
    required this.inkFaint,
    required this.line,
    required this.lineStrong,
    required this.accent,
    required this.accentStrong,
    required this.accentSoft,
    required this.onAccent,
    required this.brass,
    required this.audio,
    required this.audioSoft,
    required this.warning,
    required this.danger,
    required this.focus,
    required this.highlight,
    required this.highlightWord,
  });

  final Color paper;
  final Color paperDeep;
  final Color surface;
  final Color surfaceRaised;
  final Color ink;
  final Color inkSoft;
  final Color inkFaint;
  final Color line;
  final Color lineStrong;
  final Color accent;
  final Color accentStrong;
  final Color accentSoft;
  final Color onAccent;
  final Color brass;
  final Color audio;
  final Color audioSoft;
  final Color warning;
  final Color danger;
  final Color focus;
  final Color highlight;
  final Color highlightWord;

  static const light = BibliotecaColors(
    paper: Color(0xFFF2EBDD),
    paperDeep: Color(0xFFE7DDCB),
    surface: Color(0xFFFAF6EE),
    surfaceRaised: Color(0xFFFDFAF4),
    ink: Color(0xFF211D19),
    inkSoft: Color(0xFF574C43),
    inkFaint: Color(0xFF6E6258),
    line: Color(0xFFD8CDBD),
    lineStrong: Color(0xFFB9AA97),
    accent: Color(0xFF7A2E2E),
    accentStrong: Color(0xFF5E2028),
    accentSoft: Color(0xFFEADDD8),
    onAccent: Color(0xFFFDFAF4),
    brass: Color(0xFFA8771F),
    audio: Color(0xFF35505F),
    audioSoft: Color(0xFFDCE5E9),
    warning: Color(0xFF8C5A1F),
    danger: Color(0xFFA33A32),
    focus: Color(0xFF35505F),
    highlight: Color(0xFFEAD9A8),
    highlightWord: Color(0xFFDCC173),
  );

  static const dark = BibliotecaColors(
    paper: Color(0xFF14110F),
    paperDeep: Color(0xFF0E0C0A),
    surface: Color(0xFF1D1916),
    surfaceRaised: Color(0xFF26211D),
    ink: Color(0xFFEDE6DA),
    inkSoft: Color(0xFFB8AC9E),
    inkFaint: Color(0xFF92857A),
    line: Color(0xFF332D27),
    lineStrong: Color(0xFF4B4239),
    accent: Color(0xFFD19A8A),
    accentStrong: Color(0xFFE5B4A6),
    accentSoft: Color(0xFF3A2523),
    onAccent: Color(0xFF14110F),
    brass: Color(0xFFD6B36A),
    audio: Color(0xFF9BB7D4),
    audioSoft: Color(0xFF1B2B3A),
    warning: Color(0xFFD9A45C),
    danger: Color(0xFFE0857A),
    focus: Color(0xFF9BB7D4),
    highlight: Color(0xFF3B3120),
    highlightWord: Color(0xFF574A25),
  );

  @override
  BibliotecaColors copyWith({
    Color? paper,
    Color? paperDeep,
    Color? surface,
    Color? surfaceRaised,
    Color? ink,
    Color? inkSoft,
    Color? inkFaint,
    Color? line,
    Color? lineStrong,
    Color? accent,
    Color? accentStrong,
    Color? accentSoft,
    Color? onAccent,
    Color? brass,
    Color? audio,
    Color? audioSoft,
    Color? warning,
    Color? danger,
    Color? focus,
    Color? highlight,
    Color? highlightWord,
  }) {
    return BibliotecaColors(
      paper: paper ?? this.paper,
      paperDeep: paperDeep ?? this.paperDeep,
      surface: surface ?? this.surface,
      surfaceRaised: surfaceRaised ?? this.surfaceRaised,
      ink: ink ?? this.ink,
      inkSoft: inkSoft ?? this.inkSoft,
      inkFaint: inkFaint ?? this.inkFaint,
      line: line ?? this.line,
      lineStrong: lineStrong ?? this.lineStrong,
      accent: accent ?? this.accent,
      accentStrong: accentStrong ?? this.accentStrong,
      accentSoft: accentSoft ?? this.accentSoft,
      onAccent: onAccent ?? this.onAccent,
      brass: brass ?? this.brass,
      audio: audio ?? this.audio,
      audioSoft: audioSoft ?? this.audioSoft,
      warning: warning ?? this.warning,
      danger: danger ?? this.danger,
      focus: focus ?? this.focus,
      highlight: highlight ?? this.highlight,
      highlightWord: highlightWord ?? this.highlightWord,
    );
  }

  @override
  BibliotecaColors lerp(ThemeExtension<BibliotecaColors>? other, double t) {
    if (other is! BibliotecaColors) {
      return this;
    }
    return BibliotecaColors(
      paper: Color.lerp(paper, other.paper, t)!,
      paperDeep: Color.lerp(paperDeep, other.paperDeep, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      surfaceRaised: Color.lerp(surfaceRaised, other.surfaceRaised, t)!,
      ink: Color.lerp(ink, other.ink, t)!,
      inkSoft: Color.lerp(inkSoft, other.inkSoft, t)!,
      inkFaint: Color.lerp(inkFaint, other.inkFaint, t)!,
      line: Color.lerp(line, other.line, t)!,
      lineStrong: Color.lerp(lineStrong, other.lineStrong, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentStrong: Color.lerp(accentStrong, other.accentStrong, t)!,
      accentSoft: Color.lerp(accentSoft, other.accentSoft, t)!,
      onAccent: Color.lerp(onAccent, other.onAccent, t)!,
      brass: Color.lerp(brass, other.brass, t)!,
      audio: Color.lerp(audio, other.audio, t)!,
      audioSoft: Color.lerp(audioSoft, other.audioSoft, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      danger: Color.lerp(danger, other.danger, t)!,
      focus: Color.lerp(focus, other.focus, t)!,
      highlight: Color.lerp(highlight, other.highlight, t)!,
      highlightWord: Color.lerp(highlightWord, other.highlightWord, t)!,
    );
  }
}

class BibliotecaSpacing {
  static const x1 = 4.0;
  static const x2 = 8.0;
  static const x3 = 12.0;
  static const x4 = 16.0;
  static const x5 = 24.0;
  static const x6 = 32.0;
  static const x7 = 48.0;
  static const x8 = 64.0;
}

class BibliotecaRadii {
  static const sm = BorderRadius.all(Radius.circular(2));
  static const md = BorderRadius.all(Radius.circular(4));
  static const lg = BorderRadius.all(Radius.circular(6));
}

class ReaderPalette {
  const ReaderPalette({
    required this.name,
    required this.paper,
    required this.paperDeep,
    required this.surface,
    required this.ink,
    required this.inkSoft,
    required this.inkFaint,
    required this.line,
    required this.accent,
    required this.accentSoft,
    required this.highlight,
    required this.highlightWord,
    required this.onAccent,
  });

  final String name;
  final Color paper;
  final Color paperDeep;
  final Color surface;
  final Color ink;
  final Color inkSoft;
  final Color inkFaint;
  final Color line;
  final Color accent;
  final Color accentSoft;
  final Color highlight;
  final Color highlightWord;
  final Color onAccent;

  static const paperPalette = ReaderPalette(
    name: 'paper',
    paper: Color(0xFFFBF7EF),
    paperDeep: Color(0xFFF3EDE2),
    surface: Color(0xFFFDFAF4),
    ink: Color(0xFF211D19),
    inkSoft: Color(0xFF574C43),
    inkFaint: Color(0xFF6E6258),
    line: Color(0xFFD8CDBD),
    accent: Color(0xFF7A2E2E),
    accentSoft: Color(0xFFEADDD8),
    highlight: Color(0xFFEAD9A8),
    highlightWord: Color(0xFFDCC173),
    onAccent: Color(0xFFFDFAF4),
  );

  static const sepiaPalette = ReaderPalette(
    name: 'sepia',
    paper: Color(0xFFF1E4CC),
    paperDeep: Color(0xFFE8D8B8),
    surface: Color(0xFFF8EFDD),
    ink: Color(0xFF2D2822),
    inkSoft: Color(0xFF5E5344),
    inkFaint: Color(0xFF6B604D),
    line: Color(0xFFD9C7A5),
    accent: Color(0xFF7A2E2E),
    accentSoft: Color(0xFFEAD9C4),
    highlight: Color(0xFFE5CFA0),
    highlightWord: Color(0xFFD4B36A),
    onAccent: Color(0xFFFDFAF4),
  );

  static const nightPalette = ReaderPalette(
    name: 'night',
    paper: Color(0xFF12100E),
    paperDeep: Color(0xFF0C0A09),
    surface: Color(0xFF1B1714),
    ink: Color(0xFFEDE6D8),
    inkSoft: Color(0xFFB8AC9E),
    inkFaint: Color(0xFF92857A),
    line: Color(0xFF332D27),
    accent: Color(0xFFD19A8A),
    accentSoft: Color(0xFF3A2523),
    highlight: Color(0xFF3B3120),
    highlightWord: Color(0xFF574A25),
    onAccent: Color(0xFF14110F),
  );

  static ReaderPalette byName(String name) {
    return switch (name) {
      'sepia' => sepiaPalette,
      'night' => nightPalette,
      _ => paperPalette,
    };
  }
}
