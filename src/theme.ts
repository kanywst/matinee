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

export const font =
  '"SF Mono", "JetBrains Mono", "Menlo", ui-monospace, monospace';

export const sans =
  '-apple-system, "SF Pro Text", "Helvetica Neue", "Hiragino Sans", sans-serif';
