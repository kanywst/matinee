/**
 * Catppuccin Mocha, to match `Set Theme "Catppuccin Mocha"` in the repos' VHS
 * tapes. The recorded terminal already carries these colours, so the frame
 * around it has to agree or the composite looks like two screenshots taped
 * together.
 */
export const theme = {
  base: "#1e1e2e",
  mantle: "#181825",
  crust: "#11111b",
  surface0: "#313244",
  surface1: "#45475a",
  overlay1: "#7f849c",
  text: "#cdd6f4",
  subtext0: "#a6adc8",
  mauve: "#cba6f7",
  green: "#a6e3a1",
  peach: "#fab387",
  red: "#f38ba8",
} as const;

/*
 * Both stacks name a CJK fallback explicitly and list a Linux one beside the
 * macOS one: a `lang: ja` project rendered on a machine without Hiragino
 * comes out as tofu, and that path is documented while CI only renders
 * English. Install a Noto CJK font if your narration is not Latin.
 */
export const font =
  '"SF Mono", "JetBrains Mono", "DejaVu Sans Mono", Menlo, ' +
  '"Noto Sans Mono CJK JP", ui-monospace, monospace';

export const sans =
  '-apple-system, "SF Pro Text", "Helvetica Neue", "Noto Sans", ' +
  '"Hiragino Sans", "Noto Sans CJK JP", sans-serif';
