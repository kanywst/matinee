import type { Chapter, Crop } from "./types";

/**
 * Per-chapter zoom, for the vertical cut.
 *
 * A two-pane TUI fitted whole into 9:16 is legible only just: the clip ends up
 * about a third of the frame's height, and the text with it. The fix is to
 * show the part that matters for the chapter being narrated -- the list while
 * navigating, the detail pane while reading it -- which is what a human editor
 * would do with a zoom.
 *
 * Crops are normalised (0..1) fractions of the recording, so they survive a
 * re-record at a different scale. A chapter with no crop shows the whole
 * frame, which is also the default for every chapter in 16:9.
 */

export const FULL_FRAME: Crop = { x: 0, y: 0, w: 1, h: 1 };

/** How long the move between two chapters' crops takes, in ms. */
export const CROP_TWEEN_MS = 400;

export const isFullFrame = (crop: Crop): boolean =>
  crop.x === 0 && crop.y === 0 && crop.w === 1 && crop.h === 1;

/**
 * Clamp a crop into the frame and reject degenerate rectangles.
 *
 * A crop that runs off the edge would otherwise scale the video so the card
 * shows empty space beside it, which reads as a rendering bug rather than as
 * the bad input it is.
 */
export const normaliseCrop = (crop: Crop | undefined): Crop => {
  if (!crop) {
    return FULL_FRAME;
  }
  const w = Math.min(Math.max(crop.w, 0.05), 1);
  const h = Math.min(Math.max(crop.h, 0.05), 1);
  const x = Math.min(Math.max(crop.x, 0), 1 - w);
  const y = Math.min(Math.max(crop.y, 0), 1 - h);
  return { x, y, w, h };
};

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Ease in and out, so the move starts and stops rather than jerking. */
const ease = (t: number) =>
  t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

export const lerpCrop = (from: Crop, to: Crop, t: number): Crop => {
  const e = ease(Math.min(Math.max(t, 0), 1));
  return {
    x: lerp(from.x, to.x, e),
    y: lerp(from.y, to.y, e),
    w: lerp(from.w, to.w, e),
    h: lerp(from.h, to.h, e),
  };
};

/**
 * The crop to show at `nowMs`, tweened from the previous chapter's.
 *
 * Chapters are assumed sorted; build_project.py emits them that way. The tween
 * runs at the start of a chapter rather than before it, so the move lands on
 * the cut the narration is already talking about.
 */
export const cropAt = (chapters: Chapter[], nowMs: number): Crop => {
  if (chapters.length === 0) {
    return FULL_FRAME;
  }
  let index = -1;
  for (let i = 0; i < chapters.length; i++) {
    if (chapters[i].startMs <= nowMs) {
      index = i;
    } else {
      break;
    }
  }
  if (index < 0) {
    return normaliseCrop(chapters[0].crop);
  }

  const target = normaliseCrop(chapters[index].crop);
  if (index === 0) {
    return target;
  }
  const previous = normaliseCrop(chapters[index - 1].crop);
  const elapsed = nowMs - chapters[index].startMs;
  if (elapsed >= CROP_TWEEN_MS) {
    return target;
  }
  return lerpCrop(previous, target, elapsed / CROP_TWEEN_MS);
};

/**
 * Turn a crop into a CSS transform on the video element.
 *
 * The video keeps filling the card; the transform scales it up around the
 * crop's centre so the cropped region is what remains visible. Returned as a
 * scale plus a percentage translate, which is resolution-independent.
 */
export const cropTransform = (crop: Crop) => {
  const scale = 1 / Math.max(crop.w, crop.h);
  // Distance from the crop's centre to the frame's, as a fraction of the frame.
  const dx = 0.5 - (crop.x + crop.w / 2);
  const dy = 0.5 - (crop.y + crop.h / 2);
  return {
    scale,
    translatePercentX: dx * 100,
    translatePercentY: dy * 100,
    css:
      `translate(${(dx * 100).toFixed(3)}%, ${(dy * 100).toFixed(3)}%) ` +
      `scale(${scale.toFixed(4)})`,
  };
};
