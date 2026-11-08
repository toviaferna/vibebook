import { ArrowLeft, Bookmark, Keyboard, List, Maximize, Search, Type } from "lucide-react";
import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { apiUrl, errorMessage } from "../../api/client";
import {
  useReaderChapter,
  useReaderManifest,
  useReaderState,
  useSaveReaderState,
  useSettings,
  useUpdateSettings,
} from "../../api/queries";
import type { ChapterTiming } from "../../api/types";
import { Button } from "../../components/Button";
import { alignSegment, findActive } from "./alignment";
import { OriginalEpubView } from "./original/OriginalEpubView";
import { ReaderBookmarksDialog } from "./ReaderBookmarksDialog";
import { ReaderContent } from "./ReaderContent";
import { ReaderPlayer } from "./ReaderPlayer";
import { ReaderSearchDialog } from "./ReaderSearchDialog";
import { ReaderSettingsDialog } from "./ReaderSettingsDialog";
import { ReaderToc } from "./ReaderToc";
import { ReaderTocDialog } from "./ReaderTocDialog";
import { ShortcutsDialog } from "./ShortcutsDialog";
import { useAudioPlayer } from "./useAudioPlayer";
import { useMediaSession } from "./useMediaSession";

type ReaderTheme = "light" | "sepia" | "night";
type ReaderFont = "serif" | "sans" | "hyperlegible";

