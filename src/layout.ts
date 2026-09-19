/**
 * Where each band of the frame lives.
 *
 * The terminal card is fitted into what is left after the chapter chip and the
 * caption block have taken their space -- by height as well as width. Letting
 * flexbox shrink the card instead clipped 25% off the bottom of the recording
 * in 16:9, because `overflow: hidden` on a rounded card hides exactly the rows
 * a dense TUI puts its status bar in.
 */

export const WINDOW_BAR_HEIGHT = 52;

/**
 * Half-width of a fade-in/fade-out pair that fits inside `durationInFrames`.
 *
 * Remotion's `interpolate` requires a strictly increasing input range, so a
 * fade window of `f` frames at each end needs `f < d - f`. A fixed 10 crashed
 * the whole render on a short chapter; clamping to `floor(d / 2)` still
 * crashed on every even `d` in 4..20, because there `f === d - f`. Hence
 * `(d - 1) / 2`, and a caller that skips the fade entirely below 4 frames.
 */
export const fadeFrames = (durationInFrames: number): number =>
  Math.max(1, Math.min(10, Math.floor((durationInFrames - 1) / 2)));

type Band = {
  /** Space reserved above the card for the chapter chip. */
  top: number;
  /** Space reserved below the card for captions. */
  bottom: number;
  /** Side gutter. */
  side: number;
  /** Distance from the frame bottom to the caption block. */
  captionBottom: number;
  /** Caption block height to keep clear, enough for three wrapped lines. */
  captionReserve: number;
};

/**
 * The bottom band is sized for three wrapped caption lines, not the usual one
 * or two: MAX_WORDS_PER_LINE long words do wrap that far, and a caption that
 * grows upward into the card lands on exactly the status bar a terminal demo
 * needs readable. Subtitles normally overlay the picture; here they must not.
 */
export const bands = (vertical: boolean): Band =>
  vertical
    ? { top: 280, bottom: 400, side: 20, captionBottom: 150, captionReserve: 230 }
    : { top: 110, bottom: 240, side: 110, captionBottom: 40, captionReserve: 200 };

/**
 * Largest card that fits the available box while preserving the recording's
 * aspect ratio. Returns the outer card size, window bar included.
 */
export const fitCard = (
  frameWidth: number,
  frameHeight: number,
  terminalWidth: number,
  terminalHeight: number,
  vertical: boolean,
) => {
  const band = bands(vertical);
  const availableWidth = frameWidth - band.side * 2;
  const availableHeight = frameHeight - band.top - band.bottom;

  const aspect = terminalWidth / terminalHeight;
  // Fit by width, then pull back if the resulting height (plus the bar we draw
  // above the video) would not fit.
  let width = availableWidth;
  let height = width / aspect + WINDOW_BAR_HEIGHT;
  if (height > availableHeight) {
    height = availableHeight;
    width = (height - WINDOW_BAR_HEIGHT) * aspect;
  }
  return { width: Math.floor(width), height: Math.floor(height), band };
};
