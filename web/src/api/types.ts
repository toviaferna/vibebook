export type BookStatus = "imported" | "converting" | "ready" | "error" | "interrupted" | "missing";

export type JobStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "completed"
  | "failed"
  | "cancelled"
  | "interrupted";

export type JobStage =
  | "preparing"
  | "synthesizing"
  | "assembling"
  | "finalizing"
  | "done"
  | "cancelled"
  | "error";

export interface Book {
  id: string;
  title: string;
  author: string;
  language: string;
  status: BookStatus;
  chapter_count: number;
  duration_ms: number | null;
  voice: string | null;
  engine: string | null;
  rate: string | null;
  cover_url: string | null;
  progress: number;
  last_position_ms: number;
  last_chapter_index: number;
  reading_progress: number;
  last_read_chapter_index: number | null;
  last_read_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookState {
  position_ms: number;
  chapter_index: number;
  playback_rate: number;
  updated_at: string | null;
}

export interface Job {
  id: string;
  book_id: string;
  status: JobStatus;
  stage: JobStage;
  completed_segments: number;
  total_segments: number;
  chapter_index: number | null;
  chapter_title: string | null;
  current_text: string | null;
  message: string | null;
  error: string | null;
  options: {
    voice?: string;
    engine?: string;
    style?: string;
    rate?: string;
    force?: boolean;
  };
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface BookDetail extends Book {
  state: BookState;
  last_job: Job | null;
}

export interface BookList {
  items: Book[];
  total: number;
  limit: number;
  offset: number;
}

export interface Voice {
  id: string;
  locale: string;
  gender: string;
  engines: string[];
  styles: string[];
}

export interface Engine {
  id: string;
  label: string;
  kind: "builtin" | "plugin";
  transport: "local" | "http" | "command";
  requires_network: boolean;
  requires_key: boolean;
  supports_styles: boolean;
  timing: "native_word" | "estimated_word" | "segment";
  max_chars: number;
  audio_suffix: string;
  license: string;
  source_url: string;
  description: string;
  config_schema: Record<string, string>;
  legacy: boolean;
  implemented: boolean;
  test_only: boolean;
  available: boolean;
  configured: boolean;
  plugin_url: string | null;
}

export interface EngineList {
  items: Engine[];
}

export interface Plugin {
  id: string;
  name: string;
  version: string;
  url: string;
  protocol: string;
  license: string;
  source: string;
  languages: string[];
  styles: string[];
  timings: string;
  max_chars: number;
  timeout_seconds: number;
  voice_count: number;
  has_token: boolean;
  enabled: boolean;
  added_at: string;
  updated_at: string;
}

export interface PluginList {
  items: Plugin[];
}

export interface PluginTest {
  ok: boolean;
  latency_ms: number;
  voice_count: number;
  message: string;
}

export interface Settings {
  library_dir: string;
  default_engine: string | null;
  default_voice: string;
  default_rate: string;
  reader_theme: "light" | "sepia" | "night";
  reader_font: "serif" | "sans" | "hyperlegible";
  reader_size: number;
  auto_scroll: boolean;
  skip_seconds: number;
  azure_configured: boolean;
}

export interface Preview {
  url: string;
  key: string;
}

export interface ConversionInput {
  voice: string;
  engine: string;
  style: string;
  rate: string;
  force: boolean;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface ManifestSegment {
  id: string;
  chapter_index: number;
  paragraph_index: number;
  chunk_index: number;
  text: string;
  source_href?: string | null;
  source_fragment?: string | null;
}

export interface ManifestChapter {
  index: number;
  title: string;
  level?: number;
  kind?: string;
  number?: number | null;
  generated_title?: boolean;
  duration_ms: number | null;
  audio: string | null;
  timing: string | null;
  segments: ManifestSegment[];
}

export interface TocNode {
  title: string;
  level: number;
  chapter_index: number | null;
  kind: string;
  children: TocNode[];
}

export interface ManifestImage {
  id: string;
  path: string;
  alt: string;
  caption: string | null;
  role: string;
  chapter_index: number | null;
  paragraph_index: number;
  position: "before" | "after" | "inline" | "page";
  width: number | null;
  height: number | null;
}

export interface Manifest {
  schema_version: number;
  id: string;
  title: string;
  author: string;
  language: string;
  status: BookStatus;
  duration_ms: number | null;
  voice: string | null;
  engine: string | null;
  style: string | null;
  rate: string | null;
  epub?: string | null;
  toc?: TocNode[];
  images?: ManifestImage[];
  chapters: ManifestChapter[];
}

export interface WordTiming {
  text: string;
  start_ms: number;
  end_ms: number;
}

export interface TimingSegment {
  id: string;
  start_ms: number;
  end_ms: number;
  precision: "exact" | "estimated";
  words: WordTiming[];
}

export interface ChapterTiming {
  schema_version: number;
  chapter_index: number;
  duration_ms: number;
  precision: "exact" | "estimated";
  segments: TimingSegment[];
}

export interface ChapterPayload {
  chapter: ManifestChapter;
  timing: ChapterTiming | null;
  audio_ready: boolean;
  duration_ms: number | null;
}

export interface ReadingState {
  book_id: string;
  chapter_index: number;
  char_offset: number;
  page_index: number;
  page_count: number | null;
  percent: number;
  cfi: string | null;
  updated_at: string | null;
}

export interface ReadingStateInput {
  chapter_index: number;
  char_offset: number;
  page_index: number;
  page_count: number | null;
  percent: number;
  cfi?: string | null;
}

export interface ReadingBookmark {
  id: number;
  book_id: string;
  chapter_index: number;
  char_offset: number;
  page_index: number;
  note: string | null;
  created_at: string;
}

export interface ReadingBookmarkInput {
  chapter_index: number;
  char_offset: number;
  page_index: number;
  note?: string | null;
}

export interface ReadingBookmarkList {
  items: ReadingBookmark[];
}

export interface BookPreferences {
  book_id: string;
  reader_mode: "book" | "text" | "original" | null;
  reader_palette: "paper" | "sepia" | "night" | null;
  reader_font: "serif" | "sans" | "hyperlegible" | null;
  reader_size: number | null;
  page_turn: boolean | null;
  ambience_enabled: boolean | null;
  updated_at: string | null;
}

export interface SearchResult {
  chapter_index: number;
  chapter_title: string;
  segment_id: string;
  position_ms: number;
  excerpt: string;
  offset: number;
}

export interface SearchResponse {
  items: SearchResult[];
}

export interface Bookmark {
  id: number;
  book_id: string;
  chapter_index: number;
  position_ms: number;
  note: string | null;
  created_at: string;
}

export interface BookmarkList {
  items: Bookmark[];
}

export interface BookmarkInput {
  chapter_index: number;
  position_ms: number;
  note?: string | null;
}

export type ReaderState = BookState;
