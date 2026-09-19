import type { Project } from "../src/types";
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
  y509 as Project,
  prpr as Project,
  brtc as Project,
];
