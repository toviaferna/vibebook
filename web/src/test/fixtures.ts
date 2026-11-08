import type {
  Book,
  BookDetail,
  BookmarkList,
  ChapterPayload,
  Job,
  Manifest,
  SearchResponse,
  Settings,
  Voice,
} from "../api/types";

export const sampleBook: Book = {
  id: "lazarillo-1234",
  title: "El Lazarillo de Tormes",
  author: "Anónimo",
  language: "es",
  status: "ready",
  chapter_count: 7,
  duration_ms: 3_600_000,
  voice: "es-MX-JorgeNeural",
  engine: "edge",
  rate: "-10%",
  cover_url: null,
  progress: 0.25,
  last_position_ms: 900_000,
  last_chapter_index: 3,
  created_at: "2026-11-07T10:00:00+00:00",
  updated_at: "2026-11-07T10:00:00+00:00",
};

export const sampleBookDetail: BookDetail = {
  ...sampleBook,
  state: {
    position_ms: 900_000,
    chapter_index: 3,
    playback_rate: 1,
    updated_at: "2026-11-07T10:00:00+00:00",
  },
  last_job: null,
};

export const sampleSettings: Settings = {
  library_dir: "C:\\Vibebook\\library",
  default_voice: "es-MX-JorgeNeural",
  default_rate: "-10%",
  reader_theme: "light",
  reader_font: "serif",
  reader_size: 19,
  auto_scroll: true,
  skip_seconds: 15,
  azure_configured: false,
};

export const sampleVoices: Voice[] = [
  {
    id: "es-MX-JorgeNeural",
    locale: "es-MX",
    gender: "male",
    engines: ["edge", "azure"],
    styles: ["cheerful", "sad"],
  },
  {
    id: "es-MX-DaliaNeural",
    locale: "es-MX",
    gender: "female",
    engines: ["edge", "azure"],
    styles: ["cheerful"],
  },
  {
    id: "es-PY-MarioNeural",
    locale: "es-PY",
    gender: "male",
    engines: ["edge"],
    styles: [],
  },
];

export const sampleManifest: Manifest = {
  schema_version: 2,
  id: sampleBook.id,
  title: sampleBook.title,
  author: sampleBook.author,
  language: sampleBook.language,
  status: "ready",
  duration_ms: 2_000,
  voice: "es-MX-JorgeNeural",
  engine: "edge",
  style: "neutral",
  rate: "-10%",
  chapters: [
    {
      index: 1,
      title: "Capítulo 1",
      duration_ms: 2_000,
      audio: "audio/chapters/chapter_001.mp3",
      timing: "timings/chapter_001.json",
      segments: [
        {
          id: "c001p0001s00",
          chapter_index: 1,
          paragraph_index: 1,
          chunk_index: 0,
          text: "Hola, mundo. Esta es una prueba.",
        },
      ],
    },
  ],
};

export const sampleChapter: ChapterPayload = {
  chapter: sampleManifest.chapters[0],
  audio_ready: true,
  duration_ms: 2_000,
  timing: {
    schema_version: 1,
    chapter_index: 1,
    duration_ms: 2_000,
    precision: "exact",
    segments: [
      {
        id: "c001p0001s00",
        start_ms: 0,
        end_ms: 2_000,
        precision: "exact",
        words: [
          { text: "Hola,", start_ms: 0, end_ms: 300 },
          { text: "mundo.", start_ms: 300, end_ms: 700 },
          { text: "Esta", start_ms: 800, end_ms: 1_100 },
          { text: "es", start_ms: 1_100, end_ms: 1_300 },
          { text: "una", start_ms: 1_300, end_ms: 1_500 },
          { text: "prueba.", start_ms: 1_500, end_ms: 2_000 },
        ],
      },
    ],
  },
};

export const sampleSearch: SearchResponse = {
  items: [
    {
      chapter_index: 1,
      chapter_title: "Capítulo 1",
      segment_id: "c001p0001s00",
      position_ms: 0,
      excerpt: "Hola, mundo. Esta es una prueba.",
      offset: 0,
    },
  ],
};

export const sampleBookmarks: BookmarkList = {
  items: [
    {
      id: 1,
      book_id: sampleBook.id,
      chapter_index: 1,
      position_ms: 500,
      note: "Marcador de prueba",
      created_at: "2026-11-07T10:00:00+00:00",
    },
  ],
};

export const sampleJob: Job = {
  id: "job_1",
  book_id: sampleBook.id,
  status: "completed",
  stage: "done",
  completed_segments: 10,
  total_segments: 10,
  chapter_index: null,
  chapter_title: null,
  current_text: null,
  message: "Listo",
  error: null,
  options: {
    voice: "es-MX-JorgeNeural",
    engine: "edge",
    style: "neutral",
    rate: "-10%",
    force: false,
  },
  created_at: "2026-11-07T10:00:00+00:00",
  updated_at: "2026-11-07T10:01:00+00:00",
  started_at: "2026-11-07T10:00:00+00:00",
  finished_at: "2026-11-07T10:01:00+00:00",
};
