import { describe, expect, it } from "vitest";
import {
  activeUntil,
  groupIntoLines,
  lineAt,
  MAX_WORDS_PER_LINE,
} from "./captions";
import type { Caption } from "./types";

const w = (text: string, startMs: number, endMs: number): Caption => ({
  text,
  startMs,
  endMs,
});

/** Consecutive words, 200ms each, no gaps. */
const run = (texts: string[], from = 0): Caption[] =>
  texts.map((t, i) => w(t, from + i * 200, from + i * 200 + 200));

describe("groupIntoLines", () => {
  it("returns no lines for no captions", () => {
    expect(groupIntoLines([])).toEqual([]);
  });

  it("never emits an empty line", () => {
    for (const captions of [[], run(["a"]), run(["a", "b", "c"])]) {
      for (const line of groupIntoLines(captions)) {
        expect(line.length).toBeGreaterThan(0);
      }
    }
  });

  it("caps a line at MAX_WORDS_PER_LINE", () => {
    const captions = run(Array.from({ length: 20 }, (_, i) => `w${i}`));
    for (const line of groupIntoLines(captions)) {
      expect(line.length).toBeLessThanOrEqual(MAX_WORDS_PER_LINE);
    }
  });

  it("keeps every word exactly once, in order", () => {
    const captions = run(Array.from({ length: 23 }, (_, i) => `w${i}`));
    const flat = groupIntoLines(captions).flat();
    expect(flat).toEqual(captions);
  });

  it("breaks on a silence of LINE_BREAK_GAP_MS or more", () => {
    const captions = [...run(["a", "b"]), ...run(["c", "d"], 1000)];
    expect(groupIntoLines(captions).map((l) => l.map((c) => c.text))).toEqual([
      ["a", "b"],
      ["c", "d"],
    ]);
  });

  it("does not break on a gap under the threshold", () => {
    const captions = [w("a", 0, 200), w("b", 500, 700)];
    expect(groupIntoLines(captions)).toHaveLength(1);
  });

  // The regression: two chapters' narration meets with no gap at all, because
  // each is synthesised separately and laid down at its own start time.
  it("breaks after sentence-final punctuation even with no gap", () => {
    const captions = [
      w("terminal.", 0, 200),
      w("Search", 200, 400),
      w("jumps", 400, 600),
    ];
    expect(groupIntoLines(captions).map((l) => l.map((c) => c.text))).toEqual([
      ["terminal."],
      ["Search", "jumps"],
    ]);
  });

  it("breaks on Japanese sentence punctuation too", () => {
    const captions = [w("です。", 0, 200), w("次は", 200, 400)];
    expect(groupIntoLines(captions)).toHaveLength(2);
  });

  it("does not break on a mid-sentence comma or ellipsis", () => {
    const captions = [w("Subject,", 0, 200), w("issuer,", 200, 400)];
    expect(groupIntoLines(captions)).toHaveLength(1);
  });
});

describe("activeUntil", () => {
  // The regression: whisper emits startMs === endMs for tightly timed words,
  // and frames only sample every ~33ms, so `now <= endMs` never matched.
  it("extends a zero-length word to the next word's start", () => {
    const line = [w("And", 25680, 25680), w("every", 25680, 26000)];
    expect(activeUntil(line, 0)).toBe(25680);
    const withGap = [w("And", 25680, 25680), w("every", 25900, 26000)];
    expect(activeUntil(withGap, 0)).toBe(25900);
  });

  it("falls back to the word's own end for the last word", () => {
    const line = [w("help.", 1000, 1500)];
    expect(activeUntil(line, 0)).toBe(1500);
  });

  it("never goes backwards when the next word starts early", () => {
    const line = [w("a", 0, 500), w("b", 300, 700)];
    expect(activeUntil(line, 0)).toBe(500);
  });

  it("gives every word in a real line a non-empty active window", () => {
    const line = [
      w("And", 25680, 25680),
      w("every", 25680, 25680),
      w("key", 25680, 25680),
      w("is", 25680, 26010),
    ];
    // Only the trailing run of identical timestamps can be empty; the point is
    // that a word followed by a later one always lights up.
    expect(activeUntil(line, 3)).toBeGreaterThan(line[3].startMs);
  });
});

describe("lineAt", () => {
  const lines = groupIntoLines([...run(["a", "b"]), ...run(["c", "d"], 2000)]);

  it("finds the line covering a moment inside it", () => {
    expect(lineAt(lines, 100)?.[0].text).toBe("a");
    expect(lineAt(lines, 2100)?.[0].text).toBe("c");
  });

  it("returns undefined between lines and before the first", () => {
    expect(lineAt(lines, 1000)).toBeUndefined();
    expect(lineAt(lines, 9999)).toBeUndefined();
  });

  it("is safe on an empty caption list", () => {
    expect(lineAt(groupIntoLines([]), 0)).toBeUndefined();
  });
});
