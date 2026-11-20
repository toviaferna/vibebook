enum ReaderViewMode {
  text('Texto'),
  book('Libro'),
  original('Original');

  const ReaderViewMode(this.label);

  final String label;

  static ReaderViewMode fromName(String? name) {
    return switch (name) {
      'book' => ReaderViewMode.book,
      'original' => ReaderViewMode.original,
      _ => ReaderViewMode.text,
    };
  }
}
