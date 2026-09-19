import React, { useMemo } from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import type { Caption } from "../types";
import { activeUntil, groupIntoLines, lineAt } from "../captions";
import { sans, theme } from "../theme";

/**
 * Karaoke captions: the active word is lifted and tinted, the rest of the line
 * stays dim. Word-level timings come from whisper (scripts/captions.py) --
 * without them there is nothing to highlight, which is why the STT step asks
 * for word granularity.
 *
 * The line-breaking and highlight-window rules live in ../captions.ts so they
 * can be tested without a renderer.
 */
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
  const line = lineAt(lines, nowMs);
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
        const until = activeUntil(line, i);
        const active = nowMs >= word.startMs && nowMs < until;
        const spoken = nowMs >= until;
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
