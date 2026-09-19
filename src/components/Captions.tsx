import React, { useMemo } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import type { Caption } from "../types";
import { sans, theme } from "../theme";

/**
 * Karaoke captions: the active word is lifted and tinted, the rest of the line
 * stays dim. Word-level timings come from whisper (scripts/captions.py) --
 * without them there is nothing to highlight and this degrades to a static
 * line, which is why the STT step asks for word granularity.
 */

const MAX_WORDS_PER_LINE = 7;
/** A gap this long or longer starts a new line. */
const LINE_BREAK_GAP_MS = 420;
/** Sentence-final punctuation, Latin and Japanese. */
const SENTENCE_END = /[.!?。！？]$/;

const groupIntoLines = (captions: Caption[]): Caption[][] => {
  const lines: Caption[][] = [];
  let current: Caption[] = [];

  for (const caption of captions) {
    const previous = current[current.length - 1];
    const gap = previous ? caption.startMs - previous.endMs : 0;
    // Break on punctuation as well as on silence. Each chapter's narration is
    // synthesised separately and laid down at its own start time, so two
    // sentences can meet with no gap at all between them -- without this the
    // tail of one chapter's line shares the screen with the head of the next.
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

export const Captions: React.FC<{
  captions: Caption[];
  accent: string;
  vertical: boolean;
  /** Where the caption block sits, in px from the bottom. */
  bottom: number;
}> = ({ captions, accent, vertical, bottom }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowMs = (frame / fps) * 1000;

  const lines = useMemo(() => groupIntoLines(captions), [captions]);

  const line = lines.find(
    (l) => nowMs >= l[0].startMs && nowMs <= l[l.length - 1].endMs,
  );
  if (!line) {
    return null;
  }

  const lineStart = line[0].startMs;
  const opacity = interpolate(nowMs, [lineStart, lineStart + 120], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom,
        left: 0,
        right: 0,
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "center",
        // Wide enough to absorb the active word's scale(1.08): transform does
        // not affect layout, so a long word grows ~13px per side and would
        // otherwise touch its neighbour.
        gap: vertical ? "12px 34px" : "10px 30px",
        padding: `0 ${vertical ? 72 : 200}px`,
        opacity,
      }}
    >
      {line.map((word, i) => {
        // A word is active until the next one starts, not until its own endMs.
        // whisper emits zero-length segments for words it timed tightly (four
        // of them in the y509 narration share a single millisecond), and those
        // would never light up under `nowMs <= endMs`.
        const nextStart = line[i + 1]?.startMs ?? word.endMs;
        const activeUntil = Math.max(word.endMs, nextStart);
        const active = nowMs >= word.startMs && nowMs < activeUntil;
        const spoken = nowMs >= activeUntil;
        return (
          <span
            key={`${word.startMs}-${i}`}
            style={{
              fontFamily: sans,
              fontSize: vertical ? 56 : 48,
              fontWeight: 800,
              color: active ? accent : spoken ? theme.text : theme.overlay1,
              transform: `scale(${active ? 1.08 : 1})`,
              textShadow: "0 3px 14px rgba(0,0,0,0.85)",
              transition: "none",
              lineHeight: 1.25,
            }}
          >
            {word.text}
          </span>
        );
      })}
    </div>
  );
};
