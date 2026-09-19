#!/usr/bin/env bash
#
# Step 1: turn a repo's existing VHS tape into an mp4 for Remotion.
#
#   scripts/record.sh y509 ~/y509 demo.tape [scale]
#
# The repos already ship .tape files that render a gif for the README. This
# reuses them verbatim rather than maintaining a second script: it copies the
# tape, redirects the output to a PNG frame directory, and encodes those frames
# with our own ffmpeg.
#
# Why frames and not `Output demo.mp4`:
#   VHS v0.12.0 shells out to ffmpeg for every encoded output, and against
#   ffmpeg 9.x that call fails silently -- it logs "Creating ...mp4" and writes
#   nothing, with the same result for gif. Frame output is written by VHS
#   itself with no ffmpeg involved, so it is the one path that still works.
#   Encoding here also means we pick the codec and CRF instead of inheriting
#   VHS's.
#
# What this loses, and where it comes back:
#   VHS adds the window bar, padding and rounded corners in that same ffmpeg
#   stage, so the raw frames are the bare terminal grid. TerminalStage.tsx
#   draws that chrome instead, which keeps it consistent with the rest of the
#   composition and themeable from theme.ts.
#
# Scaling multiplies Width, Height, FontSize, Padding and WindowBarSize
# together. VHS derives the terminal grid from Width/FontSize, so scaling them
# by the same factor keeps the exact same column/row layout -- change only one
# and the TUI reflows and the tape's Sleep timings stop lining up.

set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <project-id> <repo-dir> <tape-path> [scale]" >&2
  exit 64
fi

PROJECT_ID="$1"
REPO_DIR="$(cd "$2" && pwd)"
TAPE_REL="$3"
SCALE="${4:-2}"

PIPELINE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$PIPELINE_DIR/public/projects/$PROJECT_ID"
OUT_MP4="$OUT_DIR/terminal.mp4"
TAPE_PATH="$REPO_DIR/$TAPE_REL"

[ -f "$TAPE_PATH" ] || { echo "error: tape not found: $TAPE_PATH" >&2; exit 66; }
command -v vhs >/dev/null || { echo "error: vhs not installed (brew install vhs)" >&2; exit 69; }
command -v ffmpeg >/dev/null || { echo "error: ffmpeg not installed (brew install ffmpeg)" >&2; exit 69; }

mkdir -p "$OUT_DIR"

WORK="$(mktemp -d -t "vhs-${PROJECT_ID}")"
trap 'rm -rf "$WORK"' EXIT
FRAMES="$WORK/frames"
TMP_TAPE="$WORK/recording.tape"

# VHS's default framerate; a tape may override it with `Set Framerate`.
FRAMERATE="$(awk '
  /^[[:space:]]*Set[[:space:]]+Framerate[[:space:]]+[0-9.]+/ { print $3; found = 1 }
  END { if (!found) print 50 }
' "$TAPE_PATH" | tail -1)"

# Absolute, quoted output path: VHS lexes a bare absolute path as a sequence of
# commands and fails to parse.
# Fields, not a whole-line regex: awk's default splitting already strips
# leading blanks, so $1/$2/$3 are right for an indented `  Set Width 1200`.
# Matching the raw line and then split()ing it produced an empty leading field
# on those lines and rewrote them to `Set Set 0`. The NF test accepts a
# trailing `# comment`, which VHS allows and which otherwise left that line
# unscaled while its neighbours doubled -- reflowing the grid, which is exactly
# the failure the note above warns about.
awk -v frames="$FRAMES" -v scale="$SCALE" '
  # Drop every existing Output; we emit exactly one of our own.
  $1 == "Output" { next }
  {
    if (scale != 1 && $1 == "Set" \
        && $2 ~ /^(Width|Height|FontSize|Padding|WindowBarSize)$/ \
        && $3 ~ /^[0-9]+$/ && (NF == 3 || $4 ~ /^#/)) {
      printf "Set %s %d\n", $2, $3 * scale
      next
    }
    print
  }
  END { printf "Output \"%s/\"\n", frames }
' "$TAPE_PATH" > "$TMP_TAPE"

echo "==> recording $PROJECT_ID (scale ${SCALE}x, ${FRAMERATE}fps)"
# The tape's own commands (go build, go run) assume the repo root.
( cd "$REPO_DIR" && vhs "$TMP_TAPE" )

FRAME_COUNT="$(find "$FRAMES" -name 'frame-text-*.png' | wc -l | tr -d ' ')"
[ "$FRAME_COUNT" -gt 0 ] || { echo "error: vhs produced no frames" >&2; exit 70; }
echo "==> $FRAME_COUNT frames"

# VHS writes the terminal grid and the cursor as separate layers; overlay them
# in the order VHS's own pipeline does. The pad forces even dimensions, which
# yuv420p requires and an arbitrary tape size will not always give.
echo "==> encoding"
ffmpeg -y -v error \
  -framerate "$FRAMERATE" -i "$FRAMES/frame-text-%05d.png" \
  -framerate "$FRAMERATE" -i "$FRAMES/frame-cursor-%05d.png" \
  -filter_complex "[0][1]overlay,pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p" \
  -c:v libx264 -crf 18 -preset slow -movflags +faststart \
  "$OUT_MP4"

DURATION_MS="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT_MP4" \
  | awk '{ printf "%d", $1 * 1000 }')"

echo "==> wrote $OUT_MP4"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate \
  -of default=noprint_wrappers=1 "$OUT_MP4"
echo "==> terminalDurationMs: $DURATION_MS"
