import { act, renderHook } from "@testing-library/react";

import { useAudioPlayer } from "./useAudioPlayer";

function makeAudio() {
  const audio = document.createElement("audio");
  let currentTime = 0;
  let paused = true;

  Object.defineProperty(audio, "duration", { configurable: true, get: () => 10 });
  Object.defineProperty(audio, "currentTime", {
    configurable: true,
    get: () => currentTime,
    set: (value: number) => {
      currentTime = value;
    },
  });
  Object.defineProperty(audio, "paused", { configurable: true, get: () => paused });
  vi.spyOn(audio, "play").mockImplementation(() => {
    paused = false;
    audio.dispatchEvent(new Event("play"));
    return Promise.resolve();
  });
  vi.spyOn(audio, "pause").mockImplementation(() => {
    paused = true;
    audio.dispatchEvent(new Event("pause"));
  });

  return {
    audio,
    currentTime: () => currentTime,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useAudioPlayer", () => {
  it("refleja play y pausa", () => {
    const { audio } = makeAudio();
    const { result } = renderHook(() => useAudioPlayer(audio));

    act(() => result.current.play());
    expect(result.current.isPlaying).toBe(true);

    act(() => result.current.pause());
    expect(result.current.isPlaying).toBe(false);
  });

  it("recorta el seek a la duración del audio", () => {
    const { audio, currentTime } = makeAudio();
    const { result } = renderHook(() => useAudioPlayer(audio));

    expect(result.current.durationMs).toBe(10_000);

    act(() => result.current.seekMs(15_000));
    expect(currentTime()).toBe(10);
    expect(result.current.currentTimeMs).toBe(10_000);

    act(() => result.current.seekMs(-5_000));
    expect(currentTime()).toBe(0);
  });

  it("aplica velocidad y volumen al elemento de audio", () => {
    const { audio } = makeAudio();
    const { result } = renderHook(() => useAudioPlayer(audio));

    act(() => result.current.setRate(1.5));
    expect(audio.playbackRate).toBe(1.5);

    act(() => result.current.setVolume(2));
    expect(audio.volume).toBe(1);
  });

  it("expone un error cuando el audio no carga", () => {
    const { audio } = makeAudio();
    const { result } = renderHook(() => useAudioPlayer(audio));

    act(() => audio.dispatchEvent(new Event("error")));
    expect(result.current.error).toMatch(/audio/i);
  });
});
