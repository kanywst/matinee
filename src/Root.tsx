import React from "react";
import { Composition } from "remotion";
import { projects } from "../projects/registry";
import { DemoVideo, totalDurationInFrames } from "./DemoVideo";

const FPS = 30;

/**
 * Two compositions per project from one component: 16:9 for the README and
 * talks, 9:16 for social. Same props, same timings -- only the layout flags
 * differ, which is the whole reason the video is code and not a timeline.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      {projects.map((project) => {
        const duration = totalDurationInFrames(project, FPS);
        return (
          <React.Fragment key={project.id}>
            <Composition
              id={`${project.id}-16x9`}
              component={DemoVideo}
              durationInFrames={duration}
              fps={FPS}
              width={1920}
              height={1080}
              defaultProps={{ project, vertical: false }}
            />
            <Composition
              id={`${project.id}-9x16`}
              component={DemoVideo}
              durationInFrames={duration}
              fps={FPS}
              width={1080}
              height={1920}
              defaultProps={{ project, vertical: true }}
            />
          </React.Fragment>
        );
      })}
    </>
  );
};
