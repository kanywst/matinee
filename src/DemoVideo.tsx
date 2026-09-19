import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useVideoConfig,
} from "remotion";
import type { Project } from "./types";
import { theme } from "./theme";
import { bands } from "./layout";
import { TitleCard } from "./components/TitleCard";
import { TerminalStage } from "./components/TerminalStage";
import { ChapterChip } from "./components/ChapterChip";
import { Captions } from "./components/Captions";
import { EndCard } from "./components/EndCard";

export const TITLE_SECONDS = 3;
export const END_SECONDS = 2.5;
/** How long the title card lingers over the terminal while fading out. */
export const CROSSFADE_FRAMES = 12;

const msToFrames = (ms: number, fps: number) => Math.round((ms / 1000) * fps);

export const totalDurationInFrames = (project: Project, fps: number) =>
  msToFrames(project.terminalDurationMs, fps) +
  Math.round((TITLE_SECONDS + END_SECONDS) * fps);

export const DemoVideo: React.FC<{
  project: Project;
  vertical: boolean;
}> = ({ project, vertical }) => {
  // Read the composition's own fps rather than taking it as a prop: passing it
  // in let the ms->frame maths here diverge from the captions', which read
  // useVideoConfig().
  const { fps } = useVideoConfig();
  const titleFrames = Math.round(TITLE_SECONDS * fps);
  const terminalFrames = msToFrames(project.terminalDurationMs, fps);
  const endFrames = Math.round(END_SECONDS * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.crust }}>
      {/*
        The terminal is mounted before the title so the title paints on top of
        it: the title's out-fade then reveals a terminal that is already there,
        which is a dissolve. Mounted the other way round the title fades to the
        background colour first and the cut reads as a dip to black.
      */}
      <Sequence from={titleFrames} durationInFrames={terminalFrames}>
        <TerminalStage
          src={project.terminalSrc}
          vertical={vertical}
          terminalWidth={project.terminalWidth}
          terminalHeight={project.terminalHeight}
          chapters={project.chapters}
        />

        {project.audioSrc ? <Audio src={staticFile(project.audioSrc)} /> : null}

        {project.chapters.map((chapter, i) => {
          const next = project.chapters[i + 1];
          const endMs = next ? next.startMs : project.terminalDurationMs;
          const from = msToFrames(chapter.startMs, fps);
          const duration = Math.max(1, msToFrames(endMs, fps) - from);
          return (
            <Sequence
              key={chapter.title + chapter.startMs}
              from={from}
              durationInFrames={duration}
            >
              <ChapterChip
                title={chapter.title}
                index={i}
                total={project.chapters.length}
                accent={project.accent}
                vertical={vertical}
              />
            </Sequence>
          );
        })}

        <Captions
          captions={project.captions}
          accent={project.accent}
          vertical={vertical}
          bottom={bands(vertical).captionBottom}
        />
      </Sequence>

      {/* Overlaps the terminal by CROSSFADE_FRAMES; see the note above. */}
      <Sequence durationInFrames={titleFrames + CROSSFADE_FRAMES}>
        <TitleCard
          title={project.title}
          subtitle={project.subtitle}
          repo={project.repo}
          accent={project.accent}
          vertical={vertical}
          brollSrc={project.brollSrc}
        />
      </Sequence>

      <Sequence from={titleFrames + terminalFrames} durationInFrames={endFrames}>
        <EndCard
          repo={project.repo}
          accent={project.accent}
          vertical={vertical}
        />
      </Sequence>
    </AbsoluteFill>
  );
};
