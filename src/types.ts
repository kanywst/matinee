/**
 * The input contract for one demo video.
 *
 * Everything the render needs comes from a project.json next to the repo's
 * VHS tape. Timings are in milliseconds against the recorded terminal clip,
 * because that is the unit VHS and whisper both speak.
 */

export type Caption = {
  text: string;
  startMs: number;
  endMs: number;
};

/**
 * A region of the recording, as fractions of its width and height.
 *
 * Normalised rather than in pixels so it survives a re-record at a different
 * scale: `record.sh` doubles the tape's dimensions by default, and a tape may
 * be re-recorded at another factor.
 */
export type Crop = {
  x: number;
  y: number;
  w: number;
  h: number;
};

export type Chapter = {
  /** Shown in the corner while this section plays. */
  title: string;
  /** Offset into the terminal recording, in ms. */
  startMs: number;
  /** Narration script for this chapter. Read by scripts/tts.py. */
  narration: string;
  /**
   * Optional zoom for the 9:16 cut, from script.yaml. Ignored in 16:9, where
   * the whole recording already fits legibly.
   */
  crop?: Crop;
};

export type Project = {
  /** Slug; must match the directory under public/projects/. */
  id: string;
  title: string;
  subtitle: string;
  repo: string;
  /** Hex accent used for the title rule, chapter chip and caption highlight. */
  accent: string;
  /** Duration of the recorded terminal clip in ms. */
  terminalDurationMs: number;
  /**
   * Pixel size of the recorded clip. TerminalStage fits by height as well as
   * width, which it cannot do from CSS alone: the aspect comes from the tape's
   * Set Width/Height and differs per repo.
   */
  terminalWidth: number;
  terminalHeight: number;
  chapters: Chapter[];
  /** Relative to public/. Written by scripts/record.sh. */
  terminalSrc: string;
  /** Relative to public/. Written by scripts/tts.py. Optional: silent if absent. */
  audioSrc?: string;
  /** Relative to public/. Written by scripts/captions.py. */
  captions: Caption[];
  /** Optional AI-generated b-roll behind the title card. See scripts/broll.py. */
  brollSrc?: string;
};
