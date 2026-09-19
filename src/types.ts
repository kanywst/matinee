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

export type Chapter = {
  /** Shown in the corner while this section plays. */
  title: string;
  /** Offset into the terminal recording, in ms. */
  startMs: number;
  /** Narration script for this chapter. Read by scripts/tts.py. */
  narration: string;
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
