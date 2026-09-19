import React from "react";
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { font, sans, theme } from "../theme";

export const TitleCard: React.FC<{
  title: string;
  subtitle: string;
  repo: string;
  accent: string;
  vertical: boolean;
  brollSrc?: string;
}> = ({ title, subtitle, repo, accent, vertical, brollSrc }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200 } });
  // Fade the whole card out over the last 12 frames so the cut into the
  // terminal is a dissolve rather than a hard switch.
  const out = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: theme.crust, opacity: out }}>
      {brollSrc ? (
        <AbsoluteFill style={{ opacity: 0.28 }}>
          <OffthreadVideo
            src={staticFile(brollSrc)}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      ) : null}

      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "flex-start",
          padding: vertical ? 90 : 160,
          transform: `translateY(${interpolate(enter, [0, 1], [24, 0])}px)`,
          opacity: enter,
        }}
      >
        <div
          style={{
            width: 96,
            height: 6,
            backgroundColor: accent,
            borderRadius: 3,
            marginBottom: 40,
          }}
        />
        <div
          style={{
            fontFamily: font,
            fontSize: vertical ? 104 : 120,
            fontWeight: 700,
            color: theme.text,
            letterSpacing: -2,
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontFamily: sans,
            fontSize: vertical ? 40 : 44,
            color: theme.subtext0,
            marginTop: 28,
            lineHeight: 1.45,
            maxWidth: vertical ? 880 : 1300,
          }}
        >
          {subtitle}
        </div>
        <div
          style={{
            fontFamily: font,
            fontSize: vertical ? 30 : 32,
            color: theme.overlay1,
            marginTop: 48,
          }}
        >
          {repo}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
