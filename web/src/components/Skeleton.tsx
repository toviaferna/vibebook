const SKELETON_KEYS = ["one", "two", "three", "four", "five", "six"];

export function LibrarySkeleton() {
  return (
    <div className="page-loading" aria-label="Cargando biblioteca" role="status">
      <div className="skeleton skeleton--title" />
      <div className="book-grid">
        {SKELETON_KEYS.map((key) => (
          <div className="skeleton skeleton--card" key={key} />
        ))}
      </div>
    </div>
  );
}
