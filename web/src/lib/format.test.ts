import { formatDuration, formatPercent, formatRate, formatStatus, formatTime } from "./format";

describe("format", () => {
  it("formatea duraciones", () => {
    expect(formatDuration(3_600_000)).toBe("1 h 0 min");
    expect(formatDuration(90_000)).toBe("1 min");
    expect(formatDuration(1_400)).toBe("1 s");
    expect(formatDuration(null)).toBe("—");
  });

  it("formatea tiempos de audio", () => {
    expect(formatTime(0)).toBe("0:00");
    expect(formatTime(59_000)).toBe("0:59");
    expect(formatTime(65_000)).toBe("1:05");
    expect(formatTime(3_600_000)).toBe("1:00:00");
    expect(formatTime(3_665_000)).toBe("1:01:05");
  });

  it("recorta tiempos negativos a cero", () => {
    expect(formatTime(-1_000)).toBe("0:00");
  });

  it("formatea porcentajes y velocidades", () => {
    expect(formatPercent(0.426)).toBe("43%");
    expect(formatRate("-10%")).toBe("-10%");
    expect(formatRate("+0%")).toBe("0%");
  });

  it("traduce estados", () => {
    expect(formatStatus("ready")).toBe("Listo");
    expect(formatStatus("running")).toBe("En curso");
    expect(formatStatus("unknown")).toBe("unknown");
  });
});
