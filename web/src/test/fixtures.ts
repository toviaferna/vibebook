import type {
  Book,
  BookDetail,
  BookmarkList,
  ChapterPayload,
  EngineList,
  Job,
  Manifest,
  PluginList,
  ReadingBookmarkList,
  ReadingState,
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
  reading_progress: 0.4,
  last_read_chapter_index: 2,
  last_read_at: "2026-11-07T10:00:00+00:00",
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
  default_engine: "edge",
  default_voice: "es-MX-JorgeNeural",
  default_rate: "-10%",
  theme_mode: "system",
  reader_palette: "paper",
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
  {
    id: "es_MX-ald-medium",
    locale: "es-MX",
    gender: "male",
    engines: ["piper"],
    styles: [],
  },
];

export const sampleEngines: EngineList = {
  items: [
    {
      id: "piper",
      label: "Piper",
      kind: "builtin",
      transport: "local",
      requires_network: false,
      requires_key: false,
      supports_styles: false,
      timing: "segment",
      max_chars: 400,
      audio_suffix: ".wav",
      license: "GPL-3.0",
      source_url: "https://github.com/OHF-Voice/piper1-gpl",
      description: "TTS local en CPU; requiere binario, voz Piper y espeak-ng-data.",
      config_schema: {
        binary_env: "VIBEBOOK_PIPER_BIN",
        voices_env: "VIBEBOOK_PIPER_VOICES",
      },
      legacy: false,
      implemented: true,
      test_only: false,
      available: true,
      configured: true,
      plugin_url: null,
    },
    {
      id: "edge",
      label: "Edge TTS",
      kind: "builtin",
      transport: "http",
      requires_network: true,
      requires_key: false,
      supports_styles: false,
      timing: "native_word",
      max_chars: 400,
      audio_suffix: ".mp3",
      license: "Servicio externo no oficial",
      source_url: "https://github.com/rany2/edge-tts",
      description: "Voz gratuita de Microsoft Edge; requiere internet.",
      config_schema: {},
      legacy: true,
      implemented: true,
      test_only: false,
      available: true,
      configured: true,
      plugin_url: null,
    },
    {
      id: "azure",
      label: "Azure Speech",
      kind: "builtin",
      transport: "http",
      requires_network: true,
      requires_key: true,
      supports_styles: true,
      timing: "native_word",
      max_chars: 400,
      audio_suffix: ".mp3",
      license: "Servicio comercial",
      source_url: "https://azure.microsoft.com/products/ai-services/text-to-speech",
      description: "Estilos y word boundaries; requiere clave y cuota.",
      config_schema: {
        key_env: "AZURE_SPEECH_KEY",
        region_env: "AZURE_SPEECH_REGION",
      },
      legacy: true,
      implemented: true,
      test_only: false,
      available: false,
      configured: false,
      plugin_url: null,
    },
    {
      id: "fake",
      label: "Motor de prueba",
      kind: "builtin",
      transport: "local",
      requires_network: false,
      requires_key: false,
      supports_styles: false,
      timing: "segment",
      max_chars: 400,
      audio_suffix: ".wav",
      license: "AGPL-3.0-only",
      source_url: "",
      description: "Genera WAV sintético para tests; no usar en producción.",
      config_schema: {},
      legacy: false,
      implemented: true,
      test_only: true,
      available: true,
      configured: true,
      plugin_url: null,
    },
  ],
};

export const samplePlugin = {
  id: "demo-vep",
  name: "Demo VEP",
  version: "1.0.0",
  url: "http://127.0.0.1:9001",
  protocol: "vep/1",
  license: "MIT",
  source: "https://example.com/demo-vep",
  languages: ["es"],
  styles: [],
  timings: "segment",
  max_chars: 400,
  timeout_seconds: 30,
  voice_count: 1,
  has_token: false,
  enabled: true,
  added_at: "2026-11-08T10:00:00+00:00",
  updated_at: "2026-11-08T10:00:00+00:00",
};

export const samplePlugins: PluginList = { items: [] };

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
  toc: [
    {
      title: "Parte I",
      level: 0,
      chapter_index: null,
      kind: "part",
      children: [
        {
          title: "Capítulo 1",
          level: 1,
          chapter_index: 1,
          kind: "chapter",
          children: [],
        },
      ],
    },
  ],
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

export const sampleReadingState: ReadingState = {
  book_id: sampleBook.id,
  chapter_index: 1,
  char_offset: 0,
  page_index: 0,
  page_count: 1,
  percent: 0,
  cfi: null,
  updated_at: null,
};

export const sampleReadingBookmarks: ReadingBookmarkList = {
  items: [
    {
      id: 1,
      book_id: sampleBook.id,
      chapter_index: 1,
      char_offset: 0,
      page_index: 0,
      note: "Marcador de lectura",
      created_at: "2026-11-07T10:00:00+00:00",
    },
  ],
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
