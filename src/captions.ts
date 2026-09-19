import type { Caption } from "./types";

/**
 * Caption logic, kept out of the component so it can be tested without a
 * renderer. Both rules here exist because of a real defect, so both are
 * covered in captions.test.ts.
 */

export const MAX_WORDS_PER_LINE = 7;
/** A gap this long or longer starts a new line. */
export const LINE_BREAK_GAP_MS = 420;
/** Sentence-final punctuation, Latin and Japanese. */
const SENTENCE_END = /[.!?。！？]$/;

/**
 * Break a word stream into caption lines.
 *
 * Breaking on punctuation as well as on silence matters because each chapter's
 * narration is synthesised separately and laid down at its own start time, so
 * two sentences can meet with no gap at all between them. Without it the tail
 * of one chapter's line shares the screen with the head of the next.
 */
export const groupIntoLines = (captions: Caption[]): Caption[][] => {
  const lines: Caption[][] = [];
  let current: Caption[] = [];

  for (const caption of captions) {
    const previous = current[current.length - 1];
    const gap = previous ? caption.startMs - previous.endMs : 0;
    if (
      current.length >= MAX_WORDS_PER_LINE ||
      (previous && gap >= LINE_BREAK_GAP_MS) ||
      (previous && SENTENCE_END.test(previous.text))
    ) {
      lines.push(current);
      current = [];
    }
    current.push(caption);
  }
  if (current.length > 0) {
    lines.push(current);
  }
  return lines;
};

/**
 * When each word in a line stops being the highlighted one.
 *
 * Derived from the next word's start rather than this word's own end: whisper
 * emits zero-length segments for words it timed tightly, and those would never
 * light up under `now <= endMs` because frames only sample every 33ms.
 */
export const activeUntil = (line: Caption[], index: number): number =>
  Math.max(line[index].endMs, line[index + 1]?.startMs ?? line[index].endMs);

/** The line covering `nowMs`, or undefined between lines. */
export const lineAt = (
  lines: Caption[][],
  nowMs: number,
): Caption[] | undefined =>
  lines.find(
    (l) => nowMs >= l[0].startMs && nowMs <= l[l.length - 1].endMs,
  );
