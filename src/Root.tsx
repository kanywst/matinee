import React from "react";
import { Composition } from "remotion";
import { projects } from "../projects/registry";
import { DemoVideo, totalDurationInFrames } from "./DemoVideo";
import type { Project } from "./types";

const FPS = 30;

/**
 * Two compositions per project from one component: 16:9 for the README and
 * talks, 9:16 for social. Same props, same timings -- only the layout flags
 * differ, which is the whole reason the video is code and not a timeline.
 *
 * The duration is derived from the props rather than fixed at build time, so
 * rendering any composition with `--props=<another project.json>` produces a
 * clip the length of *that* recording. CI relies on it to render a four-second
 * smoke project without registering a composition for it.
 */
const withDuration = ({ props }: { props: { project: Project } }) => ({
  durationInFrames: totalDurationInFrames(props.project, FPS),
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {projects.map((project) => (
        <React.Fragment key={project.id}>
          <Composition
            id={`${project.id}-16x9`}
            component={DemoVideo}
            durationInFrames={totalDurationInFrames(project, FPS)}
            calculateMetadata={withDuration}
            fps={FPS}
            width={1920}
            height={1080}
            defaultProps={{ project, vertical: false }}
          />
          <Composition
            id={`${project.id}-9x16`}
            component={DemoVideo}
            durationInFrames={totalDurationInFrames(project, FPS)}
            calculateMetadata={withDuration}
            fps={FPS}
            width={1080}
            height={1920}
            defaultProps={{ project, vertical: true }}
          />
        </React.Fragment>
      ))}
    </>
  );
};