export function ReaderPage() {
  const { id } = useParams<{ id: string }>();
  const manifestQuery = useReaderManifest(id);
  const stateQuery = useReaderState(id);
  const settingsQuery = useSettings();
  const saveState = useSaveReaderState(id ?? "");
  const updateSettings = useUpdateSettings();
  const manifest = manifestQuery.data;
  const settings = settingsQuery.data;
  const [chapterIndex, setChapterIndex] = useState(1);
  const [view, setView] = useState<"text" | "original">("text");
  const [tocOpen, setTocOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [bookmarksOpen, setBookmarksOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [follow, setFollow] = useState(true);
  const [followSuspended, setFollowSuspended] = useState(false);
  const [theme, setTheme] = useState<ReaderTheme>("light");
  const [font, setFont] = useState<ReaderFont>("serif");
  const [size, setSize] = useState(19);
  const [skipSeconds, setSkipSeconds] = useState(15);
  const [sleepMinutes, setSleepMinutes] = useState(0);
  const [seekNonce, setSeekNonce] = useState(0);
  const initialized = useRef(false);
  const prefsSeeded = useRef(false);
  const pendingSeek = useRef<number | null>(null);
  const autoPlay = useRef(false);
  const followTimer = useRef<number | null>(null);
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);
  const contentRef = useRef<HTMLElement>(null);

  const suspendFollow = useCallback(() => {
    if (!follow) {
      return;
    }
    setFollowSuspended(true);
    if (followTimer.current !== null) {
      window.clearTimeout(followTimer.current);
    }
    followTimer.current = window.setTimeout(() => {
      setFollowSuspended(false);
      followTimer.current = null;
    }, 5_000);
  }, [follow]);

  useEffect(
    () => () => {
      if (followTimer.current !== null) {
        window.clearTimeout(followTimer.current);
      }
    },
    [],
  );

  const goToChapter = useCallback((index: number, positionMs = 0, autoplay = false) => {
    pendingSeek.current = positionMs;
    autoPlay.current = autoplay;
    setChapterIndex(index);
    setSeekNonce((current) => current + 1);
    setTocOpen(false);
  }, []);

  const handleEnded = useCallback(() => {
    const chapters = manifest?.chapters ?? [];
    const position = chapters.findIndex((chapter) => chapter.index === chapterIndex);
    const next = chapters[position + 1];
    if (next) {
      goToChapter(next.index, 0, true);
    }
  }, [chapterIndex, goToChapter, manifest?.chapters]);

  const {
    isPlaying,
    currentTimeMs,
    durationMs,
    rate: playbackRate,
    volume,
    error: audioError,
    play,
    pause,
    toggle,
    seekMs,
    skip,
    setRate,
    setVolume,
  } = useAudioPlayer(audio, { onEnded: handleEnded });

  const chapterQuery = useReaderChapter(id, chapterIndex);
  const chapterPayload = chapterQuery.data;
  const chapter = chapterPayload?.chapter;
  const timing = chapterPayload?.timing ?? null;
  const audioSrc = id ? apiUrl(`/books/${id}/audio/${chapterIndex}`) : undefined;
  const chapters = manifest?.chapters ?? [];
  const chapterPosition = chapters.findIndex((item) => item.index === chapterIndex);
  const previousChapter = chapterPosition > 0 ? chapters[chapterPosition - 1] : null;
  const nextChapter =
    chapterPosition >= 0 && chapterPosition < chapters.length - 1
      ? chapters[chapterPosition + 1]
      : null;

  useEffect(() => {
    if (prefsSeeded.current || !settings) {
      return;
    }
    setTheme(settings.reader_theme);
    setFont(settings.reader_font);
    setSize(settings.reader_size);
    setFollow(settings.auto_scroll);
    setSkipSeconds(settings.skip_seconds);
    prefsSeeded.current = true;
  }, [settings]);

  useEffect(() => {
    document.body.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (!prefsSeeded.current) {
      return;
    }
    const timer = window.setTimeout(() => {
      updateSettings.mutate({
        reader_theme: theme,
        reader_font: font,
        reader_size: size,
        auto_scroll: follow,
      });
    }, 500);
    return () => window.clearTimeout(timer);
  }, [follow, font, size, theme, updateSettings.mutate]);

  useEffect(() => {
    if (initialized.current || !manifest || !stateQuery.data) {
      return;
    }
    if (manifest.chapters.length === 0) {
      return;
    }
    const initial =
      manifest.chapters.find((item) => item.index === stateQuery.data.chapter_index) ??
      manifest.chapters[0];
    pendingSeek.current = stateQuery.data.position_ms;
    setChapterIndex(initial.index);
    setRate(stateQuery.data.playback_rate);
    initialized.current = true;
  }, [manifest, setRate, stateQuery.data]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: re-attach pending seek when the chapter audio changes or the chapter is reselected
  useEffect(() => {
    if (!audio) {
      return;
    }
    const applyPending = () => {
      if (pendingSeek.current !== null) {
        const maximum = Number.isFinite(audio.duration)
          ? audio.duration * 1000
          : pendingSeek.current;
        audio.currentTime = Math.min(pendingSeek.current, maximum) / 1000;
        pendingSeek.current = null;
      }
      if (autoPlay.current) {
        autoPlay.current = false;
        void audio.play().catch(() => {
          // The control remains available when autoplay is blocked.
        });
      }
    };
    if (audio.readyState >= 1) {
      applyPending();
      return;
    }
    audio.addEventListener("loadedmetadata", applyPending, { once: true });
    return () => audio.removeEventListener("loadedmetadata", applyPending);
  }, [audio, chapterIndex, audioSrc, seekNonce]);

  const save = saveState.mutate;
  useEffect(() => {
    if (!initialized.current || !id) {
      return;
    }
    const timer = window.setTimeout(() => {
      save({
        position_ms: Math.round(currentTimeMs),
        chapter_index: chapterIndex,
        playback_rate: playbackRate,
      });
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [chapterIndex, currentTimeMs, id, playbackRate, save]);

  useEffect(() => {
    if (!id) {
      return;
    }
    const timer = window.setInterval(() => {
      if (!initialized.current) {
        return;
      }
      if (audio && !audio.paused) {
        save({
          position_ms: Math.round(audio.currentTime * 1000),
          chapter_index: chapterIndex,
          playback_rate: playbackRate,
        });
      }
    }, 5_000);
    return () => window.clearInterval(timer);
  }, [audio, chapterIndex, id, playbackRate, save]);

  useEffect(() => {
    if (!sleepMinutes || !isPlaying) {
      return;
    }
    const timer = window.setTimeout(() => {
      pause();
      setSleepMinutes(0);
    }, sleepMinutes * 60_000);
    return () => window.clearTimeout(timer);
  }, [isPlaying, pause, sleepMinutes]);

  const active = useMemo(() => findActive(timing, currentTimeMs), [currentTimeMs, timing]);
  const activeSegmentId = timing?.segments[active.segmentIndex]?.id ?? null;
  const activeWordIndex = active.wordIndex;

  const alignments = useMemo(() => {
    const result = new Map<string, ReturnType<typeof alignSegment>>();
    if (!chapter || !timing) {
      return result;
    }
    const byId = new Map(timing.segments.map((segment) => [segment.id, segment]));
    for (const segment of chapter.segments) {
      const aligned = alignSegment(segment, byId.get(segment.id));
      if (aligned.words.length > 0) {
        result.set(segment.id, aligned);
      }
    }
    return result;
  }, [chapter, timing]);

  useEffect(() => {
    if (view !== "text" || !follow || followSuspended || !activeSegmentId || !contentRef.current) {
      return;
    }
    const target = contentRef.current.querySelector(`[data-segment-id="${activeSegmentId}"]`);
    if (target && typeof target.scrollIntoView === "function") {
      const reduce =
        typeof window.matchMedia === "function" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      target.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
    }
  }, [activeSegmentId, follow, followSuspended, view]);

  const goPrevious = useCallback(() => {
    if (previousChapter) {
      goToChapter(previousChapter.index, 0, isPlaying);
    }
  }, [goToChapter, isPlaying, previousChapter]);

  const goNext = useCallback(() => {
    if (nextChapter) {
      goToChapter(nextChapter.index, 0, isPlaying);
    }
  }, [goToChapter, isPlaying, nextChapter]);

  const seekBackward = useCallback(() => skip(-skipSeconds), [skip, skipSeconds]);
  const seekForward = useCallback(() => skip(skipSeconds), [skip, skipSeconds]);

  const seekAndPlay = useCallback(
    (ms: number) => {
      seekMs(ms);
      if (audio?.paused) {
        play();
      }
    },
    [audio, play, seekMs],
  );

  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void document.documentElement.requestFullscreen().catch(() => {
        // Fullscreen is not available in every webview.
      });
    }
  }, []);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.tagName === "BUTTON" ||
          target.tagName === "A" ||
          target.isContentEditable)
      ) {
        return;
      }
      if (event.key === " " || event.code === "Space") {
        event.preventDefault();
        toggle();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        skip(-skipSeconds);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        skip(skipSeconds);
      } else if (event.key.toLowerCase() === "j") {
        event.preventDefault();
        goPrevious();
      } else if (event.key.toLowerCase() === "k") {
        event.preventDefault();
        goNext();
      } else if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        setRate(Math.min(2, Math.round((playbackRate + 0.25) * 100) / 100));
      } else if (event.key === "-") {
        event.preventDefault();
        setRate(Math.max(0.75, Math.round((playbackRate - 0.25) * 100) / 100));
      } else if (event.key.toLowerCase() === "t") {
        event.preventDefault();
        setTocOpen((current) => !current);
      } else if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        toggleFullscreen();
      } else if (event.key === "?") {
        event.preventDefault();
        setShortcutsOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goNext, goPrevious, playbackRate, setRate, skip, skipSeconds, toggle, toggleFullscreen]);

  useMediaSession({
    title: manifest?.title ?? "Vibebook",
    artist: manifest?.author ?? "",
    album: chapter?.title ?? "Audiolibro",
    isPlaying,
    rate: playbackRate,
    currentTimeMs,
    durationMs,
    onPlay: play,
    onPause: pause,
    onSeekBackward: seekBackward,
    onSeekForward: seekForward,
    onPrevious: goPrevious,
    onNext: goNext,
  });

  if (manifestQuery.isLoading) {
    return <ReaderLoading />;
  }

  if (manifestQuery.isError || !manifest) {
    return (
      <div className="reader-fallback">
        <p className="eyebrow">Lector</p>
        <h1>No se pudo abrir el libro.</h1>
        <p className="muted">{errorMessage(manifestQuery.error)}</p>
        <Link className="button" to="/">
          Volver a la biblioteca
        </Link>
      </div>
    );
  }

  if (manifest.status !== "ready") {
    return (
      <div className="reader-fallback">
        <p className="eyebrow">Lector</p>
        <h1>Este libro todavía no tiene audio.</h1>
        <p className="muted">Prepará la conversión y volvé cuando esté listo.</p>
        <Link className="button button--primary" to={`/books/${manifest.id}/studio`}>
          Abrir estudio
        </Link>
      </div>
    );
  }

  return (
    <div
      className="reader-shell"
      style={
        {
          "--reader-size": `${size}px`,
          "--reader-font":
            font === "serif"
              ? "var(--font-reading)"
              : font === "sans"
                ? "var(--font-ui)"
                : "'Atkinson Hyperlegible', sans-serif",
        } as CSSProperties
      }
    >
      <a className="skip-link" href="#reader-main">
        Saltar al texto
      </a>
      <header className="reader-topbar">
        <div className="reader-topbar-left">
          <Link className="icon-button" to={`/books/${manifest.id}`} aria-label="Volver al libro">
            <ArrowLeft size={19} />
          </Link>
          <div className="reader-topbar-title">
            <p className="eyebrow">Leyendo</p>
            <strong>{manifest.title}</strong>
            {chapter ? <span>{chapter.title}</span> : null}
          </div>
        </div>
        <div className="reader-topbar-actions">
          <fieldset className="reader-view-toggle">
            <legend className="sr-only">Vista de lectura</legend>
            <button type="button" aria-pressed={view === "text"} onClick={() => setView("text")}>
              Texto
            </button>
            <button
              type="button"
              aria-pressed={view === "original"}
              onClick={() => setView("original")}
            >
              Original
            </button>
          </fieldset>
          <button
            type="button"
            className="icon-button"
            onClick={() => setTocOpen(true)}
            aria-label="Abrir índice"
            title="Índice (T)"
          >
            <List size={19} />
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => setSearchOpen(true)}
            aria-label="Buscar en el libro"
            title="Buscar"
          >
            <Search size={19} />
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => setBookmarksOpen(true)}
            aria-label="Marcadores"
            title="Marcadores"
          >
            <Bookmark size={19} />
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => setSettingsOpen(true)}
            aria-label="Ajustes de lectura"
            title="Tipografía"
          >
            <Type size={19} />
          </button>
          <button
            type="button"
            className="icon-button reader-optional"
            onClick={toggleFullscreen}
            aria-label="Pantalla completa"
            title="Pantalla completa (F)"
          >
            <Maximize size={18} />
          </button>
          <button
            type="button"
            className="icon-button reader-optional"
            onClick={() => setShortcutsOpen(true)}
            aria-label="Atajos de teclado"
            title="Atajos (?)"
          >
            <Keyboard size={19} />
          </button>
        </div>
      </header>

      <div className="reader-layout">
        <aside className="reader-toc-panel">
          <ReaderToc chapters={chapters} currentIndex={chapterIndex} onSelect={goToChapter} />
        </aside>

        <main
          className="reader-article-wrap"
          id="reader-main"
          tabIndex={-1}
          onWheel={suspendFollow}
          onTouchMove={suspendFollow}
        >
          {chapterQuery.isLoading ? (
            <div className="reader-chapter-loading">
              <span className="sr-only">Cargando capítulo</span>
              <div className="skeleton skeleton--title" />
              <div className="skeleton" />
              <div className="skeleton" />
              <div className="skeleton" />
            </div>
          ) : chapterQuery.isError || !chapter ? (
            <div className="alert" role="alert">
              <span>{errorMessage(chapterQuery.error)}</span>
              <Button variant="ghost" onClick={() => chapterQuery.refetch()}>
                Reintentar
              </Button>
            </div>
          ) : view === "original" ? (
            <OriginalEpubView bookId={manifest.id} chapter={chapter} />
          ) : (
            <ReaderContent
              ref={contentRef}
              chapter={chapter}
              timing={timing as ChapterTiming | null}
              alignments={alignments}
              activeSegmentId={activeSegmentId}
              activeWordIndex={activeWordIndex}
              onSeek={seekAndPlay}
            />
          )}

          {view === "text" && activeSegmentId && (followSuspended || !follow) ? (
            <button
              type="button"
              className="reader-follow-float"
              onClick={() => {
                setFollow(true);
                setFollowSuspended(false);
              }}
            >
              Volver al texto
            </button>
          ) : null}
        </main>
      </div>

      {/* biome-ignore lint/a11y/useMediaCaption: the audiobook text is shown and synchronized on screen */}
      <audio ref={setAudio} className="reader-audio" src={audioSrc} preload="metadata" />

      <ReaderPlayer
        chapterTitle={chapter?.title ?? ""}
        isPlaying={isPlaying}
        currentTimeMs={currentTimeMs}
        durationMs={durationMs}
        rate={playbackRate}
        volume={volume}
        skipSeconds={skipSeconds}
        sleepMinutes={sleepMinutes}
        follow={follow}
        audioError={audioError}
        onToggle={toggle}
        onSkip={skip}
        onPrevious={goPrevious}
        onNext={goNext}
        onSeek={seekMs}
        onRate={setRate}
        onVolume={setVolume}
        onSleep={setSleepMinutes}
        onFollow={() => setFollow((current) => !current)}
      />

      <ReaderTocDialog
        open={tocOpen}
        onOpenChange={setTocOpen}
        chapters={chapters}
        currentIndex={chapterIndex}
        onSelect={goToChapter}
      />
      <ReaderSearchDialog
        open={searchOpen}
        onOpenChange={setSearchOpen}
        bookId={manifest.id}
        onSelect={goToChapter}
      />
      <ReaderBookmarksDialog
        open={bookmarksOpen}
        onOpenChange={setBookmarksOpen}
        bookId={manifest.id}
        chapters={chapters}
        currentChapter={chapterIndex}
        currentTimeMs={currentTimeMs}
        onSelect={(bookmark) => goToChapter(bookmark.chapter_index, bookmark.position_ms)}
      />
      <ReaderSettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        theme={theme}
        font={font}
        size={size}
        follow={follow}
        onTheme={setTheme}
        onFont={setFont}
        onSize={setSize}
        onFollow={setFollow}
      />
      <ShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </div>
  );
}

function ReaderLoading() {
  return (
    <div className="reader-fallback">
      <div className="page-loading" aria-label="Cargando lector" role="status">
        <div className="skeleton skeleton--title" />
        <div className="skeleton" />
        <div className="skeleton" />
      </div>
    </div>
  );
}
