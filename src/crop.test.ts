import { describe, expect, it } from "vitest";
import {
  CROP_TWEEN_MS,
  cropAt,
  cropTransform,
  FULL_FRAME,
  isFullFrame,
  lerpCrop,
  normaliseCrop,
} from "./crop";
import type { Chapter } from "./types";

const chapter = (
  title: string,
  startMs: number,
  crop?: Chapter["crop"],
): Chapter => ({ title, startMs, narration: "", crop });

describe("normaliseCrop", () => {
  it("treats a missing crop as the whole frame", () => {
    expect(normaliseCrop(undefined)).toEqual(FULL_FRAME);
  });

  it("keeps a valid crop", () => {
    const crop = { x: 0.1, y: 0.2, w: 0.5, h: 0.6 };
    expect(normaliseCrop(crop)).toEqual(crop);
  });

  it("pulls a crop that runs off the right edge back inside", () => {
    const out = normaliseCrop({ x: 0.9, y: 0, w: 0.5, h: 1 });
    expect(out.x + out.w).toBeLessThanOrEqual(1);
  });

  it("pulls a crop that runs off the bottom back inside", () => {
    const out = normaliseCrop({ x: 0, y: 0.95, w: 1, h: 0.4 });
    expect(out.y + out.h).toBeLessThanOrEqual(1);
  });

  it("refuses a degenerate rectangle", () => {
    const out = normaliseCrop({ x: 0, y: 0, w: 0, h: -1 });
    expect(out.w).toBeGreaterThan(0);
    expect(out.h).toBeGreaterThan(0);
  });

  it("clamps negative origins", () => {
    const out = normaliseCrop({ x: -0.5, y: -0.5, w: 0.5, h: 0.5 });
    expect(out.x).toBe(0);
    expect(out.y).toBe(0);
  });

  it("always returns something inside the frame", () => {
    const wild = [
      { x: 2, y: 2, w: 2, h: 2 },
      { x: -9, y: 0.5, w: 0.1, h: 9 },
      { x: 0.5, y: 0.5, w: 1, h: 1 },
    ];
    for (const crop of wild) {
      const out = normaliseCrop(crop);
      expect(out.x).toBeGreaterThanOrEqual(0);
      expect(out.y).toBeGreaterThanOrEqual(0);
      expect(out.x + out.w).toBeLessThanOrEqual(1 + 1e-9);
      expect(out.y + out.h).toBeLessThanOrEqual(1 + 1e-9);
    }
  });
});

describe("isFullFrame", () => {
  it("recognises the whole frame", () => {
    expect(isFullFrame(FULL_FRAME)).toBe(true);
    expect(isFullFrame({ x: 0, y: 0, w: 1, h: 0.5 })).toBe(false);
  });
});

describe("lerpCrop", () => {
  const a = { x: 0, y: 0, w: 1, h: 1 };
  const b = { x: 0.5, y: 0.5, w: 0.5, h: 0.5 };

  it("returns the endpoints exactly", () => {
    expect(lerpCrop(a, b, 0)).toEqual(a);
    expect(lerpCrop(a, b, 1)).toEqual(b);
  });

  it("clamps t outside 0..1", () => {
    expect(lerpCrop(a, b, -5)).toEqual(a);
    expect(lerpCrop(a, b, 5)).toEqual(b);
  });

  it("is monotonic between the endpoints", () => {
    let previous = -Infinity;
    for (let t = 0; t <= 1.0001; t += 0.1) {
      const x = lerpCrop(a, b, t).x;
      expect(x).toBeGreaterThanOrEqual(previous);
      previous = x;
    }
  });
});

describe("cropAt", () => {
  it("is the whole frame with no chapters", () => {
    expect(cropAt([], 0)).toEqual(FULL_FRAME);
  });

  it("is the whole frame for chapters that set no crop", () => {
    const chapters = [chapter("a", 0), chapter("b", 1000)];
    expect(cropAt(chapters, 1500)).toEqual(FULL_FRAME);
  });

  it("uses the active chapter's crop once the tween is done", () => {
    const crop = { x: 0, y: 0, w: 0.5, h: 0.5 };
    const chapters = [chapter("a", 0), chapter("b", 1000, crop)];
    expect(cropAt(chapters, 1000 + CROP_TWEEN_MS)).toEqual(crop);
  });

  it("does not tween into the first chapter", () => {
    const crop = { x: 0.25, y: 0, w: 0.5, h: 1 };
    expect(cropAt([chapter("a", 0, crop)], 0)).toEqual(crop);
  });

  it("tweens from the previous chapter's crop", () => {
    const chapters = [
      chapter("a", 0, { x: 0, y: 0, w: 1, h: 1 }),
      chapter("b", 1000, { x: 0.5, y: 0, w: 0.5, h: 1 }),
    ];
    const mid = cropAt(chapters, 1000 + CROP_TWEEN_MS / 2);
    expect(mid.w).toBeGreaterThan(0.5);
    expect(mid.w).toBeLessThan(1);
  });

  it("holds the first chapter's crop before it starts", () => {
    const crop = { x: 0.1, y: 0.1, w: 0.5, h: 0.5 };
    expect(cropAt([chapter("a", 500, crop)], 0)).toEqual(crop);
  });

  it("stays on the last chapter past the end", () => {
    const crop = { x: 0, y: 0.5, w: 1, h: 0.5 };
    const chapters = [chapter("a", 0), chapter("b", 1000, crop)];
    expect(cropAt(chapters, 999999)).toEqual(crop);
  });
});

describe("cropTransform", () => {
  it("is a no-op for the whole frame", () => {
    const t = cropTransform(FULL_FRAME);
    expect(t.scale).toBe(1);
    expect(t.translatePercentX).toBe(0);
    expect(t.translatePercentY).toBe(0);
  });

  it("scales up as the crop shrinks", () => {
    expect(cropTransform({ x: 0, y: 0, w: 0.5, h: 0.5 }).scale).toBe(2);
    expect(cropTransform({ x: 0, y: 0, w: 0.25, h: 0.25 }).scale).toBe(4);
  });

  it("uses the larger dimension so the crop always fits", () => {
    // A wide, short crop must not scale by its height, or the sides get cut.
    expect(cropTransform({ x: 0, y: 0, w: 1, h: 0.25 }).scale).toBe(1);
  });

  it("shifts a left-hand crop to the right", () => {
    const t = cropTransform({ x: 0, y: 0, w: 0.5, h: 1 });
    expect(t.translatePercentX).toBeGreaterThan(0);
  });

  it("shifts a right-hand crop to the left", () => {
    const t = cropTransform({ x: 0.5, y: 0, w: 0.5, h: 1 });
    expect(t.translatePercentX).toBeLessThan(0);
  });

  it("emits a css transform string", () => {
    expect(cropTransform({ x: 0, y: 0, w: 0.5, h: 0.5 }).css).toMatch(
      /^translate\(.*%, .*%\) scale\(2\.0000\)$/,
    );
  });
});
