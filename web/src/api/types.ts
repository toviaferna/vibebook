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

export interface ResegmentChapterChange {
  index: number;
  title: string;
  changed: boolean;
  changed_segments: number;
  added_segments: number;
  removed_segments: number;
}

export interface ResegmentPlan {
  book_id: string;
  title: string;
  status: BookStatus;
  can_repair: boolean;
  needs_repair: boolean;
  reason: string | null;
  current_version: number | null;
  target_version: number;
  max_chars: number;
  source_available: boolean;
  old_segments: number;
  new_segments: number;
  changed_segments: number;
  changed_chapters: number[];
  chapters: ResegmentChapterChange[];
}

export interface ResegmentResult extends ResegmentPlan {
  changed: boolean;
  dry_run: boolean;
  backup_id: string | null;
  synthesized_segments?: number;
  reused_segments?: number;
  rebuilt_chapters?: number[];
  duration_ms?: number | null;
}

export interface ResegmentBackup {
  id: string;
  created_at: string | null;
  reason: string | null;
  changed_chapters: number[];
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
  theme_mode: "system" | "light" | "dark";
  reader_palette: "paper" | "sepia" | "night";
  /** @deprecated Use reader_palette. Kept for old API clients. */
  reader_theme: "light" | "sepia" | "night";
  reader_font: "serif" | "sans" | "hyperlegible";
  reader_size: number;
  auto_scroll: boolean;
  skip_seconds: number;
  azure_configured: boolean;
}

export type SoundKind = "ambience" | "effect" | "music";

export interface SoundAsset {
  id: string;
  kind: SoundKind;
  prompt: string;
  tags: string[];
  provider: string;
  model: string | null;
  seed: number | null;
  duration_ms: number;
  loopable: boolean;
  sample_rate: number;
  channels: number;
  loudness_lufs: number | null;
  license: string;
  attribution: string | null;
  source_url: string | null;
  checksum: string;
  approved: boolean;
  created_at: string;
  last_used_at: string | null;
  usage_count: number;
  audio_url: string;
}

export interface SoundAssetList {
  items: SoundAsset[];
  total: number;
  limit: number;
  offset: number;
}

export interface AmbienceSettings {
  enabled: boolean;
  master_gain_db: number;
  ducking_db: number;
}

export interface AmbienceAnchor {
  segment_id: string;
  offset_ms: number;
}

export interface AmbienceBed {
  asset_id: string;
  kind: "ambience";
  start_ms: number;
  end_ms: number | null;
  loop: boolean;
  gain_db: number;
  fade_in_ms: number;
  fade_out_ms: number;
  confidence: number;
  reason: string;
}

export interface AmbienceEffect {
  asset_id: string;
  kind: "effect";
  anchor: AmbienceAnchor;
  duration_ms: number;
  gain_db: number;
  confidence: number;
  reason: string;
}

export interface AmbienceChapter {
  chapter_index: number;
  bed: AmbienceBed | null;
  effects: AmbienceEffect[];
}

export interface AmbiencePlan {
  version: number;
  chapters: AmbienceChapter[];
}

export interface BookAmbience {
  book_id: string;
  settings: AmbienceSettings;
  plan: AmbiencePlan;
}

export interface AmbiencePlanUpdate {
  settings: AmbienceSettings;
  plan: AmbiencePlan;
}

export interface Preview {
  url: string;
  key: string;
}

export interface MediaTicket {
  url: string;
  expires_at: string;
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
  boundary?: string;
  continuation?: boolean;
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
  timing_offset_ms?: number;
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
  sequence: number;
  updated_at: string | null;
}

export interface ReadingStateInput {
  chapter_index: number;
  char_offset: number;
  page_index: number;
  page_count: number | null;
  percent: number;
  cfi?: string | null;
  sequence?: number;
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
  char_offset: number;
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
