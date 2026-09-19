import React from "react";
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { theme } from "../theme";
import { fitCard, WINDOW_BAR_HEIGHT } from "../layout";

/**
 * The VHS recording, framed.
 *
 * The card is sized explicitly from the recording's own pixel dimensions (see
 * src/layout.ts) rather than left to flexbox, so the whole clip is always
 * visible. The video is not allowed to shrink: `overflow: hidden` on the
 * rounded card would silently crop the bottom rows, which is where a TUI keeps
 * its status bar.
 */
export const TerminalStage: React.FC<{
  src: string;
  vertical: boolean;
  terminalWidth: number;
  terminalHeight: number;
}> = ({ src, vertical, terminalWidth, terminalHeight }) => {
  const frame = useCurrentFrame();
  const { width: frameWidth, height: frameHeight } = useVideoConfig();

  const { width, height, band } = fitCard(
    frameWidth,
    frameHeight,
    terminalWidth,
    terminalHeight,
    vertical,
  );

  // Scale only, no fade: the title card sits on top and dissolves away to
  // reveal this. Fading both at once puts a dip between them.
  const enter = interpolate(frame, [0, 14], [0.965, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.base,
        justifyContent: "center",
        alignItems: "center",
        // Centre the card inside the band left over by the chip and captions,
        // not inside the whole frame.
        paddingTop: band.top,
        paddingBottom: band.bottom,
      }}
    >
      <div
        style={{
          width,
          height,
          flexShrink: 0,
          borderRadius: 14,
          overflow: "hidden",
          boxShadow: "0 40px 120px rgba(0,0,0,0.6)",
          transform: `scale(${enter})`,
          lineHeight: 0,
        }}
      >
        {/*
          VHS draws its window bar in the ffmpeg stage that record.sh bypasses,
          so it is redrawn here -- themed from theme.ts rather than from the
          tape, which means every project's video matches even when the repos'
          tapes disagree about chrome.
        */}
        <div
          style={{
            height: WINDOW_BAR_HEIGHT,
            backgroundColor: theme.surface0,
            display: "flex",
            alignItems: "center",
            gap: 12,
            paddingLeft: 22,
          }}
        >
          {["#f38ba8", "#f9e2af", "#a6e3a1"].map((c) => (
            <div
              key={c}
              style={{
                width: 16,
                height: 16,
                borderRadius: 8,
                backgroundColor: c,
              }}
            />
          ))}
        </div>
        <OffthreadVideo
          src={staticFile(src)}
          muted
          style={{
            width: "100%",
            height: height - WINDOW_BAR_HEIGHT,
            display: "block",
            objectFit: "contain",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
