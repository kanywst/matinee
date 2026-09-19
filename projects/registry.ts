import type { Project } from "../src/types";
import hello from "./hello/project.json";
import y509 from "./y509/project.json";
import prpr from "./prpr/project.json";
import brtc from "./brtc/project.json";

/**
 * Every project that gets compositions in the Remotion studio.
 *
 * Adding a repo is one import plus one array entry. The JSON is generated --
 * scripts/build_project.py writes it from script.yaml plus whatever the
 * record/tts/captions steps produced -- so it is checked in but not hand
 * edited.
 */
export const projects: Project[] = [
  // First, so it is what `remotion studio` opens on: it is the only example
  // whose recording is checked in, so it works from a bare clone.
  hello as Project,
  y509 as Project,
  prpr as Project,
  brtc as Project,
];
