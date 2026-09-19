import { describe, expect, it } from "vitest";
import { bands, fitCard, WINDOW_BAR_HEIGHT } from "./layout";

/**
 * These guard the defect that shipped once already: the card was sized by
 * width alone, flexbox shrank it to fit, and `overflow: hidden` silently cut
 * the bottom quarter off the recording -- including the status bar a TUI keeps
 * there. Every assertion below is about the card fitting its box.
 */

const SOURCES = {
  y509: { w: 2280, h: 1406 },
  prpr: { w: 2014, h: 1226 },
  brtc: { w: 2200, h: 1368 },
  // Extremes a tape could plausibly produce.
  ultrawide: { w: 3440, h: 1000 },
  tall: { w: 800, h: 1600 },
  square: { w: 1000, h: 1000 },
};

const FRAMES = {
  "16x9": { w: 1920, h: 1080, vertical: false },
  "9x16": { w: 1080, h: 1920, vertical: true },
};

describe("fitCard", () => {
  for (const [frameName, frame] of Object.entries(FRAMES)) {
    describe(frameName, () => {
      for (const [sourceName, source] of Object.entries(SOURCES)) {
        it(`fits ${sourceName} inside the available box`, () => {
          const { width, height, band } = fitCard(
            frame.w,
            frame.h,
            source.w,
            source.h,
            frame.vertical,
          );
          expect(width).toBeGreaterThan(0);
          expect(height).toBeGreaterThan(WINDOW_BAR_HEIGHT);
          expect(width).toBeLessThanOrEqual(frame.w - band.side * 2);
          expect(height).toBeLessThanOrEqual(frame.h - band.top - band.bottom);
        });

        it(`preserves ${sourceName}'s aspect ratio`, () => {
          const { width, height } = fitCard(
            frame.w,
            frame.h,
            source.w,
            source.h,
            frame.vertical,
          );
          const videoHeight = height - WINDOW_BAR_HEIGHT;
          // Within a pixel of the source ratio; fitCard floors both.
          expect(width / videoHeight).toBeCloseTo(source.w / source.h, 1);
        });
      }

      it("leaves the caption block clear of the card", () => {
        const band = bands(frame.vertical);
        const { height } = fitCard(
          frame.w,
          frame.h,
          SOURCES.y509.w,
          SOURCES.y509.h,
          frame.vertical,
        );
        // The card is centred in the band between top and bottom.
        const cardBottom =
          band.top + (frame.h - band.top - band.bottom + height) / 2;
        const captionTop = frame.h - band.captionBottom - band.captionReserve;
        expect(captionTop).toBeGreaterThanOrEqual(cardBottom);
      });
    });
  }

  // The 16:9 box is 1700x730 once the bands are taken, so its own aspect is
  // ~2.33. A source wider than that is limited by width, anything squarer by
  // height -- and it was the height-limited case that used to be clipped.
  it("is limited by width for a source wider than the box", () => {
    const band = bands(false);
    const { width } = fitCard(1920, 1080, 3440, 1000, false);
    expect(width).toBe(1920 - band.side * 2);
  });

  it("is limited by height for a source squarer than the box", () => {
    const band = bands(false);
    const { height } = fitCard(1920, 1080, 2280, 1406, false);
    expect(height).toBe(1080 - band.top - band.bottom);
    expect(height).toBeLessThanOrEqual(1080 - band.top - band.bottom);
  });
});

describe("bands", () => {
  it("reserves three caption lines' worth of space in both orientations", () => {
    // 16:9 captions are 48px at 1.25 line-height, 9:16 are 56px.
    expect(bands(false).captionReserve).toBeGreaterThanOrEqual(48 * 1.25 * 3);
    expect(bands(true).captionReserve).toBeGreaterThanOrEqual(56 * 1.25 * 3);
  });

  it("keeps the caption block inside the bottom band", () => {
    for (const vertical of [false, true]) {
      const band = bands(vertical);
      expect(band.captionBottom + band.captionReserve).toBeLessThanOrEqual(
        band.bottom,
      );
    }
  });
});
