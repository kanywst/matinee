import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { font, theme } from "../theme";
import { fadeFrames } from "../layout";

/**
 * The "you are here" label. Mounted inside a <Sequence> per chapter, so it
 * only has to animate its own 0..n window.
 */
export const ChapterChip: React.FC<{
  title: string;
  index: number;
  total: number;
  accent: string;
  vertical: boolean;
}> = ({ title, index, total, accent, vertical }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // interpolate() requires a strictly increasing input range, so the fade
  // window has to shrink with the chapter -- see fadeFrames for why it is
  // (d - 1) / 2 and not d / 2. A tape with a quick section produces these,
  // and so does DemoVideo's Math.max(1, …) on chapters that are out of order.
  const fade = fadeFrames(durationInFrames);
  const opacity =
    durationInFrames < 4
      ? 1
      : interpolate(
          frame,
          [0, fade, durationInFrames - fade, durationInFrames],
          [0, 1, 1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        );
  const slide = interpolate(frame, [0, Math.max(1, Math.min(14, durationInFrames))], [-18, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        // Inside the band layout.ts reserves above the card, so the chip and
        // the recording never share pixels.
        top: vertical ? 170 : 38,
        left: vertical ? 64 : 80,
        display: "flex",
        alignItems: "center",
        gap: 18,
        opacity,
        transform: `translateX(${slide}px)`,
      }}
    >
      <div
        style={{
          fontFamily: font,
          fontSize: 26,
          fontWeight: 700,
          color: theme.crust,
          backgroundColor: accent,
          borderRadius: 8,
          padding: "8px 16px",
        }}
      >
        {String(index + 1).padStart(2, "0")}/{String(total).padStart(2, "0")}
      </div>
      <div
        style={{
          fontFamily: font,
          fontSize: 34,
          color: theme.text,
          backgroundColor: "rgba(17,17,27,0.82)",
          borderRadius: 8,
          padding: "8px 20px",
        }}
      >
        {title}
      </div>
    </div>
  );
};
