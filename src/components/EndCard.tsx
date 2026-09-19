import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { font, sans, theme } from "../theme";

export const EndCard: React.FC<{
  repo: string;
  accent: string;
  vertical: boolean;
}> = ({ repo, accent, vertical }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const opacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const rule = interpolate(frame, [6, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const out = interpolate(
    frame,
    [durationInFrames - 8, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.crust,
        justifyContent: "center",
        alignItems: "center",
        opacity: opacity * out,
      }}
    >
      <div
        style={{
          fontFamily: sans,
          fontSize: vertical ? 34 : 32,
          color: theme.overlay1,
          letterSpacing: 6,
          textTransform: "uppercase",
        }}
      >
        Try it
      </div>
      <div
        style={{
          width: interpolate(rule, [0, 1], [0, vertical ? 420 : 560]),
          height: 5,
          backgroundColor: accent,
          borderRadius: 3,
          margin: "34px 0",
        }}
      />
      <div
        style={{
          fontFamily: font,
          fontSize: vertical ? 48 : 60,
          fontWeight: 700,
          color: theme.text,
        }}
      >
        {repo}
      </div>
    </AbsoluteFill>
  );
};
